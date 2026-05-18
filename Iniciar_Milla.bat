@echo off
title Milla OS - OLLAMA AMD & Server Orchestrator
cls
echo ====================================================================
echo            🔮 MILLA OS - COMPLETE COGNITIVE SERVER ORCHESTRATOR
echo ====================================================================
echo.
echo [1/5] Configurando variaveis de ambiente de hardware (AMD GPU)...
echo Setting Environment Variables:
echo   - OLLAMA_VULKAN = 1 (Force Vulkan backend)
echo   - HSA_OVERRIDE_GFX_VERSION = 10.3.0 (RDNA2 fix)
echo.

set OLLAMA_VULKAN=1
set HSA_OVERRIDE_GFX_VERSION=10.3.0

echo [2/5] Verificando processos ativos do Ollama...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo.
    echo [AVISO] Um processo ativo do Ollama foi detectado!
    echo Reiniciando o servico para aplicar as variaveis de hardware AMD...
    taskkill /f /im ollama.exe >nul 2>&1
    taskkill /f /im "ollama app.exe" >nul 2>&1
    timeout /t 2 /nobreak >nul
)

echo.
echo [3/5] Inicializando servidor Ollama em segundo plano...
start "Milla OS - Ollama Engine" /min ollama serve

echo.
echo [4/5] Inicializando Servidor Backend da Milla (FastAPI)...
start "Milla OS - Backend Server (FastAPI)" cmd /k "python api.py"

echo.
echo [5/5] Inicializando Interface Grafica da Milla (React + Vite)...
start "Milla OS - Frontend Server (Vite)" cmd /k "cd frontend && npm run dev"

echo.
echo ====================================================================
echo [SUCESSO] Todos os servicos foram disparados!
echo Aguardando 4 segundos para os servidores inicializarem...
echo ====================================================================
timeout /t 4 /nobreak >nul

echo.
echo [!] Abrindo painel de controle holografico no seu navegador...
start http://localhost:5173/

echo.
echo ====================================================================
echo   🔮 Milla OS esta pronta para interacao!
echo   - Backend: http://127.0.0.1:8000
echo   - Frontend: http://localhost:5173
echo ====================================================================
echo.
echo Mantenha as janelas abertas enquanto estiver utilizando o sistema.
echo Pressione qualquer tecla nesta janela para encerrar o orquestrador.
pause >nul
