param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($env:WINDOWS_SIGNING_PFX_BASE64)) {
    throw 'WINDOWS_SIGNING_PFX_BASE64 is not configured'
}
if ([string]::IsNullOrWhiteSpace($env:WINDOWS_SIGNING_PFX_PASSWORD)) {
    throw 'WINDOWS_SIGNING_PFX_PASSWORD is not configured'
}
if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw "Signing target does not exist: $Path"
}

$certPath = Join-Path $env:RUNNER_TEMP 'cybrex-signing.pfx'
try {
    $raw = [Convert]::FromBase64String($env:WINDOWS_SIGNING_PFX_BASE64)
    [IO.File]::WriteAllBytes($certPath, $raw)

    $signtool = Get-ChildItem `
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" `
        -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if ($null -eq $signtool) {
        throw 'signtool.exe was not found on the GitHub runner'
    }

    & $signtool.FullName sign `
        /fd SHA256 `
        /f $certPath `
        /p $env:WINDOWS_SIGNING_PFX_PASSWORD `
        /tr https://timestamp.digicert.com `
        /td SHA256 `
        $Path
    if ($LASTEXITCODE -ne 0) {
        throw "signtool failed with exit code $LASTEXITCODE"
    }

    $signature = Get-AuthenticodeSignature -FilePath $Path
    if ($signature.Status -ne 'Valid') {
        throw "Windows signature verification failed for $Path`: $($signature.Status)"
    }

    Write-Host "Verified Authenticode signature: $Path"
}
finally {
    Remove-Item -LiteralPath $certPath -Force -ErrorAction SilentlyContinue
    Remove-Variable raw -ErrorAction SilentlyContinue
}
