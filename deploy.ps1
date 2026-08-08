[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$ForceInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = $script:Utf8NoBom
try {
    [Console]::InputEncoding = $script:Utf8NoBom
    [Console]::OutputEncoding = $script:Utf8NoBom
}
catch {
    # 某些非交互宿主不允许修改控制台编码，不影响脚本继续执行。
}

$script:ExitSuccess = 0
$script:ExitFailure = 1
$script:ExitCancelled = 2
$script:FrontendPort = 5173
$script:BackendPort = 8002
$script:DatabaseHost = "127.0.0.1"
$script:DatabaseUser = "root"
$script:DatabaseName = "green_finance"
$script:RootDir = $PSScriptRoot
$script:BackendDir = Join-Path $script:RootDir "greenfianace_server"
$script:BackendVenvDir = Join-Path $script:BackendDir ".venv"
$script:BackendPython = Join-Path $script:BackendVenvDir "Scripts\python.exe"
$script:FrontendFingerprintPath = Join-Path $script:RootDir "node_modules\.green-finance-dependencies.sha256"
$script:BackendFingerprintPath = Join-Path $script:BackendVenvDir ".green-finance-requirements.sha256"
$script:SqlPaths = @(
    (Join-Path $script:BackendDir "green_finance.sql"),
    (Join-Path $script:BackendDir "city_carbon_gdp.sql")
)

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)

    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet("Pass", "Warn", "Info")][string]$Level = "Info"
    )

    $color = switch ($Level) {
        "Pass" { "Green" }
        "Warn" { "Yellow" }
        default { "Gray" }
    }
    Write-Host ("[{0}] {1}" -f $Label, $Message) -ForegroundColor $color
}

function Fail {
    param([Parameter(Mandatory = $true)][string]$Message)

    throw $Message
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Content
    )

    [IO.File]::WriteAllText($Path, $Content, $script:Utf8NoBom)
}

function Read-Utf8Text {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [IO.File]::ReadAllText($Path, $script:Utf8NoBom)
}

function Read-SecretText {
    param([Parameter(Mandatory = $true)][string]$Prompt)

    $secure = Read-Host $Prompt -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Assert-SafeDatabaseName {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -notmatch "^[A-Za-z0-9_]+$") {
        Fail "数据库名只能包含英文字母、数字和下划线：$Value"
    }
}

function Assert-SafeDatabaseHost {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -notmatch "^[A-Za-z0-9_.:-]+$") {
        Fail "数据库地址包含不支持的字符：$Value"
    }
}

function Assert-SafeDatabaseUser {
    param([Parameter(Mandatory = $true)][string]$Value)

    if ($Value -notmatch "^[A-Za-z0-9_@.%+-]+$") {
        Fail "数据库用户名包含不支持的字符：$Value"
    }
}

function Quote-PowerShellLiteral {
    param([Parameter(Mandatory = $true)][string]$Value)

    return "'" + $Value.Replace("'", "''") + "'"
}

function Get-CommandPath {
    param([Parameter(Mandatory = $true)][string]$Name)

    $command = Get-Command -Name $Name -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $command) {
        return $null
    }
    return $command.Source
}

function Get-ToolVersionText {
    param([Parameter(Mandatory = $true)][string]$Path)

    $output = & $Path --version 2>&1
    $exitCode = $LASTEXITCODE
    $text = (($output | ForEach-Object { $_.ToString() }) -join " ").Trim()
    if ($exitCode -ne 0) {
        Fail "无法读取工具版本：$Path"
    }
    return $text
}

function ConvertTo-NumericVersion {
    param([Parameter(Mandatory = $true)][string]$Text)

    $match = [regex]::Match($Text, '(?<!\d)(?<version>\d+\.\d+(?:\.\d+){0,2})')
    if (-not $match.Success) {
        return $null
    }
    try {
        return [version]$match.Groups["version"].Value
    }
    catch {
        return $null
    }
}

