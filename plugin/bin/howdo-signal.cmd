@echo off
REM Windows shim for bin/howdo-signal.
REM
REM A plugin host puts bin/ on PATH, but a shebang means nothing here and the
REM extensionless file is not executable. Without this, every bin/ affordance
REM the docs describe is silently POSIX-only -- and How Do claims Windows
REM support explicitly enough to branch the store location on it.
setlocal
where python >nul 2>&1
if %errorlevel%==0 (
  python "%~dp0howdo-signal" %*
  exit /b %errorlevel%
)
py -3 "%~dp0howdo-signal" %*
exit /b %errorlevel%
