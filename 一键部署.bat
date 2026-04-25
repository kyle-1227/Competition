@echo off
chcp 65001 >nul
setlocal

set "ROOT_DIR=%~dp0"
set "DEPLOY_SCRIPT=%ROOT_DIR%scripts\deploy-local.ps1"

if not exist "%DEPLOY_SCRIPT%" (
  echo 未找到部署脚本: %DEPLOY_SCRIPT%
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%DEPLOY_SCRIPT%"

echo.
echo 部署脚本已结束。
pause
