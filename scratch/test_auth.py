# scratch/test_auth.py
# Testes do controle de acesso: política de token/loopback, parsing do
# cabeçalho e do subprotocolo WebSocket, e o comportamento real dos endpoints
# quando MILLA_TOKEN está definido.

import os
import sys

import pytest

# Adiciona o diretório raiz ao path para poder importar api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import api
from core import auth

TOKEN = "milla-token-de-teste-1234567890"


@pytest.fixture(autouse=True)
def sem_token(monkeypatch):
    """Cada teste começa no modo local (sem autenticação)."""
    monkeypatch.delenv(auth.VARIAVEL_TOKEN, raising=False)


# ─── Política: token ausente → só loopback ───────────────────────────────────

@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "127.0.0.2", "testclient"])
def test_sem_token_aceita_clientes_locais(host):
    assert auth.acesso_autorizado(host, None) is True


@pytest.mark.parametrize("host", ["192.168.0.10", "10.1.2.3", "8.8.8.8", "::ffff:192.168.0.10"])
def test_sem_token_recusa_qualquer_ip_de_rede(host):
    assert auth.acesso_autorizado(host, None) is False


def test_sem_token_recusa_cliente_sem_endereco():
    assert auth.acesso_autorizado(None, None) is False
    assert auth.acesso_autorizado("host-que-nao-e-ip", None) is False


def test_sem_token_nao_ha_autenticacao_ativa():
    assert auth.autenticacao_ativa() is False
    assert auth.erro_de_configuracao() is None


# ─── Política: token definido → obrigatório para todos ───────────────────────

def test_com_token_exige_token_ate_no_loopback(monkeypatch):
    monkeypatch.setenv(auth.VARIAVEL_TOKEN, TOKEN)

    assert auth.autenticacao_ativa() is True
    assert auth.acesso_autorizado("127.0.0.1", None) is False
    assert auth.acesso_autorizado("127.0.0.1", "outro-token-qualquer-1234") is False
    assert auth.acesso_autorizado("127.0.0.1", TOKEN) is True
    assert auth.acesso_autorizado("192.168.0.10", TOKEN) is True


def test_token_curto_e_recusado_com_instrucao_de_geracao(monkeypatch):
    monkeypatch.setenv(auth.VARIAVEL_TOKEN, "curto")

    erro = auth.erro_de_configuracao()
    assert erro is not None
    assert "16" in erro
    assert "secrets.token_urlsafe" in erro
    # Falha fechada: nem o token certo (que é o curto) libera o acesso.
    assert auth.acesso_autorizado("127.0.0.1", "curto") is False


def test_token_com_caractere_invalido_para_subprotocolo_e_recusado(monkeypatch):
    monkeypatch.setenv(auth.VARIAVEL_TOKEN, "token com espaço e 1234567890")

    erro = auth.erro_de_configuracao()
    assert erro is not None
    assert "subprotocolo" in erro


# ─── Parsing das credenciais ─────────────────────────────────────────────────

@pytest.mark.parametrize(
    "cabecalho",
    ["Bearer " + TOKEN, "bearer " + TOKEN, "BEARER   " + TOKEN],
)
def test_cabecalho_bearer_aceita_qualquer_caixa(cabecalho):
    assert auth.token_do_cabecalho(cabecalho) == TOKEN


@pytest.mark.parametrize("cabecalho", [None, "", "Basic abc", "Bearer", "Bearer   "])
def test_cabecalho_sem_bearer_nao_vira_token(cabecalho):
    assert auth.token_do_cabecalho(cabecalho) is None


def test_token_do_websocket_vem_da_lista_de_subprotocolos():
    assert auth.token_do_websocket("milla.v1, " + TOKEN) == TOKEN
    assert auth.token_do_websocket(TOKEN) == TOKEN


@pytest.mark.parametrize("protocolos", [None, "", "milla.v1", " milla.v1 , "])
def test_websocket_sem_token_nao_inventa_credencial(protocolos):
    assert auth.token_do_websocket(protocolos) is None


# ─── X-Forwarded-For do proxy local ──────────────────────────────────────────

def test_xff_de_proxy_local_revela_o_cliente_real():
    assert auth.host_do_cliente("127.0.0.1", "203.0.113.7, 127.0.0.1") == "203.0.113.7"
    assert auth.host_do_cliente("::1", "192.168.0.50") == "192.168.0.50"


