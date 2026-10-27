# scratch/test_pathfinding.py
# Testes do PathfinderCognitivo: extração semântica de conceitos (com
# subconsciente mockado), busca de caminho por Dijkstra invertido e
# extração de contexto textual para o prompt.

import os
import sys

import networkx as nx

# Adiciona o diretório raiz ao path para poder importar core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.no_dodecaedrico import NoDodecaedrico
from core.pathfinding import PathfinderCognitivo


class SubconscienteFalso:
    """Subconsciente mínimo: devolve respostas pré-montadas do ChromaDB.

    O `query()` do ChromaDB devolve um DICT ({"metadatas": [...],
    "distances": [...]}), não uma lista — o mock espelha isso.
    """

    SCHEMA_VERSION = "3.0"

    def __init__(self, resposta=None, erro=False):
        self.resposta = resposta or {}
        self.erro = erro
        self.ultima_query = None
        self.colecao = self

    def query(self, **kwargs):
        self.ultima_query = kwargs
        if self.erro:
            raise RuntimeError("ChromaDB indisponível")
        return self.resposta


def _grafo(names):
    g = nx.Graph()
    for n in names:
        g.add_node(n, objeto=NoDodecaedrico(conceito=n))
    return g


# ─── extrair_conceitos_da_pergunta ───────────────────────────────────────────

def test_extrair_com_grafo_vazio():
    pf = PathfinderCognitivo(nx.Graph(), SubconscienteFalso())
    assert pf.extrair_conceitos_da_pergunta("o que é consciência?") == []


def test_extrair_filtra_por_similaridade_e_presenca_no_grafo():
    """Só passa similaridade > 0.4 E conceito existente no grafo ativo."""
    grafo = _grafo(["Consciencia", "Geometria"])

    resposta = {
        "metadatas": [[
            {"conceito": "Consciencia"},   # dist 0.1 → sim 0.9 ✓
            {"conceito": "Desconectado"},  # sim alta, mas fora do grafo ✗
            {"conceito": "Geometria"},     # dist 0.5 → sim 0.5 ✓
            {"conceito": "Fraco"},         # dist 0.8 → sim 0.2 ✗
        ]],
        "distances": [[0.1, 0.05, 0.5, 0.8]],
    }
    sub = SubconscienteFalso(resposta=resposta)
    pf = PathfinderCognitivo(grafo, sub)

    conceitos = pf.extrair_conceitos_da_pergunta("pergunta qualquer")

    assert conceitos == ["Consciencia", "Geometria"]
    # A query usa o schema versionado como filtro do ChromaDB
    assert sub.ultima_query["where"] == {
        "schema_version": {"$eq": "3.0"}
    }


def test_extrair_limita_a_tres_conceitos():
    grafo = _grafo(["A", "B", "C", "D", "E"])
    resposta = {
        "metadatas": [[{"conceito": n} for n in ["A", "B", "C", "D", "E"]]],
        "distances": [[0.05] * 5],
    }
    pf = PathfinderCognitivo(grafo, SubconscienteFalso(resposta=resposta))
    assert pf.extrair_conceitos_da_pergunta("x") == ["A", "B", "C"]


def test_extrair_retorna_vazio_ao_falhar_o_chroma():
    """Falha do ChromaDB não pode derrubar a extração — degrada para []."""
    grafo = _grafo(["A"])
    pf = PathfinderCognitivo(grafo, SubconscienteFalso(erro=True))
    assert pf.extrair_conceitos_da_pergunta("x") == []


def test_extrair_com_resposta_malformada():
    """Resposta sem metadatas/dists utilizáveis → []."""
    grafo = _grafo(["A"])
    pf = PathfinderCognitivo(
        grafo, SubconscienteFalso(resposta={"metadatas": [None]})
    )
    assert pf.extrair_conceitos_da_pergunta("x") == []


# ─── encontrar_caminho ───────────────────────────────────────────────────────

def test_caminho_inexistente_quando_no_fora_do_grafo():
    grafo = _grafo(["A", "B"])
    grafo.add_edge("A", "B", weight=0.5)
    pf = PathfinderCognitivo(grafo, SubconscienteFalso())
    assert pf.encontrar_caminho("A", "Zumbei") is None
    assert pf.encontrar_caminho("Zumbei", "A") is None


