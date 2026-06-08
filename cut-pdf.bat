@echo off
setlocal

rem === PDF Cutter: drag & drop a PDF onto this file to cut it ===

rem Directory where this .bat lives (with trailing backslash)
set "SCRIPT_DIR=%~dp0"

rem Pick the venv python if it exists, otherwise fall back to system python
set "PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

rem No file dropped -> show usage and quit
if "%~1"=="" (
    echo.
    echo   Drag and drop a PDF file onto this .bat to cut it.
    echo.
    pause
    exit /b 1
)

:next
if "%~1"=="" goto done

echo.
echo ================================================================
echo  Processing: %~nx1
echo ================================================================
echo.

"%PYTHON%" "%SCRIPT_DIR%main.py" "%~1"

shift
goto next

:done
echo.
echo Done.
pause
endlocal
