#!/usr/bin/env bash
# docker/entrypoint.sh — sobe o Ollama, garante o modelo e inicia o FastAPI.
set -euo pipefail

# Dentro do contêiner nenhum cliente é loopback: a política de core/auth.py
# exige token. Sem MILLA_TOKEN geramos um e mostramos no log, em vez de deixar
# a API inalcançável (e nunca subir sem senha).
if [[ -z "${MILLA_TOKEN:-}" ]]; then
    MILLA_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
    export MILLA_TOKEN
    echo "──────────────────────────────────────────────────────────────"
    echo " MILLA_TOKEN não definido — gerado para esta execução:"
    echo "     ${MILLA_TOKEN}"
    echo " Defina MILLA_TOKEN no .env para manter o mesmo entre reinícios."
    echo "──────────────────────────────────────────────────────────────"
fi

modelo="${MILLA_MODELO:-qwen2.5:7b-instruct-q4_K_M}"

echo "[Milla] Iniciando o Ollama embutido..."
ollama serve &
ollama_pid=$!

# Espera o servidor responder antes de pedir o modelo (limite de ~90 s).
for _ in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# `ollama list` imprime um cabeçalho; a primeira coluna é o nome do modelo.
if ! ollama list | awk 'NR > 1 { print $1 }' | grep -qx "${modelo}"; then
    echo "[Milla] Baixando o modelo ${modelo} (primeira execução, alguns GB)..."
    ollama pull "${modelo}"
fi

echo "[Milla] Iniciando o backend em ${MILLA_HOST:-0.0.0.0}:${MILLA_PORT:-8000}..."
uvicorn api:app --host "${MILLA_HOST:-0.0.0.0}" --port "${MILLA_PORT:-8000}" &
api_pid=$!

# `docker compose stop` manda SIGTERM para o PID 1 (este script): repassamos
# para o uvicorn, que fecha o lifespan e grava o snapshot pendente.
encerrar() {
    kill "${api_pid}" "${ollama_pid}" 2>/dev/null || true
    wait "${api_pid}" 2>/dev/null || true
}
trap encerrar TERM INT

# Se o backend cair, o contêiner cai junto e o `restart` do compose se aplica.
wait "${api_pid}"
