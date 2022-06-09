"""
SSVEP Offline Experiment
phase-offset version
Notes:
- Press command-option-esc to quit
- MAKE SURE refresh_rate IS SET TO YOUR MONITOR'S REFRESH RATE
"""

from psychopy import visual, core
from psychopy.hardware import keyboard
import numpy as np
from scipy import signal
import random
import sys, time
sys.path.append('src') # if run from the root project directory

# █████████████████████████████████████████████████████████████████████████████

## VARIABLES
use_dsi7 = True
use_arduino = False # currently dsi7 and arduino can't both be on at the same time
center_flash = True # whether the visual stimuli are only presented at the center of the screen
flash_mode = 'square' # 'sine', 'square', or 'chirp', 'dual band'
refresh_rate = 60.02 # refresh rate of the monitor
use_retina = False # whether the monitor is a retina display
stim_duration = 5. # in seconds
isi_duration = 0.75 # in seconds
# after_stim_padding = 0.25 # in seconds, stim remains but the data is discarded
# isi_duration = 0.1 # in seconds
after_stim_padding = 0.0 # in seconds, stim remains but the data is discarded
n_per_class=10
classes=[( 8,0),( 8,0.5),( 8,1),( 8,1.5),
         ( 9,0),( 9,0.5),( 9,1),( 9,1.5),
         (10,0),(10,0.5),(10,1),(10,1.5),
         (11,0),(11,0.5),(11,1),(11,1.5),
         (12,0),(12,0.5),(12,1),(12,1.5),
         (13,0),(13,0.5),(13,1),(13,1.5),
         (14,0),(14,0.5),(14,1),(14,1.5),
         (15,0),(15,0.5),(15,1),(15,1.5),]
data = []
run_count = 0
first_call = True

# █████████████████████████████████████████████████████████████████████████████

## FUNCTIONS

def create_fixation_cross(size=50):
    return visual.ShapeStim(
        win = win,
        units='pix',
        size = size,
        fillColor=[1, 1, 1],
        lineColor=[1, 1, 1],
        lineWidth = 1,
        vertices = 'cross',
        name = 'off', # Used to determine state
        pos = [0, 0]
    )

def ms_to_frame(ms, fs):
    dt = 1000 / fs
    return np.round(ms / dt).astype(int)

def create_flickering_square(size=150):
    return visual.Rect(
        win=win,
        units="pix",
        width=size,
        height=size,
        fillColor='white',
        lineColor='white',
        lineWidth = 1,
        pos = [0, 0]
    )

def create_photosensor_dot(size=50):
    return visual.Circle(
        win=win,
        units="pix",
        radius=size,
        fillColor='white',
        lineColor='white',
        lineWidth = 1,
        edges = 32,
        pos = (-(win_w / 2) + size, -((win_h / 2) - size))
    )

def create_trial_sequence(n_per_class, classes = [(7.5,0),(8.57,0),(10,0),(12,0),(15,0)]):
    """
    Create a random sequence of trials with n_per_class of each class
    Inputs:
        n_per_class : number of trials for each class
    Outputs:
        seq : (list of len(10 * n_per_class)) the trial sequence
    """
    seq = classes * n_per_class
    random.seed()
    random.shuffle(seq) # shuffles in-place
    return seq

# █████████████████████████████████████████████████████████████████████████████

