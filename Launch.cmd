@echo off
rem =====================================================================
rem  SCAU LLM 检索 Harness  ——  Web 界面一键启动
rem
rem  双击本文件：用 DSH 自带 Python 启动服务，浏览器自动打开
rem              http://127.0.0.1:8848/
rem  服务就跑在这个窗口里：Ctrl+C 或直接关掉窗口 = 停止服务
rem
rem  本文件可以随便复制，只要和 harness\ 子目录放在一起就能用。
rem =====================================================================
setlocal
chcp 936 >nul
title SCAU Harness Web

set "PORT=8848"
set "PROJ=%~dp0"
if not exist "%PROJ%harness\cli.py" set "PROJ=D:\Documents\Desktop\SCAU\harness\"

rem --- 已经在运行？只把浏览器打开，不重复启动 ---------------------------
netstat -ano | find "127.0.0.1:%PORT%" | find "LISTENING" >nul
if not errorlevel 1 (
  start "" "http://127.0.0.1:%PORT%/"
  exit /b 0
)

rem --- 找到 DSH 自带的 Python -------------------------------------------
set "PY=C:\Users\FlyingBlock\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if not exist "%PY%" for /d %%D in ("%USERPROFILE%\.dsh\dsh-runtimes\*") do if not exist "%PY%" if exist "%%~fD\dependencies\python\python.exe" set "PY=%%~fD\dependencies\python\python.exe"

if not exist "%PY%" goto nopython
if not exist "%PROJ%harness\cli.py" goto noproject

rem --- 没配 LLM key 时提醒一句 ------------------------------------------
if not exist "%PROJ%harness\.env" if not defined LLM_API_KEY if not defined DEEPSEEK_API_KEY if not defined OPENAI_API_KEY (
  echo.
  echo   [提示] 还没配置 LLM API key：检索能用，问答会失败。
  echo          配置命令："%PY%" -m harness.cli setup-key
)

cd /d "%PROJ%"
echo.
echo   启动 SCAU Harness Web ...  浏览器会自动打开 http://127.0.0.1:%PORT%/
echo   停止服务：Ctrl+C，或直接关闭本窗口
echo.
"%PY%" -m harness.cli web
echo.
echo   服务已退出。
pause
exit /b 0

:nopython
echo.
echo   [错误] 找不到 DSH 自带的 Python：
echo     %PY%
echo   确认 DeepSeek Harness 已安装，或改本文件里的 PY 那一行。
echo.
pause
exit /b 1

:noproject
echo.
echo   [错误] 找不到项目文件：
echo     %PROJ%harness\cli.py
echo   请把本文件放回 harness 项目目录里（与 harness\ 子目录同级）。
echo.
pause
exit /b 1
