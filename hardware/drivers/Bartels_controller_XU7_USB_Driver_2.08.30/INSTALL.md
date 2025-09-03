Overview

This folder contains FTDI USB drivers (v2.08.30) customized for Bartels controller devices. Windows requires that each INF matches its catalog (CAT); if the INF is edited, you must regenerate and re‑sign the CAT.

Single Installer (recommended)

Use the unified installer to import the public signing certificate and install both drivers.

Examples (run from an elevated PowerShell in the repo root):
- Install cert to LocalMachine stores and install drivers:
  powershell -NoProfile -ExecutionPolicy Bypass -File "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\install_cert_and_drivers.ps1" -CertPath "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\MicropumpTestSigning.cer" -StoreLocation LocalMachine
- If LocalMachine is restricted, install cert to CurrentUser stores:
  powershell -NoProfile -ExecutionPolicy Bypass -File "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\install_cert_and_drivers.ps1" -CertPath "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\MicropumpTestSigning.cer" -StoreLocation CurrentUser
- Drivers only (skip cert install):
  powershell -NoProfile -ExecutionPolicy Bypass -File "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\install_cert_and_drivers.ps1" -InstallOnly
- Cert only (skip driver install):
  powershell -NoProfile -ExecutionPolicy Bypass -File "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\install_cert_and_drivers.ps1" -CertOnly -CertPath "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\MicropumpTestSigning.cer"

Calling from a main installer

You can call this script from another PowerShell script or setup tool. The script returns a non‑zero exit code on failures. You can optionally pass `-DriverDir` if calling from a different working directory.

Developer Packaging (regen + sign CATs)

Prereqs on a dev machine: Windows Driver Kit (Inf2Cat.exe) and Windows SDK (signtool.exe).

Run in elevated PowerShell:
- Generate and sign with a self‑signed test cert:
  powershell -NoProfile -ExecutionPolicy Bypass -File "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\repackage_catalogs.ps1" -OSList 10_X64 -Sign -CreateTestCert -InstallTestCert -CertSubject "CN=Micropump Test Signing"
- Existing PFX:
  powershell -NoProfile -ExecutionPolicy Bypass -File "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\repackage_catalogs.ps1" -OSList 10_X64 -Sign -PfxPath C:\certs\codesign.pfx -PfxPassword (Read-Host -AsSecureString 'PFX password')
- Optional timestamp:
  add -TimeStampUrl http://timestamp.digicert.com

Troubleshooting

- Hash/catalog error: Ensure the `.cat` was regenerated after any INF edits and is signed by a cert trusted on the target machine.
- Trust issues: Import the matching `.cer` to Trusted Root and Trusted Publishers (use the installer script).
- Test mode (dev only): `bcdedit /set testsigning on` to enable; `off` to disable (reboot required).

Notes

- Production/distribution: Use an organization code‑signing cert or Microsoft attestation signing for catalogs.
- Keep INF + signed CAT + required FTDI binaries together when deploying to target PCs.
