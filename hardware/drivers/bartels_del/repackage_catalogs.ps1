param(
    [string]$DriverDir = (Split-Path -Parent $MyInvocation.MyCommand.Path),
    [string]$OSList = "10_X64,10_X86",
    [switch]$VerboseInf2Cat,
    [switch]$Sign,
    [string]$PfxPath,
    [SecureString]$PfxPassword,
    [switch]$CreateTestCert,
    [switch]$InstallTestCert,
    [string]$CertSubject = "CN=Micropump Test Signing",
    [string]$TimeStampUrl
)

<#
Re-generates catalog (.cat) files for the INFs in this folder using Inf2Cat,
then optionally signs them with Signtool.

Requirements:
- Windows Driver Kit (WDK) for Inf2Cat.exe
- Windows SDK for signtool.exe (if -Sign)
Run from an elevated PowerShell if installing certificates to trusted stores.

Examples:
  .\repackage_catalogs.ps1 -OSList "10_X64,10_X86"
  .\repackage_catalogs.ps1 -OSList "10_X64,10_X86" -Sign -PfxPath C:\certs\codesign.pfx -PfxPassword (Read-Host -AsSecureString 'PFX password')
  .\repackage_catalogs.ps1 -OSList "10_X64,10_X86" -Sign -CreateTestCert -InstallTestCert -CertSubject "CN=Micropump Test Signing"
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Find-ExistingCodeSigningCert {
    param([string]$Subject)
    $stores = @('Cert:\\CurrentUser\\My','Cert:\\LocalMachine\\My')
    foreach ($store in $stores) {
        try {
            $match = Get-ChildItem $store | Where-Object { $_.HasPrivateKey -and $_.Subject -eq $Subject }
            if ($match) { return ($match | Sort-Object NotBefore -Descending | Select-Object -First 1) }
        } catch { }
    }
    return $null
}

