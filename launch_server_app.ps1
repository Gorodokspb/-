param(
    [ValidateSet("CRM", "SMETA")]
    [string]$App = "CRM",
    [string]$PythonExe = "python",
    [string]$SshUser = "crmadmin",
    [string]$ServerHost = "130.49.129.245",
    [int]$LocalPort = 15432,
    [string]$DbName = "dekorcrm",
    [string]$DbUser = "dekorcrm",
    [string]$DbPassword = ""
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-LocalPort {
    param([int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(700)
        if ($connected -and $client.Connected) {
            $client.EndConnect($async)
            $client.Close()
            return $true
        }
        $client.Close()
        return $false
    } catch {
        return $false
    }
}

function Wait-ForLocalPort {
    param(
        [int]$Port,
        [int]$TimeoutSeconds = 90
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-LocalPort -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

function Read-PlainPassword {
    param([string]$Prompt)
    $secure = Read-Host $Prompt -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    throw "Команда ssh не найдена. Установите OpenSSH Client в Windows."
}

if (-not (Test-LocalPort -Port $LocalPort)) {
    $sshCommand = "ssh -L ${LocalPort}:127.0.0.1:5432 ${SshUser}@${ServerHost} -N"
    Write-Host "Открываю окно SSH-туннеля. В новом окне введите пароль пользователя ${SshUser}." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $sshCommand | Out-Null
    Write-Host "Ожидаю, пока SSH-туннель поднимется на 127.0.0.1:${LocalPort}..." -ForegroundColor Yellow
    if (-not (Wait-ForLocalPort -Port $LocalPort -TimeoutSeconds 90)) {
        throw "SSH-туннель не поднялся на порту ${LocalPort}. Проверьте, что в окне SSH введен пароль и соединение осталось открытым."
    }
}

if (-not (Test-LocalPort -Port $LocalPort)) {
    throw "SSH-туннель не поднялся на порту ${LocalPort}. Проверьте окно туннеля и повторите запуск."
}

$dbPassword = $DbPassword
if ([string]::IsNullOrWhiteSpace($dbPassword)) {
    $dbPassword = $env:DEKORCRM_DB_PASSWORD
}
if ([string]::IsNullOrWhiteSpace($dbPassword)) {
    $dbPassword = Read-PlainPassword -Prompt "Введите пароль PostgreSQL для пользователя ${DbUser}"
}
$env:DEKORCRM_POSTGRES_DSN = "postgresql://${DbUser}:${dbPassword}@127.0.0.1:${LocalPort}/${DbName}"

$targetScript = if ($App -eq "SMETA") { "smeta.py" } else { "CRM.py" }
$targetPath = Join-Path $scriptDir $targetScript

Write-Host "Запускаю ${targetScript} с серверной PostgreSQL через SSH-туннель..." -ForegroundColor Green
& $PythonExe $targetPath
