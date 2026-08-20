# Dot-source this file from your PowerShell profile.
if ($global:DrpPowerShellHookLoaded) { return }
$global:DrpPowerShellHookLoaded = $true

$drpBase = $env:LOCALAPPDATA
if ([string]::IsNullOrWhiteSpace($drpBase)) {
    $drpBase = Join-Path $HOME 'AppData\Local'
}
$drpCacheDir = Join-Path $drpBase 'discord-rich-presence\cache'
$drpCommandDir = Join-Path $drpCacheDir 'commands'
New-Item -ItemType Directory -Force -Path $drpCommandDir | Out-Null
$drpCommandFile = Join-Path $drpCacheDir 'rp_last_cmd.txt'
$drpPidCommandFile = Join-Path $drpCommandDir ("{0}.txt" -f $PID)
$drpUtf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-DrpCommandCache([string]$Command) {
    if ([string]::IsNullOrWhiteSpace($Command)) { return }
    if ($Command -match 'rp_last_cmd|Write-DrpCommandCache|DrpPowerShellHookLoaded') { return }
    [System.IO.File]::WriteAllText($drpPidCommandFile, $Command + [Environment]::NewLine, $drpUtf8NoBom)
    # Compatibility with older service versions.
    [System.IO.File]::WriteAllText($drpCommandFile, $Command + [Environment]::NewLine, $drpUtf8NoBom)
}

if (Get-Module -ListAvailable -Name PSReadLine) {
    Import-Module PSReadLine -ErrorAction SilentlyContinue
    $drpPreviousHistoryHandler = (Get-PSReadLineOption).AddToHistoryHandler
    $drpHistoryHandler = {
        param([string]$Line)
        Write-DrpCommandCache $Line
        if ($null -ne $drpPreviousHistoryHandler) {
            return $drpPreviousHistoryHandler.Invoke($Line)
        }
        return $true
    }.GetNewClosure()
    Set-PSReadLineOption -AddToHistoryHandler $drpHistoryHandler
}
