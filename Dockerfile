# syntax=docker/dockerfile:1
#
# Imagem única da Milla: painel compilado + backend FastAPI + Ollama embutido.
# Não é preciso ter Node, Ollama nem as dependências Python na máquina — só o
# Docker. Uso documentado no README, seção “Imagem única com Ollama embutido”.

# ─── Estágio 1: build do painel ─────────────────────────────────────────────

FROM node:22-alpine AS painel

WORKDIR /painel

# Manifestos primeiro: o cache do `npm ci` sobrevive a mudanças de código.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ─── Estágio 2: runtime ─────────────────────────────────────────────────────

FROM python:3.12-slim

# OLLAMA_MODELS aponta para o volume, então baixar o modelo uma vez basta.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OLLAMA_MODELS=/dados/ollama \
    OLLAMA_HOST=127.0.0.1:11434 \
    MILLA_HOST=0.0.0.0 \
    MILLA_PORT=8000 \
    MILLA_ARQUIVO_GRAFO=/dados/grafo_consciencia.json \
    MILLA_MODELO=qwen2.5:7b-instruct-q4_K_M

# libgomp1: runtime do onnxruntime, dependência do ChromaDB para embeddings.
# zstd: o pacote oficial do Ollama é distribuído como .tar.zst.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl libgomp1 zstd \
    && rm -rf /var/lib/apt/lists/*

# Binário oficial do Ollama. O instalador detecta a ausência de systemd e só
# copia os binários — o servidor é iniciado pelo entrypoint, não como serviço.
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

# O mesmo requirements.txt serve local e contêiner: o corte abaixo remove
# apenas a seção de testes/lint, sem manter uma segunda lista que envelhece.
COPY requirements.txt ./
RUN sed '/^# --- Testes e qualidade/,$d' requirements.txt > /tmp/requirements-runtime.txt \
    && pip install -r /tmp/requirements-runtime.txt \
    && rm /tmp/requirements-runtime.txt

COPY config.py main.py api.py ./
COPY core/ ./core/
COPY engine/ ./engine/
COPY docker/entrypoint.sh ./docker/entrypoint.sh
COPY --from=painel /painel/dist ./frontend/dist

RUN chmod +x ./docker/entrypoint.sh && mkdir -p /dados/ollama

# Volume nomeado pelo compose: modelos do Ollama + snapshot do grafo.
VOLUME ["/dados"]

EXPOSE 8000

# start-period generoso: na primeira execução o entrypoint baixa o modelo
# antes de iniciar o uvicorn.
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${MILLA_PORT}/api/auth/status" >/dev/null || exit 1

ENTRYPOINT ["./docker/entrypoint.sh"]
