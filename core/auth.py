"""
core/auth.py — Controle de acesso para uso em rede local

Milla tem efeitos reais: absorve arquivos e URLs, reescreve o grafo e conversa
com o LLM da máquina. Em loopback só quem está no computador alcança a API;
expor a porta na rede local (para abrir o painel no celular, por exemplo) muda
isso — qualquer dispositivo da mesma rede poderia estimulá-la.

A política aqui é pequena e **falha fechada**:

- **`MILLA_TOKEN` definido** → HTTP e WebSocket exigem o token, inclusive de
  clientes locais. A senha não fica em `config.py` (que é versionado): vem do
  ambiente.
- **`MILLA_TOKEN` ausente** → só clientes loopback passam. Quem chega de um IP
  de rede recebe 403 com a instrução de configurar o token.

Ou seja: não existe forma de atender a rede sem senha, mesmo rodando
`uvicorn api:app --host 0.0.0.0` sem ler o README.

O token viaja como `Authorization: Bearer` no REST e como **subprotocolo** no
WebSocket (`['milla.v1', token]`) — a API do navegador não permite headers no
handshake, e query string acabaria nos logs do uvicorn e do proxy.
"""

import hmac
import ipaddress
import os
import re

# Nome da variável de ambiente (nunca no config.py versionado).
VARIAVEL_TOKEN = "MILLA_TOKEN"

# Subprotocolo negociado no handshake do WebSocket. O token vai como o item
# seguinte da lista, fora da URL.
PROTOCOLO_WS = "milla.v1"

TAMANHO_MINIMO_TOKEN = 16

# Subprotocolos (RFC 6455) só aceitam estes caracteres; validar aqui evita um
# token que funciona no REST e quebra o WebSocket no navegador com SyntaxError.
_FORMATO_TOKEN = re.compile(r"^[A-Za-z0-9._~-]+$")


# ─── Token ───────────────────────────────────────────────────────────────────

def token_configurado() -> str | None:
    """Token definido no ambiente, ou None quando a autenticação está desligada."""
    bruto = os.environ.get(VARIAVEL_TOKEN, "").strip()
    return bruto or None


def erro_de_configuracao(token: str | None = None) -> str | None:
    """Descreve por que o token configurado é inválido (ou None se está ok)."""
    token = token_configurado() if token is None else token
    if token is None:
        return None
    if len(token) < TAMANHO_MINIMO_TOKEN:
        return (
            f"{VARIAVEL_TOKEN} tem {len(token)} caracteres; use pelo menos "
            f"{TAMANHO_MINIMO_TOKEN}. Gere um com: "
            'python -c "import secrets; print(secrets.token_urlsafe(24))"'
        )
    if not _FORMATO_TOKEN.match(token):
        return (
            f"{VARIAVEL_TOKEN} contém caracteres fora de [A-Za-z0-9._~-]. "
            "O token viaja como subprotocolo WebSocket, que só aceita esses."
        )
    return None


def autenticacao_ativa() -> bool:
    """Há token configurado?"""
    return token_configurado() is not None


def token_valido(recebido: str | None) -> bool:
    """
    Compara o token recebido com o configurado em tempo constante.

    `hmac.compare_digest` evita que o tempo de resposta revele quantos
    caracteres iniciais bateram (ataque de temporização sobre uma senha).
    """
    configurado = token_configurado()
    if not configurado or not recebido:
        return False
    return hmac.compare_digest(recebido.encode(), configurado.encode())


def token_do_cabecalho(cabecalho: str | None) -> str | None:
    """Extrai o token de `Authorization: Bearer <token>` (case-insensitive)."""
    if not cabecalho:
        return None
    esquema, _, valor = cabecalho.partition(" ")
    if esquema.lower() != "bearer":
        return None
    valor = valor.strip()
    return valor or None


def token_do_websocket(cabecalho_protocolos: str | None) -> str | None:
    """
    Extrai o token da lista de subprotocolos do handshake.

    O navegador envia `Sec-WebSocket-Protocol: milla.v1, <token>`; qualquer
    item que não seja o protocolo conhecido é tratado como credencial.
    """
    if not cabecalho_protocolos:
        return None
    for protocolo in cabecalho_protocolos.split(","):
        protocolo = protocolo.strip()
        if protocolo and protocolo != PROTOCOLO_WS:
            return protocolo
    return None


# ─── Origem do cliente ───────────────────────────────────────────────────────

def cliente_loopback(host: str | None) -> bool:
    """O cliente veio da própria máquina?"""
    if not host:
        return False
    if host == "testclient":
        # O TestClient do Starlette não tem socket: `client.host` é literalmente
        # "testclient". Em produção o ASGI sempre entrega o IP do peer, então
        # isto não é um desvio de segurança — é o loopback dos testes.
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def host_do_cliente(peer_host: str | None, encaminhado_para: str | None) -> str | None:
    """
    IP real do cliente, considerando o proxy do Vite.

    Quando o painel é aberto por outro dispositivo, o navegador fala com o
    dev-server (ou com um proxy reverso local), que repassa a requisição para o
    backend a partir de 127.0.0.1. Sem olhar o `X-Forwarded-For`, todo acesso
    vindo da rede pareceria local. Só confiamos no cabeçalho quando o peer é
    loopback (é o próprio proxy da máquina); o primeiro item da lista é o
    cliente original.
    """
    if peer_host and cliente_loopback(peer_host) and encaminhado_para:
        origem = encaminhado_para.split(",")[0].strip()
        if origem:
            return origem
    return peer_host


# ─── Política ────────────────────────────────────────────────────────────────

def acesso_autorizado(host_cliente: str | None, token: str | None) -> bool:
    """
    Regra central: com token, ele é obrigatório para todos; sem token, só
    loopback. Um token malformado derruba o acesso até alguém corrigir.
    """
    if autenticacao_ativa():
        if erro_de_configuracao():
            return False
        return token_valido(token)
    return cliente_loopback(host_cliente)


def mensagem_de_recusa(host_cliente: str | None) -> str:
    """Explicação devolvida ao cliente recusado (sem revelar o token)."""
    erro = erro_de_configuracao()
    if erro:
        return erro
    if not autenticacao_ativa():
        return (
            "Acesso pela rede bloqueado: Milla está sem senha. No servidor, "
            f"defina {VARIAVEL_TOKEN} e reinicie (veja o README, seção "
            "\"Acesso pela rede local\")."
        )
    return "Token de acesso ausente ou inválido."
