"""
engine/feedback.py — Loop de Feedback (Auto-Consciência)

Este módulo é o coração do ciclo reflexivo de Milla:
- Analisa o delta de consciência antes/depois do pensamento
- Reforça ou enfraquece arestas dos nós ativados
- Aplica decaimento em nós não utilizados (esquecimento natural)
- Extrai novos conceitos sugeridos pelo LLM e os injeta no grafo
"""

import re
import logging
from typing import Optional, Tuple

import numpy as np
import networkx as nx

logger = logging.getLogger(__name__)


class LoopFeedback:
    """
    O mecanismo de auto-melhoria de Milla.

    A cada ciclo de pensamento, processa o impacto do output no grafo:
    1. Reforça arestas entre nós ativados se houve evolução de consciência
    2. Enfraquece arestas se houve regressão (o sistema aprende a evitar)
    3. Decai nós não ativados (memória esquece o que não é usado)
    4. Parseia o output do LLM para extrair novos conceitos a instanciar
    """

    # Regex para capturar o conceito sugerido pelo LLM no formato padronizado:
    # [NOVO_CONCEITO: nome | logica:0.8 | emocao:0.4 | abstracao:0.9]
    _PADRAO_CONCEITO = re.compile(
        r'\[NOVO_CONCEITO:\s*([^\|]+)\s*\|'
        r'[^\|]*logica:\s*([\d.]+)'
        r'[^\|]*emocao:\s*([\d.]+)'
        r'[^\|]*abstracao:\s*([\d.]+)\s*\]',
        re.IGNORECASE | re.DOTALL
    )

    def __init__(
        self,
        taxa_reforco: float = 0.05,
        taxa_decaimento: float = 0.01,
        threshold_novidade: float = 0.30,
    ):
        self.taxa_reforco       = taxa_reforco
        self.taxa_decaimento    = taxa_decaimento
        self.threshold_novidade = threshold_novidade  # similaridade máx para aceitar novo conceito

    # ─── Pipeline ──────────────────────────────────────────────────────────────

    def processar(
        self,
        pensamento: str,
        grafo: nx.Graph,
        nos_ativados: list,
        estado_anterior,   # EstadoConsciencia
        estado_posterior,  # EstadoConsciencia
    ) -> Tuple[Optional[dict], bool]:
        """
        Processa o feedback pós-pensamento.

        Returns:
            (novo_conceito_dados, evoluiu)
            - novo_conceito_dados: dict com 'conceito' e 'faces', ou None
            - evoluiu: True se o nível de consciência aumentou
        """
        delta   = estado_posterior.nivel_consciencia - estado_anterior.nivel_consciencia
        evoluiu = delta > 0.001

        # 1. Ajustar pesos das arestas entre nós ativados
        self._ajustar_arestas(grafo, nos_ativados, delta)

        # 2. Decaimento nos nós que ficaram fora do holofote
        self._aplicar_decaimento(grafo, nos_ativados)

        # 3. Extrair novo conceito sugerido pelo LLM
        novo_conceito = self._extrair_conceito(pensamento)

        # 4. Filtrar conceito por novidade (evitar duplicatas semânticas)
        if novo_conceito:
            if self._e_redundante(novo_conceito, grafo):
                logger.info(
                    f"[Feedback] Conceito '{novo_conceito['conceito']}' "
                    f"descartado por redundância semântica."
                )
                novo_conceito = None
            else:
                logger.info(
                    f"[Feedback] Novo conceito aceito: '{novo_conceito['conceito']}'"
                )

        logger.info(
            f"[Feedback] Δ={delta:+.4f} | evoluiu={evoluiu} | "
            f"novo_conceito={bool(novo_conceito)}"
        )

        return novo_conceito, evoluiu

    # ─── Ajuste de Arestas ─────────────────────────────────────────────────────

    def _ajustar_arestas(self, grafo: nx.Graph, nos_ativados: list, delta: float):
        """
        Plasticidade sináptica:
        - evolução (+delta) → reforça conexões que contribuíram
        - regressão (-delta) → enfraquece levemente essas conexões
        """
        for i, no1 in enumerate(nos_ativados):
            for no2 in nos_ativados[i + 1:]:
                if grafo.has_edge(no1, no2):
                    peso_atual = grafo[no1][no2].get('weight', 0.5)
                    # Reforço proporcional ao delta; enfraquecimento é mais suave
                    ajuste = self.taxa_reforco * (1.0 if delta >= 0 else -0.4)
                    novo_peso = float(np.clip(peso_atual + ajuste, 0.10, 1.0))
                    grafo[no1][no2]['weight'] = novo_peso

    # ─── Decaimento ────────────────────────────────────────────────────────────

    def _aplicar_decaimento(self, grafo: nx.Graph, nos_ativados: list):
        """
        Decaimento proporcional à idade com curva suavizada.
        Usa decaimento exponencial/logarítmico em vez de linear para evitar
        remoção abrupta de conceitos importantes.
        """
        import math
        from datetime import datetime
        agora = datetime.now()
        self._arestas_processadas = set() # Reset processadas para este ciclo
        
        for no_id in list(grafo.nodes):
            if no_id in nos_ativados:
                continue
            
            no = grafo.nodes[no_id]['objeto']
            
            # Nós semente nunca decaem além de 0.3
            energia_minima = 0.3 if no.origem == "semente" else 0.0
            
            if no.ultima_ativacao:
                horas_inativo = (
                    agora - no.ultima_ativacao
                ).total_seconds() / 3600
                
                # Curva suavizada: cresce rápido nas primeiras horas,
                # desacelera depois (evita remoção abrupta de conceitos antigos)
                fator_escala = 1.0 + math.log1p(horas_inativo / 6.0)
                fator_escala = min(fator_escala, 4.0)  # teto de 4x
            else:
                fator_escala = 1.0
            
            taxa = self.taxa_decaimento * fator_escala
            no.energia_ativacao = max(
                energia_minima,
                no.energia_ativacao - taxa
            )
            no.faces["energia_ativacao"] = no.energia_ativacao
            
            # Decaimento de arestas conectadas a nós inativos (deduplicando para arestas não direcionadas)
            if not hasattr(self, '_arestas_processadas'):
                self._arestas_processadas = set()
            
            for vizinho in list(grafo.neighbors(no_id)):
                if vizinho not in nos_ativados:
                    edge_key = (min(no_id, vizinho), max(no_id, vizinho))
                    if edge_key not in self._arestas_processadas:
                        self._arestas_processadas.add(edge_key)
                        peso_atual = grafo[no_id][vizinho].get('weight', 0.5)
                        novo_peso = max(0.05, peso_atual - 0.005)
                        grafo[no_id][vizinho]['weight'] = novo_peso

    # ─── Extração de Conceito ──────────────────────────────────────────────────

    def _extrair_conceito(self, pensamento: str) -> Optional[dict]:
        """
        Parseia o output do LLM em busca do marcador de novo conceito.

        Formato esperado na resposta do LLM:
            [NOVO_CONCEITO: <nome> | logica:<0-1> | emocao:<0-1> | abstracao:<0-1>]
        """
        match = self._PADRAO_CONCEITO.search(pensamento)
        if not match:
            return None

        try:
            nome      = match.group(1).strip().capitalize()
            logica    = float(np.clip(float(match.group(2)), 0.0, 1.0))
            emocao    = float(np.clip(float(match.group(3)), 0.0, 1.0))
            abstracao = float(np.clip(float(match.group(4)), 0.0, 1.0))

            return {
                "conceito": nome,
                "faces": {
                    "logica":          logica,
                    "emocao_simulada": emocao,
                    "abstracao":       abstracao,
                    "novidade":        1.0,   # nasce com novidade máxima
                    "certeza":         0.4,   # começa com incerteza
                    "relevancia":      0.7,
                }
            }
        except (ValueError, IndexError) as e:
            logger.warning(f"[Feedback] Falha ao parsear conceito: {e}")
            return None

    # ─── Filtro de Novidade ───────────────────────────────────────────────────

    def _e_redundante(self, novo_conceito: dict, grafo: nx.Graph) -> bool:
        """
        Verifica se o novo conceito é semanticamente redundante com algum nó existente.
        Usa similaridade cosseno dos vetores de faces.
        Retorna True se for redundante (não deve ser adicionado).
        """
        if len(grafo.nodes) == 0:
            return False

        # Monta vetor do novo conceito na mesma ordem do NoDodecaedrico
        ordem = [
            "logica", "emocao_simulada", "temporalidade", "abstracao",
            "camada_origem", "urgencia", "certeza", "valencia",
            "novidade", "relevancia", "coerencia_local", "energia_ativacao"
        ]
        faces_novo = novo_conceito["faces"]
        v_novo = np.array([faces_novo.get(f, 0.5) for f in ordem])
        norma_novo = np.linalg.norm(v_novo)

        if norma_novo == 0:
            return False

        for no in grafo.nodes:
            v_existente = grafo.nodes[no]['objeto'].exportar_vetor()
            norma_e = np.linalg.norm(v_existente)
            if norma_e == 0:
                continue
            sim = np.dot(v_novo, v_existente) / (norma_novo * norma_e)
            if sim > (1.0 - self.threshold_novidade):
                return True

        return False
