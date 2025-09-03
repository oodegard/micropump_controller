param(
    [Parameter(Mandatory=$false, HelpMessage='Path to a .cer file (public cert) used to sign the catalogs')]
    [string]$CertPath,

    [Parameter(Mandatory=$false, HelpMessage='Certificate store location: LocalMachine or CurrentUser')]
    [ValidateSet('LocalMachine','CurrentUser')]
    [string]$StoreLocation = 'LocalMachine',

    [Parameter(Mandatory=$false, HelpMessage='Drivers only; skip certificate installation')]
    [Alias('DriversOnly')]
    [switch]$InstallOnly,

    [Parameter(Mandatory=$false, HelpMessage='Certificate only; skip driver installation')]
    [switch]$CertOnly,

    [Parameter(Mandatory=$false, HelpMessage='Driver folder containing ftdibus.inf and ftdiport.inf')]
    [string]$DriverDir
)

<#
Installs the signing certificate (public .cer) into Trusted Root and Trusted Publishers,
then installs the FTDI drivers via pnputil.

Usage examples (run from elevated PowerShell):

1) Install cert (LocalMachine) and drivers:
   .\install_cert_and_drivers.ps1 -CertPath C:\path\to\YourSigningCert.cer

2) Current user stores only (if LocalMachine is restricted):
   .\install_cert_and_drivers.ps1 -CertPath C:\path\to\YourSigningCert.cer -StoreLocation CurrentUser

3) Skip cert (if trust already deployed) and just install drivers:
   .\install_cert_and_drivers.ps1 -InstallOnly

Notes:
 - Requires Administrator to install into LocalMachine stores and to run pnputil.
 - Provide the public certificate (.cer) that corresponds to the cert used to sign the .cat files.
 - This script does NOT install any private keys; only trust for the publisher is added.
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

if (-not $DriverDir) {
    $DriverDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

if (-not (Test-Path $DriverDir)) { throw "Driver directory not found: $DriverDir" }

$infBus  = Join-Path $DriverDir 'ftdibus.inf'
$infPort = Join-Path $DriverDir 'ftdiport.inf'
if (-not (Test-Path $infBus))  { throw "Missing file: $infBus" }
if (-not (Test-Path $infPort)) { throw "Missing file: $infPort" }

function Install-CertToStores {
    param(
        [Parameter(Mandatory=$true)] [string]$Path,
        [Parameter(Mandatory=$true)] [ValidateSet('LocalMachine','CurrentUser')] [string]$Location
    )

    if (-not (Test-Path $Path)) {
        throw "Certificate file not found: $Path"
    }

    Write-Host "Importing certificate from: $Path" -ForegroundColor Cyan
    $stores = @('Root','TrustedPublisher')

    foreach ($storeName in $stores) {
        $storePath = "Cert:\$Location\$storeName"
        Write-Host " -> Import to $storePath" -ForegroundColor DarkCyan
        $null = Import-Certificate -FilePath $Path -CertStoreLocation $storePath -ErrorAction Stop
    }
}

try {
    if (-not $InstallOnly) {
        if (-not $CertPath) {
            throw 'Please provide -CertPath to a .cer file, use -InstallOnly for drivers only, or use -CertOnly for certificate only.'
        }
        Install-CertToStores -Path $CertPath -Location $StoreLocation
        Write-Host 'Certificate import completed.' -ForegroundColor Green
    } else {
        Write-Host 'Skipping certificate installation as requested (-InstallOnly).' -ForegroundColor Yellow
    }

    if ($CertOnly) {
        Write-Host 'CertOnly specified; skipping driver installation.' -ForegroundColor Yellow
        return
    }

    Write-Host 'Installing FTDI Bus/D2XX driver (ftdibus.inf)...' -ForegroundColor Cyan
    pnputil /add-driver "$infBus" /install | Write-Output

    Write-Host 'Installing FTDI VCP driver (ftdiport.inf)...' -ForegroundColor Cyan
    pnputil /add-driver "$infPort" /install | Write-Output

    Write-Host 'Done.' -ForegroundColor Green
    Write-Host 'If Windows reports a catalog/hash or trust error, ensure the .cer matches the signer of the .cat files and was imported into the correct stores.' -ForegroundColor Yellow
}
catch {
    Write-Error $_
    exit 1
}
