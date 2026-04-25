@echo off
setlocal

npx vercel@33 whoami
if errorlevel 1 (
  echo.
  echo Vercel CLI is not logged in. Run:
  echo npx vercel@33 login
  exit /b 1
)

npx vercel@33 deploy --yes
