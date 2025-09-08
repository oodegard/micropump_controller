# src/device_control/pump.py
"""
PumpController (Bartels Implementation)
---------------------------------------

Implementation of the BartelsPumpController class for controlling the Bartels pump.

Originally written by:
Kai Sandvold Beckwith
Ellenberg group
EMBL Heidelberg for Tracebot control

Modified by:
Øyvind Ødegård Fougner
Schink group
UIO

"""

import time
import serial
import logging


class BartelsPumpController:
    def __init__(self, config):
        self.config = config
        try:
            self.pump = self.initialize_pump()
            time.sleep(0.2)
            self.bartels_set_freq(self.config["bartels_freq"])
            time.sleep(0.5)
            self.bartels_set_voltage(self.config["bartels_voltage"])
        except serial.SerialException:
            logging.error("No pump found on " + self.config["pump_port"])

    def initialize_pump(self):
        """Initialize pump communication."""
        try:
            pump = serial.Serial(port=self.config['pump_port'], timeout=3)  # open serial port
            logging.info(f'Pump connection established on {pump.name}')
            return pump
        except serial.SerialException:
            logging.error('No pump found on ' + self.config['pump_port'])
            return None

    def close(self):
        if self.pump is None:
            logging.error("Pump is not initialized.")
            return
        logging.info("Disconnecting pump.")
        self.pump.close()

    def bartels_set_freq(self, freq):
        if self.pump is None:
            logging.error("Pump is not initialized.")
            return
        self.pump.write(("F" + str(freq) + "\r").encode("utf-8"))
        logging.info("Set frequency " + str(freq))

    def bartels_set_voltage(self, voltage):
        if self.pump is None:
            logging.error("Pump is not initialized.")
            return
        self.pump.write(("A" + str(voltage) + "\r").encode("utf-8"))
        logging.info("Set voltage " + str(voltage))

    def bartels_set_waveform(self, waveform):
        if self.pump is None:
            logging.error("Pump is not initialized.")
            return
        self.pump.write((waveform + "\r").encode("utf-8"))
        logging.info("Set waveform to " + waveform)

    def bartels_start(self):
        if self.pump is None:
            logging.error("Pump is not initialized.")
            return
        self.pump.write(b"bon\r")
        logging.info("Pump ON")

    def bartels_stop(self):
        if self.pump is None:
            logging.error("Pump is not initialized.")
            return
        self.pump.reset_output_buffer()
        self.pump.write(b"boff\r")
        logging.info("Pump OFF")

    def pump_cycle(self, run_time):
        self.bartels_start()
        time.sleep(run_time)
        self.bartels_stop()
