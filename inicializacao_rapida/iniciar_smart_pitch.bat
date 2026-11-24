@echo off
title Smart Pitch - Inicializador Rapido
:: Navega ate a raiz do projeto (uma pasta acima)
cd /d "%~dp0\.."

echo ==============================================================
echo   GESTAO AUTOMATIZADA DE ESTADIOS - SMART PITCH (SD)
echo ==============================================================
echo [1/2] Subindo Broker MQTT e 3 bancos PostgreSQL (Docker)...
docker compose up -d
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao subir os containers Docker. Verifique se o Docker Desktop esta aberto.
    pause
    exit /b 1
)

echo Aguardando containers iniciarem...
timeout /t 3 /nobreak >nul

echo.
echo [2/2] Iniciando gerenciador unificado do Smart Pitch...
where python >nul 2>nul
if %errorlevel%==0 (
    python gramado\start_all.py
) else (
    py gramado\start_all.py
)

echo.
echo Gerenciador encerrado. (Para parar tambem os containers Docker, execute parar_smart_pitch.bat)
pause
