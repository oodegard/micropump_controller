"""
Valve Control Package
---------------------

A simple Python interface to control a 24VDC valve via Arduino + relay.
"""

from .controller import ValveController

__all__ = ["ValveController"]

__version__ = "0.1.0"
__author__ = "Øyvind Ødegård Fougner"
__license__ = "MIT"
