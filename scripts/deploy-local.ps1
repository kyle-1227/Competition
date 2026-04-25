param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$OutputEncoding = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = $OutputEncoding

$RootDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RootDir "greenfianace_server"
$BackendEnvPath = Join-Path $BackendDir ".env"
$FrontendEnvPath = Join-Path $RootDir ".env"
$BackendVenvDir = Join-Path $BackendDir ".venv_deploy"
$BackendPython = Join-Path $BackendVenvDir "Scripts\python.exe"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail {
    param([string]$Message)
    throw $Message
}

function Require-Command {
    param(
        [string]$Name,
        [string]$InstallHint
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        Fail "Command '$Name' was not found. $InstallHint"
    }
    return $command.Source
}

function Read-Default {
    param(
        [string]$Prompt,
        [string]$DefaultValue
    )

    $value = Read-Host "$Prompt [$DefaultValue]"
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $DefaultValue
    }
    return $value.Trim()
}

function Read-SecretText {
    param([string]$Prompt)

    $secure = Read-Host $Prompt -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Read-YesNo {
    param(
        [string]$Prompt,
        [bool]$DefaultValue = $false
    )

    $defaultLabel = if ($DefaultValue) { "Y" } else { "N" }
    while ($true) {
        $value = (Read-Host "$Prompt (Y/N, default $defaultLabel)").Trim()
        if ([string]::IsNullOrWhiteSpace($value)) {
            return $DefaultValue
        }
        switch -Regex ($value) {
            "^(y|yes)$" { return $true }
            "^(n|no)$" { return $false }
            default { Write-Host "Please enter Y or N." -ForegroundColor Yellow }
        }
    }
}

function Assert-SafeName {
    param(
        [string]$Value,
        [string]$Label
    )

    if ($Value -notmatch "^[A-Za-z0-9_]+$") {
        Fail "$Label can only contain letters, numbers, and underscores. Current value: $Value"
    }
}

function Assert-SafeHost {
    param([string]$Value)
    if ($Value -notmatch "^[A-Za-z0-9_.:-]+$") {
        Fail "Database host contains unsupported characters: $Value"
    }
}

function Assert-SafeUser {
    param([string]$Value)
    if ($Value -notmatch "^[A-Za-z0-9_@.%+-]+$") {
        Fail "Database user contains unsupported characters: $Value"
    }
}

function Read-DatabaseName {
    $defaultName = "green_finance"

    while ($true) {
        $name = Read-Default "Database name used by backend DB_NAME" $defaultName
        Assert-SafeName $name "Database name"

        if ($name -eq $defaultName) {
            return $name
        }

        Write-Host ""
        Write-Host "Custom database name entered: $name" -ForegroundColor Yellow
        Write-Host "The deploy script will create/import this database and write it to greenfianace_server\.env as DB_NAME." -ForegroundColor Yellow
        Write-Host "If you later change DB_NAME manually, the backend will use that value instead." -ForegroundColor Yellow

        if (Read-YesNo "Continue with custom database name" $false) {
            return $name
        }

        Write-Host "Please enter another database name, or press Enter to use $defaultName." -ForegroundColor Yellow
    }
}

function Format-DotEnvValue {
    param([string]$Value)
    if ($null -eq $Value) {
        $Value = ""
    }
    $escaped = $Value.Replace("\", "\\").Replace('"', '\"')
    return '"' + $escaped + '"'
}

function Quote-PS {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Test-PortInUse {
    param([int]$Port)

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if ($async.AsyncWaitHandle.WaitOne(500, $false)) {
            $client.EndConnect($async)
            return $true
        }
        return $false
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Get-SqlPlan {
    $fullGreen = Join-Path $BackendDir "green_finance.sql"
    $fullCity = Join-Path $BackendDir "city_carbon_gdp.sql"
    $sampleGreen = Join-Path $BackendDir "sql_samples\green_finance_sample.sql"
    $sampleCity = Join-Path $BackendDir "sql_samples\city_carbon_gdp_sample.sql"

    if ((Test-Path -LiteralPath $fullGreen) -and (Test-Path -LiteralPath $fullCity)) {
        return [PSCustomObject]@{
            GreenSql = $fullGreen
            CitySql = $fullCity
            UsesSample = $false
        }
    }

    if ((Test-Path -LiteralPath $sampleGreen) -and (Test-Path -LiteralPath $sampleCity)) {
        return [PSCustomObject]@{
            GreenSql = $sampleGreen
            CitySql = $sampleCity
            UsesSample = $true
        }
    }

    Fail "Database SQL was not found. Provide greenfianace_server\green_finance.sql and city_carbon_gdp.sql, or greenfianace_server\sql_samples\*_sample.sql."
}

function Test-RequiredFiles {
    $required = @(
        (Join-Path $RootDir "package.json"),
        (Join-Path $RootDir "pnpm-lock.yaml"),
        (Join-Path $BackendDir "server.py"),
        (Join-Path $BackendDir "requirements.txt")
    )
    foreach ($path in $required) {
        if (-not (Test-Path -LiteralPath $path)) {
            Fail "Required file is missing: $path"
        }
    }

    [void](Get-SqlPlan)
}

function New-ImportSqlPath {
    param(
        [string]$SourcePath,
        [string]$DatabaseName
    )

    $content = Get-Content -LiteralPath $SourcePath -Raw -Encoding UTF8
    $bt = [char]96
    $replacement = "USE $bt$DatabaseName$bt;"
    $normalized = [regex]::Replace(
        $content,
        '(?im)^\s*use\s+green_finance\s*;\s*$',
        $replacement
    )

    if ($normalized -eq $content) {
        return [PSCustomObject]@{
            Path = $SourcePath
            Temporary = $false
        }
    }

    $tempPath = Join-Path ([IO.Path]::GetTempPath()) ("green_finance_import_" + [Guid]::NewGuid().ToString("N") + ".sql")
    Set-Content -LiteralPath $tempPath -Value $normalized -Encoding UTF8
    return [PSCustomObject]@{
        Path = $tempPath
        Temporary = $true
    }
}

function Invoke-MySqlFile {
    param(
        [string]$MysqlExe,
        [string]$DatabaseHost,
        [string]$DatabaseUser,
        [string]$DatabaseName,
        [string]$SqlPath
    )

    $dq = [char]34
    $mysqlQuoted = "$dq$MysqlExe$dq"
    $sqlQuoted = "$dq$SqlPath$dq"
    $cmd = "$mysqlQuoted --host=$DatabaseHost --user=$DatabaseUser --default-character-set=utf8mb4 --binary-mode=1 $DatabaseName < $sqlQuoted"

    & cmd.exe /d /c $cmd
    if ($LASTEXITCODE -ne 0) {
        Fail "Failed to import SQL: $SqlPath"
    }
}

function Write-BackendEnv {
    param(
        [string]$DatabaseHost,
        [string]$DatabaseUser,
        [string]$DatabasePassword,
        [string]$DatabaseName,
        [bool]$EnableAi,
        [string]$DeepSeekApiKey
    )

    $lines = @(
        "DB_HOST=" + (Format-DotEnvValue $DatabaseHost),
        "DB_USER=" + (Format-DotEnvValue $DatabaseUser),
        "DB_PASSWORD=" + (Format-DotEnvValue $DatabasePassword),
        "DB_NAME=" + (Format-DotEnvValue $DatabaseName),
        "DB_CHARSET=" + (Format-DotEnvValue "utf8mb4"),
        "",
        "DEEPSEEK_API_KEY=" + (Format-DotEnvValue $DeepSeekApiKey),
        "DEEPSEEK_BASE_URL=" + (Format-DotEnvValue "https://api.deepseek.com"),
        "DEEPSEEK_MODEL=" + (Format-DotEnvValue "deepseek-chat"),
        "DEEPSEEK_TIMEOUT=" + (Format-DotEnvValue "60")
    )
    $lines | Set-Content -LiteralPath $BackendEnvPath -Encoding UTF8

    if (-not $EnableAi) {
        Write-Host ""
        Write-Host "AI assistant is disabled: AI chat, page summaries, tooltip AI analysis, and streaming chat will be unavailable." -ForegroundColor Yellow
        Write-Host "Maps, charts, database queries, and prediction views will still work." -ForegroundColor Yellow
    }
}

function Write-FrontendEnv {
    $lines = @(
        "VITE_APP_TITLE=Green Finance Carbon Reduction Dashboard",
        "VITE_BASE=/vue3-vite5-dashboard/",
        "VITE_APP_DOMAIN=/api"
    )
    $lines | Set-Content -LiteralPath $FrontendEnvPath -Encoding UTF8
}

function Main {
    Write-Host "Green Finance Dashboard local one-click deploy" -ForegroundColor Green
    Write-Host "Workspace: $RootDir"

    Test-RequiredFiles
    if ($DryRun) {
        Write-Host "DryRun passed: required files and SQL entrypoints exist." -ForegroundColor Green
        return
    }

    Write-Step "Checking local commands"
    $mysqlExe = Require-Command "mysql" "Install MySQL Client and make sure mysql.exe is in PATH."
    [void](Require-Command "node" "Install Node.js 18+.")
    [void](Require-Command "pnpm" "Install pnpm, or run corepack enable and try again.")
    [void](Require-Command "python" "Install Python 3.10+ and make sure python is in PATH.")

    Write-Step "Enter database connection"
    $dbHost = Read-Default "MySQL host" "127.0.0.1"
    $dbUser = Read-Default "MySQL user" "root"
    $dbName = Read-DatabaseName
    $dbPassword = Read-SecretText "MySQL password"

    Assert-SafeHost $dbHost
    Assert-SafeUser $dbUser

    Write-Step "Choose whether to enable AI assistant"
    $enableAi = Read-YesNo "Enable AI assistant" $false
    $deepSeekApiKey = ""
    if ($enableAi) {
        while ([string]::IsNullOrWhiteSpace($deepSeekApiKey)) {
            $deepSeekApiKey = (Read-SecretText "DeepSeek API Key").Trim()
            if ([string]::IsNullOrWhiteSpace($deepSeekApiKey)) {
                Write-Host "DeepSeek API Key cannot be empty when AI assistant is enabled." -ForegroundColor Yellow
            }
        }
    }

    Write-Step "Writing environment files"
    Write-BackendEnv $dbHost $dbUser $dbPassword $dbName $enableAi $deepSeekApiKey
    Write-FrontendEnv
    Write-Host "Generated: $BackendEnvPath"
    Write-Host "Generated: $FrontendEnvPath"

    Write-Step "Creating database and importing SQL"
    $sqlPlan = Get-SqlPlan
    if ($sqlPlan.UsesSample) {
        Write-Host ""
        Write-Host "Sample/simple SQL mode: full SQL was not found, so this script will import greenfianace_server\sql_samples." -ForegroundColor Yellow
        Write-Host "Impact: only a small subset of tables and rows is loaded." -ForegroundColor Yellow
        Write-Host "Maps, charts, rankings, drill-down data, prediction views, and AI summaries may be incomplete, sparse, or not representative." -ForegroundColor Yellow
        Write-Host "For a complete demo, restore the full SQL files or full dataset listed in the competition summary form before running this script." -ForegroundColor Yellow
        Write-Host ""
    }

    $bt = [char]96
    $createSql = "CREATE DATABASE IF NOT EXISTS $bt$dbName$bt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    $oldMysqlPwd = $env:MYSQL_PWD
    $tempFiles = New-Object System.Collections.Generic.List[string]
    try {
        $env:MYSQL_PWD = $dbPassword
        & $mysqlExe "--host=$dbHost" "--user=$dbUser" "--default-character-set=utf8mb4" "-e" $createSql
        if ($LASTEXITCODE -ne 0) {
            Fail "Failed to create database. Check MySQL password, user, and service status."
        }

        foreach ($sql in @($sqlPlan.GreenSql, $sqlPlan.CitySql)) {
            Write-Host "Importing: $sql"
            $importSql = New-ImportSqlPath $sql $dbName
            if ($importSql.Temporary) {
                $tempFiles.Add($importSql.Path)
            }
            Invoke-MySqlFile $mysqlExe $dbHost $dbUser $dbName $importSql.Path
        }
    }
    finally {
        $env:MYSQL_PWD = $oldMysqlPwd
        foreach ($temp in $tempFiles) {
            if (Test-Path -LiteralPath $temp) {
                Remove-Item -LiteralPath $temp -Force
            }
        }
    }

    Write-Step "Installing frontend dependencies"
    if (-not (Test-Path -LiteralPath (Join-Path $RootDir "node_modules"))) {
        Push-Location $RootDir
        $oldHusky = $env:HUSKY
        try {
            $env:HUSKY = "0"
            & pnpm install
            if ($LASTEXITCODE -ne 0) {
                Fail "pnpm install failed."
            }
        }
        finally {
            $env:HUSKY = $oldHusky
            Pop-Location
        }
    }
    else {
        Write-Host "node_modules exists; skipping pnpm install."
    }

    Write-Step "Installing backend dependencies"
    if (-not (Test-Path -LiteralPath $BackendPython)) {
        Push-Location $BackendDir
        try {
            & python -m venv $BackendVenvDir
            if ($LASTEXITCODE -ne 0) {
                Fail "Failed to create Python virtual environment."
            }
        }
        finally {
            Pop-Location
        }
    }

    & $BackendPython -m pip install -r (Join-Path $BackendDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        Fail "Failed to install backend dependencies."
    }

    Write-Step "Checking ports"
    if (Test-PortInUse 8000) {
        Fail "Port 8000 is already in use. Close the backend process using it and try again."
    }
    if (Test-PortInUse 5173) {
        Fail "Port 5173 is already in use. Close the frontend process using it and try again."
    }

    Write-Step "Starting services"
    $backendCommand = "Set-Location -LiteralPath $(Quote-PS $BackendDir); & $(Quote-PS $BackendPython) -m uvicorn server:app --reload --host 0.0.0.0 --port 8000"
    $frontendCommand = "Set-Location -LiteralPath $(Quote-PS $RootDir); pnpm run serve"

    Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand) -WindowStyle Normal
    Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand) -WindowStyle Normal

    Write-Host ""
    Write-Host "Deployment has started." -ForegroundColor Green
    Write-Host "Backend: http://127.0.0.1:8000/api"
    Write-Host "Frontend: http://localhost:5173/vue3-vite5-dashboard/"
    Write-Host "Keep the newly opened frontend and backend terminal windows running."
}

try {
    Main
}
catch {
    Write-Host ""
    Write-Host "Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