def test_caminho_encontrado_entre_conectados():
    grafo = _grafo(["A", "B", "C"])
    grafo.add_edge("A", "B", weight=0.9)
    grafo.add_edge("B", "C", weight=0.8)
    pf = PathfinderCognitivo(grafo, SubconscienteFalso())

    caminho = pf.encontrar_caminho("A", "C")

    assert caminho == ["A", "B", "C"]


def test_caminho_prefere_aresta_mais_forte():
    """Dijkstra invertido: peso alto = custo baixo = caminho preferido."""
    grafo = _grafo(["A", "B", "C"])
    # Rota direta fraca vs. rota indireta forte
    grafo.add_edge("A", "C", weight=0.1)   # custo ~9.09
    grafo.add_edge("A", "B", weight=1.0)   # custo ~0.99
    grafo.add_edge("B", "C", weight=1.0)   # custo ~0.99
    pf = PathfinderCognitivo(grafo, SubconscienteFalso())

    caminho = pf.encontrar_caminho("A", "C")

    assert caminho == ["A", "B", "C"], "deveria preferir a aresta forte"


def test_caminho_none_quando_desconectado():
    grafo = _grafo(["A", "B", "X", "Y"])
    grafo.add_edge("A", "B", weight=0.5)
    grafo.add_edge("X", "Y", weight=0.5)
    pf = PathfinderCognitivo(grafo, SubconscienteFalso())
    assert pf.encontrar_caminho("A", "Y") is None


def test_caminho_none_quando_excede_max_hops():
    """Cadeia longa demais é rejeitada (evita delírio sem fim)."""
    nomes = [f"N{i}" for i in range(8)]
    grafo = _grafo(nomes)
    for a, b in zip(nomes, nomes[1:]):
        grafo.add_edge(a, b, weight=1.0)
    pf = PathfinderCognitivo(grafo, SubconscienteFalso())

    # 8 nós = 7 hops; com max_hops=5 → None
    assert pf.encontrar_caminho("N0", "N7", max_hops=5) is None
    # com max_hops=7 → cabe
    assert pf.encontrar_caminho("N0", "N7", max_hops=7) == nomes


def test_caminho_do_no_para_si_mesmo():
    grafo = _grafo(["A"])
    pf = PathfinderCognitivo(grafo, SubconscienteFalso())
    assert pf.encontrar_caminho("A", "A") == ["A"]


def test_caminho_com_no_isolado_nao_crasha():
    """Nó existe no grafo mas não tem arestas → None, nunca exceção.

    Regressão: grafo_inv só é montado a partir das arestas, então um nó
    isolado não é copiado e o Dijkstra lançava NodeNotFound — que escapava
    do except (só pegava NetworkXNoPath) e derrubava a consulta.
    """
    grafo = _grafo(["Isolado", "A", "B"])
    grafo.add_edge("A", "B", weight=0.5)
    pf = PathfinderCognitivo(grafo, SubconscienteFalso())

    assert pf.encontrar_caminho("Isolado", "A") is None
    assert pf.encontrar_caminho("A", "Isolado") is None
    assert pf.encontrar_caminho("Isolado", "Isolado") == ["Isolado"]


# ─── extrair_contexto_caminho ────────────────────────────────────────────────

def test_contexto_de_caminho_vazio():
    grafo = _grafo(["A"])
    pf = PathfinderCognitivo(grafo, SubconscienteFalso())
    assert pf.extrair_contexto_caminho([]) == ""


def test_contexto_descreve_nos_e_arestas():
    grafo = _grafo(["Logica", "Tempo"])
    grafo.add_edge("Logica", "Tempo", weight=0.75)
    pf = PathfinderCognitivo(grafo, SubconscienteFalso())

    texto = pf.extrair_contexto_caminho(["Logica", "Tempo"])

    assert "Conceito 1: Logica" in texto
    assert "Conceito 2: Tempo" in texto
    assert "Força Sináptica de 0.75" in texto
    assert "Lógica:" in texto
    assert "Abstração:" in texto


def test_contexto_sem_ultima_aresta():
    """Caminho de 1 nó não imprime seta (não há aresta seguinte)."""
    grafo = _grafo(["Sozinho"])
    pf = PathfinderCognitivo(grafo, SubconscienteFalso())
    texto = pf.extrair_contexto_caminho(["Sozinho"])
    assert "Conceito 1: Sozinho" in texto
    assert "→" not in texto