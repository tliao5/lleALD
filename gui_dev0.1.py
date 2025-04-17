import threading
import queue
import time
import logging
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

## Dummy nidaqmx and LLE_ALD_pythonlib
class DummyTask:
    def __init__(self, name):
        self.name = name
        self.channels = []

    def do_channels(self):
        return self

    def add_do_chan(self, channel, line_grouping=None):
        logging.info(f"Adding DO channel: {channel}")

    def ai_channels(self):
        return self

    def add_ai_thrmcpl_chan(self, channel, min_val, max_val, units, thermocouple_type, cjc_source, cjc_val):
        logging.info(f"Adding AI thermocouple channel: {channel}")

    def add_ai_voltage_chan(self, channel, min_val, max_val):
        logging.info(f"Adding AI voltage channel: {channel}")

    def start(self):
        logging.info(f"Starting task: {self.name}")

    def stop(self):
        logging.info(f"Stopping task: {self.name}")

    def write(self, value):
        logging.info(f"Writing value {value} to task: {self.name}")

    def read(self):
        logging.info(f"Reading data from task: {self.name}")
        return [np.random.random() for _ in range(8)]

    def close(self):
        logging.info(f"Closing task: {self.name}")

class DummyLLE_ALD:
    @staticmethod
    def readTemp():
        logging.info("Reading temperature")

    @staticmethod
    def setValve():
        logging.info("Setting valve")

    @staticmethod
    def pulseValve():
        logging.info("Pulsing valve")

    @staticmethod
    def closeValves():
        logging.info("Closing valves")

    @staticmethod
    def readPressure():
        logging.info("Reading pressure")

    @staticmethod
    def readPressure_pdr200():
        logging.info("Reading pressure PDR200")

