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

