# scratch/test_micelio.py
# Testes do Motor de Nutrição Sináptica Micelial: difusão pontual,
# distribuição global de nutrientes, brotamento de hifas e ciclo vital.

import os
import sys

import networkx as nx

# Adiciona o diretório raiz ao path para poder importar core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.micelio import MicelioMilla
from core.no_dodecaedrico import NoDodecaedrico


def _grafo_com(nodes: dict) -> nx.Graph:
    """Monta um grafo a partir de {nome: energia} (sem arestas)."""
    g = nx.Graph()
    for nome, energia in nodes.items():
        no = NoDodecaedrico(conceito=nome, origem="absorcao")
        no.energia_ativacao = energia
        g.add_node(nome, objeto=no)
    return g


# ─── espalhar_energia (API legada) ───────────────────────────────────────────

async def test_espalhar_energia_hub_inexistente_e_ignorado():
    micelio = MicelioMilla()
    grafo = _grafo_com({"A": 1.0})
    # Não deve levantar exceção
    await micelio.espalhar_energia(grafo, hub="Inexistente")


async def test_espalhar_energia_hub_sem_vizinhos():
    micelio = MicelioMilla()
    grafo = _grafo_com({"A": 1.0, "B": 0.5})  # sem arestas
    await micelio.espalhar_energia(grafo, hub="A")
    assert grafo.nodes["B"]["objeto"].energia_ativacao == 0.5  # intacto


async def test_espalhar_energia_proporcional_ao_peso():
    """Vizinho de peso 0.8 recebe 4× o incremento do de peso 0.2."""
    micelio = MicelioMilla()
    grafo = _grafo_com({"Hub": 1.0, "Forte": 0.5, "Fraco": 0.5})
    grafo.add_edge("Hub", "Forte", weight=0.8)
    grafo.add_edge("Hub", "Fraco", weight=0.2)

    await micelio.espalhar_energia(grafo, hub="Hub", intensidade=0.2)

    delta_forte = grafo.nodes["Forte"]["objeto"].energia_ativacao - 0.5
    delta_fraco = grafo.nodes["Fraco"]["objeto"].energia_ativacao - 0.5
    assert abs(delta_forte - 0.16) < 1e-9   # 1.0 * 0.2 * 0.8
    assert abs(delta_fraco - 0.04) < 1e-9   # 1.0 * 0.2 * 0.2
    # O hub não doa a si mesmo
    assert grafo.nodes["Hub"]["objeto"].energia_ativacao == 1.0


# ─── distribuir_nutrientes ───────────────────────────────────────────────────

def test_distribuir_grafo_vazio():
    assert MicelioMilla().distribuir_nutrientes(nx.Graph()) == {}


def test_distribuir_so_nos_ricos_doam():
    """Energia > 0.70 (limiar) doa; abaixo disso, ninguém doa."""
    micelio = MicelioMilla()
    grafo = _grafo_com({"Rico": 1.0, "Pobre": 0.5})
    grafo.add_edge("Rico", "Pobre", weight=1.0)

    deltas = micelio.distribuir_nutrientes(grafo)

    assert deltas["Rico"] < 0            # perdeu
    assert deltas["Pobre"] > 0           # ganhou
    assert abs(deltas["Rico"] + deltas["Pobre"]) < 1e-9  # conservação
    # 1.0 * taxa 0.15
    assert abs(deltas["Rico"] - (-0.15)) < 1e-9


def test_distribuir_energia_preservada_entre_nos_ricos():
    """Dois ricos doem entre si mas o total do sistema não cria energia."""
    micelio = MicelioMilla()
    grafo = _grafo_com({"A": 0.9, "B": 0.8})
    grafo.add_edge("A", "B", weight=1.0)

    micelio.distribuir_nutrientes(grafo)

    total = (grafo.nodes["A"]["objeto"].energia_ativacao
             + grafo.nodes["B"]["objeto"].energia_ativacao)
    # clamp [0,1] pode perder um pouco nas bordas, mas aqui não satura
    assert abs(total - 1.7) < 1e-9


def test_distribuir_com_clamp_biologico():
    """Receptor não pode passar de 1.0 mesmo com doação grande."""
    micelio = MicelioMilla(taxa_transferencia=0.9)
    grafo = _grafo_com({"Rico": 1.0, "Pobre": 0.70})
    grafo.add_edge("Rico", "Pobre", weight=1.0)

    micelio.distribuir_nutrientes(grafo)

    assert grafo.nodes["Pobre"]["objeto"].energia_ativacao == 1.0
    # e a face espelha a energia (sincronia grafo ↔ dodecaedro)
    assert grafo.nodes["Pobre"]["objeto"].faces["energia_ativacao"] == 1.0


def test_distribuir_nos_isolados_nao_doam():
    """Nó rico sem vizinhos não entra no ciclo de doação."""
    micelio = MicelioMilla()
    grafo = _grafo_com({"Ilhado": 1.0})
    deltas = micelio.distribuir_nutrientes(grafo)
    assert deltas == {"Ilhado": 0.0}
    assert grafo.nodes["Ilhado"]["objeto"].energia_ativacao == 1.0


