import nidaqmx
from nidaqmx.constants import AcquisitionType, LineGrouping
import threading
import queue
import time
import datetime
import logging
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from collections import deque

import duty_cycle as duty


# DAQ Channels
# Pchannel = "cDAQ1Mod2/ai2" # What is this channel for?
# mpchannel = "CDAQ1Mod4/line11" # Main Power Switch
h1channel = "CDAQ1Mod4/port0/line8" # Heater 1

# DAQ Tasks
# mptask - Main Power
# h1task - Trap Heater
# h2task - 
# h3task - 

# Setup of DAQ tasks
#mptask=nidaqmx.Task()

# need to figure out if it is possible to roll the different heater control tasks into one task
h1task=nidaqmx.Task() 
#h2task=nidaqmx.Task()
#h3task=nidaqmx.Task()

# Turn on the main power to system
#mptask.do_channels.add_do_chan(mpchannel, line_grouping=LineGrouping.CHAN_PER_LINE)
#mptask.start()
#mptask.write(True)
#mptask.stop()

# Initialize heater tasks

h1task.do_channels.add_do_chan(h1channel, line_grouping=LineGrouping.CHAN_PER_LINE)

h1task.start()

# Create Duty Cycle threads
stopthread=threading.Event()
h1queue=queue.Queue()
print('test0')

# Set initial value for duty cycle
duty.setDuty(h1queue)
print('test1')
h1dutycycle = threading.Thread(target=duty.duty_cycle,args=(stopthread,h1queue,h1task))
print('test2')
h1dutycycle.start()
print('test3')


### ^^^^^^^ Duty Cycle Code

logging.basicConfig(filename='PressureTemperatureMarch.log', level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%m/%d/%Y %H:%M:%S %p")

fig, ax = plt.subplots()
pressure = deque([0.1], maxlen=200)
t_start = time.time()
t_array = deque([0], maxlen=200)
sensors = ["main reactor", "inlet lower", "inlet upper", "exhaust", "TMA", "Trap", "Gauges", "Pressure"]

def initialize_task():
    logging.info("Starting a new run")
    logging.info("main reactor,inlet lower, inlet upper, exhaust,TMA,Trap,Gauges,Pressure")
    tempchannels = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6"]
    task = nidaqmx.Task()
    for channel_name in tempchannels:
        task.ai_channels.add_ai_thrmcpl_chan(
            "cDaq1Mod1/" + channel_name, name_to_assign_to_channel="", min_val=0.0, max_val=200.0,
            units=nidaqmx.constants.TemperatureUnits.DEG_C, thermocouple_type=nidaqmx.constants.ThermocoupleType.K,
            cjc_source=nidaqmx.constants.CJCSource.CONSTANT_USER_VALUE, cjc_val=20.0, cjc_channel=""
        )
    task.ai_channels.add_ai_voltage_chan("CDAQ1Mod2/ai2", min_val=0, max_val=5)
    task.start()
    return task

task = initialize_task()

def animate(i, t_array, pressure):
    try:
        data = task.read()
        logging.info(data)  # data[7] is the voltage from the pressure controller, and needs to be converted to Torr (data[7]/10)
        pressure.append(round(data[7] / 10, 5))
        t_array.append(time.time() - t_start)

        ax.clear()
        ax.plot(t_array, pressure)
        ax.set_ylim(0.4, .8)
        ax.set_yscale('log')
        ax.set_title("Press q to quit")
        ax.set_xlim(left=t_array[0], right=t_array[0] + 300)  # the +100 part may eventually need adjusting.

        for j in range(len(sensors) - 1):
            ax.text(t_array[0]+200,.6+.03*j,sensors[j]+", "+str(data[j])[0:5])
    except Exception as e:
        logging.error("Error during animation: %s", e)

def on_key_press(event):
    if event.key == 'q':
        ani.event_source.stop()
        task.stop()
        task.close()
        plt.close(fig)
    
    # steal this function to allow for updating duty during runtime - may have to move to some other convenient place
    # can you still access the terminal while running the animation? will that cause issues?
    if event.key == 'd':
        duty.setDuty(h1queue) # in the future allow also for selecting which heater to change

fig.canvas.mpl_connect('key_press_event', on_key_press)
ani = animation.FuncAnimation(fig, animate, fargs=(t_array, pressure), interval=500)
plt.title("Press q to quit")
plt.show()

"""
i = input("Shut off main power? (y/n)")
while True:
    if i == 'y':
        logging.info("Turning off the main power pin, cdaq1mod4 line 11")
        mptask.do_channels.add_do_chan(mpchannel, line_grouping=LineGrouping.CHAN_PER_LINE)
        mptask.start()
        mptask.write(False)
        mptask.stop()
    else:
        break
    
"""
stopthread.set()
h1dutycycle.join()
h1task.write(False)
h1task.stop()


