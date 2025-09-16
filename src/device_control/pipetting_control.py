import serial
import yaml
import logging
import time
# Removed json and os imports (status file handling removed)
# 'sys' removed (was only used in commented socket code)
from threading import Event
#from threading import Thread

'''
Tracebot control was initially created by:
Kai Sandvold Beckwith
Ellenberg group
EMBL Heidelberg

This version modified by:
Øyvind Ødegård Fougner
Schink lab
University of Oslo

'''

class Robot():

    def __init__(self, config_path):
        
        #Load configuration file
        self.stop = Event() 
        self.config_path = config_path
        self.config = self.load_config()
        self.start_stage()
        time.sleep(1)
        # Pump functionality removed; Robot now only manages stage (and sequencing logic)
    # Internal state replacing former status.json persistence
    self.current_well = None
    self.command = None

        #self.start_socket_server()

    def start_stage(self):
        self.stage = Stage(self.config)

    # Pump methods removed.
    
    def close_stage(self):
        try:
            self.stage.close()
            logging.info('Closed stage connection.')
        except AttributeError:
            logging.info('Stage already closed')

    def load_config(self):
        #Open config file and return config variable form yaml file
        with open(self.config_path, 'r') as file:
            try:
                config=yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print(exc)
        return config

    def refresh_config(self):
        self.config = self.load_config()
        if hasattr(self, 'stage'):
            self.stage.config = self.config

        logging.info('Config refreshed.')

    def set_well(self, well):
        # Set current well in internal state
        self.current_well = well
        logging.info(f'Set current well to {well}')

    def set_command(self, command):
        # Set current command in internal state
        self.command = command
        logging.info(f'Set command to {command}')

    def pause(self, sleep_time):
        #Set and run a pause step, and log.
        time.sleep(int(sleep_time))
        logging.info('Paused for '+str(sleep_time))

    def wp_coord_list(self, sequence):
    # Generate coordinate list for whole and selected wells of a 96-well plate.
    # Also adjusts for a rotated plate by using measured top left and bottom right positions from
    # config file.

        config=self.config['well_plate']
        rows=config['rows']
        columns=config['columns']
        z_base=config['z_base']
        well_spacing=config['well_spacing']
        tl_x=config['top_left']['x']
        tl_y=config['top_left']['y']
        br_x=config['bottom_right']['x']
        br_y=config['bottom_right']['y']
        first_probe=sequence['first_well']
        last_probe=sequence['last_well']

        # Make list of well names selected in config file
        all_wells=[]
        for i in range(rows):
            for j in range(columns):
                all_wells.append(chr(65+i)+str(j+1))
        
        # Calculate adjustment based on measured top left and bottom right well positions 
        well_adjust_x=(1-(br_x-tl_x)/(12*well_spacing))
        well_adjust_y=(1-(br_y-tl_y)/(8*well_spacing))
        
        # Generate list of all well coordinates adjusted for rotation.
        all_coords={} 
        for i in range(rows):
            for j in range(columns):
                all_coords[chr(65+i)+str(1+j)]={'x': tl_x+j*well_spacing+i*well_adjust_x, 'y': tl_y+i*well_spacing+j*well_adjust_y, 'z':config['z_base']}
        
        # Make coordinate list for only the selected wells
        first_well=all_wells.index(first_probe)
        last_well=all_wells.index(last_probe)
        sel_wells=all_wells[first_well:(last_well+1)]
        sel_coords={}
        for well in sel_wells:
            sel_coords[well]=all_coords[well]
        
        return all_coords, sel_coords

    def calc_num_cycles(self, sequence):
        '''
        Helper function to check number of cycles based config setting.
        If an int, runs that number of cycles. If 'all' counts how many cycles is 
        needed to probe all wellplate positions.
        
        Output:
            num_cycles: Int with number of cycles.

        '''
        wells_seq = 0
        for seq in sequence['sequence']:
            for val in seq.values():
                if val == 'wp':
                    wells_seq += 1
        wells=len(self.sel_coords.keys())
        num_cycles=wells//wells_seq
        print('Calculated number of cycles is ', num_cycles)
        return num_cycles

    '''
    # Make json files that store all wellplate coordinates and selected wellplate coordinates.
    with open('all_coords.json', 'w') as file:
        json.dump(all_coords, file)
    with open('sel_coords.json', 'w') as file:
        json.dump(sel_coords, file)
    '''

    def single_cycle(self, sequence):
        '''
        Runs a single sequence as defined in the config file.
        '''
        config=self.config

        for a in sequence['sequence']:                # Sequences is defined as list of subsequences in config file.
        #for a in seq:                                # Loop through each sequence in turn
            action=list(a.keys())[0]
            param=list(a.values())[0]

            if action == 'probe' and param == 'wp': # Run for current well in internal state.
                if self.stop.is_set():
                    logging.info('Stopping robot.')
                    raise SystemExit

                current_pos = self.current_well
                if current_pos is None:
                    logging.error('Current well not set before probing well plate.')
                    raise RuntimeError('Current well not set')
                coords=self.all_coords[current_pos]
                self.stage.move_stage(coords)
                while self.stage.check_stage() != 'Idl': #Wait until move is done before proceeding.
                    time.sleep(2)
                logging.info('Probe at '+str(current_pos))
                i=self.sel_coord_list.index(current_pos)
                try:
                    next_well=self.sel_coord_list[i+1]
                except IndexError:
                    logging.info('Last well reached')
                    next_well='Last'
                self.set_well(next_well if next_well != 'Last' else None)
                
            elif action == 'probe' and param != 'wp':   # For all position outside well plates, such as reservoirs.
                if self.stop.is_set():
                    logging.info('Stopping robot.')
                    raise SystemExit
                try: 
                    coords=config['positions'][param]
                    self.stage.move_stage(coords)
                    while self.stage.check_stage() != 'Idl': #Wait until move is done before proceeding.
                        time.sleep(2)
                    logging.info('probe at '+str(param))
                except KeyError:
                    logging.error('Invalid probe position: '+str(param))

            elif action == 'pump':
                logging.warning('Pump action encountered in sequence but pump functionality has been removed. Skipping.')

            elif action == 'pause':
                if self.stop.is_set():
                    logging.info('Stopping robot.')
                    raise SystemExit
                self.pause(param)

            elif action == 'image':
                if self.stop.is_set():
                    logging.info('Stopping robot.')
                    raise SystemExit
                self.set_command('image')
                logging.info('Imaging step triggered (external imaging system should act on command state).')
                # Placeholder: external system expected to clear or change command.
                # For now, we just simulate brief wait.
                time.sleep(param if isinstance(param, (int, float)) else 2)
                self.set_command('robot')
                logging.info('Imaging complete (simulated).')
            else:
                logging.error('Unrecognized sequence command')  


    def wp_cycle(self, restart=True):
        '''
        Runs a full cycle of sequences for all selected well positions.
        Refreshes coordinate list based on config file.
        Runs number of cycles determined by det_num_cycles helper function.
    Restart flag determines if start from configured first well or continue from existing internal current_well.
        '''
        
        config=self.config

        for i, seq_name in enumerate(config['sequences']):
            seq = config['sequences'][seq_name]
            print(seq)
            try: 
                first_well = seq['first_well']
                last_well = seq['last_well']
                self.all_coords, self.sel_coords = self.wp_coord_list(seq)
                self.sel_coord_list=list(self.sel_coords.keys())
                print('Sequence with wells: ', self.sel_coords)
            except KeyError: # If first or last well are not defined.
                print('well definition not found')
                self.all_coords, self.sel_coords = (None, None)

            if seq['n_cycles'] == 'all':
                num_cycles = self.calc_num_cycles(seq)
            else:
                num_cycles = seq['n_cycles']

            self.set_command('robot')

            if restart:
                try:
                    self.set_well(seq['first_well'])
                except KeyError: #Sequence has no wells
                    pass
            for cycle in range(num_cycles):
                logging.info('Starting cycle ' + str(cycle+1) + ' of ' +str(num_cycles) + ' in sequence ' +str(seq_name) +'.') 
                self.single_cycle(seq)

    '''
    #Work in progress.
    # 
    #     
    def socket_server(self):
        import socket
        import sys

        host = 'localhost'
        port = 65432
        address = (host, port)

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(address)
        server_socket.listen(5)

        while True:
            print("Listening for client . . .")
            conn, address = server_socket.accept()
            print("Connected to client at ", address)
            #pick a large output buffer size because i dont necessarily know how big the incoming packet is                                                    
            while True:
                data = conn.recv(2048);
                if data.strip() == b"disconnect":
                    conn.close()
                    print('Closing connection.')
                    break
                    #sys.exit("Received disconnect message.  Shutting down.")
                    #conn.send(b"dack")
                elif data.strip() == b"shutdown":
                    conn.close()
                    print('Received shutdown message.  Shutting down.')
                    sys.exit()

                elif data.strip() == b'read_command':
                    conn.sendall(bytes(self.command))

                elif data.strip() == b'set_imaging':
                    self.set_command('imaging')
                    conn.sendall(bytes('Imaging started.'))

                elif data.strip() == b'set_robot':
                    self.set_command('robot')
                    conn.sendall(bytes('Robot set.'))

                    
    def start_socket_server(self):
        self.socket_thread = Thread(target=self.socket_server)
        self.socket_thread.start()
    
    def stop_socket_server(self):
        self.socket_thread.join()
    '''

