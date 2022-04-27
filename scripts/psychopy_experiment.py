"""
SSVEP Offline Experiment
Notes:
- Press command-option-esc to quit
- MAKE SURE refresh_rate IS SET TO YOUR MONITOR'S REFRESH RATE
"""

from psychopy import visual
import numpy as np
from scipy import signal
import random
import sys, time
sys.path.append('src') # if run from the root project directory

# █████████████████████████████████████████████████████████████████████████████

## VARIABLES

refresh_rate = 60. # refresh rate of the monitor
use_retina = False # whether the monitor is a retina display
stim_duration = 5. # in seconds
n_per_class=20
classes=[9,11,12,13,14,16,17,18]
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

def create_trial_sequence(n_per_class, classes = [7.5,8.57,10,12,15]):
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

import dsi, ctypes, multiprocessing
SampleCallback = ctypes.CFUNCTYPE( None, ctypes.c_void_p, ctypes.c_double, ctypes.c_void_p )
@SampleCallback
def ExampleSampleCallback_Signals( headsetPtr, packetTime, userData ):
    global run_count
    global data
    global first_call
    h = dsi.Headset( headsetPtr )
    sample_data = [packetTime] # time stamp
    sample_data.extend([ch.ReadBuffered() for ch in h.Channels()]) # channel voltages
    data.append(sample_data)
    run_count += 1
    if first_call:
        with open("meta.csv", 'w') as csv_file:
            csv_file.write(str(time.time()) + '\n')
        first_call = False
    if run_count >= 300: # save data every second
        run_count = 0
        data_np = np.array(data)
        with open("eeg.csv", 'a') as csv_file:
            np.savetxt(csv_file, data_np, delimiter=', ')
        data = []
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
        csv_file.write('time, '+', '.join([ ch.GetName()  for ch in headset.Channels() ])+'\n')
    while True:
        headset.Idle(2.0)
if __name__ == "__main__": 
    recording = multiprocessing.Process(target=record,daemon=True)
    recording.start()
    time.sleep(6)

# █████████████████████████████████████████████████████████████████████████████

## EXPERIMENT

# if this script is run as a script rather than imported
if __name__ == "__main__": 
    win = visual.Window(
        screen = 0,
        fullscr = True,
        color = [-1,-1,-1], # black
        useRetina = use_retina
    )
    [win_w,win_h] = win.size
    if use_retina:
        win_w,win_h = win_w/2,win_h/2
    fixation = create_fixation_cross()
    square = create_flickering_square()
    photosensor = create_photosensor_dot()
    sequence = create_trial_sequence(n_per_class=n_per_class,classes=classes)
    for flickering_freq in sequence: # for each trial in the trail sequence
        # 750ms fixation cross:
        for frame in range(ms_to_frame(750, refresh_rate)):
            if frame == 0:
                with open("meta.csv", 'a') as csv_file:
                    csv_file.write(str(flickering_freq) + ', ' + str(time.time()) + '\n')
            fixation.draw()
            win.flip()
        # # 'stim_duration' seconds stimulation using constant period:
        # frames_per_cycle = ms_to_frame(1/flickering_freq*1000, refresh_rate) 
        # stim_duration_frames = ms_to_frame(stim_duration*1000, refresh_rate)
        # frames_on = int(frames_per_cycle/2)
        # frames_off = int(frames_per_cycle - frames_on)
        # single_cycle = [1] * frames_on + [0] * frames_off
        # trial = (single_cycle * int(flickering_freq*stim_duration + 2))[:stim_duration_frames]

        # 'stim_duration' seconds stimulation using flashing frequency approximation:
        phase_offset = 0 # for implementing frequency and phase mixed coding in the future
        phase_offset += 0.00001 # nudge phase slightly from points of sudden jumps for offsets that are pi multiples
        stim_duration_frames = ms_to_frame(stim_duration*1000, refresh_rate) # total number of frames for the stimulation
        frame_indices = np.arange(stim_duration_frames) # the frames as integer indices
        trial = signal.square(2 * np.pi * flickering_freq * (frame_indices / 60) + phase_offset) # frequency approximation formula
        trial[trial<0] = 0 # turn -1 into 0
        trial = trial.astype(int) # change float to int
        for frame in trial: # present the stimulation frame by frame
            if frame == 1:
                square.draw()
                photosensor.draw()
                win.flip()
            else:
                win.flip()
    time.sleep(3)