function Get-ToolStatus {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][version]$MinimumVersion
    )

    $path = Get-CommandPath $Name
    if ([string]::IsNullOrWhiteSpace($path)) {
        return [PSCustomObject]@{
            Name = $Name
            Path = $null
            VersionText = $null
            Version = $null
            Available = $false
            Supported = $false
        }
    }

    try {
        $versionText = Get-ToolVersionText $path
        $version = ConvertTo-NumericVersion $versionText
        $supported = ($null -ne $version) -and ($version -ge $MinimumVersion)
        return [PSCustomObject]@{
            Name = $Name
            Path = $path
            VersionText = $versionText
            Version = $version
            Available = $true
            Supported = $supported
        }
    }
    catch {
        return [PSCustomObject]@{
            Name = $Name
            Path = $path
            VersionText = $_.Exception.Message
            Version = $null
            Available = $true
            Supported = $false
        }
    }
}

function Get-EnvironmentReport {
    $specifications = @(
        [PSCustomObject]@{ Key = "Mysql"; Name = "mysql"; Minimum = [version]"8.0"; Hint = "请安装 MySQL 8.0+ Client 并加入 PATH。" },
        [PSCustomObject]@{ Key = "Node"; Name = "node"; Minimum = [version]"18.0"; Hint = "请安装 Node.js 18+。" },
        [PSCustomObject]@{ Key = "Pnpm"; Name = "pnpm"; Minimum = [version]"8.0"; Hint = "请安装 pnpm 8+，或执行 corepack enable。" },
        [PSCustomObject]@{ Key = "Python"; Name = "python"; Minimum = [version]"3.10"; Hint = "请安装 Python 3.10+ 并加入 PATH。" }
    )

    $report = @{}
    foreach ($specification in $specifications) {
        $status = Get-ToolStatus $specification.Name $specification.Minimum
        $status | Add-Member -NotePropertyName Key -NotePropertyValue $specification.Key
        $status | Add-Member -NotePropertyName Minimum -NotePropertyValue $specification.Minimum
        $status | Add-Member -NotePropertyName Hint -NotePropertyValue $specification.Hint
        $report[$specification.Key] = $status
    }
    return $report
}

function Assert-EnvironmentReport {
    param([Parameter(Mandatory = $true)][hashtable]$Report)

    foreach ($key in @("Mysql", "Node", "Pnpm", "Python")) {
        $status = $Report[$key]
        if (-not $status.Available) {
            Fail "未找到命令 '$($status.Name)'。$($status.Hint)"
        }
        if ($null -eq $status.Version) {
            Fail "无法识别 $($status.Name) 的版本。检测结果：$($status.VersionText)"
        }
        if (-not $status.Supported) {
            Fail "$($status.Name) 版本过低，需要 $($status.Minimum)+。当前：$($status.VersionText)"
        }
    }
}

function Ensure-LocalEnv {
    $localEnvPath = Join-Path $script:RootDir ".env"
    $templatePath = Join-Path $script:RootDir ".env.example"

    if (Test-Path -LiteralPath $localEnvPath) {
        if (-not (Test-Path -LiteralPath $localEnvPath -PathType Leaf)) {
            Fail "根目录 .env 已存在但不是文件，请处理后重试：$localEnvPath"
        }
        Write-Check "本地配置" "已存在 .env，保留现有内容，不覆盖。" "Pass"
        return
    }

    Copy-Item -LiteralPath $templatePath -Destination $localEnvPath
    Write-Check "本地配置" "已从 .env.example 生成 .env；模板不含真实密码。" "Warn"
}

function Test-RequiredFiles {
    $requiredFiles = @(
        (Join-Path $script:RootDir ".env.example"),
        (Join-Path $script:RootDir "package.json"),
        (Join-Path $script:RootDir "pnpm-lock.yaml"),
        (Join-Path $script:RootDir "requirements.txt"),
        (Join-Path $script:RootDir "vite.config.ts"),
        (Join-Path $script:BackendDir "server.py")
    ) + $script:SqlPaths

    foreach ($path in $requiredFiles) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            Fail "缺少部署必需文件：$path"
        }
    }
    return $requiredFiles
}