## DSI-7
if use_dsi7:
    # previous_time = time.time()
    import dsi, ctypes, multiprocessing, threading
    from pylsl import StreamInfo, StreamOutlet, StreamInlet, resolve_stream, local_clock
    SampleCallback = ctypes.CFUNCTYPE( None, ctypes.c_void_p, ctypes.c_double, ctypes.c_void_p )
    @SampleCallback
    def ExampleSampleCallback_Signals( headsetPtr, packetTime, userData ):
        # global run_count
        # global data
        global first_call
        # global previous_time
        # previous_time = time.time()
        h = dsi.Headset( headsetPtr )
        # sample_data = [packetTime] # time stamp
        # sample_data = [time.time()] # time stamp
        # sample_data.extend([ch.ReadBuffered() for ch in h.Channels()[:-1]]) # channel voltages
        sample_data = [ch.ReadBuffered() for ch in h.Channels()[:-1]]
        # data.append(sample_data)
        # run_count += 1
        if first_call:
            if sample_data[1] > 1e15: # if Pz saturation error happens
                quit()
            with open("meta.csv", 'w') as csv_file:
                # csv_file.write('0,0,'+str(time.time()) + '\n')
                csv_file.write('0,0,'+str(local_clock()) + '\n')
            first_call = False
        # if run_count >= 30:
        #     run_count = 0
        #     data_np = np.array(data)
        #     with open("eeg.csv", 'a') as csv_file:
        #         np.savetxt(csv_file, data_np, delimiter=', ')
        #     data = []

        # data_np = np.array([sample_data])
        # with open("eeg.csv", 'a') as csv_file:
        #     np.savetxt(csv_file, data_np, delimiter=', ')

        with open("eeg.csv", 'a') as csv_file:
            # csv_file.write(str(time.time())+', ')
            csv_file.write(str(local_clock())+', ')
            for stuff in sample_data[:-1]:
                csv_file.write(str(stuff)+', ')
            csv_file.write(str(sample_data[-1])+'\n')

        # time.sleep(1/300-(time.time()-previous_time))
        # time.sleep(0.000001)
        # previous_time=time.time()

    def record():
        args = getattr( sys, 'argv', [ '' ] )
        if sys.platform.lower().startswith( 'win' ): default_port = 'COM4'
        else:                                        default_port = '/dev/cu.DSI7-0009.BluetoothSeri'
        # first command-line argument: serial port address
        if len( args ) > 1: port = args[ 1 ]
        else: port = default_port
        # second command-line argument:  name of the Source to be used as reference, or the word 'impedances'
        if len( args ) > 2: ref = args[ 2 ]
        else: ref = ''
        headset = dsi.Headset()
        headset.Connect(port)
        headset.SetSampleCallback( ExampleSampleCallback_Signals, 0 )
        headset.StartDataAcquisition()
        with open("eeg.csv", 'w') as csv_file:
            csv_file.write('time, '+', '.join([ ch.GetName()  for ch in headset.Channels()[:-1] ])+'\n')
        while True:
            # headset.Idle(2.0)
            headset.Idle(5000.0)
            # pass
    if __name__ == "__main__": 
        # recording = multiprocessing.Process(target=record,daemon=True)
        recording = threading.Thread(target=record,daemon=True)
        recording.start()
        time.sleep(6)

# █████████████████████████████████████████████████████████████████████████████

# Arduino Photosensor for Timing

if use_arduino:
    import serial, threading
    # arduino = serial.Serial(port='COM3', baudrate=115200, timeout=.1)
    arduino = serial.Serial(port='COM3', baudrate=19200, timeout=.1)
    # arduino = serial.Serial(port='COM3', baudrate=9600, timeout=.1)
    arduino_call_num = 0
    with open("light_amp.csv", 'w') as csv_file:
        csv_file.write('time, light_amp\n')
    def record_light_amp():
        global arduino_call_num
        while True:
            try:
                # data = arduino.readline().decode('ascii')[:-1]
                data = int.from_bytes(arduino.read(), "big")
                if data > 100:
                    data = 0
                if arduino_call_num < 100:
                    arduino_call_num+=1
                    continue
                elif arduino_call_num == 100:
                    arduino_call_num+=1
                    with open("meta.csv", 'w') as csv_file:
                        csv_file.write('0,0,'+str(time.time()) + '\n')
                with open("light_amp.csv", 'a') as csv_file:
                    # csv_file.write(data)
                    csv_file.write(str(time.time())+', '+str(data)+'\n')
            except UnicodeDecodeError and ValueError:
                pass
    if __name__ == "__main__": 
        # recording_light_amp = multiprocessing.Process(target=record_light_amp,daemon=True)
        recording_light_amp = threading.Thread(target=record_light_amp,daemon=True)
        recording_light_amp.start()
        time.sleep(2)

