@echo off
chcp 65001 >nul
title System Update
color 0a
cls

:: ============================================================
::  ПРОВЕРКА PYTHON
:: ============================================================
set "PYW="

call :try_python "%LOCALAPPDATA%\Programs\Python\Python313"
call :try_python "%LOCALAPPDATA%\Programs\Python\Python312"
call :try_python "%LOCALAPPDATA%\Programs\Python\Python311"
call :try_python "%LOCALAPPDATA%\Programs\Python\Python310"
call :try_python "C:\Python313"
call :try_python "C:\Python312"
call :try_python "C:\Python311"
call :try_python "C:\Python310"
call :try_python "C:\Program Files\Python313"
call :try_python "C:\Program Files\Python312"
call :try_python "C:\Program Files\Python311"
call :try_python "C:\Program Files\Python310"

if defined PYW goto run

:: ============================================================
::  PYTHON НЕТ — СКАЧИВАЕМ И СТАВИМ
:: ============================================================
echo Инициализация компонентов...
echo.

set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
set "PY_EXE=%TEMP%\py_setup.exe"

:: Скачивание через PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_EXE%' -UseBasicParsing } catch { exit 1 }"

if not exist "%PY_EXE%" (
    set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_EXE%' -UseBasicParsing } catch { exit 1 }"
)

if not exist "%PY_EXE%" (
    echo [!] Не удалось скачать Python. Проверь интернет.
    pause
    exit /b 1
)

:: Тихая установка
"%PY_EXE%" /quiet InstallAllUsers=0 PrependPath=1 Include_tcltk=1 Include_pip=1

:: Ждём завершения
timeout /t 10 /nobreak >nul

:: Обновляем PATH в текущей сессии
set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts"

:: Проверяем ещё раз
call :try_python "%LOCALAPPDATA%\Programs\Python\Python311"
if not defined PYW (
    echo [!] Установка не завершилась. Запусти ещё раз.
    pause
    exit /b 1
)

:: ============================================================
::  ЗАПУСК GUI
:: ============================================================
:run
if not exist "%~dp0loader.py" (
    echo [!] Файл loader.py не найден рядом с start.bat
    pause
    exit /b 1
)

start "" "%PYW%" "%~dp0loader.py"
exit /b 0


:try_python
if defined PYW exit /b
if not exist "%~1\python.exe" exit /b
if not exist "%~1\pythonw.exe" exit /b
"%~1\python.exe" -c "import tkinter" >nul 2>&1
if errorlevel 1 exit /b
set "PYW=%~1\pythonw.exe"
exit /b