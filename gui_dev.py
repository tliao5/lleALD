import nidaqmx
from nidaqmx.constants import LineGrouping
import threading
import queue
import time
import logging
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
import tkinter as tk
from tkinter import ttk

def duty_cycle(stopthread, duty_queue, task, light):
    voltageold = False
    duty = duty_queue.get(block=False)
    while not stopthread.is_set():
        if not duty_queue.empty():
            duty = duty_queue.get(block=False)
        for i in range(200):
            voltage = i < duty
            if voltageold != voltage:
                voltageold = voltage
                #light.config(bg="green" if voltage else "red")
                task.write(voltage)
            time.sleep(0.005)
    print(f"Task {task}: Task Closing, Voltage set to False")
    task.write(False)
    task.close()

# DAQ Channels
Pchannel = "cDAQ1Mod2/ai2"  # Pressure channel
mpchannel = "CDAQ1Mod4/line11"  # Main Power Switch
h1channel = "CDAQ1Mod4/port0/line5"  # Heater 1
h2channel = "CDAQ1Mod4/port0/line6"  # Heater 2
h3channel = "CDAQ1Mod4/port0/line7"  # Heater 3

# DAQ Tasks
mptask = nidaqmx.Task("Main Power")
h1task = nidaqmx.Task("Heater 1")
h2task = nidaqmx.Task("Heater 2")
h3task = nidaqmx.Task("Heater 3")

# Main power off by default
mptask.do_channels.add_do_chan(mpchannel, line_grouping=LineGrouping.CHAN_PER_LINE)
mptask.start()
mptask.write(False)
mptask.stop()

# Initialize heater tasks
h1task.do_channels.add_do_chan(h1channel, line_grouping=LineGrouping.CHAN_PER_LINE)
h2task.do_channels.add_do_chan(h2channel, line_grouping=LineGrouping.CHAN_PER_LINE)
h3task.do_channels.add_do_chan(h3channel, line_grouping=LineGrouping.CHAN_PER_LINE)

h1task.start()
h2task.start()
h3task.start()

# Create Duty Cycle threads
stopthread = threading.Event()
h1queue = queue.Queue()
h2queue = queue.Queue()
h3queue = queue.Queue()