logging.basicConfig(filename='test.log', level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%m/%d/%Y %H:%M:%S %p")
logger = logging.getLogger(__name__)

## Duty Cycle
def duty_cycle(stopthread, duty_queue, task):
    voltageold = False
    duty = duty_queue.get(block=False)
    while not stopthread.is_set():
        if not duty_queue.empty():
            duty = duty_queue.get(block=False)
        for i in range(200):
            voltage = i < duty
            if voltageold != voltage:
                voltageold = voltage
                task.write(voltage)
            time.sleep(0.005)
    logging.info(f"Task {task.name}: Task Closing, Voltage set to False")
    task.write(False)
    task.close()

# DAQ Channels and Tasks
channels = {
    "Pchannel": "cDAQ1Mod2/ai2", # pressure reading
    "mpchannel": "CDAQ1Mod4/line11", # main power
    "h1channel": "CDAQ1Mod4/port0/line5", # heater 1
    "h2channel": "CDAQ1Mod4/port0/line6", # heater 2
    "h3channel": "CDAQ1Mod4/port0/line7" # heater 3
}

# Main Power on
Ptask = DummyTask("Ptask")
mptask = DummyTask("mptask")
h1task = DummyTask("h1task")
h2task = DummyTask("h2task")
h3task = DummyTask("h3task")

mptask.do_channels().add_do_chan(channels["mpchannel"])
mptask.start()
mptask.write(False)
mptask.stop()

# Initialize heater tasks
h1task.do_channels().add_do_chan(channels["h1channel"])
h1task.start()
h2task.do_channels().add_do_chan(channels["h2channel"])
h2task.start()
h3task.do_channels().add_do_chan(channels["h3channel"])
h3task.start()

# Create Duty Cycle threads
stopthread = threading.Event()
h1queue = queue.Queue()
h2queue = queue.Queue()
h3queue = queue.Queue()

class QueueHandler(logging.Handler):
    """Class to send logging records to a queue. It can be used from different threads."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


class ConsoleUi:
    """Poll messages from a logging queue and display them in a scrolled text widget"""
    def __init__(self, frame):
        self.frame = frame
        # Create a ScrolledText widget
        self.scrolled_text = ScrolledText(frame, state='disabled', height=12)
        self.scrolled_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        self.scrolled_text.configure(font='TkFixedFont')
        self.scrolled_text.tag_config('INFO', foreground='black')
        self.scrolled_text.tag_config('DEBUG', foreground='gray')
        self.scrolled_text.tag_config('WARNING', foreground='orange')
        self.scrolled_text.tag_config('ERROR', foreground='red')
        self.scrolled_text.tag_config('CRITICAL', foreground='red', underline=1)
        # Create a logging handler using a queue
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s: %(message)s')
        self.queue_handler.setFormatter(formatter)
        logger.addHandler(self.queue_handler)
        # Start polling messages from the queue
        self.frame.after(100, self.poll_log_queue)

    def display(self, record):
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state='normal')
        self.scrolled_text.insert(tk.END, msg + '\n', record.levelname)
        self.scrolled_text.configure(state='disabled')
        # Autoscroll to the bottom
        self.scrolled_text.yview(tk.END)

    def poll_log_queue(self):
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.frame.after(100, self.poll_log_queue)

# Main GUI class
class ALDControlApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ALD Control")
        self.geometry("800x500")
        self.task = self.initialize_task()
        self.create_widgets()
        self.start_threads()

    def create_widgets(self):
        ## Frame 1 - Main power and heaters
        # Main Power Button
        controls_frame = tk.Frame(self, height=200, width=300)
        controls_frame.grid(row=0, column=0, padx=10, pady=10)

        self.main_power_button = ttk.Button(controls_frame, text="Main Power Off", command=lambda: self.toggle_main_power(mptask))
        self.main_power_button.grid(row=0, column=0, padx=10, pady=10)
        self.main_power_light = tk.Canvas(controls_frame, width=20, height=20, bg="red")
        self.main_power_light.grid(row=0, column=1, padx=10, pady=10)

        # Heater Buttons
        for i, name in enumerate(["h1", "h2", "h3"], start=1):
            label = ttk.Label(controls_frame, text=f"Heater {i} Duty Cycle:")
            label.grid(row=i, column=0, padx=10, pady=10)
            entry = ttk.Entry(controls_frame)
            entry.insert(0, 0)
            entry.grid(row=i, column=1, padx=10, pady=10)
            entry.bind("<Return>", lambda event, q=eval(f"{name}queue"), e=entry: self.update_duty_cycle(q, e, name))
            setattr(self, f"{name}_entry", entry)
            light = tk.Canvas(controls_frame, width=20, height=20, bg="red")
            light.grid(row=i, column=2, padx=10, pady=10)
            setattr(self, f"{name}_light", light)
            self.update_duty_cycle(eval(f"{name}queue"), entry, name)

        aldRunButton = tk.Button(controls_frame, text="ALD Cycle")

        # Manual control buttons
        manualcontrol_button = ttk.Button(controls_frame, text="Manual Control", command=lambda: self.createmanualcontrols())
        manualcontrol_button.grid(row=4, column=0, padx=10, pady=10)

        controls_frame.grid(row=0, column=0, padx=10, pady=10)

        ## Frame 2 Plot
        plot_frame = tk.Frame(self)
        plot_frame.grid(sticky="nsew")
        self.fig, self.ax, self.pressure, self.t_array, self.t_start, self.sensors = self.plotinitialize()
        ani = animation.FuncAnimation(self.fig, self.animate, interval=500)
        tempplot = FigureCanvasTkAgg(self.fig, plot_frame)
        tempplot.draw()
        tempplot.get_tk_widget().grid(row=0, column=5, rowspan=40, columnspan=30, padx=10, pady=10, sticky=tk.EW)
        toolbarFrame = tk.Frame(master=plot_frame)
        toolbarFrame.grid(row=41, column=5)
        NavigationToolbar2Tk(tempplot, toolbarFrame)

        ## Frame 4 Logging Console
        logging_frame = tk.Frame(self)
        logging_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.console = ConsoleUi(logging_frame)

    def createmanualcontrols(self):
        manualcontrols = tk.Toplevel(self)
        manualcontrols.title("Manual Controls")

        readTempButton = tk.Button(manualcontrols, text="Read Temperature", command=lambda: DummyLLE_ALD.readTemp())
        readTempButton.pack()
        setValveButton = tk.Button(manualcontrols, text="Set Valve", command=lambda: DummyLLE_ALD.setValve())
        setValveButton.pack()
        pulseValveButton = tk.Button(manualcontrols, text="Pulse Valve", command=lambda: DummyLLE_ALD.pulseValve())
        pulseValveButton.pack()
        closeValvesButton = tk.Button(manualcontrols, text="Close Valve", command=lambda: DummyLLE_ALD.closeValves())
        closeValvesButton.pack()
        readPressureButton = tk.Button(manualcontrols, text="Read Pressure", command=lambda: DummyLLE_ALD.readPressure())
        readPressureButton.pack()
        readPressure_pdr200 = tk.Button(manualcontrols, text="Read Pressure PDR200", command=lambda: DummyLLE_ALD.readPressure_pdr200())
        readPressure_pdr200.pack()

    def plotinitialize(self):
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
        task = DummyTask("Thermocouples")
        for channel_name in tempchannels:
            task.ai_channels().add_ai_thrmcpl_chan(
                f"cDaq1Mod1/{channel_name}", min_val=0.0, max_val=200.0,
                units="DEG_C", thermocouple_type="K",
                cjc_source="CONSTANT_USER_VALUE", cjc_val=20.0
            )
        task.ai_channels().add_ai_voltage_chan(channels["Pchannel"], min_val=0, max_val=5)
        task.start()
        return task

    def animate(self, i):
        try:
            data = self.task.read()
            logging.info(data)
            self.pressure.append(round(data[7] / 10, 5))
            self.t_array.append(time.time() - self.t_start)
            self.ax.clear()
            self.ax.plot(self.t_array, self.pressure)
            self.ax.set_ylim(0.4, .8)
            self.ax.set_yscale('log')
            self.ax.set_title("Press q to quit")
            self.ax.set_xlim(left=self.t_array[0], right=self.t_array[0] + 300)
            for j, sensor in enumerate(self.sensors[:-1]):
                self.ax.text(self.t_array[0] + 200, .6 + .03 * j, f"{sensor}, {str(data[j])[:5]}")
        except Exception as e:
            logging.error("Error during animation: %s", e)

    def toggle_main_power(self, mptask):
        if self.main_power_button.config('text')[-1] == 'Main Power ON':
            mptask.start()
            mptask.write(False)
            mptask.stop()
            self.main_power_button.config(text='Main Power OFF')
            self.main_power_light.config(bg="red")
            logging.info("Main Power OFF")
        else:
            mptask.start()
            mptask.write(True)
            mptask.stop()
            self.main_power_button.config(text='Main Power ON')
            self.main_power_light.config(bg="green")
            logging.info("Main Power ON")

    def update_duty_cycle(self, queue, duty, heater_name):
        try:
            duty_value = int(duty.get())
            if 0 <= duty_value <= 200:
                logging.info(f"Duty cycle for {heater_name} updated to {duty_value}")
                queue.put(duty_value)
            else:
                raise Exception()
        except:
            logging.error("Invalid Input. Please enter an integer between 0 and 200.")

    def start_threads(self):
        self.h1dutycycle = threading.Thread(target=duty_cycle, args=(stopthread, h1queue, h1task))
        self.h2dutycycle = threading.Thread(target=duty_cycle, args=(stopthread, h2queue, h2task))
        self.h3dutycycle = threading.Thread(target=duty_cycle, args=(stopthread, h3queue, h3task))
        self.h1dutycycle.start()
        self.h2dutycycle.start()
        self.h3dutycycle.start()

    def on_closing(self):
        stopthread.set()
        time.sleep(1)
        self.h1dutycycle.join()
        self.h2dutycycle.join()
        self.h3dutycycle.join()
        mptask.start()
        mptask.write(False)
        mptask.stop()
        mptask.close()
        self.task.close()
        plt.close(self.fig)
        self.destroy()

if __name__ == "__main__":
    aldgui = ALDControlApp()
    aldgui.protocol("WM_DELETE_WINDOW", aldgui.on_closing)
    aldgui.mainloop()