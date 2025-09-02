param(
    [switch]$Force
)

<#
Installs the FTDI drivers in this folder using pnputil.
Run from an elevated PowerShell. If Windows reports a catalog/hash error,
boot with Driver Signature Enforcement disabled (dev) or repackage/sign the catalogs.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Require-Admin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Please run this script from an elevated PowerShell (Run as Administrator).'
    }
}

Require-Admin

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root
try {
    $infBus = Join-Path $root 'ftdibus.inf'
    $infPort = Join-Path $root 'ftdiport.inf'

    if (-not (Test-Path $infBus)) { throw "Missing file: $infBus" }
    if (-not (Test-Path $infPort)) { throw "Missing file: $infPort" }

    Write-Host 'Installing FTDI Bus/D2XX driver (ftdibus.inf)...' -ForegroundColor Cyan
    pnputil /add-driver "$infBus" /install | Write-Output

    Write-Host 'Installing FTDI VCP driver (ftdiport.inf)...' -ForegroundColor Cyan
    pnputil /add-driver "$infPort" /install | Write-Output

    Write-Host 'Done. If you saw a catalog/hash error, see INSTALL.md for options.' -ForegroundColor Green
}
finally {
    Pop-Location
}

