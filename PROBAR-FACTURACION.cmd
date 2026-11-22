@echo off
setlocal
set "PROYECTO=%~dp0"
if not exist "%PROYECTO%tests\probar-postgres.cjs" set "PROYECTO=C:\Users\rolda\Documents\Codex\2026-11-19\new-chat-2\facturacion\"
set "MOTOR=%LOCALAPPDATA%\FacturacionServicios\pruebas-pg-0.5.10"
if exist "%MOTOR%\node_modules\@electric-sql\pglite\package.json" if exist "%MOTOR%\node_modules\.bin\node.cmd" goto prueba
echo Preparando el motor de prueba local. La primera vez requiere Internet.
call npm.cmd install --prefix "%MOTOR%" --registry=https://registry.npmjs.org --no-audit --no-fund --no-save @electric-sql/pglite@0.5.10 node@22
if errorlevel 1 goto error
:prueba
call "%MOTOR%\node_modules\.bin\node.cmd" "%PROYECTO%tests\probar-postgres.cjs" "%MOTOR%"
if errorlevel 1 goto error
pause
exit /b 0
:error
echo Prueba pendiente. Revisa el error anterior.
pause
exit /b 1