function Find-Inf2Cat {
    $paths = @(
        Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin\*\x64\Inf2Cat.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin\*\x86\Inf2Cat.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\8.1\bin\x64\Inf2Cat.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\8.1\bin\x86\Inf2Cat.exe')
    $candidates = @()
    foreach ($p in $paths) { $candidates += Get-ChildItem $p -ErrorAction SilentlyContinue }
    $candidates | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
}

function Find-SignTool {
    $paths = @(
        Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin\*\x64\signtool.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin\*\x86\signtool.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\8.1\bin\x64\signtool.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\8.1\bin\x86\signtool.exe')
    $candidates = @()
    foreach ($p in $paths) { $candidates += Get-ChildItem $p -ErrorAction SilentlyContinue }
    $candidates | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
}

function Backup-ExistingCats {
    param([string]$Dir)
    $cats = Get-ChildItem -Path $Dir -Filter '*.cat' -ErrorAction SilentlyContinue
    if (-not $cats) { return }
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    foreach ($c in $cats) {
        $backup = Join-Path $Dir ("{0}.{1}.bak" -f $c.Name, $stamp)
        Write-Host "Backing up $($c.Name) -> $([IO.Path]::GetFileName($backup))" -ForegroundColor Yellow
        Copy-Item -LiteralPath $c.FullName -Destination $backup -Force
    }
}

function Run-Inf2Cat {
    param([string]$Inf2CatPath,[string]$Dir,[string]$OS,[switch]$Verbose)
    # Build arguments explicitly to avoid quoting issues
    $args = @("/driver:$Dir", "/os:$OS")
    if ($Verbose) { $args += '/verbose' }
    Write-Host "Running Inf2Cat: `"$Inf2CatPath`" $($args -join ' ')" -ForegroundColor Cyan
    & $Inf2CatPath @args
    $exit = $LASTEXITCODE
    if ($exit -ne 0) { throw "Inf2Cat failed with exit code $exit" }
}

function New-TestCodeSigningCertIfNeeded {
    param([string]$Subject,[switch]$Install)
    $existing = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $Subject -and $_.HasPrivateKey }
    if ($existing) { return $existing | Select-Object -First 1 }
    Write-Host "Creating self-signed test code signing certificate: $Subject" -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $Subject -KeyAlgorithm RSA -KeyLength 2048 -HashAlgorithm SHA256 -CertStoreLocation Cert:\CurrentUser\My
    if ($Install) {
        Write-Host 'Installing test cert to Trusted Root and Trusted Publishers (CurrentUser)…' -ForegroundColor Yellow
        $tmpCer = Join-Path $env:TEMP ("{0}.cer" -f ([Guid]::NewGuid()))
        try {
            Export-Certificate -Cert $cert -FilePath $tmpCer -Force | Out-Null
            Import-Certificate -FilePath $tmpCer -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
            Import-Certificate -FilePath $tmpCer -CertStoreLocation Cert:\CurrentUser\TrustedPublisher | Out-Null
        } finally {
            Remove-Item -LiteralPath $tmpCer -ErrorAction SilentlyContinue
        }
    }
    return $cert
}

function Export-PfxIfRequested {
    param($Cert,[string]$OutPath,[SecureString]$Password)
    if (-not $OutPath) { return $null }
    Write-Host "Exporting PFX to: $OutPath" -ForegroundColor Yellow
    Export-PfxCertificate -Cert $Cert -FilePath $OutPath -Password $Password -Force | Out-Null
    return $OutPath
}

function Sign-Catalogs {
    param([string]$SignToolPath,[string]$Dir,[string]$Pfx,[SecureString]$Password,[string]$Subject,[string]$TsUrl,[string]$Thumbprint)
    $cats = Get-ChildItem -Path $Dir -Filter '*.cat'
    if (-not $cats) { throw 'No .cat files found to sign.' }
    foreach ($cat in $cats) {
        $args = @('sign','/fd','SHA256')
        if ($Pfx) {
            $tmp = New-TemporaryFile
            try {
                if ($Password) {
                    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
                    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
                }
                $args += @('/f', $Pfx)
                if ($plain) { $args += @('/p', $plain) }
            } finally {
                if ($bstr) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
                Remove-Item $tmp -ErrorAction SilentlyContinue
            }
        } elseif ($Thumbprint) {
            # Use precise thumbprint selection from CurrentUser\My
            $args += @('/sha1', $Thumbprint)
        } elseif ($Subject) {
            # Fallback to subject name matching
            $args += @('/n', $Subject)
        } else {
            # Try best available certificate automatically
            $args += '/a'
        }
        if ($TsUrl) { $args += @('/tr', $TsUrl, '/td', 'SHA256') }
        $args += '"{0}"' -f $cat.FullName
        Write-Host "Signing: $($cat.Name)" -ForegroundColor Cyan
        & $SignToolPath @args
    }
}

Push-Location $DriverDir
try {
    Write-Host "Driver directory: $DriverDir" -ForegroundColor Green
    $inf2cat = Find-Inf2Cat
    if (-not $inf2cat) { throw 'Inf2Cat.exe not found. Install the Windows Driver Kit (WDK).' }

    Backup-ExistingCats -Dir $DriverDir
    Run-Inf2Cat -Inf2CatPath $inf2cat -Dir $DriverDir -OS $OSList -Verbose:$VerboseInf2Cat

    if ($Sign) {
        $signtool = Find-SignTool
        if (-not $signtool) { throw 'signtool.exe not found. Install the Windows SDK.' }

        # Prefer an existing cert by subject; create one if requested
        $certToUse = Find-ExistingCodeSigningCert -Subject $CertSubject
        if (-not $certToUse -and $CreateTestCert) {
            $certToUse = New-TestCodeSigningCertIfNeeded -Subject $CertSubject -Install:$InstallTestCert
            # Refresh from store to ensure we have the persisted instance with Thumbprint populated
            $certToUse = Find-ExistingCodeSigningCert -Subject $CertSubject
        }

        if ($certToUse -and -not $PfxPath) {
            Write-Host "Signing with certificate in CurrentUser store: $($certToUse.Subject)" -ForegroundColor Yellow
            Write-Host ("Using thumbprint: {0}" -f $certToUse.Thumbprint)
            Sign-Catalogs -SignToolPath $signtool -Dir $DriverDir -Thumbprint $($certToUse.Thumbprint) -TsUrl $TimeStampUrl
        } else {
            if (-not $PfxPath -and $certToUse) {
                # Export to temp PFX if no path provided
                $PfxPath = Join-Path $env:TEMP ('MicropumpTestCert_{0}.pfx' -f ([Guid]::NewGuid()))
                if (-not $PfxPassword) { $PfxPassword = Read-Host -AsSecureString 'Create a password for the test PFX' }
                Export-PfxIfRequested -Cert $certToUse -OutPath $PfxPath -Password $PfxPassword | Out-Null
            }
            if (-not $PfxPath) { throw "No code signing cert found for subject '$CertSubject'. Use -CreateTestCert or provide -PfxPath/-PfxPassword." }
            if (-not $PfxPassword) { $PfxPassword = Read-Host -AsSecureString 'Enter PFX password' }
            Sign-Catalogs -SignToolPath $signtool -Dir $DriverDir -Pfx $PfxPath -Password $PfxPassword -TsUrl $TimeStampUrl
        }
        Write-Host 'Catalog signing complete.' -ForegroundColor Green
    } else {
        Write-Host 'Catalogs generated (unsigned). Use -Sign to sign them.' -ForegroundColor Yellow
    }
}
finally {
    Pop-Location
}
