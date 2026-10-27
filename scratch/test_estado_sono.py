# scratch/test_estado_sono.py
# Testes da máquina de estados de sono: transição de fases, payload do
# WebSocket e a propriedade esta_dormindo.

import os
import sys

# Adiciona o diretório raiz ao path para poder importar core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.estado_sono import EstadoSono, FaseSono


def test_estado_inicial_e_desperto():
    sono = EstadoSono()
    assert sono.fase == FaseSono.DESPERTO
    assert sono.ciclo_atual == 0
    assert not sono.esta_dormindo


def test_transicionar_retorna_payload_para_websocket():
    sono = EstadoSono(total_ciclos=4)
    payload = sono.transicionar(FaseSono.HIPNAGOGIA)

    assert sono.fase == FaseSono.HIPNAGOGIA
    assert sono.ultima_transicao is not None

    assert payload["type"] == "sono_fase"
    assert payload["payload"]["fase"] == "hipnagogia"
    assert payload["payload"]["total"] == 4
    assert payload["payload"]["ciclo"] == 0
    assert payload["payload"]["insights"] == 0
    assert payload["payload"]["hifas"] == 0


def test_esta_dormindo_durante_ciclo():
    sono = EstadoSono()
    sono.transicionar(FaseSono.SONHO)
    assert sono.esta_dormindo

    sono.transicionar(FaseSono.DESPERTO)
    assert not sono.esta_dormindo


def test_despertando_nao_conta_como_dormindo():
    """DESPERTANDO é transição de volta à vigília — não é sono."""
    sono = EstadoSono()
    sono.transicionar(FaseSono.DESPERTANDO)
    assert not sono.esta_dormindo


def test_conteudo_do_payload_acompanha_telemetria():
    sono = EstadoSono()
    sono.ciclo_atual = 2
    sono.insights_gerados.append("insight A")
    sono.hifas_criadas = 3

    payload = sono.transicionar(FaseSono.SONHO)["payload"]

    assert payload["ciclo"] == 2
    assert payload["insights"] == 1
    assert payload["hifas"] == 3


def test_todas_as_fases_sao_serializaveis():
    """Cada fase stringifica para o valor usado no protocolo."""
    esperado = {
        FaseSono.DESPERTO: "desperto",
        FaseSono.HIPNAGOGIA: "hipnagogia",
        FaseSono.CONSOLIDACAO: "consolidacao",
        FaseSono.SONHO: "sonho",
        FaseSono.SONO_PROFUNDO: "sono_profundo",
        FaseSono.DESPERTANDO: "despertando",
    }
    for fase, valor in esperado.items():
        assert fase.value == valor