# Tkinter GUI
class HeaterControlApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Heater Control")
        self.geometry("800x500")
        self.task = self.initialize_task()
        self.create_widgets()

    def create_widgets(self):
        self.main_power_button = ttk.Button(self, text="Main Power Off",  command= lambda: self.toggle_main_power(mptask))
        self.main_power_button.grid(row=0, column=0, padx=10, pady=10)
        self.main_power_light = tk.Canvas(self, width=20, height=20, bg="red")
        self.main_power_light.grid(row=0, column=1, padx=10, pady=10)

        self.h1_label = ttk.Label(self, text="Heater 1 Duty Cycle:")
        self.h1_label.grid(row=1, column=0, padx=10, pady=10)
        self.h1_entry = ttk.Entry(self)
        self.h1_entry.insert(0, 0)
        self.update_duty_cycle(h1queue, self.h1_entry)
        self.h1_entry.grid(row=1, column=1, padx=10, pady=10)
        self.h1_entry.bind("<Return>", lambda event: self.update_duty_cycle(h1queue, self.h1_entry))

        self.h2_label = ttk.Label(self, text="Heater 2 Duty Cycle:")
        self.h2_label.grid(row=2, column=0, padx=10, pady=10)
        self.h2_entry = ttk.Entry(self)
        self.h2_entry.insert(0, 0)
        self.update_duty_cycle(h2queue, self.h2_entry)
        self.h2_entry.grid(row=2, column=1, padx=10, pady=10)
        self.h2_entry.bind("<Return>", lambda event: self.update_duty_cycle(h2queue, self.h2_entry))

        self.h3_label = ttk.Label(self, text="Heater 3 Duty Cycle:")
        self.h3_label.grid(row=3, column=0, padx=10, pady=10)
        self.h3_entry = ttk.Entry(self)
        self.h3_entry.insert(0, 0)
        self.update_duty_cycle(h3queue, self.h3_entry)
        self.h3_entry.grid(row=3, column=1, padx=10, pady=10)
        self.h3_entry.bind("<Return>", lambda event: self.update_duty_cycle(h3queue, self.h3_entry))

        self.h1_light = tk.Canvas(self, width=20, height=20, bg="red")
        self.h1_light.grid(row=1, column=2, padx=10, pady=10)
        self.h2_light = tk.Canvas(self, width=20, height=20, bg="red")
        self.h2_light.grid(row=2, column=2, padx=10, pady=10)
        self.h3_light = tk.Canvas(self, width=20, height=20, bg="red")
        self.h3_light.grid(row=3, column=2, padx=10, pady=10)
        
        self.fig, self.ax, self.pressure, self.t_array, self.t_start, self.sensors = self.plotinitialize()
        # Start the animation in the main thread
        ani = animation.FuncAnimation(self.fig, self.animate, interval=500)
         
        tempplot = FigureCanvasTkAgg(self.fig, self)
        tempplot.draw()
        tempplot.get_tk_widget().grid(row=0, column=5,rowspan=40, columnspan=30,padx=10, pady=10,sticky=tk.EW)
        toolbarFrame = tk.Frame(master=self)
        toolbarFrame.grid(row=41,column=5)
        toolbar = NavigationToolbar2Tk(tempplot, toolbarFrame)
  
        
        # Create Duty Cycle threads
        self.h1dutycycle = threading.Thread(target=duty_cycle, args=(stopthread, h1queue, h1task, self.h1_light))
        self.h2dutycycle = threading.Thread(target=duty_cycle, args=(stopthread, h2queue, h2task, self.h2_light))
        self.h3dutycycle = threading.Thread(target=duty_cycle, args=(stopthread, h3queue, h3task, self.h3_light))

        self.h1dutycycle.start()
        self.h2dutycycle.start()
        self.h3dutycycle.start()

    def plotinitialize(self):
        logging.basicConfig(filename='PressureTemperatureMarch.log', level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%m/%d/%Y %H:%M:%S %p")
        
        plt.rcParams["figure.figsize"] = [13.00, 6.50]
        plt.rcParams["figure.autolayout"] = True

        fig, ax = plt.subplots()
        pressure = deque([0.1], maxlen=200)
        t_start = time.time()
        t_array = deque([0], maxlen=200)
        sensors = ["main reactor", "inlet lower", "inlet upper", "exhaust", "TMA", "Trap", "Gauges", "Pressure"]
        return fig, ax, pressure, t_array, t_start, sensors
       
    def initialize_task(self):
        logging.info("Starting a new run")
        logging.info("main reactor,inlet lower, inlet upper, exhaust,TMA,Trap,Gauges,Pressure")
        tempchannels = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6"]
        task = nidaqmx.Task("Thermocouples")
        for channel_name in tempchannels:
            task.ai_channels.add_ai_thrmcpl_chan(
                "cDaq1Mod1/" + channel_name, name_to_assign_to_channel="", min_val=0.0, max_val=200.0,
                units=nidaqmx.constants.TemperatureUnits.DEG_C, thermocouple_type=nidaqmx.constants.ThermocoupleType.K,
                cjc_source=nidaqmx.constants.CJCSource.CONSTANT_USER_VALUE, cjc_val=20.0, cjc_channel=""
            )
        task.ai_channels.add_ai_voltage_chan("CDAQ1Mod2/ai2", min_val=0, max_val=5)
        task.start()
        return task

    def animate(self,i):
        try:
            ax=self.ax
            t_start=self.t_start
            t_array=self.t_array
            sensors=self.sensors
            pressure=self.pressure
        
            data = self.task.read()
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

    def toggle_main_power(self,mptask):
        if self.main_power_button.config('text')[-1] == 'Main Power ON':
            mptask.start()
            mptask.write(False)
            mptask.stop()
            self.main_power_button.config(text='Main Power OFF')
            self.main_power_light.config(bg="red")
        else:
            mptask.start()
            mptask.write(True)
            mptask.stop()
            self.main_power_button.config(text='Main Power ON')
            self.main_power_light.config(bg="green")

    def update_duty_cycle(self, queue, duty):
        try:
            duty_value = int(duty.get())
            if 0 <= duty_value <= 200:
                print("Duty cycle updated")
                queue.put(duty_value)
            else:
                raise Exception()
        except:
            print("Invalid Input. Please enter an integer between 0 and 200.")

    def on_closing(self):
        # Stop the duty cycle threads
        stopthread.set()
        time.sleep(1)
        self.h1dutycycle.join()
        time.sleep(1)
        self.h2dutycycle.join()
        time.sleep(1)
        self.h3dutycycle.join()
        
        
        # Turn off main power
        mptask.start()
        mptask.write(False)
        mptask.stop()
        mptask.close()
        
        # Turn of Thermocouples
        self.task.close()

        # Stop the animation
        plt.close(self.fig)

        # Call destroy method to close gui
        self.destroy()

if __name__ == "__main__":
    # Start the GUI
    aldgui = HeaterControlApp()

    # trigger proper closing on press of red X button to close window
    aldgui.protocol("WM_DELETE_WINDOW", aldgui.on_closing)
    
    aldgui.mainloop()