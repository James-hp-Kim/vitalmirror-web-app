@echo off
setlocal
set "PATH=%PATH%;C:\Program Files\GitHub CLI"

gh auth status
if errorlevel 1 (
  echo.
  echo GitHub CLI is not logged in. Run:
  echo gh auth login --hostname github.com --git-protocol https --web --scopes repo
  exit /b 1
)

gh repo view James-hp-Kim/vitalmirror-web-app >nul 2>nul
if errorlevel 1 (
  gh repo create James-hp-Kim/vitalmirror-web-app --public --source . --remote origin --push
) else (
  git remote remove origin 2>nul
  git remote add origin https://github.com/James-hp-Kim/vitalmirror-web-app.git
  git push -u origin main
)
