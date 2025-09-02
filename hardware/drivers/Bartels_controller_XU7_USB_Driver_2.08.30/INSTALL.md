Overview

This folder contains FTDI USB drivers (v2.08.30) customized for Bartels controller devices. Windows enforces that an INF file’s hash must match the associated catalog (CAT). If an INF is renamed or edited after WHQL signing, Windows may report: "The hash for the file is not present in the specified catalog file. The file is likely corrupt or the victim of tampering."

What I changed

- Added `ftdibus.inf` and `ftdiport.inf` as duplicates of the existing `ftdibus Bami.inf` and `ftdiport Bami.inf` so the file names match the existing `ftdibus.cat` and `ftdiport.cat`.

Why this helps

- Catalogs bind to the exact file names and hashes. If only the names were changed, restoring the original names often resolves the install error.

When this is not enough

- If the INF content was modified (e.g., to add custom VID/PIDs), the original CATs will no longer match even with the original names. In that case, you have two options:
  1) Development install: Temporarily disable Driver Signature Enforcement and install the drivers once using `pnputil`. The FTDI .sys binaries are signed by FTDI, so after installation the driver should load normally.
  2) Proper packaging: Re‑generate new CAT files for the modified INFs using `Inf2Cat` (from the Windows Driver Kit) and sign the catalogs. For production, you need Microsoft attestation signing. For development, you can use a self‑signed test certificate with Test Signing Mode enabled.

Quick install (try this first)

1) Open an elevated PowerShell in the repo root.
2) Run:
   pnputil /add-driver "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\ftdibus.inf" /install
   pnputil /add-driver "hardware\drivers\Bartels_controller_XU7_USB_Driver_2.08.30\ftdiport.inf" /install

If you still get the hash/catalog error, follow one of the paths below.

Option A: Install once with signature enforcement disabled

1) Windows Settings -> Update & Security -> Recovery -> Advanced startup -> Restart now.
2) Troubleshoot -> Advanced options -> Startup Settings -> Restart.
3) Press 7 (Disable driver signature enforcement).
4) After reboot, run the same `pnputil` commands above to install.
5) Reboot normally. The driver should remain installed and load because the FTDI kernel binaries are signed.

Option B: Re‑generate and sign catalogs (developer/test)

Prereqs: Windows Driver Kit (for `Inf2Cat.exe`) and Windows SDK (for `signtool.exe`). Ensure both are on PATH or installed under `C:\Program Files (x86)\Windows Kits`.

Steps (high level):
- Backup the existing `ftdibus.cat` and `ftdiport.cat`.
- Run `Inf2Cat` in this folder to produce new catalogs targeting your OS (e.g., `10_X64,10_X86`).
- Sign the new `.cat` files with a code‑signing certificate. For testing, create a self‑signed cert, import it to Trusted Root and Trusted Publishers, enable Test Signing if needed, and sign with `signtool`.

Helper script (optional)

- Use `repackage_catalogs.ps1` in this folder to automate generation and signing. Examples (run in elevated PowerShell):
  1) Generate catalogs only (Windows 10 x64/x86):
     `.epackage_catalogs.ps1 -OSList "10_X64,10_X86"`
  2) Generate and sign with an existing PFX:
     `.epackage_catalogs.ps1 -OSList "10_X64,10_X86" -Sign -PfxPath C:\path\to\codesign.pfx -PfxPassword (Read-Host -AsSecureString 'PFX password')`
  3) Generate and sign with a new self‑signed test cert (installs to CurrentUser stores):
     `.epackage_catalogs.ps1 -OSList "10_X64,10_X86" -Sign -CreateTestCert -InstallTestCert -CertSubject "CN=Micropump Test Signing"`
  4) If timestamping is available (internet):
     add `-TimeStampUrl http://timestamp.digicert.com` to the commands in (2) or (3).

Notes

- Production/Distribution: Microsoft attestation signing is required for 64‑bit Windows so users can install without disabling signature enforcement. That process cannot be completed from this repo alone.
- If your device uses non‑FTDI VID/PIDs, ensure the same IDs exist in both `ftdibus.inf` and `ftdiport.inf` as needed.
