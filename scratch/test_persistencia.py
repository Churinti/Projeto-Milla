# scratch/test_persistencia.py
# Testes do snapshot do grafo ativo: serialização, restauração (inclusive de
# exportações antigas), escrita atômica e coalescência por intervalo.

import json
import os
import sys
from datetime import datetime

import networkx as nx

# Adiciona o diretório raiz ao path para poder importar core/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import persistencia
from core.no_dodecaedrico import NoDodecaedrico
from core.persistencia import PersistenciaGrafo


def _grafo(*conceitos) -> nx.Graph:
    grafo = nx.Graph()
    for nome in conceitos:
        grafo.add_node(nome, objeto=NoDodecaedrico(conceito=nome))
    return grafo


class RelogioFalso:
    """Relógio controlado para testar o intervalo sem dormir."""

    def __init__(self, inicio: float = 1000.0):
        self.agora = inicio

    def __call__(self) -> float:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += segundos


# ─── Serialização ─────────────────────────────────────────────────────────────

def test_serializacao_preserva_estado_do_no_e_da_aresta():
    grafo = _grafo("A", "B")
    no = grafo.nodes["A"]["objeto"]
    no.faces["logica"] = 0.93
    no.energia_ativacao = 0.42
    no.frequencia_ativacao = 7
    no.origem = "insight"
    no.criado_em = datetime(2026, 1, 2, 3, 4, 5)
    grafo.add_edge("A", "B", weight=0.77, tipo="hifa")

    dados = persistencia.serializar_grafo(grafo)

    assert dados["versao"] == persistencia.FORMATO_VERSAO
    no_a = dados["nos"]["A"]
    assert no_a["faces"]["logica"] == 0.93
    assert no_a["energia"] == 0.42
    assert no_a["ativacoes"] == 7
    assert no_a["origem"] == "insight"
    assert no_a["criado_em"] == "2026-01-02T03:04:05"
    assert no_a["ultima_ativacao"] is None
    assert dados["arestas"] == [
        {"de": "A", "para": "B", "peso": 0.77, "tipo": "hifa"}
    ]


def test_serializacao_e_json_valido():
    grafo = _grafo("A")
    dados = persistencia.serializar_grafo(grafo)

    json.dumps(dados)  # não deve levantar TypeError (numpy float, etc.)


def test_round_trip_reconstroi_o_grafo():
    original = _grafo("A", "B")
    original.nodes["B"]["objeto"].energia_ativacao = 0.31
    original.nodes["B"]["objeto"].frequencia_ativacao = 4
    original.add_edge("A", "B", weight=0.66, tipo="restaurada")

    restaurado = nx.Graph()
    contagem = persistencia.aplicar_snapshot(
        restaurado, persistencia.serializar_grafo(original)
    )

    assert contagem == {"nos": 2, "arestas": 1}
    no_b = restaurado.nodes["B"]["objeto"]
    assert no_b.energia_ativacao == 0.31
    assert no_b.frequencia_ativacao == 4
    # A face meta acompanha a energia, senão o vetor geométrico divergiria.
    assert no_b.faces["energia_ativacao"] == 0.31
    assert restaurado["A"]["B"]["weight"] == 0.66
    assert restaurado["A"]["B"]["tipo"] == "restaurada"


def test_snapshot_antigo_sem_versao_nem_tipo_e_legivel():
    """O formato v1 (exportação antiga) usa só `de`/`para`/`peso`."""
    dados = {
        "iteracoes": 12,
        "nos": {"Velho": {"faces": {"logica": 0.8}, "energia": 0.9,
                          "origem": "semente", "ativacoes": 2}},
        "arestas": [{"de": "Velho", "para": "Outro", "peso": 0.5}],
    }
    dados["nos"]["Outro"] = {"faces": {}, "energia": 1.0, "origem": "semente",
                             "ativacoes": 0}
    grafo = nx.Graph()

    persistencia.aplicar_snapshot(grafo, dados)

    assert set(grafo.nodes) == {"Velho", "Outro"}
    assert grafo["Velho"]["Outro"]["tipo"] == "normal"
    assert grafo.nodes["Velho"]["objeto"].faces["logica"] == 0.8


def test_entradas_invalidas_sao_ignoradas_sem_derrubar():
    dados = {
        "nos": {
            "Bom": {"faces": {"logica": 0.6, "quebrada": "não é número"},
                    "energia": 0.7, "ativacoes": 1, "origem": "insight"},
            "Ruim": "não é um dicionário",
        },
        "arestas": [
            {"de": "Bom", "para": "Fantasma", "peso": 0.5},
            {"de": "Bom", "para": "Bom", "peso": 0.5},
            "não é aresta",
        ],
    }
    grafo = nx.Graph()

    persistencia.aplicar_snapshot(grafo, dados)

    assert set(grafo.nodes) == {"Bom"}
    assert grafo.number_of_edges() == 0
    # Face inválida cai no padrão (0.5) em vez de virar string no vetor.
    assert grafo.nodes["Bom"]["objeto"].faces["quebrada"] == 0.5