def test_xff_de_peer_remoto_e_ignorado():
    """Só o proxy local é confiável; um cliente da rede não escolhe o próprio IP."""
    assert auth.host_do_cliente("192.168.0.99", "127.0.0.1") == "192.168.0.99"
    assert auth.host_do_cliente("192.168.0.99", None) == "192.168.0.99"


# ─── Endpoints REST ──────────────────────────────────────────────────────────

def test_status_sem_token_libera_o_painel():
    client = TestClient(api.app)
    corpo = client.get("/api/auth/status").json()

    assert corpo["autenticacao_ativa"] is False
    assert corpo["autenticado"] is True
    assert "erro" not in corpo


def test_com_token_api_recusa_requisicao_sem_bearer(monkeypatch):
    monkeypatch.setenv(auth.VARIAVEL_TOKEN, TOKEN)
    client = TestClient(api.app)

    sem_token = client.get("/api/estado")
    assert sem_token.status_code == 401
    assert sem_token.headers["www-authenticate"] == "Bearer"

    token_errado = client.get("/api/estado", headers={"Authorization": "Bearer errado"})
    assert token_errado.status_code == 401

    autorizado = client.get("/api/estado", headers={"Authorization": f"Bearer {TOKEN}"})
    assert autorizado.status_code == 200
    assert autorizado.json()["nos_no_grafo"] >= 7


def test_status_com_token_diz_o_motivo_da_recusa(monkeypatch):
    monkeypatch.setenv(auth.VARIAVEL_TOKEN, TOKEN)
    client = TestClient(api.app)

    anonimo = client.get("/api/auth/status").json()
    assert anonimo["autenticacao_ativa"] is True
    assert anonimo["autenticado"] is False
    assert anonimo["erro"] == "Token de acesso ausente ou inválido."

    autenticado = client.get(
        "/api/auth/status", headers={"Authorization": f"Bearer {TOKEN}"}
    ).json()
    assert autenticado["autenticado"] is True
    assert "erro" not in autenticado


def test_status_explica_token_mal_configurado(monkeypatch):
    """Token curto derruba o acesso e o painel recebe o motivo, não um 401 mudo."""
    monkeypatch.setenv(auth.VARIAVEL_TOKEN, "curto")
    client = TestClient(api.app)

    corpo = client.get("/api/auth/status").json()

    assert corpo["autenticacao_ativa"] is True
    assert corpo["autenticado"] is False
    assert "16" in corpo["erro"]


def test_cliente_de_rede_via_proxy_local_e_barrado_sem_token():
    """
    O proxy do Vite fala com o backend a partir de 127.0.0.1; sem olhar o
    X-Forwarded-For, o celular na rede pareceria local.
    """
    client = TestClient(api.app, client=("127.0.0.1", 51234))
    resp = client.get("/api/estado", headers={"X-Forwarded-For": "192.168.0.50"})

    assert resp.status_code == 403
    assert "MILLA_TOKEN" in resp.json()["erro"]


def test_preflight_do_cors_nao_e_barrado(monkeypatch):
    monkeypatch.setenv(auth.VARIAVEL_TOKEN, TOKEN)
    client = TestClient(api.app)

    resp = client.options(
        "/api/absorver-url",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert resp.status_code == 200


def test_documentacao_continua_publica(monkeypatch):
    monkeypatch.setenv(auth.VARIAVEL_TOKEN, TOKEN)
    client = TestClient(api.app)

    assert client.get("/openapi.json").status_code == 200


# ─── WebSocket ───────────────────────────────────────────────────────────────

def test_websocket_recusa_handshake_sem_token(monkeypatch):
    monkeypatch.setenv(auth.VARIAVEL_TOKEN, TOKEN)
    client = TestClient(api.app)

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/consciencia"):
            pass


def test_websocket_aceita_token_como_subprotocolo(monkeypatch):
    monkeypatch.setenv(auth.VARIAVEL_TOKEN, TOKEN)
    client = TestClient(api.app)

    with client.websocket_connect(
        "/ws/consciencia", subprotocols=[auth.PROTOCOLO_WS, TOKEN]
    ) as ws:
        # O primeiro frame de toda conexão é a carga inicial do grafo.
        assert ws.receive_json()["type"] == "grafo_update"


def test_websocket_local_funciona_sem_token():
    client = TestClient(api.app)

    with client.websocket_connect("/ws/consciencia") as ws:
        assert ws.receive_json()["type"] == "grafo_update"
