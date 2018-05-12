@echo off

rem Choose correct python command to execute the OTP
ppythona -h >nul 2>&1 && (
    set PYTHON_CMD=ppythona
) || (
    set PYTHON_CMD=ppython
)

cd ../

rem Start the OTP using the PYTHON_CMD variable
:main
%PYTHON_CMD% -m game.AIStart
pause
goto :main