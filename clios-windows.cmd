@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\windows_launcher.ps1" %*
set "CLIOS_EXIT_CODE=%ERRORLEVEL%"

if not "%CLIOS_EXIT_CODE%"=="0" (
    echo.
    echo [ERREUR] CliOS n'a pas pu demarrer. Consultez le journal indique ci-dessus.
    echo Appuyez sur une touche pour fermer cette fenetre.
    pause >nul
)

exit /b %CLIOS_EXIT_CODE%