function Get-StringHash {
    param([Parameter(Mandatory = $true)][string]$Value)

    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $script:Utf8NoBom.GetBytes($Value)
        $hash = $algorithm.ComputeHash($bytes)
        return (($hash | ForEach-Object { $_.ToString("x2") }) -join "")
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-CombinedFingerprint {
    param(
        [Parameter(Mandatory = $true)][string[]]$Paths,
        [string[]]$ExtraValues = @()
    )

    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($path in $Paths) {
        $fileHash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        $parts.Add(("file:{0}:{1}" -f ([IO.Path]::GetFileName($path)), $fileHash))
    }
    foreach ($value in $ExtraValues) {
        $parts.Add("extra:$value")
    }
    return Get-StringHash ($parts -join "`n")
}

function Read-Fingerprint {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    return (Read-Utf8Text $Path).Trim()
}

function Get-FrontendDependencyStatus {
    param([bool]$Force)

    $expected = Get-CombinedFingerprint @(
        (Join-Path $script:RootDir "package.json"),
        (Join-Path $script:RootDir "pnpm-lock.yaml")
    )
    $directoryExists = Test-Path -LiteralPath (Join-Path $script:RootDir "node_modules") -PathType Container
    $stored = Read-Fingerprint $script:FrontendFingerprintPath

    $reason = "依赖指纹未变化"
    $installRequired = $false
    if ($Force) {
        $reason = "已指定 -ForceInstall"
        $installRequired = $true
    }
    elseif (-not $directoryExists) {
        $reason = "node_modules 不存在"
        $installRequired = $true
    }
    elseif ([string]::IsNullOrWhiteSpace($stored)) {
        $reason = "未找到前端依赖指纹"
        $installRequired = $true
    }
    elseif ($stored -ne $expected) {
        $reason = "package.json 或 pnpm-lock.yaml 已变化"
        $installRequired = $true
    }

    return [PSCustomObject]@{
        Expected = $expected
        Stored = $stored
        InstallRequired = $installRequired
        Reason = $reason
    }
}

function Get-PythonVersionForFingerprint {
    param([Parameter(Mandatory = $true)][string]$PythonPath)

    $versionText = Get-ToolVersionText $PythonPath
    $version = ConvertTo-NumericVersion $versionText
    if ($null -eq $version) {
        Fail "无法识别 Python 版本：$versionText"
    }
    return $version.ToString()
}

function Get-BackendDependencyStatus {
    param(
        [Parameter(Mandatory = $true)][string]$PythonPath,
        [bool]$Force
    )

    $pythonVersion = Get-PythonVersionForFingerprint $PythonPath
    $expected = Get-CombinedFingerprint @(
        (Join-Path $script:RootDir "requirements.txt")
    ) @("python:$pythonVersion")
    $stored = Read-Fingerprint $script:BackendFingerprintPath

    $reason = "依赖指纹未变化"
    $installRequired = $false
    if ($Force) {
        $reason = "已指定 -ForceInstall"
        $installRequired = $true
    }
    elseif ([string]::IsNullOrWhiteSpace($stored)) {
        $reason = "未找到后端依赖指纹"
        $installRequired = $true
    }
    elseif ($stored -ne $expected) {
        $reason = "requirements.txt 或 Python 版本已变化"
        $installRequired = $true
    }

    return [PSCustomObject]@{
        Expected = $expected
        Stored = $stored
        PythonVersion = $pythonVersion
        InstallRequired = $installRequired
        Reason = $reason
    }
}

function Test-PortInUse {
    param([Parameter(Mandatory = $true)][int]$Port)

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $asyncResult = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if ($asyncResult.AsyncWaitHandle.WaitOne(500, $false)) {
            $client.EndConnect($asyncResult)
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

function Get-SqlTables {
    $tableSet = New-Object "System.Collections.Generic.HashSet[string]" ([StringComparer]::OrdinalIgnoreCase)
    $pattern = '(?im)^\s*DROP\s+TABLE\s+IF\s+EXISTS\s+(?:(?:`[^`]+`|[A-Za-z0-9_]+)\s*\.\s*)?`?(?<name>[A-Za-z0-9_]+)`?\s*;'
    foreach ($path in $script:SqlPaths) {
        $content = Read-Utf8Text $path
        foreach ($match in [regex]::Matches($content, $pattern)) {
            [void]$tableSet.Add($match.Groups["name"].Value)
        }
    }
    return @($tableSet | Sort-Object)
}

function Test-DatabaseExists {
    param(
        [Parameter(Mandatory = $true)][string]$MysqlPath,
        [Parameter(Mandatory = $true)][string]$DatabaseHost,
        [Parameter(Mandatory = $true)][string]$DatabaseUser,
        [Parameter(Mandatory = $true)][string]$DatabaseName
    )

    $query = "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '$DatabaseName';"
    $output = & $MysqlPath "--host=$DatabaseHost" "--user=$DatabaseUser" "--default-character-set=utf8mb4" "--batch" "--skip-column-names" "-e" $query 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $detail = (($output | ForEach-Object { $_.ToString() }) -join " ").Trim()
        Fail "无法连接 MySQL 或查询目标数据库。请检查服务、地址、用户和密码。$detail"
    }
    return ((($output | ForEach-Object { $_.ToString() }) -join "`n").Trim() -eq $DatabaseName)
}

function Confirm-ExistingDatabaseRebuild {
    param(
        [Parameter(Mandatory = $true)][string]$DatabaseName,
        [Parameter(Mandatory = $true)][string[]]$TableNames
    )

    Write-Host ""
    Write-Host "警告：数据库 '$DatabaseName' 已存在。继续会按 SQL 删除并重建以下表：" -ForegroundColor Yellow
    foreach ($tableName in $TableNames) {
        Write-Host "  - $tableName" -ForegroundColor Yellow
    }
    Write-Host ""
    $confirmation = (Read-Host "请输入完整数据库名 '$DatabaseName' 以确认；直接回车或输入其他内容取消").Trim()
    return ($confirmation -eq $DatabaseName)
}

function New-ImportSqlPath {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$DatabaseName
    )

    if ($DatabaseName -eq "green_finance") {
        return [PSCustomObject]@{ Path = $SourcePath; Temporary = $false }
    }

    $content = Read-Utf8Text $SourcePath
    $backtick = [char]96
    $replacement = "USE $backtick$DatabaseName$backtick;"
    $normalized = [regex]::Replace(
        $content,
        '(?im)^\s*use\s+`?green_finance`?\s*;\s*$',
        $replacement
    )

    if ($normalized -eq $content) {
        return [PSCustomObject]@{ Path = $SourcePath; Temporary = $false }
    }

    $tempPath = Join-Path ([IO.Path]::GetTempPath()) ("green_finance_import_{0}.sql" -f [Guid]::NewGuid().ToString("N"))
    Write-Utf8NoBom $tempPath $normalized
    return [PSCustomObject]@{ Path = $tempPath; Temporary = $true }
}

function Invoke-MySqlFile {
    param(
        [Parameter(Mandatory = $true)][string]$MysqlPath,
        [Parameter(Mandatory = $true)][string]$DatabaseHost,
        [Parameter(Mandatory = $true)][string]$DatabaseUser,
        [Parameter(Mandatory = $true)][string]$DatabaseName,
        [Parameter(Mandatory = $true)][string]$SqlPath
    )

    $startInfo = New-Object Diagnostics.ProcessStartInfo
    $startInfo.FileName = $MysqlPath
    $startInfo.Arguments = "--host=$DatabaseHost --user=$DatabaseUser --default-character-set=utf8mb4 --binary-mode=1 $DatabaseName"
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $false
    $startInfo.RedirectStandardError = $false
    $startInfo.CreateNoWindow = $true

    $process = New-Object Diagnostics.Process
    $process.StartInfo = $startInfo
    $fileStream = $null
    try {
        [void]$process.Start()
        $fileStream = [IO.File]::OpenRead($SqlPath)
        $fileStream.CopyTo($process.StandardInput.BaseStream)
        $process.StandardInput.BaseStream.Flush()
        $process.StandardInput.Close()
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) {
            Fail "SQL 导入失败：$SqlPath"
        }
    }
    finally {
        if ($null -ne $fileStream) {
            $fileStream.Dispose()
        }
        $process.Dispose()
    }
}

