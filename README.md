# micropump_controller
A program to control microfluidics pumps


TODO

valve-control-project/
│
├── README.md                   # TODO list -> manual in future
├── LICENSE                      # MIT
├── .gitignore                   
│
├── docs/                        # Documentation & diagrams
│   ├── wiring-diagram.png
│   ├── system-architecture.md
│   └── ...
│
├── hardware/                    # Hardware-related files
│   ├── arduino/                 
│   │   ├── valve_serial/        # Arduino sketch for valve
│   │   │   └── valve_serial.ino
│   │   └── pump_serial/         # (Future) sketch for pump
│   │       └── pump_serial.ino
│   └── datasheets/              # Valve, relay, PSU PDFs
│
├── src/                         # Python source code (installable package)
│   └── device_control/
│       ├── __init__.py          # Exposes ValveController, PumpController
│       ├── base.py              # Abstract DeviceController class
│       ├── valve.py             # ValveController implementation
│       ├── pump.py              # PumpController (future)
│       ├── serial_manager.py    # Shared serial communication helper
│       └── cli.py               # Command-line interface entrypoint
│
├── tests/                       # Automated tests (pytest or unittest)
│   ├── test_valve.py
│   └── test_pump.py (future)
│
├── examples/                    # Usage/demo scripts
│   ├── valve_cycle.py           # Run valve 10x (2s on, 1s off)
│   └── pump_demo.py (future)
│
├── requirements.txt             # Python dependencies (pyserial, etc.)
├── pyproject.toml                # (Optional) modern packaging config
├── setup.py                      # (Optional) legacy packaging
└── Makefile / tasks.py           # (Optional) dev shortcuts (e.g., make test)

## CLI Usage (Experimental)

Run a YAML-defined sequence (see `config_examples/continuous_switching.yaml`):

```
python -m device_control.cli config_examples/continuous_switching.yaml
```

Or call the script directly:

```
python src/device_control/cli.py config_examples/continuous_switching.yaml
```

YAML schema supported (pump profile order applied: stop -> waveform -> voltage (Vpp) -> frequency -> start):

```
pump settings:
	normal speed:
		waveform: RECT
		voltage: 100
		freq: 50
required hardware:
	pump: true
	valve: true
run:
	- pump_on: normal speed
	- duration: 30
		commands:
			- action: valve_on
				duration: 5
			- action: valve_off
				duration: 5
	- pump_off: 0
```

Timed command blocks:
The `duration` + `commands` block repeats the listed commands sequentially until the block duration elapses.

Additional flags:

```
--dry-run            Simulate without opening serial ports (mock devices)
-v / --verbose       (Reserved for future detailed logging)
```

Ctrl+C (KeyboardInterrupt) handling:
- Pump is stopped cleanly
- Valve forced OFF
- Devices closed

Environment variables (optional, via `.env` in repo root):
```
PUMP_PORT=COM4
VALVE_SERIAL_PORT=COM5
VALVE_BAUDRATE=115200
```

If not set, the defaults above are used.

Limitations / TODO:
- Structured logging (replace prints)
- Pipetting robot & microscope integration
- Scheduling / concurrency improvements
- Unit tests for CLI parsing & dry-run

