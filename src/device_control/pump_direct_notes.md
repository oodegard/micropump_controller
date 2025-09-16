Direct Serial Control Notes (Bartels mp-Labtronix Control Unit)
==============================================================

Observed / Inferred Protocol
----------------------------
From existing implementation the control unit accepts simple ASCII commands terminated by `\r`:

* `F<freq>` : Set frequency (Hz) e.g. `F100`.
* `A<ampl>` : Set amplitude / voltage (datasheet units) e.g. `A120`.
* `<waveform>` : e.g. `RECT` (other possibilities could include `SINE`, `TRAPEZ`, depending on firmware).
* `bon` : Pump ON.
* `boff` : Pump OFF.

There is no checksum or length prefix in the minimal code. Device apparently tolerates short inter-command delays (~150 ms used). If the unit actually echoes or returns status lines you can enable reading after writes.

Driver Layer
------------
The board enumerates as an FTDI interface (VID:PID 0403:B4C0). Two approaches exist:

1. Windows FTDI VCP (Virtual COM Port) driver (default) → usable directly by `pyserial`.
2. FTDI D2XX proprietary DLL (ftd2xx.*) → exposes a separate API; not needed unless you require lower latency, bit-bang, or custom USB descriptors.

Because current Python code only needs basic TX of small ASCII frames at modest baud, the plain COM port is sufficient. So “no driver” in practice means: rely on Microsoft in-box FTDI driver or the signed FTDI VCP; do NOT install / link against vendor *D2XX* DLL.

Baud Rate
---------
Existing code for the pump did not explicitly set baud; `pyserial.Serial(port=..., timeout=3)` defaults to **9600** baud. Arduino / valve code uses 115200. If commands at 9600 yield no effect, retry 115200. Auto-baud probing can attempt a few common rates (9600, 115200, 57600).

Port Discovery
--------------
Use `serial.tools.list_ports.comports()` and match either:
* VID/PID: `0x0403:0xB4C0`
* Description substring: `"Micropump"`, `"Bartels"`, or `"FTDI"`.

Potential Pitfalls
------------------
* Wrong baud rate → device ignores commands. Fix: try 9600 vs 115200.
* Missing `\r` terminator → command not parsed. Always append carriage return, not `\n`.
* Buffering: sending commands too fast may drop or merge them. Add ~100–200 ms delay or wait for optional echo.
* Power state: Some units ignore parameter changes while running; stop (`boff`) before reconfiguring frequency/voltage if you observe issues.
* Windows exclusive access: Only one process can open the COM port. Close any vendor GUI first.
* Driver confusion: If D2XX driver is installed and grabs the interface, VCP may not appear. Uninstall D2XX or force VCP mode via FTDI utilities if needed.
* Permission (Linux/macOS): Add user to `dialout` / `uucp` groups or use `udev` rules. (Windows typically fine.)
* EMI / Cable quality: Spurious characters can appear; consider validating allowed character set before sending.

Enhancements / Next Steps
-------------------------
* Implement a small abstraction class with context manager and automatic waveform/parameter validation.
* Add optional response parsing if newer firmware provides `OK` or numeric echoes.
* Provide a CLI (`python -m device_control.pumpctl --port COM4 on/off/set ...`).
* Integrate watchdog: periodic `bon` refresh or status poll to ensure pump active.
* Add unit tests with a loopback or mock serial port (e.g. `pyserial-asyncio` or custom in-memory transport).
* Provide dependency-light packaging (pip install) including an entry point script.
* Investigate potential binary protocol for advanced features (if documented) like ramps or stored profiles.

Minimal Usage Recap
-------------------
```
pip install pyserial
python -m device_control.pump_direct_example --port COM4 --freq 100 --voltage 120 --waveform RECT --run-seconds 5
```

If nothing happens, press reset on the control unit, verify LEDs, re-run with `--auto-baud`.

Troubleshooting Quick Checklist
-------------------------------
1. Confirm COM port: run the `resolve_ports.py` helper or `python -m serial.tools.list_ports -v`.
2. Try alternate baud rates.
3. Ensure only one application has the port open.
4. Add `--auto-baud` and increase delays (`COMMAND_DELAY = 0.3`).
5. Use a serial sniffer (e.g. `RealTerm`) to manually type `bon<CR>`.
6. Reinstall / revert to FTDI VCP driver if only D2XX present.

Document version: 2025-09-16.