function Invoke-DatabaseDeployment {
    param(
        [Parameter(Mandatory = $true)][string]$MysqlPath,
        [Parameter(Mandatory = $true)][string]$DatabaseHost,
        [Parameter(Mandatory = $true)][string]$DatabaseUser,
        [AllowEmptyString()][string]$DatabasePassword,
        [Parameter(Mandatory = $true)][string]$DatabaseName
    )

    $hadMysqlPassword = Test-Path Env:MYSQL_PWD
    $oldMysqlPassword = if ($hadMysqlPassword) { (Get-Item Env:MYSQL_PWD).Value } else { $null }
    $temporaryFiles = New-Object System.Collections.Generic.List[string]

    try {
        $env:MYSQL_PWD = $DatabasePassword
        $databaseExists = Test-DatabaseExists $MysqlPath $DatabaseHost $DatabaseUser $DatabaseName
        if ($databaseExists) {
            $tables = @(Get-SqlTables)
            if (-not (Confirm-ExistingDatabaseRebuild $DatabaseName $tables)) {
                Write-Host "已取消：未写文件、未导入数据库、未安装依赖、未启动服务。" -ForegroundColor Yellow
                return $false
            }
        }

        $backtick = [char]96
        $createSql = "CREATE DATABASE IF NOT EXISTS $backtick$DatabaseName$backtick CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        $createOutput = & $MysqlPath "--host=$DatabaseHost" "--user=$DatabaseUser" "--default-character-set=utf8mb4" "-e" $createSql 2>&1
        $createExitCode = $LASTEXITCODE
        if ($createExitCode -ne 0) {
            $detail = (($createOutput | ForEach-Object { $_.ToString() }) -join " ").Trim()
            Fail "创建数据库失败。请检查 MySQL 权限和服务状态。$detail"
        }

        foreach ($sqlPath in $script:SqlPaths) {
            $importSql = New-ImportSqlPath $sqlPath $DatabaseName
            if ($importSql.Temporary) {
                $temporaryFiles.Add($importSql.Path)
            }
            Write-Host "导入：$sqlPath"
            Invoke-MySqlFile $MysqlPath $DatabaseHost $DatabaseUser $DatabaseName $importSql.Path
        }
        return $true
    }
    finally {
        if ($hadMysqlPassword) {
            $env:MYSQL_PWD = $oldMysqlPassword
        }
        else {
            Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue
        }
        foreach ($tempPath in $temporaryFiles) {
            if (Test-Path -LiteralPath $tempPath -PathType Leaf) {
                Remove-Item -LiteralPath $tempPath -Force
            }
        }
    }
}

