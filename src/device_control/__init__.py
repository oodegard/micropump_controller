"""
Device Control Package
----------------------

A modular Python interface for controlling hardware devices (valves, pumps, etc.)
via Arduino and serial communication.
"""

from .valve import ValveController
from .pump import PumpController  # (placeholder for future implementation)

__all__ = ["ValveController", "PumpController"]

__version__ = "0.1.0"
__author__ = "Øyvind Ødegård Fougner"
__license__ = "MIT"
