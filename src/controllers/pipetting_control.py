# Adjusted imports to reflect the new structure
import yaml
import logging
import time
from threading import Event

class Robot:
    def __init__(self, config_path):
        # Load configuration file
        self.stop = Event()
        self.config_path = config_path
        self.config = self.load_config()
        self.start_stage()
        time.sleep(1)
        # Initialize internal state
        self.current_well = None
        self.command = None

    def start_stage(self):
        self.stage = Stage(self.config)

    def close_stage(self):
        try:
            self.stage.close()
            logging.info('Closed stage connection.')
        except AttributeError:
            logging.info('Stage already closed')

    def load_config(self):
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file) or {}
        except yaml.YAMLError as exc:
            logging.error(f'YAML error: {exc}')
            return {}
        except FileNotFoundError:
            logging.error(f'Config file not found: {self.config_path}')
            return {}

    def refresh_config(self):
        self.config = self.load_config()
        if hasattr(self, 'stage'):
            self.stage.config = self.config
        logging.info('Config refreshed.')

    def set_well(self, well):
        self.current_well = well
        logging.info(f'Set current well to {well}')

    def set_command(self, command):
        self.command = command
        logging.info(f'Set command to {command}')

    def pause(self, sleep_time):
        time.sleep(int(sleep_time))
        logging.info('Paused for ' + str(sleep_time))

# Placeholder for the Stage class
class Stage:
    def __init__(self, config):
        self.config = config
        logging.info('Stage initialized.')

    def close(self):
        logging.info('Stage connection closed.')