function Install-FrontendDependencies {
    param(
        [Parameter(Mandatory = $true)][string]$PnpmPath,
        [bool]$Force
    )

    $status = Get-FrontendDependencyStatus $Force
    if (-not $status.InstallRequired) {
        Write-Check "跳过" "前端依赖：$($status.Reason)" "Pass"
        return
    }

    Write-Host "前端依赖需要安装：$($status.Reason)"
    $hadHusky = Test-Path Env:HUSKY
    $oldHusky = if ($hadHusky) { (Get-Item Env:HUSKY).Value } else { $null }
    Push-Location $script:RootDir
    try {
        $env:HUSKY = "0"
        & $PnpmPath install --frozen-lockfile | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Fail "前端依赖安装失败。"
        }
        Write-Utf8NoBom $script:FrontendFingerprintPath ($status.Expected + "`n")
    }
    finally {
        if ($hadHusky) {
            $env:HUSKY = $oldHusky
        }
        else {
            Remove-Item Env:HUSKY -ErrorAction SilentlyContinue
        }
        Pop-Location
    }
}

function Install-BackendDependencies {
    param(
        [Parameter(Mandatory = $true)][string]$SystemPythonPath,
        [bool]$Force
    )

    if (-not (Test-Path -LiteralPath $script:BackendPython -PathType Leaf)) {
        Write-Host "创建后端虚拟环境：$script:BackendVenvDir"
        & $SystemPythonPath -m venv $script:BackendVenvDir | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Fail "创建后端 Python 虚拟环境失败。"
        }
    }

    $status = Get-BackendDependencyStatus $script:BackendPython $Force
    if (-not $status.InstallRequired) {
        Write-Check "跳过" "后端依赖：$($status.Reason)" "Pass"
        return
    }

    Write-Host "后端依赖需要安装：$($status.Reason)"
    & $script:BackendPython -m pip install --disable-pip-version-check -r (Join-Path $script:RootDir "requirements.txt") | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Fail "后端依赖安装失败。"
    }
    Write-Utf8NoBom $script:BackendFingerprintPath ($status.Expected + "`n")
}