# ─── brotar_hifas ────────────────────────────────────────────────────────────

def test_brotar_com_muito_poucos_nos():
    micelio = MicelioMilla()
    assert micelio.brotar_hifas(nx.Graph(), desejo=1.0) == []
    g = _grafo_com({"A": 1.0})
    assert micelio.brotar_hifas(g, desejo=1.0) == []


def test_brotar_sem_gatilho_retorna_vazio():
    """Desejo baixo e densidade alta → nada brota."""
    micelio = MicelioMilla()
    grafo = _grafo_com({"A": 0.5, "B": 0.5, "C": 0.5})
    grafo.add_edge("A", "B", weight=0.5)
    grafo.add_edge("B", "C", weight=0.5)
    grafo.add_edge("A", "C", weight=0.5)  # densidade 1.0
    assert micelio.brotar_hifas(grafo, desejo=0.10) == []


def test_brotar_forcado_por_nos_recentes_isolados():
    """Nós recentes isolados brotam mesmo com desejo baixo (pós-upload)."""
    micelio = MicelioMilla()
    grafo = _grafo_com({"A": 0.9, "B": 0.8, "Novo": 0.6})
    grafo.add_edge("A", "B", weight=0.5)
    # "Novo" fica isolado (grau 0) e está em nos_recentes

    hifas = micelio.brotar_hifas(grafo, desejo=0.10, nos_recentes=["Novo"])

    assert len(hifas) == 1
    no_a, no_b = hifas[0]
    assert "Novo" in (no_a, no_b)          # ponta recente participa
    aresta = grafo[no_a][no_b]
    assert aresta["weight"] == 0.1         # hifa é fraca por padrão
    assert aresta["tipo"] == "hifa"


def test_brotar_costura_componentes_desconexos():
    """Dois componentes + desejo alto + densidade baixa → uma hifa."""
    micelio = MicelioMilla()
    grafo = _grafo_com({"A": 0.9, "B": 0.8, "X": 0.7, "Y": 0.6})
    grafo.add_edge("A", "B", weight=0.5)
    grafo.add_edge("X", "Y", weight=0.5)  # 2 componentes, densidade 2/6

    hifas = micelio.brotar_hifas(grafo, desejo=0.90)

    assert len(hifas) == 1
    u, v = hifas[0]
    # a hifa liga os dois componentes
    assert {u, v} != {"A", "B"} and {u, v} != {"X", "Y"}
    assert grafo.has_edge(u, v)


def test_brotar_respeita_max_hifas():
    """3 componentes, mas max_hifas=2 limita o número de pontes."""
    micelio = MicelioMilla(max_hifas=2)
    grafo = _grafo_com({
        "A": 0.9, "B": 0.8, "X": 0.7, "Y": 0.6, "P": 0.5, "Q": 0.4,
    })
    grafo.add_edge("A", "B", weight=0.5)
    grafo.add_edge("X", "Y", weight=0.5)
    grafo.add_edge("P", "Q", weight=0.5)  # 3 componentes

    hifas = micelio.brotar_hifas(grafo, desejo=0.90)

    assert len(hifas) == 2


def test_brotar_nao_liga_nos_recentes_entre_si():
    """No principal, prefere nó ANTIGO (não recente)."""
    micelio = MicelioMilla()
    grafo = _grafo_com({"Velho": 0.9, "Novo": 0.8, "Ilha": 0.7})
    grafo.add_edge("Velho", "Novo", weight=0.5)  # componente principal

    hifas = micelio.brotar_hifas(
        grafo, desejo=0.90, nos_recentes=["Ilha", "Novo"]
    )

    assert len(hifas) == 1
    u, v = hifas[0]
    assert "Ilha" in (u, v)      # ponta isolada é o recente
    principal = v if "Ilha" == u else u
    assert principal == "Velho"  # preferência: antigo, não "Novo"


# ─── ciclo_vital (orquestrador) ──────────────────────────────────────────────

def test_ciclo_vital_retorna_relatorio_completo():
    micelio = MicelioMilla()
    grafo = _grafo_com({"Rico": 1.0, "Pobre": 0.5, "Ilha": 0.4})
    grafo.add_edge("Rico", "Pobre", weight=1.0)
    # "Ilha" fica isolada e recente → hifa brota

    relatorio = micelio.ciclo_vital(
        grafo, desejo=0.10, nos_recentes=["Ilha"]
    )

    assert relatorio["status"] == "ciclo_vital_concluido"
    assert relatorio["nos_doadores"] == 1   # Rico doou
    # A Ilha não recebe nutriente: a hifa brota na fase 2, depois da
    # varredura de nutrientes da fase 1.
    assert relatorio["nos_nutridos"] == 1   # só Pobre
    assert relatorio["hifas_brotadas"] == 1
    assert relatorio["energia_circulada"] > 0
    assert len(relatorio["conexoes_hifas"]) == 1