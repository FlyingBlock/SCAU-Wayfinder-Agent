@echo off
rem =====================================================================
rem  SCAU Wayfinder - 启动 Web 界面
rem
rem  双击本文件即可。浏览器会自动打开 http://127.0.0.1:8848/
rem  停止：在这个窗口按 Ctrl+C，或直接关掉窗口
rem =====================================================================
setlocal
chcp 936 >nul
title SCAU Wayfinder

set "PORT=8848"
set "PROJ=%~dp0"

rem --- 找 Python：优先 PATH，其次 DSH 自带运行时 -------------------------
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY for /d %%D in ("%USERPROFILE%\.dsh\dsh-runtimes\*") do if not defined PY if exist "%%~fD\dependencies\python\python.exe" set "PY=%%~fD\dependencies\python\python.exe"

if not defined PY goto nopython
if not exist "%PROJ%wayfinder\main.py" goto noproject

rem --- 已经启动：只打开浏览器，不重复开服务 -----------------------------
netstat -ano | find "127.0.0.1:%PORT%" | find "LISTENING" >nul
if not errorlevel 1 (
  start "" "http://127.0.0.1:%PORT%/"
  exit /b 0
)

rem --- 没配模型 key 时提示一次（不影响启动与计算器） ---------------------
if not exist "%PROJ%.env" if not defined LLM_API_KEY if not defined DEEPSEEK_API_KEY (
  echo.
  echo   [提示] 还没有配置模型 API key：问答会失败，计算器不受影响。
  echo          配置命令："%PY%" -m wayfinder setup-key
)

cd /d "%PROJ%"
echo.
echo   正在启动 SCAU Wayfinder ...  浏览器会自动打开 http://127.0.0.1:%PORT%/
echo   停止：Ctrl+C，或直接关闭本窗口。
echo.
"%PY%" -m wayfinder web --port %PORT%
echo.
echo   服务已退出。
pause
exit /b 0

:nopython
echo.
echo   [错误] 找不到 Python。
echo   请安装 Python 3.10+ 并加入 PATH，或把本文件里的 PY 改成 python.exe 的路径。
echo.
pause
exit /b 1

:noproject
echo.
echo   [错误] 找不到项目文件：
echo     %PROJ%wayfinder\main.py
echo   请把本文件放在仓库根目录（与 wayfinder\ 同级）。
echo.
pause
exit /b 1