## Pump code removed: classes Bartels, CPP_pump, CPP_pump_dual.

class Stage(Robot):

    def __init__(self, config):
        self.config = config
        try:
            self.stage = self.initialize_grbl()
            time.sleep(1)
            self.zero_stage()
        except serial.SerialException:
            logging.error('No stage found on ' + self.config['stage_port'])

    def initialize_grbl(self):
        s = serial.Serial(port=self.config['stage_port'],baudrate=115200) # open grbl serial port
        s.write(("\r\n\r\n").encode('utf-8')) # Wake up grbl
        time.sleep(2)   # Wait for grbl to initialize
        s.flushInput()  # Flush startup text in serial input
        s.write(('? \n').encode('utf-8')) # Request machine status
        grbl_out = s.readline().decode('utf-8') # Wait for grbl response with carriage return
        logging.info('GRBL stage interface initialized:' +grbl_out)
        return s

    def zero_stage(self):
        stage = self.stage
        stage.write(('G10 L20 P0 X0 Y0 Z0 \n').encode('utf-8'))
        grbl_out = stage.readline().decode('utf-8')
        logging.info('Current position set to zero: '+grbl_out)

    def check_stage(self):
        stage = self.stage
        stage.flushInput()
        stage.write(('?\n\r').encode('utf-8'))
        time.sleep(0.2)
        grbl_out = stage.readline().decode('utf-8')
        return grbl_out[1:4]

    def move_stage(self, pos):
        stage = self.stage
        #######
        # Define positions from dictionary position input of the dict format {'x':5, etc},
        # and send GRBL code to move to give position
        # Movements will be executed in order received (use Pyton3.6 or later dicts).
        ######
        for axis in pos:
            stage.write(('G0 Z0 \n').encode('utf-8')) # Always move to Z=0 first.
            time.sleep(0.2)
            stage.write(('G0 '+axis.upper()+str(pos[axis])+' \n').encode('utf-8')) # Move code to GRBL, xy first
            time.sleep(0.2)
            grbl_out = stage.readline().decode('utf-8') # Wait for grbl response with carriage return
            logging.info('GRBL out:'+grbl_out)
            logging.info('Moved to '+axis.upper()+'='+str(pos[axis]))

    def stop_stage(self):
        self.stage.write(b'!')
        
        #sys.exit()
        time.sleep(0.5)
        self.stage.write(b'\030')
        time.sleep(0.5)
        #self.stage.write(char.ConvertFromUtf32(24))
        #time.sleep(0.5)
        #grbl_out = self.stage.readline().decode('utf-8') # Wait for grbl response with carriage return
        #logging.info('GRBL out: '+grbl_out)
        self.stage.write(b'~')
        time.sleep(0.5)
        self.stage.write(b'\030')
        
        logging.info('Stage stopped')
        grbl_out = self.stage.readline().decode('utf-8') # Wait for grbl response with carriage return
        logging.info('GRBL out: '+grbl_out)