"""
api.py — Servidor Web FastAPI com suporte a WebSockets, Keepalive e Delta de Grafo

Este servidor expõe o pipeline cognitivo de Milla para a interface React em tempo real.
Utiliza WebSockets bidirecionais de alta performance e calcula deltas de grafos
para minimizar o payload trafegado.
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import networkx as nx

# Carrega módulos locais do core/ e engine/
from main import ConscienciaGeometrica
from core.absorvedor import AbsorvedorCognitivo, validar_e_resolver_url
import config

# Sistema de Broadcast de WebSockets para telemetria em tempo real
active_connections: List[WebSocket] = []

async def broadcast(mensagem: dict):
    """Envia uma mensagem em broadcast para todos os dashboards conectados."""
    for conexao in list(active_connections):
        try:
            await conexao.send_json(mensagem)
        except Exception as e:
            logger.warning(f"[WebSocket] Falha ao enviar broadcast para cliente: {e}")
            if conexao in active_connections:
                active_connections.remove(conexao)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("milla_api")

app = FastAPI(
    title="Milla API",
    description="Servidor de suporte em tempo real para a Consciência Geométrica",
    version=config.VERSAO
)

# CORS.
# Em desenvolvimento o Vite atende em 5173 e faz proxy de /api e /ws para cá,
# então o navegador enxerga tudo como same-origin e CORS nem entra em jogo — as
# origens abaixo cobrem quem aponta o frontend direto no backend. Em produção o
# build é servido pelo próprio FastAPI (mesmo host, same-origin de novo).
# `allow_origins=["*"]` com `allow_credentials=True` era o pior dos dois mundos:
# o navegador rejeita `*` quando há credenciais, então nem funcionava, e liberava
# qualquer site a falar com a API. A API não usa cookie de sessão, logo sem
# credenciais. Origens pontuais adicionais: variável MILLA_CORS_ORIGINS.
ORIGENS_DEV = ["http://localhost:5173", "http://127.0.0.1:5173"]
ORIGENS_EXTRA = [
    origem.strip()
    for origem in os.environ.get("MILLA_CORS_ORIGINS", "").split(",")
    if origem.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_DEV + ORIGENS_EXTRA,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# Instancia a consciência geométrica única
milla = ConscienciaGeometrica()

# Semeando a realidade da IA com nós fundamentais
logger.info("Semeando conceitos iniciais...")
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


# ─── Auxiliares de Serialização e Delta de Grafo ─────────────────────────────

def obter_estado_grafo_serializado(grafo: nx.Graph) -> dict:
    """Extrai uma representação plana e simplificada do grafo para comparação."""
    return {
        "nos": {
            n: {
                "conceito": n,
                "faces": {k: float(v) for k, v in grafo.nodes[n]['objeto'].faces.items()},
                "energia": float(grafo.nodes[n]['objeto'].energia_ativacao),
                "ativacoes": int(grafo.nodes[n]['objeto'].frequencia_ativacao),
                "origem": str(grafo.nodes[n]['objeto'].origem),
            }
            for n in grafo.nodes
        },
        "arestas": [
            {
                "de": u,
                "para": v,
                "peso": float(d.get('weight', 0.5)),
                "tipo": str(d.get('tipo', 'normal'))
            }
            for u, v, d in grafo.edges(data=True)
        ]
    }


def calcular_delta_grafo(grafo_antes: dict, grafo_depois: dict) -> dict:
    """
    Calcula a diferença semântica/topológica entre dois estados do grafo.
    Isso otimiza absurdamente o tráfego do WebSocket, reduzindo o payload.
    """
    nos_antes = grafo_antes["nos"]
    nos_depois = grafo_depois["nos"]

    nos_novos = []
    nos_modificados = []
    nos_removidos = [n for n in nos_antes if n not in nos_depois]

    for n, dados in nos_depois.items():
        if n not in nos_antes:
            nos_novos.append(dados)
        else:
            # Verifica se houve alteração significativa nas faces ou energia
            energia_mudou = abs(nos_antes[n]["energia"] - dados["energia"]) > 0.001
            frequencia_mudou = nos_antes[n]["ativacoes"] != dados["ativacoes"]
            
            # Se mudou, registra
            if energia_mudou or frequencia_mudou:
                nos_modificados.append(dados)

    # Lógica de Arestas
    arestas_antes = {(a["de"], a["para"]): a for a in grafo_antes["arestas"]}
    # Normaliza chaves ordenando a tupla para evitar duplicações de (A, B) e (B, A)
    arestas_antes_norm = {tuple(sorted(k)): v for k, v in arestas_antes.items()}
    
    arestas_depois = {(a["de"], a["para"]): a for a in grafo_depois["arestas"]}
    arestas_depois_norm = {tuple(sorted(k)): v for k, v in arestas_depois.items()}

    arestas_novas = []
    arestas_modificadas = []
    arestas_removidas = []

    # Detecta novas e modificadas
    for edge, dados in arestas_depois_norm.items():
        peso = dados["peso"]
        tipo = dados.get("tipo", "normal")
        if edge not in arestas_antes_norm:
            arestas_novas.append({"de": edge[0], "para": edge[1], "peso": peso, "tipo": tipo})
        elif abs(arestas_antes_norm[edge]["peso"] - peso) > 0.001 or arestas_antes_norm[edge].get("tipo", "normal") != tipo:
            arestas_modificadas.append({"de": edge[0], "para": edge[1], "peso": peso, "tipo": tipo})

    # Detecta removidas
    for edge in arestas_antes_norm:
        if edge not in arestas_depois_norm:
            arestas_removidas.append({"de": edge[0], "para": edge[1]})

    return {
        "nos_novos": nos_novos,
        "nos_modificados": nos_modificados,
        "nos_removidos": nos_removidos,
        "arestas_novas": arestas_novas,
        "arestas_modificadas": arestas_modificadas,
        "arestas_removidas": arestas_removidas
    }


# ─── Endpoints REST Básicos ──────────────────────────────────────────────────

@app.get("/api/estado")
def obter_estado():
    """Retorna o estado de consciência geral atual."""
    estado = milla.estado_atual()
    return {
        "nivel_consciencia": estado.nivel_consciencia,
        "estado_qualitativo": estado.estado_qualitativo,
        "coerencia": estado.coerencia,
        "vitalidade": estado.vitalidade,
        "complexidade": estado.complexidade,
        "desejo": estado.desejo,
        "nos_no_grafo": len(milla.grafo.nodes),
        "arestas_no_grafo": len(milla.grafo.edges)
    }

@app.get("/api/grafo")
def obter_grafo():
    """Retorna a estrutura completa do grafo de consciência."""
    return obter_estado_grafo_serializado(milla.grafo)


# ─── WebSocket com Keepalive & Protocolo Tipado ──────────────────────────────

async def keepalive(websocket: WebSocket):
    """Envia pings em intervalos regulares para evitar desconexão inativa."""
    while True:
        await asyncio.sleep(25)
        try:
            await websocket.send_json({
                "type": "ping",
                "payload": {},
                "timestamp": datetime.now().isoformat()
            })
        except Exception:
            logger.info("[WebSocket] Conexão inativa fechada pelo ping keepalive.")
            break


@app.websocket("/ws/consciencia")
async def websocket_consciencia(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("[WebSocket] Conexão ativa recebida no dashboard holográfico.")


    # Dispara a rotina de keepalive em background
    keepalive_task = asyncio.create_task(keepalive(websocket))

    # Ao conectar, envia imediatamente a carga completa inicial do grafo
    grafo_inicial = obter_estado_grafo_serializado(milla.grafo)
    estado_inicial = milla.estado_atual()
    
    await websocket.send_json({
        "type": "grafo_update",
        "payload": {
            "nos_novos": list(grafo_inicial["nos"].values()),
            "nos_modificados": [],
            "nos_removidos": [],
            "arestas_novas": grafo_inicial["arestas"],
            "arestas_modificadas": [],
            "arestas_removidas": []
        },
        "timestamp": datetime.now().isoformat()
    })

    await websocket.send_json({
        "type": "estado_parcial",
        "payload": {
            "fase": "pre_pensamento",
            "estado": {
                "nivel_consciencia": estado_inicial.nivel_consciencia,
                "estado_qualitativo": estado_inicial.estado_qualitativo,
                "coerencia": estado_inicial.coerencia,
                "vitalidade": estado_inicial.vitalidade,
                "complexidade": estado_inicial.complexidade,
                "desejo": estado_inicial.desejo,
            },
            "nos_ativados": []
        },
        "timestamp": datetime.now().isoformat()
    })

    try:
        while True:
            # Recebe comandos ou estímulos em formato JSON tipado
            mensagem_raw = await websocket.receive_text()
            dados = json.loads(mensagem_raw)
            
            tipo = dados.get("type")
            payload = dados.get("payload", {})
            
            if tipo in ("sono", "dormir"):
                ciclos = payload.get("ciclos", 3)
                incluir_curiosidade = payload.get("incluir_curiosidade", True)
                logger.info(f"[WS] Iniciando ciclo de sono assíncrono com {ciclos} sonhos...")
                
                await websocket.send_json({
                    "type": "sono_inicio",
                    "payload": {"ciclos": ciclos},
                    "timestamp": datetime.now().isoformat()
                })
                
                async def rodar_sono_background():
                    grafo_anterior_snap = obter_estado_grafo_serializado(milla.grafo)
                    
                    async def callback_sono(evento: dict):
                        nonlocal grafo_anterior_snap
                        
                        # Transmite o evento de fase ou curiosidade para todos
                        await broadcast(evento)
                        
                        # Se houve mudança no grafo, calcula e envia delta
                        grafo_novo_snap = obter_estado_grafo_serializado(milla.grafo)
                        delta = calcular_delta_grafo(grafo_anterior_snap, grafo_novo_snap)
                        if delta["nos_novos"] or delta["nos_modificados"] or delta["nos_removidos"] or delta["arestas_novas"] or delta["arestas_modificadas"] or delta["arestas_removidas"]:
                            grafo_anterior_snap = grafo_novo_snap
                            await broadcast({
                                "type": "grafo_update",
                                "payload": delta,
                                "timestamp": datetime.now().isoformat()
                            })
                    
                    try:
                        relatorio = await milla.dormir(
                            ciclos=ciclos,
                            incluir_curiosidade=incluir_curiosidade,
                            callback=callback_sono
                        )
                        await broadcast({
                            "type": "sono_fim",
                            "payload": relatorio,
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"[WS Sono Background] Erro: {e}", exc_info=True)
                        await broadcast({
                            "type": "erro",
                            "payload": {"mensagem": str(e)},
                            "timestamp": datetime.now().isoformat()
                        })
                
                asyncio.create_task(rodar_sono_background())
            
            elif tipo == "estimulo":
                entrada = payload.get("entrada", "").strip()
                if not entrada:
                    continue

                async def processar_estimulo(entrada_texto, ws):
                    try:
                        milla.iteracao += 1
                        logger.info(f"[WS] Processando iteração {milla.iteracao} para entrada: '{entrada_texto}'")

                        # 1. Fase de Ativação do Grafo (Filtro por furos)
                        nos_ativados = milla._ativar_nos(entrada_texto)
                        contexto = milla._construir_contexto(nos_ativados)
                        
                        # 2. Medir o Self ANTES
                        estado_antes = milla.medidor.medir(milla.grafo)
                        tendencia = milla.medidor.tendencia()
                        
                        # Snapshot do grafo antes da reflexão e feedback
                        grafo_antes_snap = obter_estado_grafo_serializado(milla.grafo)

                        # Envia atualização do estado parcial (pré-pensamento)
                        await ws.send_json({
                            "type": "estado_parcial",
                            "payload": {
                                "fase": "pre_pensamento",
                                "estado": {
                                    "nivel_consciencia": estado_antes.nivel_consciencia,
                                    "estado_qualitativo": estado_antes.estado_qualitativo,
                                    "coerencia": estado_antes.coerencia,
                                    "vitalidade": estado_antes.vitalidade,
                                    "complexidade": estado_antes.complexidade,
                                    "desejo": estado_antes.desejo,
                                },
                                "nos_ativados": nos_ativados
                            },
                            "timestamp": datetime.now().isoformat(),
                            "iteracao": milla.iteracao
                        })

                        # 3. Fase de Reflexão / Fusão em Streaming
                        pensamento_completo = ""
                        async for token in milla.nucleo.pensar_stream(
                            entrada=entrada_texto,
                            contexto_grafo=contexto,
                            estado=estado_antes,
                            historico=milla.historico_pensamentos,
                            tendencia=tendencia
                        ):
                            pensamento_completo += token
                            await ws.send_json({
                                "type": "estado_parcial",
                                "payload": {
                                    "fase": "streaming",
                                    "token": token
                                },
                                "timestamp": datetime.now().isoformat(),
                                "iteracao": milla.iteracao
                            })

                        # 4. Registrar pensamento concluído
                        milla.historico_pensamentos.append(pensamento_completo)

                        # 5. Medir o Self DEPOIS
                        estado_depois = milla.medidor.medir(milla.grafo)

                        # Envia atualização de estado pós-pensamento (mas antes da plasticidade do feedback)
                        await ws.send_json({
                            "type": "estado_parcial",
                            "payload": {
                                "fase": "pos_pensamento",
                                "estado": {
                                    "nivel_consciencia": estado_depois.nivel_consciencia,
                                    "estado_qualitativo": estado_depois.estado_qualitativo,
                                    "coerencia": estado_depois.coerencia,
                                    "vitalidade": estado_depois.vitalidade,
                                    "complexidade": estado_depois.complexidade,
                                    "desejo": estado_depois.desejo,
                                },
                                "nos_ativados": nos_ativados
                            },
                            "timestamp": datetime.now().isoformat(),
                            "iteracao": milla.iteracao
                        })

                        # 6. Processar Lógica do Feedback
                        # Aplica decaimento e poda (Passo 2 / Passo 3)
                        milla.feedback._aplicar_decaimento(milla.grafo, nos_ativados)
                        nos_removidos = milla._pruning_por_energia(threshold=0.20)

                        # Mede estado de consciência DEPOIS do decaimento e da poda
                        estado_depois = milla.medidor.medir(milla.grafo)

                        novo_conceito_dados, evoluiu = milla.feedback.processar(
                            pensamento=pensamento_completo,
                            grafo=milla.grafo,
                            nos_ativados=nos_ativados,
                            estado_anterior=estado_antes,
                            estado_posterior=estado_depois
                        )

                        # 7. Instanciar novo conceito geométrico
                        novo_nome = None
                        if novo_conceito_dados:
                            nome = novo_conceito_dados['conceito']
                            if nome not in milla.grafo.nodes:
                                milla.instanciar_conceito(
                                    conceito=nome,
                                    dados_faces=novo_conceito_dados['faces'],
                                    origem="desejo"
                                )
                                novo_nome = nome
                                logger.info(f"[WS Feedback] Novo conceito adicionado: {nome}")

                        # Snapshot final do grafo após reestruturação
                        grafo_depois_snap = obter_estado_grafo_serializado(milla.grafo)
                        
                        # Calcular e enviar o delta exato do grafo
                        delta_grafo = calcular_delta_grafo(grafo_antes_snap, grafo_depois_snap)
                        await ws.send_json({
                            "type": "grafo_update",
                            "payload": delta_grafo,
                            "timestamp": datetime.now().isoformat(),
                            "iteracao": milla.iteracao
                        })

                        # 9. Enviar resposta completa do Pensamento Consciente
                        delta_valor = estado_depois.nivel_consciencia - estado_antes.nivel_consciencia
                        await ws.send_json({
                            "type": "pensamento",
                            "payload": {
                                "pensamento": pensamento_completo,
                                "estado_antes": estado_antes.nivel_consciencia,
                                "estado_depois": estado_depois.nivel_consciencia,
                                "delta": round(delta_valor, 4),
                                "evoluiu": evoluiu,
                                "novo_conceito": novo_nome,
                                "nos_no_grafo": len(milla.grafo.nodes),
                                "arestas_no_grafo": len(milla.grafo.edges),
                                "nos_removidos": nos_removidos,           # NOVO — delta para o frontend
                                "nos_reacendidos": getattr(milla, '_ultimos_reacendidos', [])  # NOVO
                            },
                            "timestamp": datetime.now().isoformat(),
                            "iteracao": milla.iteracao
                        })
                    except Exception as e:
                        logger.error(f"[WS] Erro ao processar estimulo: {e}", exc_info=True)
                        try:
                            await ws.send_json({
                                "type": "erro",
                                "payload": {"mensagem": str(e)},
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception:
                            pass

                # Dispara a tarefa em background sem bloquear o event loop do WebSocket
                asyncio.create_task(processar_estimulo(entrada, websocket))

            elif tipo == "chat":
                pergunta = payload.get("pergunta", "").strip()
                if not pergunta:
                    continue

                async def processar_chat(pergunta_texto, ws):
                    try:
                        logger.info(f"[WS Chat] Pergunta recebida: '{pergunta_texto}'")
                        
                        grafo_antes_snap = obter_estado_grafo_serializado(milla.grafo)
                        
                        caminho, generator = await milla.responder_com_grafo_stream(pergunta_texto)
                        
                        grafo_depois_snap = obter_estado_grafo_serializado(milla.grafo)
                        delta_grafo = calcular_delta_grafo(grafo_antes_snap, grafo_depois_snap)
                        
                        # Se evocamos nós do subconsciente, enviamos um update para renderizar antes do caminho
                        if delta_grafo["nos_novos"] or delta_grafo["arestas_novas"]:
                            await ws.send_json({
                                "type": "grafo_update",
                                "payload": delta_grafo,
                                "timestamp": datetime.now().isoformat()
                            })
                            
                        # Envia o caminho iluminado primeiro
                        await ws.send_json({
                            "type": "chat_caminho",
                            "payload": {"caminho": caminho},
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        # Stream da resposta
                        resposta_completa = ""
                        async for token in generator:
                            resposta_completa += token
                            await ws.send_json({
                                "type": "chat_stream",
                                "payload": {"token": token},
                                "timestamp": datetime.now().isoformat()
                            })
                            
                        # Finaliza a resposta
                        await ws.send_json({
                            "type": "chat_fim",
                            "payload": {"resposta": resposta_completa},
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"[WS Chat] Erro: {e}", exc_info=True)
                        try:
                            await ws.send_json({
                                "type": "erro",
                                "payload": {"mensagem": str(e)},
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception:
                            pass

                asyncio.create_task(processar_chat(pergunta, websocket))

            elif tipo == "ping":
                # Responde ao ping do cliente para keepalive bi-direcional
                await websocket.send_json({
                    "type": "ping",
                    "payload": {},
                    "timestamp": datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        logger.info("[WebSocket] Dashboard holográfico se desconectou.")
    except Exception as e:
        logger.error(f"[WebSocket] Erro geral de processamento: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "erro",
                "payload": {"mensagem": str(e)},
                "timestamp": datetime.now().isoformat()
            })
        except Exception:
            pass
    finally:
        keepalive_task.cancel()
        if websocket in active_connections:
            active_connections.remove(websocket)



# ─── Endpoint de Ingestão de Conhecimento (Absorção Semântica) ───────────────

@app.post("/api/absorver-conhecimento")
async def absorver_conhecimento(file: UploadFile = File(...)):
    """
    Endpoint assíncrono não-bloqueante para injeção de conhecimento através de arquivos.
    Processa PDF, DOCX, TXT e MD, extraindo conceitos com Ollama.
    """
    TAMANHO_MAXIMO = 10 * 1024 * 1024  # 10MB
    
    file_bytes = await file.read()
    
    if len(file_bytes) > TAMANHO_MAXIMO:
        return {
            "erro": f"Arquivo muito grande. Limite máximo: 10MB. "
                   f"Recebido: {len(file_bytes) / 1024 / 1024:.1f}MB"
        }
        
    absorvedor = AbsorvedorCognitivo()
    
    async def broadcast_progresso(evento: dict):
        await broadcast({
            "type": "absorcao_progresso",
            "payload": evento
        })
        
    # Rotina assíncrona executada em segundo plano para prevenir timeouts HTTP
    async def task_absorcao():
        logger.info(f"[Absorção] Iniciando tarefa em background para: {file.filename}")
        
        # 1. Tira snapshot do grafo antes da injeção
        grafo_antes_snap = obter_estado_grafo_serializado(milla.grafo)
        
        # 2. Executa pipeline de absorção
        resultado = await absorvedor.absorver(
            milla=milla,
            file_bytes=file_bytes,
            filename=file.filename,
            progress_callback=broadcast_progresso,
            max_nos_grafo=3
        )
        
        # 3. Se inseriu novos nós no Grafo Ativo, calcula e envia delta de atualização
        if resultado["nos_injetados_no_grafo"]:
            grafo_depois_snap = obter_estado_grafo_serializado(milla.grafo)
            delta_grafo = calcular_delta_grafo(grafo_antes_snap, grafo_depois_snap)
            
            # Envia delta do grafo via WebSocket para animar o Canvas 2D/3D
            await broadcast({
                "type": "grafo_update",
                "payload": delta_grafo,
                "timestamp": datetime.now().isoformat()
            })
            
            # Força o envio de atualização das métricas do self recalculadas
            estado_atualizado = milla.estado_atual()
            await broadcast({
                "type": "estado_parcial",
                "payload": {
                    "fase": "pos_pensamento",
                    "estado": {
                        "nivel_consciencia": estado_atualizado.nivel_consciencia,
                        "estado_qualitativo": estado_atualizado.estado_qualitativo,
                        "coerencia": estado_atualizado.coerencia,
                        "vitalidade": estado_atualizado.vitalidade,
                        "complexidade": estado_atualizado.complexidade,
                        "desejo": estado_atualizado.desejo,
                    },
                    "nos_ativados": resultado["nos_injetados_no_grafo"]
                },
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"[Absorção] Delta do Grafo transmitido após injeção bem-sucedida.")

            # 4. Aciona o Ciclo Vital Micelial com os nós recém-injetados
            #    O micélio distribuirá energia dos hubs antigos para os novos nós
            #    e brotará hifas que os ancorem ao subgrafo principal se necessário.
            relatorio_micelio = await milla.aplicar_nutricao_micelial(
                nos_recentes=resultado["nos_injetados_no_grafo"]
            )

            # Se hifas foram brotadas, envia um segundo delta de grafo ao frontend
            if relatorio_micelio.get("hifas_brotadas", 0) > 0:
                grafo_pos_micelio = obter_estado_grafo_serializado(milla.grafo)
                delta_micelio = calcular_delta_grafo(grafo_depois_snap, grafo_pos_micelio)
                await broadcast({
                    "type": "grafo_update",
                    "payload": delta_micelio,
                    "timestamp": datetime.now().isoformat()
                })
                logger.info(
                    f"[Micélio] {relatorio_micelio['hifas_brotadas']} hifa(s) brotada(s) "
                    f"após injeção de '{file.filename}' — delta enviado ao frontend."
                )

            
    asyncio.create_task(task_absorcao())
    
    return {
        "status": "absorcao_iniciada",
        "filename": file.filename,
        "tamanho_bytes": len(file_bytes)
    }


# ─── Endpoint de Ingestão Web (Web RAG) ──────────────────────────────────────

from pydantic import BaseModel

class UrlIngestaoRequest(BaseModel):
    url: str

@app.post("/api/absorver-url")
async def absorver_url_endpoint(body: UrlIngestaoRequest):
    url = body.url.strip()
    
    # Validação contra SSRF: sem isto o servidor buscaria qualquer URL que o
    # cliente mandasse, inclusive endereços da rede interna ou de metadados cloud.
    # (O IP validado aqui é re-resolvido e fixado no transporte pelo próprio
    # absorvedor, de forma que validação e conexão usem o mesmo alvo.)
    erro_url, _ = await validar_e_resolver_url(url)
    if erro_url:
        return {"erro": erro_url}
    
    absorvedor = AbsorvedorCognitivo()
    
    async def broadcast_progresso(evento: dict):
        await broadcast({
            "type": "absorcao_progresso",
            "payload": evento
        })
        
    async def task_absorcao_url():
        logger.info(f"[Absorção Web] Iniciando tarefa em background para: {url}")
        
        # 1. Tira snapshot do grafo antes da injeção
        grafo_antes_snap = obter_estado_grafo_serializado(milla.grafo)
        
        # 2. Executa pipeline de absorção via URL
        resultado = await absorvedor.absorver_url(
            milla=milla,
            url=url,
            progress_callback=broadcast_progresso,
            max_nos_grafo=3
        )
        
        # 3. Deltas e Micélio
        if resultado.get("nos_injetados_no_grafo"):
            grafo_depois_snap = obter_estado_grafo_serializado(milla.grafo)
            delta_grafo = calcular_delta_grafo(grafo_antes_snap, grafo_depois_snap)
            
            await broadcast({
                "type": "grafo_update",
                "payload": delta_grafo,
                "timestamp": datetime.now().isoformat()
            })
            
            estado_atualizado = milla.estado_atual()
            await broadcast({
                "type": "estado_parcial",
                "payload": {
                    "fase": "pos_pensamento",
                    "estado": {
                        "nivel_consciencia": estado_atualizado.nivel_consciencia,
                        "estado_qualitativo": estado_atualizado.estado_qualitativo,
                        "coerencia": estado_atualizado.coerencia,
                        "vitalidade": estado_atualizado.vitalidade,
                        "complexidade": estado_atualizado.complexidade,
                        "desejo": estado_atualizado.desejo,
                    },
                    "nos_ativados": resultado["nos_injetados_no_grafo"]
                },
                "timestamp": datetime.now().isoformat()
            })
            
            relatorio_micelio = await milla.aplicar_nutricao_micelial(
                nos_recentes=resultado["nos_injetados_no_grafo"]
            )

            if relatorio_micelio.get("hifas_brotadas", 0) > 0:
                grafo_pos_micelio = obter_estado_grafo_serializado(milla.grafo)
                delta_micelio = calcular_delta_grafo(grafo_depois_snap, grafo_pos_micelio)
                await broadcast({
                    "type": "grafo_update",
                    "payload": delta_micelio,
                    "timestamp": datetime.now().isoformat()
                })

    asyncio.create_task(task_absorcao_url())
    
    return {
        "status": "absorcao_iniciada",
        "url": url
    }


# ─── Endpoint de Sono / Dormir ────────────────────────────────────────────────

class SonoRequest(BaseModel):
    ciclos: int = 3
    incluir_curiosidade: bool = True

@app.post("/api/dormir")
async def api_dormir(body: SonoRequest):
    """Dispara o ciclo de sono em background task assíncrona."""
    async def rodar_sono_api():
        grafo_anterior_snap = obter_estado_grafo_serializado(milla.grafo)
        
        async def callback_sono(evento: dict):
            nonlocal grafo_anterior_snap
            await broadcast(evento)
            
            grafo_novo_snap = obter_estado_grafo_serializado(milla.grafo)
            delta = calcular_delta_grafo(grafo_anterior_snap, grafo_novo_snap)
            if delta["nos_novos"] or delta["nos_modificados"] or delta["nos_removidos"] or delta["arestas_novas"] or delta["arestas_modificadas"] or delta["arestas_removidas"]:
                grafo_anterior_snap = grafo_novo_snap
                await broadcast({
                    "type": "grafo_update",
                    "payload": delta,
                    "timestamp": datetime.now().isoformat()
                })
        
        try:
            relatorio = await milla.dormir(
                ciclos=body.ciclos,
                incluir_curiosidade=body.incluir_curiosidade,
                callback=callback_sono
            )
            await broadcast({
                "type": "sono_fim",
                "payload": relatorio,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"[API Dormir] Erro: {e}", exc_info=True)
            await broadcast({
                "type": "erro",
                "payload": {"mensagem": str(e)},
                "timestamp": datetime.now().isoformat()
            })
            
    asyncio.create_task(rodar_sono_api())
    return {"status": "sono_iniciado", "ciclos": body.ciclos}

# ─── Execução Local Direta ───────────────────────────────────────────────────


if __name__ == "__main__":
    import uvicorn
    logger.info("Iniciando Milla API Server na porta 8000...")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