function Assert-PortsAvailable {
    foreach ($port in @($script:BackendPort, $script:FrontendPort)) {
        if (Test-PortInUse $port) {
            Fail "端口 $port 已被占用，请关闭对应进程后重试。"
        }
    }
}

function Start-Services {
    param(
        [Parameter(Mandatory = $true)][hashtable]$EnvironmentReport,
        [Parameter(Mandatory = $true)][string]$DatabaseHost,
        [Parameter(Mandatory = $true)][string]$DatabaseUser,
        [AllowEmptyString()][string]$DatabasePassword,
        [Parameter(Mandatory = $true)][string]$DatabaseName
    )

    $powershellPath = Get-CommandPath "powershell.exe"
    if ([string]::IsNullOrWhiteSpace($powershellPath)) {
        Fail "未找到 powershell.exe，无法创建前后端服务窗口。"
    }

    $backendCommand = "Set-Location -LiteralPath $(Quote-PowerShellLiteral $script:BackendDir); & $(Quote-PowerShellLiteral $script:BackendPython) -m uvicorn server:app --reload --host 0.0.0.0 --port $script:BackendPort"
    $frontendCommand = "Set-Location -LiteralPath $(Quote-PowerShellLiteral $script:RootDir); & $(Quote-PowerShellLiteral $EnvironmentReport['Pnpm'].Path) run dev"

    $runtimeEnvironment = @{
        SERVER_PORT = [string]$script:BackendPort
        DB_HOST = $DatabaseHost
        DB_USER = $DatabaseUser
        DB_PASSWORD = $DatabasePassword
        DB_NAME = $DatabaseName
        DB_CHARSET = "utf8mb4"
    }
    $savedEnvironment = @{}
    foreach ($name in $runtimeEnvironment.Keys) {
        $savedEnvironment[$name] = [PSCustomObject]@{
            Exists = Test-Path -LiteralPath ("Env:{0}" -f $name)
            Value = [Environment]::GetEnvironmentVariable($name, [EnvironmentVariableTarget]::Process)
        }
        [Environment]::SetEnvironmentVariable(
            $name,
            [string]$runtimeEnvironment[$name],
            [EnvironmentVariableTarget]::Process
        )
    }

    try {
        Start-Process -FilePath $powershellPath -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand) -WorkingDirectory $script:BackendDir -WindowStyle Normal
    }
    finally {
        foreach ($name in $savedEnvironment.Keys) {
            $saved = $savedEnvironment[$name]
            $value = if ($saved.Exists) { $saved.Value } else { $null }
            [Environment]::SetEnvironmentVariable(
                $name,
                $value,
                [EnvironmentVariableTarget]::Process
            )
        }
    }

    Start-Process -FilePath $powershellPath -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand) -WorkingDirectory $script:RootDir -WindowStyle Normal
}

