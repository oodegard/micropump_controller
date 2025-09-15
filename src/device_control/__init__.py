"""
Device Control Package
----------------------

A modular Python interface for controlling hardware devices (valves, pumps, etc.)
via Arduino and serial communication.
"""

from .valve import ValveController
from .pump import BartelsPumpController

# Public API symbols
__all__ = ["ValveController", "BartelsPumpController"]

__version__ = "0.1.0"
__author__ = "Øyvind Ødegård Fougner"
__license__ = "MIT"
