# Create a package with the executable and all necessary DLLs for Windows 7

$distFolder = "dist\win7_package"
$exeSource = "dist\remote_desktop_server.exe"

# Create package folder
New-Item -ItemType Directory -Force -Path $distFolder | Out-Null

# Copy executable
Copy-Item $exeSource $distFolder\

# Copy Visual C++ runtime DLLs
$vcRedist = @(
    "C:\Windows\System32\vcruntime140.dll",
    "C:\Windows\System32\vcruntime140_1.dll",
    "C:\Windows\System32\msvcp140.dll"
)

foreach ($dll in $vcRedist) {
    if (Test-Path $dll) {
        Copy-Item $dll $distFolder\ -ErrorAction SilentlyContinue
        Write-Host "✓ Copied $(Split-Path $dll -Leaf)" -ForegroundColor Green
    }
}

Write-Host "`n✓ Package created: $distFolder" -ForegroundColor Green
Write-Host "`nCopy the entire 'win7_package' folder to Windows 7" -ForegroundColor Yellow
Write-Host "Then run: remote_desktop_server.exe" -ForegroundColor Cyan