function Show-DryRun {
    param(
        [Parameter(Mandatory = $true)][string[]]$RequiredFiles,
        [Parameter(Mandatory = $true)][hashtable]$EnvironmentReport,
        [bool]$Force
    )

    Write-Step "路径与必需文件"
    Write-Check "项目根目录" $script:RootDir "Info"
    Write-Check "后端目录" $script:BackendDir "Info"
    foreach ($path in $RequiredFiles) {
        Write-Check "存在" $path "Pass"
    }

    Write-Step "工具与版本"
    foreach ($key in @("Mysql", "Node", "Pnpm", "Python")) {
        $status = $EnvironmentReport[$key]
        if (-not $status.Available) {
            Write-Check "缺失" "$($status.Name)：$($status.Hint)" "Warn"
        }
        elseif (-not $status.Supported) {
            Write-Check "版本" "$($status.Name)：$($status.VersionText)；需要 $($status.Minimum)+" "Warn"
        }
        else {
            Write-Check "可用" "$($status.Name)：$($status.VersionText)（$($status.Path)）" "Pass"
        }
    }

    Write-Step "数据库导入范围"
    Write-Check "SQL" $script:SqlPaths[0] "Pass"
    Write-Check "SQL" $script:SqlPaths[1] "Pass"
    foreach ($tableName in @(Get-SqlTables)) {
        Write-Check "重建表" $tableName "Info"
    }
    Write-Check "说明" "DryRun 不连接数据库、不创建临时 SQL。" "Info"

    Write-Step "依赖状态"
    $frontendStatus = Get-FrontendDependencyStatus $Force
    $frontendAction = if ($frontendStatus.InstallRequired) { "需要安装" } else { "可跳过" }
    Write-Check "前端" "$frontendAction：$($frontendStatus.Reason)" $(if ($frontendStatus.InstallRequired) { "Warn" } else { "Pass" })

    $pythonCandidate = $null
    if (Test-Path -LiteralPath $script:BackendPython -PathType Leaf) {
        $pythonCandidate = $script:BackendPython
    }
    elseif ($EnvironmentReport["Python"].Available) {
        $pythonCandidate = $EnvironmentReport["Python"].Path
    }
    if ([string]::IsNullOrWhiteSpace($pythonCandidate)) {
        Write-Check "后端" "无法计算依赖指纹：未找到 Python。" "Warn"
    }
    else {
        $backendStatus = Get-BackendDependencyStatus $pythonCandidate $Force
        if (-not (Test-Path -LiteralPath $script:BackendPython -PathType Leaf)) {
            $backendStatus.InstallRequired = $true
            $backendStatus.Reason = "greenfianace_server\.venv 不存在"
        }
        $backendAction = if ($backendStatus.InstallRequired) { "需要安装" } else { "可跳过" }
        Write-Check "后端" "$backendAction：$($backendStatus.Reason)；Python $($backendStatus.PythonVersion)" $(if ($backendStatus.InstallRequired) { "Warn" } else { "Pass" })
    }

    Write-Step "端口与启动命令"
    foreach ($port in @($script:BackendPort, $script:FrontendPort)) {
        $inUse = Test-PortInUse $port
        Write-Check "端口 $port" $(if ($inUse) { "已占用" } else { "可用" }) $(if ($inUse) { "Warn" } else { "Pass" })
    }
    Write-Check "MySQL 默认" "$script:DatabaseHost / $script:DatabaseUser / $script:DatabaseName；完整部署只提示输入密码。" "Info"
    $localEnvPath = Join-Path $script:RootDir ".env"
    $localEnvStatus = if (Test-Path -LiteralPath $localEnvPath -PathType Leaf) { ".env 已存在，完整部署会保留它。" } else { ".env 不存在，完整部署会从 .env.example 生成。" }
    Write-Check "本地配置" $localEnvStatus "Info"
    Write-Check "统一配置" "前后端共同读取根目录 .env；完整部署不会覆盖已有文件。" "Info"
    Write-Check "私密配置" "数据库密码仅注入后端子进程；AI 配置读取根目录 .env，不写入仓库文件。" "Info"
    Write-Check "后端命令" "greenfianace_server\.venv\Scripts\python.exe -m uvicorn server:app --reload --host 0.0.0.0 --port $script:BackendPort" "Info"
    Write-Check "前端命令" "pnpm run dev（端口 $script:FrontendPort）" "Info"

    Write-Host ""
    Write-Host "DryRun 完成：未写文件、未安装依赖、未操作数据库、未启动服务。" -ForegroundColor Green
}

