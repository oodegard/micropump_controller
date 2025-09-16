Param(
    [string]$Vid = "0xFFFF",
    [string]$Pid = "0x5678"
)

function Ensure-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "Elevation required. Relaunching with administrative privileges..."
        $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Vid $Vid -Pid $Pid"
        Start-Process powershell -ArgumentList $arguments -Verb RunAs | Out-Null
        exit
    }
}

Ensure-Admin

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$zadigPath = Join-Path $projectRoot "external_software\libusb\win\zadig-2.9.exe"

if (-not (Test-Path $zadigPath)) {
    throw "Zadig executable not found at $zadigPath"
}

Write-Host "# WinUSB Driver Installation" -ForegroundColor Cyan
Write-Host "Device VID: $Vid" -ForegroundColor Yellow
Write-Host "Device PID: $Pid" -ForegroundColor Yellow
Write-Host "" 
Write-Host "Zadig will launch. Use the following steps:" -ForegroundColor Cyan
Write-Host " 1. In Zadig, open the 'Options' menu and select 'List All Devices'."
Write-Host " 2. Choose the device that matches the VID/PID shown above." 
Write-Host " 3. Ensure 'WinUSB' is selected as the driver." 
Write-Host " 4. Click 'Install Driver' (or 'Replace Driver')." 
Write-Host " 5. Wait for the installation to finish, then close Zadig." 
Write-Host "" 
Write-Host "Press Enter to launch Zadig..."
[void][System.Console]::ReadLine()

Start-Process -FilePath $zadigPath -WorkingDirectory (Split-Path $zadigPath) -Verb RunAs

Write-Host "Waiting for Zadig to close..."
Wait-Process -Name "zadig-2.9" -ErrorAction SilentlyContinue

Write-Host "Zadig closed. Verify the device lists WinUSB in Device Manager." -ForegroundColor Green
