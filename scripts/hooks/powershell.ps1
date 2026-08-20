# Dot-source this file from your PowerShell profile.
$drpCacheDir = Join-Path ($env:LOCALAPPDATA ?? (Join-Path $HOME 'AppData\Local')) 'discord-rich-presence\cache'
New-Item -ItemType Directory -Force -Path $drpCacheDir | Out-Null
$drpCommandFile = Join-Path $drpCacheDir 'rp_last_cmd.txt'

function Write-DrpCommandCache([string]$Command) {
    if ([string]::IsNullOrWhiteSpace($Command)) { return }
    if ($Command -match 'rp_last_cmd|Write-DrpCommandCache|__drp_') { return }
    Set-Content -LiteralPath $drpCommandFile -Value $Command -Encoding UTF8
}

if (Get-Module -ListAvailable -Name PSReadLine) {
    Import-Module PSReadLine -ErrorAction SilentlyContinue
    Set-PSReadLineOption -AddToHistoryHandler {
        param([string]$Line)
        Write-DrpCommandCache $Line
        return $true
    }
}