function Main {
    Write-Host "绿色金融与区域碳减排平台｜Windows 一键部署" -ForegroundColor Green
    Write-Host "项目目录：$script:RootDir"
    Write-Host "退出码：0=成功，1=失败，2=用户取消"

    $requiredFiles = @(Test-RequiredFiles)
    $environmentReport = Get-EnvironmentReport

    if ($DryRun) {
        Show-DryRun $requiredFiles $environmentReport ([bool]$ForceInstall)
        return $script:ExitSuccess
    }

    Write-Step "检查环境"
    Assert-EnvironmentReport $environmentReport
    foreach ($key in @("Mysql", "Node", "Pnpm", "Python")) {
        $status = $environmentReport[$key]
        Write-Check "可用" "$($status.Name)：$($status.VersionText)" "Pass"
    }

    Write-Step "准备本地环境配置"
    Ensure-LocalEnv

    Write-Step "读取固定 MySQL 配置"
    $databaseHost = $script:DatabaseHost
    $databaseUser = $script:DatabaseUser
    $databaseName = $script:DatabaseName
    Assert-SafeDatabaseHost $databaseHost
    Assert-SafeDatabaseUser $databaseUser
    Assert-SafeDatabaseName $databaseName
    Write-Check "数据库" "$databaseHost / $databaseUser / $databaseName" "Info"
    $databasePassword = Read-SecretText "MySQL 密码"

    Write-Step "检查目标数据库并导入完整 SQL"
    $databaseDeployed = Invoke-DatabaseDeployment `
        $environmentReport["Mysql"].Path `
        $databaseHost `
        $databaseUser `
        $databasePassword `
        $databaseName
    if (-not $databaseDeployed) {
        return $script:ExitCancelled
    }

    Write-Step "准备后端运行时配置"
    Write-Check "统一配置" "前后端共同读取根目录 .env；部署脚本不会覆盖已有配置" "Pass"
    Write-Check "私密配置" "仅将本次输入的数据库密码传给后端子进程，不写入文件；AI 配置按根目录 .env 读取" "Pass"

    Write-Step "智能安装前端依赖"
    Install-FrontendDependencies $environmentReport["Pnpm"].Path ([bool]$ForceInstall)

    Write-Step "智能安装后端依赖"
    Install-BackendDependencies $environmentReport["Python"].Path ([bool]$ForceInstall)

    Write-Step "检查服务端口"
    Assert-PortsAvailable
    Write-Check "可用" "后端端口 $script:BackendPort" "Pass"
    Write-Check "可用" "前端端口 $script:FrontendPort" "Pass"

    Write-Step "启动前后端服务"
    Start-Services `
        $environmentReport `
        $databaseHost `
        $databaseUser `
        $databasePassword `
        $databaseName

    Write-Host ""
    Write-Host "部署已启动。请保持新打开的两个 PowerShell 窗口运行。" -ForegroundColor Green
    Write-Host "后端：http://127.0.0.1:$script:BackendPort/api"
    Write-Host "前端：http://localhost:$script:FrontendPort/vue3-vite5-dashboard/"
    return $script:ExitSuccess
}

$exitCode = $script:ExitFailure
try {
    $exitCode = [int](Main)
}
catch {
    Write-Host ""
    Write-Host "部署失败：$($_.Exception.Message)" -ForegroundColor Red
    $exitCode = $script:ExitFailure
}
exit $exitCode
