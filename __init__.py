"""
Device Control Package
----------------------

A modular Python interface for controlling hardware devices (valves, pumps, etc.)
via Arduino and serial communication.
"""

# Adjusted imports to reflect the new structure
from src.controllers.valve_control import ValveController
from src.controllers.pump_control import BartelsPump
from src.controllers.pipetting_control import Robot

# Public API symbols
__all__ = ["ValveController", "BartelsPump", "Robot"]

__version__ = "0.1.0"
__author__ = "Øyvind Ødegård Fougner"
__license__ = "MIT"
