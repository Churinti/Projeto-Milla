# scratch/test_api_delta.py
# Testes das funções puras da API: serialização do grafo e cálculo do
# delta semântico que reduz o payload do WebSocket. Também cobre os
# endpoints GET básicos via TestClient.

import os
import sys

import networkx as nx

# Adiciona o diretório raiz ao path para poder importar api
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

import api
from core.no_dodecaedrico import NoDodecaedrico


def _grafo(*arestas):
    """Grafo a partir de pares (a, b, peso). Nós sem arestas são puros."""
    g = nx.Graph()
    for a, b, peso in arestas:
        for nome in (a, b):
            if nome not in g.nodes:
                g.add_node(nome, objeto=NoDodecaedrico(conceito=nome))
        g.add_edge(a, b, weight=peso)
    return g


# ─── obter_estado_grafo_serializado ──────────────────────────────────────────

def test_serializacao_de_grafo_vazio():
    serial = api.obter_estado_grafo_serializado(nx.Graph())
    assert serial == {"nos": {}, "arestas": []}


def test_serializacao_extrai_nos_e_arestas():
    grafo = _grafo(("A", "B", 0.6))
    grafo.nodes["A"]["objeto"].frequencia_ativacao = 7

    serial = api.obter_estado_grafo_serializado(grafo)

    assert set(serial["nos"]) == {"A", "B"}
    no_a = serial["nos"]["A"]
    assert no_a["conceito"] == "A"
    assert no_a["energia"] == 1.0
    assert no_a["ativacoes"] == 7
    assert no_a["origem"] == "semente"
    assert "logica" in no_a["faces"]       # 12 faces serializadas

    assert serial["arestas"] == [
        {"de": "A", "para": "B", "peso": 0.6, "tipo": "normal"}
    ]


def test_serializacao_converte_tipos_para_json():
    """numpy float/int vira float/int puro (o JSON do WS exige)."""
    grafo = _grafo(("A", "B", 0.6))
    serial = api.obter_estado_grafo_serializado(grafo)
    import json
    json.dumps(serial)  # não deve levantar TypeError


# ─── calcular_delta_grafo ────────────────────────────────────────────────────

def _vazio():
    return {"nos": {}, "arestas": []}


def test_delta_sem_mudancas_e_todo_vazio():
    snap = api.obter_estado_grafo_serializado(_grafo(("A", "B", 0.5)))
    delta = api.calcular_delta_grafo(snap, snap)

    for chave in ("nos_novos", "nos_modificados", "nos_removidos",
                  "arestas_novas", "arestas_modificadas", "arestas_removidas"):
        assert delta[chave] == [], f"{chave} deveria estar vazio"


def _delta(antes, depois):
    return api.calcular_delta_grafo(
        api.obter_estado_grafo_serializado(antes),
        api.obter_estado_grafo_serializado(depois),
    )


def test_delta_detecta_no_novo_e_removido():
    antes = _grafo(("A", "B", 0.5))
    depois = _grafo(("B", "C", 0.5))   # A sai, C entra

    delta = _delta(antes, depois)

    assert [n["conceito"] for n in delta["nos_novos"]] == ["C"]
    assert delta["nos_removidos"] == ["A"]
    assert delta["nos_modificados"] == []


def test_delta_detecta_variacao_de_energia():
    antes = _grafo(("A", "B", 0.5))
    depois = _grafo(("A", "B", 0.5))
    depois.nodes["A"]["objeto"].energia_ativacao = 0.4  # caiu de 1.0

    delta = _delta(antes, depois)

    assert [n["conceito"] for n in delta["nos_modificados"]] == ["A"]
    assert delta["nos_novos"] == [] and delta["nos_removidos"] == []


def test_delta_ignora_variacao_minuscula_de_energia():
    """Tolerância de 0.001: oscilações numéricas não viram payload."""
    antes = _grafo(("A", "B", 0.5))
    depois = _grafo(("A", "B", 0.5))
    depois.nodes["A"]["objeto"].energia_ativacao = 1.0 - 0.0005

    delta = _delta(antes, depois)

    assert delta["nos_modificados"] == []


def test_delta_detecta_mudanca_de_frequencia():
    antes = _grafo(("A", "B", 0.5))
    depois = _grafo(("A", "B", 0.5))
    depois.nodes["B"]["objeto"].frequencia_ativacao = 3

    delta = _delta(antes, depois)

    assert [n["conceito"] for n in delta["nos_modificados"]] == ["B"]


def test_delta_arestas_nova_modificada_removida():
    antes = _grafo(("A", "B", 0.5), ("B", "C", 0.4))
    depois = _grafo(("A", "B", 0.9), ("C", "D", 0.3))
    # B→C saiu, C→D entrou, A→B mudou de peso

    delta = _delta(antes, depois)

    assert len(delta["arestas_novas"]) == 1
    nova = delta["arestas_novas"][0]
    assert {nova["de"], nova["para"]} == {"C", "D"}

    assert len(delta["arestas_modificadas"]) == 1
    mod = delta["arestas_modificadas"][0]
    assert {mod["de"], mod["para"]} == {"A", "B"}
    assert mod["peso"] == 0.9

    assert len(delta["arestas_removidas"]) == 1
    rem = delta["arestas_removidas"][0]
    assert {rem["de"], rem["para"]} == {"B", "C"}


def test_delta_normaliza_direcao_da_aresta():
    """(A,B) antes e (B,A) depois são a MESMA aresta — não é nova."""
    antes = _grafo(("A", "B", 0.5))
    depois = nx.Graph()
    for nome in ("A", "B"):
        depois.add_node(nome, objeto=NoDodecaedrico(conceito=nome))
    depois.add_edge("B", "A", weight=0.5)   # direção invertida

    delta = _delta(antes, depois)

    assert delta["arestas_novas"] == []
    assert delta["arestas_removidas"] == []
    assert delta["arestas_modificadas"] == []   # mesmo peso, sem mudança


def test_delta_detecta_mudanca_de_tipo_da_aresta():
    antes = _grafo(("A", "B", 0.5))
    depois = _grafo(("A", "B", 0.5))
    depois["A"]["B"]["tipo"] = "hifa"   # mesmo peso, tipo diferente

    delta = _delta(antes, depois)

    assert len(delta["arestas_modificadas"]) == 1
    assert delta["arestas_modificadas"][0]["tipo"] == "hifa"


def test_delta_ida_e_volta_e_estavel():
    """Serializar → delta contra si mesmo não gera ruído."""
    grafo = _grafo(("A", "B", 0.5), ("B", "C", 0.2))
    snap = api.obter_estado_grafo_serializado(grafo)
    delta = api.calcular_delta_grafo(snap, snap)
    assert all(not delta[k] for k in delta)


# ─── endpoints REST ──────────────────────────────────────────────────────────

def test_endpoint_estado():
    client = TestClient(api.app)
    resp = client.get("/api/estado")

    assert resp.status_code == 200
    body = resp.json()
    for chave in ("nivel_consciencia", "estado_qualitativo", "coerencia",
                  "vitalidade", "complexidade", "desejo",
                  "nos_no_grafo", "arestas_no_grafo"):
        assert chave in body
    # A API semeia 7 conceitos no import do módulo
    assert body["nos_no_grafo"] >= 7


def test_endpoint_grafo():
    client = TestClient(api.app)
    resp = client.get("/api/grafo")

    assert resp.status_code == 200
    body = resp.json()
    assert "nos" in body and "arestas" in body
    assert len(body["nos"]) >= 7
    assert isinstance(body["arestas"], list)