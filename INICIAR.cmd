@echo off
cd /d "%~dp0"
python -V >nul 2>nul && goto python
py -3 -V >nul 2>nul && goto launcher
for /d %%G in ("%ProgramFiles%\Blender Foundation\Blender*") do for /d %%H in ("%%~G\*") do if exist "%%~H\python\bin\python.exe" (
  "%%~H\python\bin\python.exe" -B servidor.py --abrir
  goto fin
)
echo Se requiere Python 3.10 o posterior.
goto fin
:python
python -B servidor.py --abrir
goto fin
:launcher
py -3 -B servidor.py --abrir
:fin
pause
