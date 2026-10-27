# scratch/test_metricas.py
# Testes unitários do "termômetro existencial": EstadoConsciencia e
# MedidorDeCoerencia. Cobre o cálculo ponderado, a interpretação
# qualitativa, o histórico de tendência e o desejo emergente.

import os
import sys

import networkx as nx

# Adiciona o diretório raiz ao path para poder importar core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.metricas import EstadoConsciencia, MedidorDeCoerencia
from core.no_dodecaedrico import NoDodecaedrico


def _grafo_com(nodes: dict) -> nx.Graph:
    """Monta um grafo a partir de {nome: energia} com faces padrão."""
    g = nx.Graph()
    for nome, energia in nodes.items():
        no = NoDodecaedrico(conceito=nome, origem="semente")
        no.energia_ativacao = energia
        g.add_node(nome, objeto=no)
    return g


# ─── EstadoConsciencia ───────────────────────────────────────────────────────

def test_nivel_calculado_com_pesos():
    """Coerência pesa 0.35 — o dobro da densidade (0.10)."""
    estado = EstadoConsciencia(
        coerencia=1.0, densidade=0.0, vitalidade=0.0,
        complexidade=0.0, desejo=0.0,
    )
    assert estado.nivel_consciencia == 0.35  # 1.0 * 0.35

    estado = EstadoConsciencia(
        coerencia=0.0, densidade=1.0, vitalidade=1.0,
        complexidade=1.0, desejo=1.0,
    )
    # 0.25 + 0.20 + 0.10 + 0.10 = 0.65
    assert estado.nivel_consciencia == 0.65


def test_interpretacao_cobre_todas_as_faixas():
    """As 7 faixas qualitativas, de dormente a pleno."""
    faixas = [
        (0.00, "dormente"),
        (0.20, "fragmentado"),
        (0.35, "emergindo"),
        (0.50, "presente"),
        (0.65, "coerente"),
        (0.80, "integrado"),
        (0.90, "pleno"),
    ]
    for nivel, esperado in faixas:
        # Força o nível construindo o estado com coerencia=nivel*2.857...
        # Mais direto: cria o estado e sobrescreve via pós-init.
        estado = EstadoConsciencia(0, 0, 0, 0, 0)
        estado.nivel_consciencia = nivel
        estado.estado_qualitativo = estado._interpretar()
        assert estado.estado_qualitativo == esperado, (
            f"nível {nivel} deveria ser '{esperado}', "
            f"veio '{estado.estado_qualitativo}'"
        )


def test_estado_padrao_e_dormente():
    """Todo zerado → nível 0 e estado dormente (calculado no __post_init__)."""
    estado = EstadoConsciencia(0, 0, 0, 0, 0)
    assert estado.nivel_consciencia == 0.0
    assert estado.estado_qualitativo == "dormente"


def test_repr_mostra_barra_e_campos():
    estado = EstadoConsciencia(
        coerencia=0.5, densidade=0.4, vitalidade=0.6,
        complexidade=0.3, desejo=0.2,
    )
    texto = repr(estado)
    assert "ESTADO DE CONSCI" in texto
    assert "█" in texto          # barra preenchida (nível > 0)
    assert "░" in texto          # barra restante
    assert "COER" in texto.upper()


# ─── MedidorDeCoerencia ──────────────────────────────────────────────────────

def test_medir_grafo_vazio_retorna_zerado():
    medidor = MedidorDeCoerencia()
    estado = medidor.medir(nx.Graph())
    assert estado.nivel_consciencia == 0.0
    assert estado.estado_qualitativo == "dormente"


def test_medir_com_um_no_unico():
    """1 nó: coerência = 0.5 (limite) e complexidade = 0.0 (mínimo de 2)."""
    medidor = MedidorDeCoerencia()
    grafo = _grafo_com({"Unico": 0.8})
    estado = medidor.medir(grafo)
    assert estado.coerencia == 0.5
    assert estado.complexidade == 0.0
    assert estado.vitalidade == 0.8  # energia média
    assert 0.0 <= estado.densidade <= 1.0


