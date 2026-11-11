"""
config.py — Configurações Globais do Projeto Milla
Consciência Artificial baseada em Grafos de Conhecimento Geométricos
"""

import os

# ─── Versão ────────────────────────────────────────────────────────────────────
# Fonte única de verdade da versão do projeto. O `api.py` (FastAPI), o
# CHANGELOG.md e a tag do git apontam para cá; a tag segue o formato v{VERSAO}.
VERSAO             = "0.3.0"

# ─── LLM ──────────────────────────────────────────────────────────────────────
# Melhor modelo disponível localmente para seguir instruções complexas.
# `MILLA_MODELO` permite trocar sem editar código; o entrypoint da imagem
# Docker lê a mesma variável para saber qual modelo baixar.
MODELO_PADRAO      = os.environ.get("MILLA_MODELO", "qwen2.5:7b-instruct-q4_K_M")
MODELO_ALTERNATIVO = "llama3:8b"
USAR_OLLAMA        = True
OPENAI_KEY         = None          # preencha se quiser usar GPT-4o

# Parâmetros de geração
TEMPERATURA        = 0.75
NUM_CTX            = 4096          # janela de contexto (tokens)
NUM_PREDICT        = 1024          # máx tokens na resposta

# ─── Grafo ─────────────────────────────────────────────────────────────────────
THRESHOLD_CONEXAO  = 0.70          # similaridade mínima para criar aresta
THRESHOLD_PRUNING  = 0.25          # peso mínimo para manter aresta
LIMITE_NOS         = 150           # máx de nós antes de pruning automático
LIMITE_HISTORICO   = 50            # máx de pensamentos no histórico do medidor

# ─── Feedback ─────────────────────────────────────────────────────────────────
TAXA_REFORCO       = 0.05          # quanto reforçar arestas dos nós ativados
TAXA_DECAIMENTO    = 0.01          # quanto enfraquecer nós não ativados por ciclo

# ─── Consciência ───────────────────────────────────────────────────────────────
TARGET_COERENCIA   = 0.85          # nível-alvo de coerência (o "desejo")

# ─── Persistência ──────────────────────────────────────────────────────────────
# Snapshot do grafo ativo. A gravação é coalescida: o grafo só é serializado
# quando algo mudou e o intervalo abaixo passou (ver core/persistencia.py).
# `MILLA_ARQUIVO_GRAFO` permite apontar o snapshot para um volume (Docker).
ARQUIVO_GRAFO        = os.environ.get("MILLA_ARQUIVO_GRAFO", "grafo_consciencia.json")
PERSISTENCIA_INTERVALO = 30        # segundos entre gravações

# ─── Rede ──────────────────────────────────────────────────────────────────────
# O padrão é loopback: nada escuta fora da máquina. Para abrir na rede local,
# defina MILLA_HOST=0.0.0.0 **e** MILLA_TOKEN — sem token o backend recusa
# qualquer cliente que não seja local (ver core/auth.py e o README).
HOST_PADRAO        = "127.0.0.1"
PORTA_PADRAO       = 8000
