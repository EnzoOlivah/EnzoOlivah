@echo off
chcp 65001 >nul
title Controle PC - instalacao
echo.
echo  === Controle PC: instalacao ===
echo.

python --version >nul 2>&1
if errorlevel 1 (
  echo  Python nao encontrado.
  echo  Instale em https://www.python.org/downloads/ marcando "Add python.exe to PATH"
  echo  e depois rode este arquivo de novo.
  echo.
  pause
  exit /b 1
)

echo  [1/3] Instalando dependencias...
python -m pip install --upgrade "mcp>=1.9" pynput
if errorlevel 1 (
  echo.
  echo  Falha ao instalar as dependencias. Copie a mensagem acima e mande para o Claude.
  pause
  exit /b 1
)

set "DEST=%USERPROFILE%\pc-remote"
if not exist "%DEST%" mkdir "%DEST%"

echo.
echo  [2/3] Salvando o servidor em %DEST%...
if exist "%~dp0pc_remote_server.py" (
  copy /y "%~dp0pc_remote_server.py" "%DEST%\pc_remote_server.py" >nul
) else (
  powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/EnzoOlivah/EnzoOlivah/claude/remote-pc-control-mobile-5jmznr/pc-remote/pc_remote_server.py' -OutFile '%DEST%\pc_remote_server.py'"
)
if not exist "%DEST%\pc_remote_server.py" (
  echo  Nao consegui baixar o servidor. Coloque pc_remote_server.py na mesma pasta deste arquivo e rode de novo.
  pause
  exit /b 1
)

echo.
echo  [3/3] Configurando o app Claude...
python "%DEST%\pc_remote_server.py" --install
if errorlevel 1 (
  echo  Falha ao configurar o app Claude. Copie a mensagem acima e mande para o Claude.
  pause
  exit /b 1
)

echo.
echo  Pronto! Agora feche o app Claude por completo (inclusive o icone perto do relogio)
echo  e abra de novo. Depois abra o Controle PC e toque em "Ativar receptor".
echo.
pause