def test_aplicar_snapshot_substitui_o_conteudo_atual():
    grafo = _grafo("Antigo")
    dados = {"nos": {"Novo": {"faces": {}, "energia": 1.0,
                              "origem": "semente", "ativacoes": 0}},
             "arestas": []}

    persistencia.aplicar_snapshot(grafo, dados)

    assert set(grafo.nodes) == {"Novo"}


# ─── Disco ───────────────────────────────────────────────────────────────────

def test_escrita_atomica_nao_deixa_arquivo_temporario(tmp_path):
    caminho = tmp_path / "grafo.json"

    persistencia.salvar_json_atomico({"versao": 2, "nos": {}}, caminho)

    assert caminho.exists()
    assert not (tmp_path / "grafo.json.tmp").exists()
    assert json.loads(caminho.read_text(encoding="utf-8"))["versao"] == 2


def test_carregar_arquivo_inexistente_retorna_false(tmp_path):
    grafo = _grafo("A")
    gerenciador = PersistenciaGrafo(grafo, caminho=tmp_path / "nada.json")

    assert gerenciador.carregar() is False
    assert set(grafo.nodes) == {"A"}


def test_carregar_json_corrompido_nao_derruba(tmp_path):
    caminho = tmp_path / "grafo.json"
    caminho.write_text("{ isso não é json", encoding="utf-8")
    grafo = _grafo("A")
    gerenciador = PersistenciaGrafo(grafo, caminho=caminho)

    assert gerenciador.carregar() is False
    assert set(grafo.nodes) == {"A"}


def test_snapshot_sem_nos_e_ignorado(tmp_path):
    caminho = tmp_path / "grafo.json"
    caminho.write_text(json.dumps({"nos": {}, "arestas": []}), encoding="utf-8")
    grafo = _grafo("A")

    assert PersistenciaGrafo(grafo, caminho=caminho).carregar() is False
    assert set(grafo.nodes) == {"A"}


def test_carregar_restaura_e_nao_nasce_sujo(tmp_path):
    grafo = _grafo("A", "B")
    grafo.add_edge("A", "B", weight=0.6, tipo="normal")
    caminho = tmp_path / "grafo.json"
    persistencia.salvar_json_atomico(
        persistencia.serializar_grafo(grafo), caminho
    )

    novo = nx.Graph()
    gerenciador = PersistenciaGrafo(novo, caminho=caminho, intervalo=0)

    assert gerenciador.carregar() is True
    assert gerenciador.sujo is False
    assert gerenciador.talvez_salvar() is False   # nada pendente
    assert set(novo.nodes) == {"A", "B"}


# ─── Coalescência ────────────────────────────────────────────────────────────

def test_gravacao_coalescida_respeita_o_intervalo(tmp_path):
    relogio = RelogioFalso()
    gerenciador = PersistenciaGrafo(
        _grafo("A"), caminho=tmp_path / "grafo.json", intervalo=30, relogio=relogio
    )

    gerenciador.marcar_sujo()
    assert gerenciador.talvez_salvar() is True          # primeiro flush não espera
    assert gerenciador.salvamentos == 1

    gerenciador.marcar_sujo()
    assert gerenciador.talvez_salvar() is False         # dentro do intervalo
    assert gerenciador.salvamentos == 1

    relogio.avancar(29)
    gerenciador.marcar_sujo()
    assert gerenciador.talvez_salvar() is False

    relogio.avancar(1)
    assert gerenciador.talvez_salvar() is True          # 30 s completos
    assert gerenciador.salvamentos == 2


def test_sem_mudanca_nao_serializa_nem_escreve(tmp_path):
    caminho = tmp_path / "grafo.json"
    gerenciador = PersistenciaGrafo(_grafo("A"), caminho=caminho, intervalo=0)

    assert gerenciador.talvez_salvar() is False
    assert gerenciador.salvar_agora() is None
    assert not caminho.exists()


def test_semear_conceitos_so_adiciona_os_ausentes():
    """A lista de sementes é única (main) e não duplica o que veio do snapshot."""
    from main import SEMENTES, semear_conceitos

    class MillaFalsa:
        def __init__(self):
            self.grafo = nx.Graph()

        def instanciar_conceito(self, conceito, faces, origem="semente"):
            self.grafo.add_node(
                conceito, objeto=NoDodecaedrico(conceito=conceito, faces=faces)
            )

    milla = MillaFalsa()
    assert semear_conceitos(milla) == len(SEMENTES)
    assert set(milla.grafo.nodes) == set(SEMENTES)

    # Segunda chamada não recria nada nem duplica arestas/nós.
    assert semear_conceitos(milla) == 0
    assert len(milla.grafo.nodes) == len(SEMENTES)


def test_salvar_agora_forca_o_flush_pendente(tmp_path):
    relogio = RelogioFalso()
    caminho = tmp_path / "grafo.json"
    gerenciador = PersistenciaGrafo(
        _grafo("A", "B"), caminho=caminho, intervalo=30, relogio=relogio
    )

    gerenciador.marcar_sujo()
    gerenciador.talvez_salvar()

    gerenciador.marcar_sujo()
    caminho_gravado = gerenciador.salvar_agora()

    assert caminho_gravado == caminho
    assert gerenciador.sujo is False
    assert gerenciador.salvamentos == 2
    assert set(json.loads(caminho.read_text(encoding="utf-8"))["nos"]) == {"A", "B"}
