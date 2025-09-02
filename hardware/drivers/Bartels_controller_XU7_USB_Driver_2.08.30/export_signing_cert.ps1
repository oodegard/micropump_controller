param(
    [Parameter(Mandatory=$false, HelpMessage='Certificate subject to search for (e.g., CN=Micropump Test Signing)')]
    [string]$Subject = 'CN=Micropump Test Signing',

    [Parameter(Mandatory=$false, HelpMessage='Output .cer file path')]
    [string]$OutFile
)

<#
Exports the public certificate (.cer) for the code-signing certificate you used to sign the .cat files.

Usage examples:
  .\export_signing_cert.ps1                     # looks for default subject, writes MicropumpTestSigning.cer next to this script
  .\export_signing_cert.ps1 -Subject 'CN=Your Org Code Signing' -OutFile C:\temp\YourOrg.cer

Notes:
 - Searches both CurrentUser and LocalMachine personal stores (Cert:\<Location>\My) and picks the newest matching cert.
 - Exports public key only (.cer). No private keys are exported.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-DefaultOutFile([string]$subject) {
    $name = ($subject -replace '^CN=','') -replace '[^A-Za-z0-9._-]',''
    if (-not $name) { $name = 'SigningCert' }
    # Prefer $PSScriptRoot when available; fall back to $PSCommandPath or MyInvocation
    $folder = $null
    if ($PSScriptRoot) {
        $folder = $PSScriptRoot
    } elseif ($PSCommandPath) {
        $folder = Split-Path -Parent $PSCommandPath
    } elseif ($MyInvocation -and $MyInvocation.MyCommand -and ($MyInvocation.MyCommand | Get-Member -Name Path -ErrorAction SilentlyContinue)) {
        $folder = Split-Path -Parent $MyInvocation.MyCommand.Path
    } else {
        $folder = Get-Location | Select-Object -ExpandProperty Path
    }
    return Join-Path $folder ("{0}.cer" -f $name)
}

if (-not $OutFile) { $OutFile = Get-DefaultOutFile -subject $Subject }

Write-Host "Searching for certificate with subject: $Subject" -ForegroundColor Cyan

$candidates = @()
foreach ($loc in @('CurrentUser','LocalMachine')) {
    $storePath = "Cert:\$loc\My"
    try {
        $items = Get-ChildItem $storePath -ErrorAction Stop |
            Where-Object { $_.Subject -eq $Subject -or $_.Subject -like "*$Subject*" }
        foreach ($itm in $items) {
            # Preserve certificate object type; annotate with store location
            try { $itm | Add-Member -NotePropertyName StoreLocation -NotePropertyValue $loc -Force -ErrorAction SilentlyContinue } catch {}
            $candidates += $itm
        }
    } catch {
        # Ignore inaccessible stores
    }
}

if (-not $candidates -or $candidates.Count -eq 0) {
    throw "No certificate found matching subject '$Subject' in CurrentUser or LocalMachine personal stores."
}

$cert = $candidates | Sort-Object NotBefore -Descending | Select-Object -First 1
Write-Host ("Found certificate: Subject='{0}', Thumbprint={1}, Store={2}" -f $cert.Subject, $cert.Thumbprint, ($cert.PSObject.Properties.Match('StoreLocation').Value)) -ForegroundColor Green

$outDir = Split-Path -Parent $OutFile
if ($outDir -and -not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir | Out-Null
}

Write-Host "Exporting to: $OutFile" -ForegroundColor Cyan
Export-Certificate -Cert $cert -FilePath $OutFile -ErrorAction Stop | Out-Null

Write-Host 'Done. Copy this .cer to each target PC and run install_cert_and_drivers.ps1 with -CertPath.' -ForegroundColor Green
