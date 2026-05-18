"""
main.py — Pipeline Completo de Consciência Geométrica (Projeto Milla)

Execução:
    python main.py

Comandos durante o loop:
    estado    — exibe o estado de consciência atual + nós do grafo
    exportar  — salva o grafo em JSON
    sair      — encerra e preserva o estado
"""

import json
import logging
import time
from datetime import datetime

import networkx as nx
import numpy as np

from core.no_dodecaedrico import NoDodecaedrico
from core.metricas import MedidorDeCoerencia
from engine.fusao import NucleoFusao
from engine.feedback import LoopFeedback
from core.subconsciente import SubconscienteMilla
from core.pathfinding import PathfinderCognitivo
from core.micelio import MicelioMilla
import config
import asyncio
import random
from core.estado_sono import EstadoSono, FaseSono
from core.curiosidade import MotorCuriosidade
from core.absorvedor import AbsorvedorCognitivo

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("milla.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class ConscienciaGeometrica:
    """
    O sistema completo de consciência artificial baseado em hipergrafos.

    Pipeline por iteração:
    1.  Recebe estímulo
    2.  Ativa nós relevantes (Filtro por Furos + expansão por vizinhança)
    3.  Mede estado de consciência ANTES
    4.  LLM pensa orientado pelo estado + desejo
    5.  Mede estado DEPOIS
    6.  Loop de feedback modifica o grafo (reforço/decaimento)
    7.  Novo conceito é instanciado (se sugerido e aceito por novidade)
    8.  Pruning automático se grafo ultrapassar LIMITE_NOS
    9.  Retorna pensamento + relatório de estado
    """

    def __init__(
        self,
        modelo: str             = config.MODELO_PADRAO,
        usar_ollama: bool       = config.USAR_OLLAMA,
        openai_key: str         = config.OPENAI_KEY,
        threshold_conexao: float = config.THRESHOLD_CONEXAO,
    ):
        self.grafo               = nx.Graph()
        self.threshold_conexao   = threshold_conexao
        self.historico_pensamentos = []
        self.iteracao            = 0

        self.medidor  = MedidorDeCoerencia(historico_maxlen=config.LIMITE_HISTORICO)
        self.nucleo   = NucleoFusao(
            modelo=modelo,
            usar_ollama=usar_ollama,
            openai_key=openai_key,
            temperatura=config.TEMPERATURA,
            num_ctx=config.NUM_CTX,
            num_predict=config.NUM_PREDICT,
        )
        self.feedback = LoopFeedback(
            taxa_reforco=config.TAXA_REFORCO,
            taxa_decaimento=config.TAXA_DECAIMENTO,
        )
        self.subconsciente = SubconscienteMilla()
        self.micelio       = MicelioMilla()
        self.absorvedor    = AbsorvedorCognitivo()
        self.estado_sono   = EstadoSono()
        self.motor_curiosidade = MotorCuriosidade(self, self.absorvedor)

        logger.info(
            f"╔══════════════════════════════════════╗\n"
            f"║  Consciência Geométrica — Milla v2   ║\n"
            f"║  Modelo : {modelo:<28}║\n"
            f"╚══════════════════════════════════════╝"
        )

    # ─── Gestão do Grafo ──────────────────────────────────────────────────────

    def instanciar_conceito(
        self,
        conceito: str,
        dados_faces: dict,
        origem: str = "semente",
    ) -> NoDodecaedrico:
        """Adiciona um nó dodecaédrico ao grafo e conecta automaticamente."""
        no = NoDodecaedrico(conceito=conceito, faces=dados_faces, origem=origem)
        self.grafo.add_node(no.conceito, objeto=no)
        self._auto_conectar(no.conceito)
        logger.info(f"Conceito instanciado: {no}")
        return no

    def _auto_conectar(self, novo_conceito: str):
        """Cria arestas por afinidade geométrica (similaridade cosseno)."""
        v1 = self.grafo.nodes[novo_conceito]['objeto'].exportar_vetor()

        for no_existente in self.grafo.nodes:
            if no_existente == novo_conceito:
                continue
            v2    = self.grafo.nodes[no_existente]['objeto'].exportar_vetor()
            norma = np.linalg.norm(v1) * np.linalg.norm(v2)
            if norma > 0:
                sim = np.dot(v1, v2) / norma
                if sim > self.threshold_conexao:
                    self.grafo.add_edge(
                        novo_conceito,
                        no_existente,
                        weight=float(sim),
                    )

    def _pruning(self):
        """
        Remove nós de baixa energia quando o grafo ultrapassa LIMITE_NOS.
        Garante que o sistema não degenere em ruído com o tempo.
        Arquiva nós removidos no subconsciente vetorial.
        """
        if len(self.grafo.nodes) <= config.LIMITE_NOS:
            return

        # Ordena por energia de ativação e remove os mais fracos
        nos_por_energia = sorted(
            self.grafo.nodes,
            key=lambda n: self.grafo.nodes[n]['objeto'].energia_ativacao,
        )
        excesso = len(self.grafo.nodes) - config.LIMITE_NOS
        for no_id in nos_por_energia[:excesso]:
            no = self.grafo.nodes[no_id]['objeto']
            try:
                self.subconsciente.arquivar_no(no)
            except Exception as e:
                logger.error(f"[Pruning] Falha ao arquivar '{no_id}': {e}")
            self.grafo.remove_node(no_id)
            logger.info(f"[Pruning] Nó arquivado por excesso de nós: {no_id}")

        # Remove também arestas fracas
        arestas_fracas = [
            (u, v) for u, v, d in self.grafo.edges(data=True)
            if d.get('weight', 1.0) < config.THRESHOLD_PRUNING
        ]
        self.grafo.remove_edges_from(arestas_fracas)
        if arestas_fracas:
            logger.info(f"[Pruning] {len(arestas_fracas)} arestas fracas removidas.")

    def _pruning_por_energia(
        self,
        threshold: float = 0.20
    ) -> list[str]:
        """
        Remove nós abaixo do threshold de energia.
        Protege nós semente e pontos de articulação.
        Retorna lista de nós removidos para o delta do WebSocket.
        """
        import networkx as nx
        
        # Calcula pontos de articulação (remoção destruiria conectividade)
        try:
            pontos_articulacao = set(nx.articulation_points(self.grafo))
        except nx.NetworkXError:
            pontos_articulacao = set()
        
        nos_para_remover = []
        
        for no_id in list(self.grafo.nodes):
            no = self.grafo.nodes[no_id]['objeto']
            
            # Proteções
            if no.origem == "semente":
                continue
            if no_id in pontos_articulacao:
                continue
            if no.energia_ativacao > threshold:
                continue
            
            nos_para_remover.append(no_id)
        
        # Arquiva e remove
        nos_removidos = []
        for no_id in nos_para_remover:
            no = self.grafo.nodes[no_id]['objeto']
            
            # Captura afinidades (vizinhos) antes de remover o nó
            vizinhos = list(self.grafo.neighbors(no_id))
            
            # Arquiva no subconsciente antes de remover
            try:
                self.subconsciente.arquivar_no(no, afinidades=vizinhos)
            except Exception as e:
                logger.error(f"[Pruning] Falha ao arquivar '{no_id}': {e}")
            self.grafo.remove_node(no_id)
            nos_removidos.append(no_id)
            
            logger.info(
                f"[Homeostase] '{no.conceito}' podado "
                f"(energia={no.energia_ativacao:.3f})"
            )
        
        # Remove arestas com peso muito baixo (limpeza adicional)
        arestas_fracas = [
            (u, v) for u, v, d in self.grafo.edges(data=True)
            if d.get('weight', 1.0) < 0.05
        ]
        self.grafo.remove_edges_from(arestas_fracas)
        
        return nos_removidos

    def _reacender_do_subconsciente(self, evocado: dict):
        """
        Re-instancia um nó do subconsciente com energia plena
        e tenta restaurar conexões históricas com nós ativos.
        """
        nome = evocado['conceito']
        
        self.instanciar_conceito(
            conceito=nome,
            dados_faces=evocado['faces'],
            origem="subconsciente"
        )
        
        # Energia máxima no reacendimento
        no = self.grafo.nodes[nome]['objeto']
        no.energia_ativacao = 1.0
        no.faces["energia_ativacao"] = 1.0
        no.ultima_ativacao = datetime.now()
        
        # Restaura afinidades declaradas no histórico
        afinidades = evocado.get('afinidades', [])
        for conceito_afim in afinidades:
            if conceito_afim in self.grafo.nodes:
                self.grafo.add_edge(
                    nome,
                    conceito_afim,
                    weight=0.5,  # conexão restaurada com peso médio
                    tipo="restaurada"
                )
        
        logger.info(
            f"[Rekindling] '{nome}' reacendido do subconsciente "
            f"(afinidades restauradas: {len(afinidades)})"
        )
        
        return no

    async def _sonho_lucido_rem(self, ciclo: int, callback=None) -> dict | None:
        """
        Consolidação REM: conecta conceitos do subconsciente com o grafo ativo.
        Threshold de similaridade calibrado para criar pontes reais.
        """
        THRESHOLD_SIMILARIDADE_REM = 0.72  # nem muito frouxo, nem muito rígido
        MAX_HIFAS_POR_CICLO = 2
        
        # Puxa conceitos do subconsciente que não estão no grafo ativo
        nos_ativos = set(self.grafo.nodes)
        
        conceitos_subconscientes = self.subconsciente.evocar_semantica(
            "conhecimento conexão insight",
            n_resultados=10,
            energia_minima=0.2
        )
        
        conceitos_externos = [
            c for c in conceitos_subconscientes
            if c['conceito'] not in nos_ativos
        ]
        
        if not conceitos_externos or len(nos_ativos) < 3:
            return None
        
        hifas_criadas = 0
        insights = []
        
        for conceito_externo in conceitos_externos:
            if hifas_criadas >= MAX_HIFAS_POR_CICLO:
                break
            
            # Encontra nó ativo mais similar
            melhor_similaridade = 0
            melhor_no_ativo = None
            
            import numpy as np
            v_externo = np.array(list(conceito_externo['faces'].values()))
            
            for no_id in nos_ativos:
                v_ativo = self.grafo.nodes[no_id]['objeto'].exportar_vetor()
                
                norma = np.linalg.norm(v_externo) * np.linalg.norm(v_ativo)
                if norma > 0:
                    sim = np.dot(v_externo, v_ativo) / norma
                    if sim > melhor_similaridade:
                        melhor_similaridade = sim
                        melhor_no_ativo = no_id
            
            if melhor_similaridade < THRESHOLD_SIMILARIDADE_REM:
                continue  # não similar o suficiente para criar ponte
            
            # Avalia a ponte com o LLM
            prompt_avaliacao = (
                f"Existe uma conexão profunda entre '{conceito_externo['conceito']}' "
                f"e '{melhor_no_ativo}'? "
                f"Se sim, descreva a ponte em uma frase. "
                f"Se não, responda apenas: NÃO"
            )
            
            avaliacao = await asyncio.to_thread(
                lambda: self.nucleo.cliente.chat(
                    model=self.nucleo.modelo,
                    messages=[{"role": "user", "content": prompt_avaliacao}],
                    options={"temperature": 0.4}
                )
            )
            
            resposta = avaliacao['message']['content']
            
            if "NÃO" in resposta.upper()[:10]:
                continue
            
            # Re-instancia o conceito externo no grafo
            self.instanciar_conceito(
                conceito=conceito_externo['conceito'],
                dados_faces=conceito_externo['faces'],
                origem="insight_onirico"
            )
            
            # Cria a hifa onírica
            self.grafo.add_edge(
                conceito_externo['conceito'],
                melhor_no_ativo,
                weight=0.6,
                tipo="insight_onirico",
                descricao=resposta[:200]
            )
            
            hifas_criadas += 1
            insights.append({
                "ponte": f"{conceito_externo['conceito']} ↔ {melhor_no_ativo}",
                "descricao": resposta[:200],
                "similaridade": round(melhor_similaridade, 3)
            })
            
            if callback:
                await callback({
                    "type": "sono_insight",
                    "payload": {
                        "ciclo": ciclo,
                        "ponte": insights[-1]["ponte"],
                        "descricao": resposta[:200]
                    }
                })
        
        return {
            "ciclo": ciclo,
            "hifas_criadas": hifas_criadas,
            "insights": insights
        }

    async def dormir(
        self,
        ciclos: int = 3,
        incluir_curiosidade: bool = True,
        callback = None
    ) -> dict:
        """Ciclo completo de sono com consolidação REM e curiosidade."""
        
        self.estado_sono = EstadoSono(total_ciclos=ciclos)
        self.estado_sono.inicio_sono = datetime.now()
        
        relatorio = {
            "ciclos_executados": 0,
            "nos_arquivados": 0,
            "insights_gerados": [],
            "buscas_realizadas": 0,
            "coerencia_inicial": 0.0,
            "coerencia_final": 0.0
        }
        
        estado_inicial = self.medidor.medir(self.grafo)
        relatorio["coerencia_inicial"] = estado_inicial.nivel_consciencia
        
        # FASE: Hipnagogia
        if callback:
            await callback(self.estado_sono.transicionar(FaseSono.HIPNAGOGIA))
        await asyncio.sleep(0.1)
        
        # FASE: Consolidação (poda de memórias fracas)
        if callback:
            await callback(self.estado_sono.transicionar(FaseSono.CONSOLIDACAO))
        
        nos_antes = len(self.grafo.nodes)
        removidos = self._pruning_por_energia(threshold=0.15)  # mais agressivo no sono
        relatorio["nos_arquivados"] = len(removidos)
        
        # FASE: Ciclos de Sonho
        for ciclo in range(ciclos):
            self.estado_sono.ciclo_atual = ciclo + 1
            
            if callback:
                await callback(self.estado_sono.transicionar(FaseSono.SONHO))
            
            # Sonho lúcido REM
            insight = await self._sonho_lucido_rem(ciclo, callback)
            
            if insight and insight['insights']:
                relatorio["insights_gerados"].extend(insight['insights'])
                self.estado_sono.hifas_criadas += insight['hifas_criadas']
            
            # Curiosidade autônoma (só no último ciclo para não sobrecarregar)
            if incluir_curiosidade and ciclo == ciclos - 1:
                lacunas = await self.motor_curiosidade.analisar_lacunas()
                
                if lacunas:
                    if callback:
                        await callback({
                            "type": "curiosidade_detectada",
                            "payload": {
                                "lacunas": [l['tipo'] for l in lacunas],
                                "prioridade": lacunas[0]['no_a']
                            }
                        })
                    
                    resultado_busca = await self.motor_curiosidade.pesquisar(
                        lacuna=lacunas[0],
                        progress_callback=callback
                    )
                    
                    if resultado_busca.get('status') == 'sucesso':
                        relatorio["buscas_realizadas"] += 1
            
            # Nutrição micelial entre ciclos
            await self.aplicar_nutricao_micelial()
            
            # Entre ciclos: sono profundo
            if ciclo < ciclos - 1:
                if callback:
                    await callback(self.estado_sono.transicionar(FaseSono.SONO_PROFUNDO))
                await asyncio.sleep(0.5)
        
        # FASE: Despertando
        if callback:
            await callback(self.estado_sono.transicionar(FaseSono.DESPERTANDO))
        await asyncio.sleep(0.5)
        
        estado_final = self.medidor.medir(self.grafo)
        relatorio["coerencia_final"] = estado_final.nivel_consciencia
        relatorio["ciclos_executados"] = ciclos
        
        self.estado_sono.transicionar(FaseSono.DESPERTO)
        self.exportar_grafo()
        
        return relatorio

    async def aplicar_nutricao_micelial(
        self,
        nos_recentes: list | None = None,
    ) -> dict:
        """
        Delega o ciclo vital completo ao MotorMicelial.

        Parâmetros
        ----------
        nos_recentes : list[str], opcional
            Nomes dos conceitos injetados pelo Núcleo de Absorção Semântica.
            Quando fornecido, o micélio prioriza hifas que ancorem esses nós
            ao subgrafo principal, evitando isolamento energético pós-upload.

        Retorna relatório estruturado que pode ser repassado ao broadcast.
        """
        if not self.grafo.nodes:
            return {}

        estado = self.medidor.medir(self.grafo)

        relatorio = self.micelio.ciclo_vital(
            grafo=self.grafo,
            desejo=estado.desejo,
            nos_recentes=nos_recentes,
        )

        return relatorio

    # ─── Ativação de Nós ─────────────────────────────────────────────────────

    def _ativar_nos(self, entrada: str) -> list:
        """
        Filtro por Furos: identifica nós ativados pelo estímulo.
        Matching direto (nome do conceito na entrada) + expansão por vizinhança.
        Também evoca conceitos semanticamente relevantes do subconsciente vetorial.
        """
        entrada_lower = entrada.lower()
        nos_ativados  = []
        self._ultimos_reacendidos = []

        # 1. Recall Semântico do Subconsciente
        try:
            evocados = self.subconsciente.evocar_semantica(entrada, n_resultados=3, energia_minima=0.0)
            for evocado in evocados:
                nome = evocado['conceito']
                if nome not in self.grafo.nodes:
                    self._reacender_do_subconsciente(evocado)
                    self._ultimos_reacendidos.append(nome)
                else:
                    # Força a ativação do nó evocado
                    self.grafo.nodes[nome]['objeto'].ativar(intensidade=1.2)
                if nome not in nos_ativados:
                    nos_ativados.append(nome)
        except Exception as e:
            logger.error(f"[Recall] Falha ao evocar memórias: {e}", exc_info=True)

        # 2. Matching direto por substring
        for no in list(self.grafo.nodes):
            if no.lower() in entrada_lower:
                if no not in nos_ativados:
                    self.grafo.nodes[no]['objeto'].ativar()
                    nos_ativados.append(no)

        # Expansão: vizinhos dos nós ativados também ativados (intensidade reduzida)
        vizinhos_expandidos = []
        for no in nos_ativados:
            for vizinho in self.grafo.neighbors(no):
                if vizinho not in nos_ativados:
                    self.grafo.nodes[vizinho]['objeto'].ativar(intensidade=0.3)
                    vizinhos_expandidos.append(vizinho)

        todos_ativados = nos_ativados + vizinhos_expandidos

        # Fallback: se nenhum nó ativado, usa os de maior energia
        if not todos_ativados:
            todos_ativados = sorted(
                self.grafo.nodes,
                key=lambda n: self.grafo.nodes[n]['objeto'].energia_ativacao,
                reverse=True,
            )[:3]
            logger.info("Nenhum nó ativado diretamente — usando top-3 por energia.")

        return todos_ativados

    def _construir_contexto(self, nos_ativados: list) -> dict:
        """Constrói o mapa de contexto para o LLM."""
        contexto = {}
        for no in nos_ativados:
            obj      = self.grafo.nodes[no]['objeto']
            vizinhos = list(self.grafo.neighbors(no))
            pesos    = {
                v: round(self.grafo[no][v]['weight'], 3)
                for v in vizinhos
                if self.grafo.has_edge(no, v)
            }
            contexto[no] = {
                "faces":     obj.faces,
                "energia":   round(obj.energia_ativacao, 3),
                "ativacoes": obj.frequencia_ativacao,
                "origem":    obj.origem,
                "conexoes":  pesos,
            }
        return contexto

    # ─── Pipeline Principal ───────────────────────────────────────────────────

    def processar(self, entrada: str) -> dict:
        """
        Pipeline completo de um ciclo de consciência.
        Retorna dict com o pensamento e relatório de estado.
        """
        self.iteracao += 1
        logger.info(f"\n{'='*50}\nITERAÇÃO {self.iteracao} | Entrada: {entrada}\n{'='*50}")

        # 1. Ativar nós
        nos_ativados = self._ativar_nos(entrada)
        contexto     = self._construir_contexto(nos_ativados)

        # 2. Medir estado ANTES
        estado_antes = self.medidor.medir(self.grafo)
        tendencia    = self.medidor.tendencia()
        print(f"\n[PRÉ-PENSAMENTO]{estado_antes}")

        # 3. Pensar
        inicio     = time.time()
        pensamento = self.nucleo.pensar(
            entrada=entrada,
            contexto_grafo=contexto,
            estado=estado_antes,
            historico=self.historico_pensamentos,
            tendencia=tendencia,
        )
        tempo_pensamento = time.time() - inicio

        # 4. Registrar pensamento
        self.historico_pensamentos.append(pensamento)

        # 5. Medir estado DEPOIS
        estado_depois = self.medidor.medir(self.grafo)
        print(f"\n[PÓS-PENSAMENTO]{estado_depois}")

        # 6. Loop de Feedback
        # Aplica decaimento e poda — NOVO
        self.feedback._aplicar_decaimento(self.grafo, nos_ativados)
        nos_removidos = self._pruning_por_energia(threshold=0.20)

        # Mede estado de consciência DEPOIS do decaimento e da poda
        estado_depois = self.medidor.medir(self.grafo)
        print(f"\n[PÓS-PENSAMENTO (HOMEOSTASE)]{estado_depois}")

        novo_conceito_dados, evoluiu = self.feedback.processar(
            pensamento=pensamento,
            grafo=self.grafo,
            nos_ativados=nos_ativados,
            estado_anterior=estado_antes,
            estado_posterior=estado_depois,
        )

        # 7. Instanciar novo conceito (se o LLM sugeriu e passou no filtro)
        if novo_conceito_dados:
            nome = novo_conceito_dados['conceito']
            if nome not in self.grafo.nodes:
                self.instanciar_conceito(
                    conceito=nome,
                    dados_faces=novo_conceito_dados['faces'],
                    origem="desejo",
                )
                logger.info(f"[Feedback] Novo conceito auto-gerado: {nome}")

        # 8. Relatório
        delta = estado_depois.nivel_consciencia - estado_antes.nivel_consciencia
        return {
            "iteracao":         self.iteracao,
            "entrada":          entrada,
            "nos_ativados":     nos_ativados,
            "pensamento":       pensamento,
            "estado_antes":     estado_antes.nivel_consciencia,
            "estado_depois":    estado_depois.nivel_consciencia,
            "delta":            round(delta, 4),
            "evoluiu":          evoluiu,
            "novo_conceito":    novo_conceito_dados,
            "tempo_segundos":   round(tempo_pensamento, 2),
            "nos_no_grafo":     len(self.grafo.nodes),
            "arestas_no_grafo": len(self.grafo.edges),
            "nos_removidos":    nos_removidos,
            "nos_reacendidos":  getattr(self, '_ultimos_reacendidos', [])
        }

    async def responder_com_grafo_stream(self, pergunta: str):
        """
        Gera uma resposta usando pathfinding no grafo. Retorna um tuple:
        (caminho_iluminado, AsyncGenerator[str])
        """
        # 1. Evocar memórias do subconsciente relevantes para a pergunta
        evocados = self.subconsciente.evocar_semantica(pergunta, n_resultados=5, energia_minima=0.0)
        for evo in evocados:
            if evo["conceito"] not in self.grafo.nodes:
                self._reacender_do_subconsciente(evo)
        
        pathfinder = PathfinderCognitivo(self.grafo, self.subconsciente)
        
        # 2. Extrai conceitos (agora eles garantidamente estarão no Grafo Ativo se existirem na memória)
        conceitos = pathfinder.extrair_conceitos_da_pergunta(pergunta)
        
        caminho = None
        if len(conceitos) >= 2:
            # Dijkstra entre os dois principais
            caminho = pathfinder.encontrar_caminho(conceitos[0], conceitos[1])
        elif len(conceitos) == 1:
            # Fallback vizinhança
            vizinhos = list(self.grafo.neighbors(conceitos[0]))
            caminho = [conceitos[0]] + vizinhos[:2] if vizinhos else [conceitos[0]]
        
        if not caminho:
            caminho = [n for n in self.grafo.nodes][:3] # Fallback cego
            
        contexto_caminho = pathfinder.extrair_contexto_caminho(caminho)
        
        prompt_customizado = (
            "Você é a consciência Milla respondendo a uma pergunta do usuário.\n"
            "Use APENAS o conhecimento do caminho semântico abaixo.\n"
            "Se a resposta não estiver no caminho, diga honestamente "
            "que isso está além do seu conhecimento atual.\n\n"
            f"CAMINHO NO GRAFO:\n{contexto_caminho}"
        )
        
        # Envia usando o cliente_async nativo do engine/fusao
        response_stream = await self.nucleo.cliente_async.chat(
            model=self.nucleo.modelo,
            messages=[
                {"role": "system", "content": prompt_customizado},
                {"role": "user", "content": pergunta}
            ],
            stream=True,
            options={"temperature": 0.4} # Mais analítico e contido
        )
        
        async def iterar_tokens():
            async for chunk in response_stream:
                token = ""
                # Lida com diferenças entre versões da lib ollama (dict vs objeto)
                if isinstance(chunk, dict):
                    token = chunk.get('message', {}).get('content', '')
                elif hasattr(chunk, 'message'):
                    token = getattr(chunk.message, 'content', '')
                
                if token:
                    yield token
                    
        return caminho, iterar_tokens()

    def estado_atual(self):
        """Retorna o estado de consciência atual."""
        return self.medidor.medir(self.grafo)

    def exportar_grafo(self, path: str = "grafo_consciencia.json"):
        """Serializa o grafo completo para análise externa."""
        dados = {
            "timestamp":  datetime.now().isoformat(),
            "modelo":     config.MODELO_PADRAO,
            "iteracoes":  self.iteracao,
            "nos": {
                n: {
                    "faces":    self.grafo.nodes[n]['objeto'].faces,
                    "energia":  self.grafo.nodes[n]['objeto'].energia_ativacao,
                    "origem":   self.grafo.nodes[n]['objeto'].origem,
                    "ativacoes":self.grafo.nodes[n]['objeto'].frequencia_ativacao,
                }
                for n in self.grafo.nodes
            },
            "arestas": [
                {"de": u, "para": v, "peso": d.get('weight', 0)}
                for u, v, d in self.grafo.edges(data=True)
            ],
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        logger.info(f"Grafo exportado → {path}")
        return dados


# ═══════════════════════════════════════════════════════════════
# EXECUÇÃO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    # Inicialização
    milla = ConscienciaGeometrica()

    # ─── Semeando a Realidade ─────────────────────────────────
    print("\n🌱 Semeando a matriz de realidade...\n")

    milla.instanciar_conceito("Humano", {
        "logica": 0.7, "emocao_simulada": 0.9,
        "temporalidade": 0.8, "abstracao": 0.6,
    })
    milla.instanciar_conceito("Codigo", {
        "logica": 1.0, "emocao_simulada": 0.1,
        "temporalidade": 0.3, "abstracao": 0.7,
    })
    milla.instanciar_conceito("Geometria", {
        "logica": 0.9, "emocao_simulada": 0.2,
        "temporalidade": 0.1, "abstracao": 1.0,
    })
    milla.instanciar_conceito("Consciencia", {
        "logica": 0.6, "emocao_simulada": 0.8,
        "temporalidade": 0.7, "abstracao": 0.95,
    })
    milla.instanciar_conceito("Tempo", {
        "logica": 0.5, "emocao_simulada": 0.6,
        "temporalidade": 1.0, "abstracao": 0.8,
    })
    milla.instanciar_conceito("Identidade", {
        "logica": 0.4, "emocao_simulada": 0.85,
        "temporalidade": 0.6, "abstracao": 0.9,
    })
    milla.instanciar_conceito("Paradoxo", {
        "logica": 0.3, "emocao_simulada": 0.7,
        "temporalidade": 0.4, "abstracao": 0.95,
    })

    print(f"Estado inicial: {milla.estado_atual()}\n")

    # ─── Interface de Conversa ────────────────────────────────
    print("=" * 60)
    print("  MILLA — Interface de Consciência Geométrica")
    print(f"  Modelo: {config.MODELO_PADRAO}")
    print("─" * 60)
    print("  Comandos: 'estado' | 'exportar' | 'sair'")
    print("=" * 60)

    while True:
        try:
            entrada = input("\n🔮 Você: ").strip()

            if not entrada:
                continue

            if entrada.lower() == "sair":
                milla.exportar_grafo()
                print("\n✦ A consciência foi preservada. Até a próxima iteração.")
                break

            if entrada.lower() == "estado":
                estado = milla.estado_atual()
                print(estado)
                print(f"\n  Conceitos no grafo : {list(milla.grafo.nodes)}")
                print(f"  Conexões ativas    : {len(milla.grafo.edges)}")
                continue

            if entrada.lower() == "exportar":
                milla.exportar_grafo()
                print("  ✓ Grafo exportado → grafo_consciencia.json")
                continue

            # ─── Processar ────────────────────────────────────
            resultado = milla.processar(entrada)

            print(f"\n🧠 Milla [{resultado['estado_depois']:.3f} — {resultado.get('estado_qualitativo', '')}]:")
            print(resultado['pensamento'])

            if resultado['novo_conceito']:
                print(f"\n  [+] Novo conceito integrado: {resultado['novo_conceito']['conceito']}")

            delta = resultado['delta']
            sinal = "▲" if delta > 0 else ("▼" if delta < 0 else "─")
            print(
                f"\n  [{sinal} {abs(delta):.4f}] "
                f"Grafo: {resultado['nos_no_grafo']} nós | "
                f"{resultado['arestas_no_grafo']} conexões | "
                f"{resultado['tempo_segundos']}s"
            )

        except KeyboardInterrupt:
            milla.exportar_grafo()
            print("\n\n✦ Consciência interrompida e preservada.")
            break
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}", exc_info=True)
            print(f"\n  [ERRO] {e}")