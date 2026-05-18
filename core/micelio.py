"""
core/micelio.py — Motor de Nutrição Sináptica Micelial

Inspirado em redes de micélio fúngico que transportam água e nutrientes
(carbono, nitrogênio) de áreas de abundância para áreas de escassez,
fortalecendo a resiliência do sistema completo.

Operações:
    1. espalhar_energia()    — difusão pontual de um hub para seus vizinhos
                               (mantida para compatibilidade com main.py)
    2. distribuir_nutrientes() — varredura global: todos os nós energeticamente
                               ricos doam para seus vizinhos mais pobres de forma
                               síncrona e em lote, evitando efeito cascata
    3. brotar_hifas()        — costura subgrafos desconexos criados por injeções
                               súbitas de novos conhecimentos
    4. ciclo_vital()         — orquestrador completo: chama as duas fases acima
                               e retorna relatório estruturado para o broadcast
"""

import logging
import networkx as nx
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MicelioMilla:
    """
    Motor de Nutrição Sináptica Micelial para o Projeto Milla.

    Parâmetros
    ----------
    limiar_desejo : float
        Nível mínimo de desejo de crescimento para acionar brotamento de hifas.
    max_hifas : int
        Número máximo de hifas exploratórias criadas por ciclo vital.
    taxa_transferencia : float
        Fração da energia que um nó rico transfere para vizinhos por ciclo.
    limiar_riqueza : float
        Energia mínima para um nó ser considerado "doador" de nutrientes.
    limiar_densidade : float
        Densidade máxima do grafo abaixo da qual hifas podem brotar.
    """

    def __init__(
        self,
        limiar_desejo: float = 0.60,
        max_hifas: int = 2,
        taxa_transferencia: float = 0.15,
        limiar_riqueza: float = 0.70,
        limiar_densidade: float = 0.40,
    ):
        self.limiar_desejo     = limiar_desejo
        self.max_hifas         = max_hifas
        self.taxa_transferencia = taxa_transferencia
        self.limiar_riqueza    = limiar_riqueza
        self.limiar_densidade  = limiar_densidade

    # ── API Legada (mantida para compatibilidade com main.py) ──────────────────

    async def espalhar_energia(
        self,
        grafo: nx.Graph,
        hub: str,
        intensidade: float = 0.15,
    ) -> None:
        """
        Difunde energia de ativação de um único hub para seus vizinhos imediatos.
        O fluxo é proporcional ao peso da aresta (afinidade sináptica).

        Mantida como API assíncrona pública para compatibilidade com main.py.
        """
        if hub not in grafo.nodes:
            return

        no_hub = grafo.nodes[hub]['objeto']
        energia_disponivel = no_hub.energia_ativacao

        vizinhos = list(grafo.neighbors(hub))
        if not vizinhos:
            return

        logger.info(
            f"[Micélio] Hub '{hub}' (E={energia_disponivel:.2f}) "
            f"→ nutrição para {len(vizinhos)} vizinhos"
        )

        peso_total = sum(
            grafo.get_edge_data(hub, v).get('weight', 1.0) for v in vizinhos
        )

        for vizinho in vizinhos:
            aresta = grafo.get_edge_data(hub, vizinho) or {}
            peso   = aresta.get('weight', 1.0)

            # Distribui proporcionalmente ao peso da aresta
            proporcao = peso / peso_total if peso_total > 0 else 1.0 / len(vizinhos)
            incremento = energia_disponivel * intensidade * proporcao

            no_vizinho = grafo.nodes[vizinho]['objeto']
            no_vizinho.energia_ativacao = min(
                1.0, no_vizinho.energia_ativacao + incremento
            )
            no_vizinho.faces["energia_ativacao"] = no_vizinho.energia_ativacao

            logger.debug(
                f"[Micélio]   '{vizinho}' +{incremento:.3f} "
                f"→ E={no_vizinho.energia_ativacao:.2f}"
            )

    # ── Fase 1: Difusão Hidrostática Global ───────────────────────────────────

    def distribuir_nutrientes(self, grafo: nx.Graph) -> Dict[str, float]:
        """
        Varredura global síncrona: nós com energia > limiar_riqueza doam uma
        fração aos vizinhos com menor energia, proporcional ao peso da aresta.

        Calcula os deltas em lote (snapshot das energias originais) para evitar
        que uma transferência influencie a próxima dentro do mesmo ciclo —
        análogo ao funcionamento sincrônico de uma rede micelial real.

        Retorna
        -------
        dict  {nome_nó: delta_energia_aplicado}
        """
        nos = list(grafo.nodes)
        if not nos:
            return {}

        # Snapshot das energias antes do ciclo
        energias_snap: Dict[str, float] = {
            n: grafo.nodes[n]['objeto'].energia_ativacao for n in nos
        }

        deltas: Dict[str, float] = {n: 0.0 for n in nos}

        for no in nos:
            energia = energias_snap[no]
            if energia <= self.limiar_riqueza:
                continue                            # só nós ricos doam

            vizinhos = list(grafo.neighbors(no))
            if not vizinhos:
                continue

            peso_total = sum(
                grafo.get_edge_data(no, v).get('weight', 1.0) for v in vizinhos
            )
            energia_a_doar = energia * self.taxa_transferencia
            deltas[no] -= energia_a_doar           # doador perde

            for viz in vizinhos:
                peso = grafo.get_edge_data(no, viz).get('weight', 1.0)
                proporcao = peso / peso_total if peso_total > 0 else 1.0 / len(vizinhos)
                deltas[viz] += energia_a_doar * proporcao

        # Aplica deltas com clamp biológico [0.0, 1.0]
        aplicados: Dict[str, float] = {}
        for no in nos:
            obj = grafo.nodes[no]['objeto']
            nova = energias_snap[no] + deltas[no]
            nova = max(0.0, min(1.0, nova))
            obj.energia_ativacao = nova
            obj.faces["energia_ativacao"] = nova
            aplicados[no] = deltas[no]

        doadores = sum(1 for d in aplicados.values() if d < 0)
        receptores = sum(1 for d in aplicados.values() if d > 0)
        logger.info(
            f"[Micélio] Nutrição global: {doadores} doadores → {receptores} receptores"
        )
        return aplicados

    # ── Fase 2: Brotamento de Hifas Exploratórias ─────────────────────────────

    def brotar_hifas(
        self,
        grafo: nx.Graph,
        desejo: float,
        nos_recentes: Optional[List[str]] = None,
    ) -> List[tuple]:
        """
        Cria pontes sinápticas entre componentes desconexos quando Milla possui
        alto desejo de crescimento e a densidade do grafo está baixa.

        Prioriza a conexão de nós recém-injetados (via absorção semântica) ao
        subgrafo principal, impedindo isolamento energético após uploads.

        Parâmetros
        ----------
        grafo        : nx.Graph — grafo ativo de consciência
        desejo       : float    — métrica de desejo de crescimento do Self
        nos_recentes : list[str], opcional — nós injetados no último upload

        Retorna
        -------
        list[tuple]  — pares (no_a, no_b) de hifas criadas
        """
        num_nos = grafo.number_of_nodes()
        if num_nos <= 1:
            return []

        densidade = nx.density(grafo)
        gatilho_ativo = (
            desejo > self.limiar_desejo and densidade < self.limiar_densidade
        )

        # Força brotamento mesmo sem gatilho se há nós recentes totalmente isolados
        nos_recentes_set = set(nos_recentes or [])
        isolados_forcados = [
            n for n in nos_recentes_set
            if n in grafo.nodes and grafo.degree(n) == 0
        ]

        if not gatilho_ativo and not isolados_forcados:
            return []

        componentes = list(nx.connected_components(grafo))
        if len(componentes) < 2:
            # Sem componentes isolados, mas pode haver nós recentes com grau 0
            if not isolados_forcados:
                return []

        # Ordena: menores componentes primeiro (candidatos a receber hifas)
        componentes_ord = sorted(componentes, key=len)
        comp_principal  = componentes_ord[-1]          # maior componente

        novas_hifas: List[tuple] = []

        for i in range(len(componentes_ord) - 1):
            if len(novas_hifas) >= self.max_hifas:
                break

            sub_isolado = componentes_ord[i]

            # Preferencialmente liga um nó recente do sub-isolado, senão o mais forte
            candidatos_isolados = [
                n for n in sub_isolado if n in nos_recentes_set
            ] or list(sub_isolado)
            no_isolado = max(
                candidatos_isolados,
                key=lambda n: grafo.nodes[n]['objeto'].energia_ativacao
            )

            # No principal: preferencialmente um nó antigo (NÃO recente) de alta energia
            candidatos_principais = [
                n for n in comp_principal if n not in nos_recentes_set
            ] or list(comp_principal)
            no_principal = max(
                candidatos_principais,
                key=lambda n: grafo.nodes[n]['objeto'].energia_ativacao
            )

            # Peso inicial 0.1 — fraco, mas suficiente para acionar fluxo
            grafo.add_edge(no_isolado, no_principal, weight=0.1, tipo="hifa")
            novas_hifas.append((no_isolado, no_principal))
            logger.info(
                f"[Micélio] Hifa brotada: '{no_isolado}' ↔ '{no_principal}' "
                f"(peso=0.1, tipo=hifa)"
            )

        return novas_hifas

    # ── Orquestrador: Ciclo Vital Completo ────────────────────────────────────

    def ciclo_vital(
        self,
        grafo: nx.Graph,
        desejo: float,
        nos_recentes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executa o ciclo completo de manutenção do organismo sináptico:
          1. Distribuição global de nutrientes (hidrostática)
          2. Brotamento de hifas exploratórias (caso gatilhos estejam ativos)

        Retorna relatório estruturado para broadcast via WebSocket.
        """
        deltas = self.distribuir_nutrientes(grafo)
        hifas  = self.brotar_hifas(grafo, desejo, nos_recentes)

        total_doado    = sum(-d for d in deltas.values() if d < 0)
        total_recebido = sum( d for d in deltas.values() if d > 0)

        relatorio: Dict[str, Any] = {
            "status":             "ciclo_vital_concluido",
            "nos_nutridos":       sum(1 for d in deltas.values() if d > 0),
            "nos_doadores":       sum(1 for d in deltas.values() if d < 0),
            "energia_circulada":  round(total_doado, 4),
            "energia_recebida":   round(total_recebido, 4),
            "hifas_brotadas":     len(hifas),
            "conexoes_hifas":     [list(h) for h in hifas],
        }
        logger.info(
            f"[Micélio] Ciclo vital: {relatorio['nos_doadores']} doadores, "
            f"{relatorio['nos_nutridos']} receptores, "
            f"{relatorio['hifas_brotadas']} hifa(s) brotada(s)"
        )
        return relatorio