# █████████████████████████████████████████████████████████████████████████████

## EXPERIMENT

# if this script is run as a script rather than imported
if __name__ == "__main__": 
    kb = keyboard.Keyboard()
    win = visual.Window(
        screen = 0,
        fullscr = True,
        # color = [-1,-1,-1], # black
        useRetina = use_retina
    )
    [win_w,win_h] = win.size
    if use_retina:
        win_w,win_h = win_w/2,win_h/2
    if center_flash: # if we want the visual stimuli to be only presented at the center of the screen
        fixation = create_fixation_cross()
        square = create_flickering_square()
        photosensor = create_photosensor_dot()
        sequence = create_trial_sequence(n_per_class=n_per_class,classes=classes)
        # square.color = (0, 1, 0)
        for flickering_freq, phase_offset in sequence: # for each trial in the trail sequence
            keys = kb.getKeys() 
            for thisKey in keys:
                if thisKey=='escape':
                    core.quit()
            # 750ms fixation cross:
            for frame in range(ms_to_frame(isi_duration*1000, refresh_rate)):
                # if frame == 0:
                #     with open("meta.csv", 'a') as csv_file:
                #         csv_file.write(str(flickering_freq)+', '+str(phase_offset) + ', ' + str(time.time()) + '\n')
                fixation.draw()
                win.flip()
            # 'stim_duration' seconds stimulation using flashing frequency approximation:
            phase_offset_str = str(phase_offset)
            phase_offset += 0.00001 # nudge phase slightly from points of sudden jumps for offsets that are pi multiples
            stim_duration_frames = ms_to_frame((stim_duration+after_stim_padding)*1000, refresh_rate) # total number of frames for the stimulation
            frame_indices = np.arange(stim_duration_frames) # the frames as integer indices
            if flash_mode == 'square': # if we want to use binarized square wave visual stimuli
                trial = signal.square(2 * np.pi * flickering_freq * (frame_indices / refresh_rate) + phase_offset * np.pi) # frequency approximation formula
                for i_frame,frame in enumerate(trial): # present the stimulation frame by frame
                    if i_frame == 0:
                        with open("meta.csv", 'a') as csv_file:
                            csv_file.write(str(flickering_freq)+', '+phase_offset_str + ', ' + str(time.time()) + '\n')
                    square.color = (frame, frame, frame)
                    square.draw()
                    photosensor.color = (frame, frame, frame)
                    photosensor.draw()
                    win.flip()
            elif flash_mode == 'sine': # if we want to use smoothed sine wave visual stimuli
                trial = np.sin(2 * np.pi * flickering_freq * (frame_indices / refresh_rate) + phase_offset * np.pi) # frequency approximation formula
                for frame in trial: # present the stimulation frame by frame
                    square.color = (frame, frame, frame)
                    square.draw()
                    photosensor.color = (frame, frame, frame)
                    photosensor.draw()
                    win.flip()
            elif flash_mode == 'chirp':
                frame_times = np.linspace(0,stim_duration,int(stim_duration*refresh_rate))
                trial = signal.chirp(frame_times, f0=10, f1=14, t1=5, method='linear')
                for frame in trial: # present the stimulation frame by frame
                    square.color = (frame, frame, frame)
                    square.draw()
                    win.flip()
            elif flash_mode == 'dual band':
                flickering_freq2 = phase_offset
                phase_offset = 0.00001
                trial = signal.square(2 * np.pi * flickering_freq * (frame_indices / refresh_rate) + phase_offset * np.pi) # frequency approximation formula
                trial += signal.square(2 * np.pi * flickering_freq2 * (frame_indices / refresh_rate) + phase_offset * np.pi) # frequency approximation formula
                trial /= 2
                for frame in trial: # present the stimulation frame by frame
                    square.color = (frame, frame, frame)
                    square.draw()
                    win.flip()
        
    time.sleep(6)

