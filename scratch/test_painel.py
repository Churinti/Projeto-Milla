"""
test_painel.py — o painel compilado servido pelo próprio FastAPI

No contêiner não existe Vite: `frontend/dist` é entregue pelo backend, o que
deixa painel, REST e WebSocket na mesma origem. Estes testes dependem do build;
sem `dist` (a CI de backend não compila o frontend) são pulados, porque o que
está sob teste é justamente o artefato compilado.
"""

import pytest
from fastapi.testclient import TestClient

import api

pytestmark = pytest.mark.skipif(
    not api.PAINEL_DISPONIVEL, reason="frontend/dist não compilado"
)

cliente = TestClient(api.app)


def test_raiz_entrega_o_painel_sem_exigir_token():
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "text/html" in resposta.headers["content-type"]
    assert '<div id="root">' in resposta.text


def test_assets_com_hash_sao_publicos():
    assets = api.PASTA_PAINEL / "assets"
    js = next(p.name for p in assets.iterdir() if p.suffix == ".js")

    resposta = cliente.get(f"/assets/{js}")

    assert resposta.status_code == 200
    assert "javascript" in resposta.headers["content-type"]


def test_favicon_e_publico():
    assert cliente.get("/favicon.svg").status_code == 200


def test_travessia_de_diretorio_nao_serve_codigo():
    resposta = cliente.get("/%2e%2e%2fconfig.py")

    assert resposta.status_code == 200
    assert "VERSAO" not in resposta.text


def test_api_desconhecida_responde_json_e_nao_o_painel():
    resposta = cliente.get("/api/nao-existe")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith("application/json")