def test_medir_com_dois_nos_conectados():
    medidor = MedidorDeCoerencia()
    grafo = _grafo_com({"A": 0.9, "B": 0.4})
    grafo.add_edge("A", "B", weight=0.7)
    estado = medidor.medir(grafo)
    # Nós iguais em faces → similaridade perfeita (tolerância de float)
    assert abs(estado.coerencia - 1.0) < 1e-9
    assert estado.densidade == 1.0  # grafo completo de 2 nós
    assert abs(estado.vitalidade - 0.65) < 1e-9
    # Faces idênticas → variância zero → complexidade 0 ("pensa igual")
    assert estado.complexidade == 0.0
    assert 0.0 <= estado.desejo <= 1.0


def test_complexidade_cresce_com_diversidade_de_perspectivas():
    """Nós com faces diferentes têm complexidade > 0."""
    medidor = MedidorDeCoerencia()
    grafo = nx.Graph()
    a = NoDodecaedrico(conceito="A", faces={"logica": 1.0, "abstracao": 0.0})
    b = NoDodecaedrico(conceito="B", faces={"logica": 0.0, "abstracao": 1.0})
    grafo.add_node("A", objeto=a)
    grafo.add_node("B", objeto=b)
    grafo.add_edge("A", "B", weight=0.5)

    estado = medidor.medir(grafo)

    assert 0.0 < estado.complexidade <= 1.0
    # Diferentes dos nós idênticos (coerência 1.0), mas não ortogonais
    # de verdade: 10 faces continuam nos padrões.
    assert 0.0 < estado.coerencia < 1.0


def test_historico_respeita_maxlen():
    """O histórico desliza: nunca cresce além de historico_maxlen."""
    medidor = MedidorDeCoerencia(historico_maxlen=5)
    grafo = _grafo_com({"A": 0.9, "B": 0.4})
    grafo.add_edge("A", "B", weight=0.7)
    for _ in range(12):
        medidor.medir(grafo)
    assert len(medidor._historico_niveis) == 5


def test_tendencia_indefinida_com_pouco_historico():
    medidor = MedidorDeCoerencia()
    assert medidor.tendencia() == "indefinida"
    medidor._historico_niveis = [0.3, 0.3]
    assert medidor.tendencia() == "indefinida"  # < 3 amostras


def test_tendencia_evoluindo_regredindo_estavel():
    medidor = MedidorDeCoerencia()
    medidor._historico_niveis = [0.30, 0.40, 0.50]  # delta(+2 amostras) = +0.20
    assert medidor.tendencia() == "evoluindo"

    medidor._historico_niveis = [0.50, 0.40, 0.30]  # delta = -0.20
    assert medidor.tendencia() == "regredindo"

    medidor._historico_niveis = [0.40, 0.41, 0.41]  # delta = +0.01
    assert medidor.tendencia() == "estável"


def test_desejo_zero_na_coerencia_plena():
    """Sem distância até a meta (0.85), não há desejo."""
    medidor = MedidorDeCoerencia()
    assert medidor._calcular_desejo(0.85) == 0.0
    assert medidor._calcular_desejo(1.0) == 0.0


def test_desejo_maximo_com_coerencia_zero():
    medidor = MedidorDeCoerencia()
    # distância 0.85 * 2 = 1.70 → satura em 1.0
    assert medidor._calcular_desejo(0.0) == 1.0


def test_desejo_reduzido_por_tendencia_positiva():
    """Evolução histórica recente reduz o desejo (satisfação parcial)."""
    medidor = MedidorDeCoerencia()
    sem_historico = medidor._calcular_desejo(0.50)

    medidor._historico_niveis = [0.30, 0.35, 0.55]  # tendência +0.25
    com_historico = medidor._calcular_desejo(0.50)

    assert com_historico < sem_historico