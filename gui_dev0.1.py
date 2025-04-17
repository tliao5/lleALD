import datetime
import queue
import logging
import time
import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk, VERTICAL, HORIZONTAL, N, S, E, W
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
import tkinter as tk
import nidaqmx
from nidaqmx.constants import LineGrouping
import LLE_ALD_pythonlib

logger = logging.getLogger(__name__)

class QueueHandler(logging.Handler):
    """Class to send logging records to a queue

    It can be used from different threads
    The ConsoleUi class polls this queue to display records in a ScrolledText widget
    """
    # Example from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    # (https://stackoverflow.com/questions/13318742/python-logging-to-tkinter-text-widget) is not thread safe!
    # See https://stackoverflow.com/questions/43909849/tkinter-python-crashes-on-new-thread-trying-to-log-on-main-thread

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)


class ConsoleUi:
    """Poll messages from a logging queue and display them in a scrolled text widget"""

    def __init__(self, frame):
        self.frame = frame
        # Create a ScrolledText wdiget
        self.scrolled_text = ScrolledText(frame, state='disabled', height=12)
        self.scrolled_text.grid(row=0, column=0, sticky=(N, S, W, E))
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

class ControlPanelUi:

    def __init__(self, frame):
        self.frame = frame

        self.main_power_button = ttk.Button(self.frame, text="Main Power Off", command=lambda: self.toggle_main_power(tasks["mptask"]))
        self.main_power_button.grid(row=0, column=0, padx=10, pady=10)
        self.main_power_light = tk.Canvas(self.frame, width=20, height=20, bg="red")
        self.main_power_light.grid(row=0, column=1, padx=10, pady=10)

        # Heater Buttons
        for i, name in enumerate(["h1", "h2", "h3"], start=1):
            label = ttk.Label(self.frame, text=f"Heater {i} Duty Cycle:")
            label.grid(row=i, column=0, padx=10, pady=10)
            entry = ttk.Entry(self.frame)
            entry.insert(0, 0)
            entry.grid(row=i, column=1, padx=10, pady=10)
            entry.bind("<Return>", lambda event, q=queues[f"{name}queue"], e=entry: self.update_duty_cycle(q, e))
            setattr(self, f"{name}_entry", entry)
            light = tk.Canvas(self.frame, width=20, height=20, bg="red")
            light.grid(row=i, column=2, padx=10, pady=10)
            setattr(self, f"{name}_light", light)

        manualcontrol_button = ttk.Button(self.frame, text="Manual Control", command=lambda: self.manualcontrol())

        self.start_threads

    def manualcontrol():
        #Creates a pop up window to do manual controls
        while True:
            i = input("what would you like to do? (manualcontrol, runprogram, exit):  ")
            if i == "exit":
                print("goodbye")
                break
            elif i == "manualcontrol":
                print("you are now in manual conrol.")
                while True:
                    manualinput = input("You can now call any function in the library (setValve, closeValves, pulseValve, getP). Type 'done' when done.")
                    if manualinput == 'done':
                        break
                    elif manualinput == 'setValve':
                        addr = input('enter relay number: ')
                        state = input('enter state (True or False): ')
                        if state == 'True':
                            state = True
                        elif state == 'False':
                            state = False
                        else:
                            state = False
                        aldGO.setValve(addr,state)
                    elif manualinput =='closeValves':
                        aldGO.closeValves()
                    elif manualinput =='pulseValve':
                        addr = input('enter relay number: ')
                        pulseW = int(input('how long do you want the valve open? '))
                        aldGO.pulseValve(addr, pulseW)
                    elif manualinput == 'getP':
                        print(aldGO.readPressure())
                        
            elif i == "runprogram":
                file = aldGO.fileInput()
                loops = int(input("how many times you wanna run through this thing?"))
                print("here we go!")
                aldGO.aldRun(file,loops)
            else:
                print("Umm, what? Please try again.")    
        

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
        
    def start_threads(self):
        self.h1dutycycle = threading.Thread(target=self.duty_cycle, args=(stopthread, h1queue, h1task))
        self.h2dutycycle = threading.Thread(target=self.duty_cycle, args=(stopthread, h2queue, h2task))
        self.h3dutycycle = threading.Thread(target=self.duty_cycle, args=(stopthread, h3queue, h3task))
        self.h1dutycycle.start()
        self.h2dutycycle.start()
        self.h3dutycycle.start()

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

    def on_closing(self):
        stopthread.set()
        time.sleep(1)
        self.h1dutycycle.join()
        self.h2dutycycle.join()
        self.h3dutycycle.join()


class PlotUi:
    def __init__(self, frame):
        self.frame = frame
        self.frame.grid(sticky="nsew")
        self.fig, self.ax, self.pressure, self.t_array, self.t_start, self.sensors = self.plotinitialize()
        ani = animation.FuncAnimation(self.fig, self.animate, interval=500)
        tempplot = FigureCanvasTkAgg(self.fig, self.frame)
        tempplot.draw()
        tempplot.get_tk_widget().grid(row=0, column=5, rowspan=40, columnspan=30, padx=10, pady=10, sticky=tk.EW)
        toolbarFrame = tk.Frame(master=self.frame)
        toolbarFrame.grid(row=41, column=5)
        NavigationToolbar2Tk(tempplot, toolbarFrame)

    def plotinitialize(self):
        plt.rcParams["figure.figsize"] = [13.00, 6.50]
        plt.rcParams["figure.autolayout"] = True
        fig, ax = plt.subplots()
        pressure = deque([0.1], maxlen=200)
        t_start = time.time()
        t_array = deque([0], maxlen=200)
        sensors = ["main reactor", "inlet lower", "inlet upper", "exhaust", "TMA", "Trap", "Gauges", "Pressure"]
        return fig, ax, pressure, t_array, t_start, sensors

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

    def on_closing(self):
        self.task.close()
        plt.close(self.fig)
        self.destroy()

class ALDControlApp(tk.Tk):
    def __init__(self):
        self.title("ALD Control")
        self.geometry("800x500")
        self.task = self.initialize_task()
        self.create_widgets()
    
    def initialize_task(self):
        logging.info("Starting a new run")
        logging.info("main reactor,inlet lower, inlet upper, exhaust,TMA,Trap,Gauges,Pressure")
        tempchannels = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6"]
        task = nidaqmx.Task()
        for channel_name in tempchannels:
            task.ai_channels().add_ai_thrmcpl_chan(
                f"cDaq1Mod1/{channel_name}", min_val=0.0, max_val=200.0,
                units="DEG_C", thermocouple_type="K",
                cjc_source="CONSTANT_USER_VALUE", cjc_val=20.0
            )
        task.ai_channels().add_ai_voltage_chan(channels["Pchannel"], min_val=0, max_val=5)
        task.start()
        return task

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        # Create the panes and frames
        vertical_pane = ttk.PanedWindow(self.root, orient=VERTICAL)
        vertical_pane.grid(row=0, column=0, sticky="nsew")
        horizontal_pane = ttk.PanedWindow(vertical_pane, orient=HORIZONTAL)
        vertical_pane.add(horizontal_pane)
        controlpanel_frame = ttk.Labelframe(horizontal_pane, text="Control Panel")
        controlpanel_frame.columnconfigure(1, weight=1)
        horizontal_pane.add(controlpanel_frame, weight=1)
        console_frame = ttk.Labelframe(horizontal_pane, text="Console")
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        horizontal_pane.add(console_frame, weight=1)
        plot_frame = ttk.Labelframe(vertical_pane, text="Plot")
        vertical_pane.add(plot_frame, weight=1)
        # Initialize all frames
        self.control = ControlPanelUi(controlpanel_frame)
        self.console = ConsoleUi(console_frame)
        self.plot = PlotUi(plot_frame)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        mptask.start()
        mptask.write(False)
        mptask.stop()
        mptask.close()
        self.task.close()
        plt.close(self.fig)
        self.destroy()

if __name__ == '__main__':
    # DAQ Channels and Tasks
    channels = {
        "Pchannel": "cDAQ1Mod2/ai2", # pressure reading
        "mpchannel": "CDAQ1Mod4/line11", # main power
        "h1channel": "CDAQ1Mod4/port0/line5", # heater 1
        "h2channel": "CDAQ1Mod4/port0/line6", # heater 2
        "h3channel": "CDAQ1Mod4/port0/line7" # heater 3
    }

    # declare Tasks
    Ptask = nidaqmx.Task()
    mptask = nidaqmx.Task()
    h1task = nidaqmx.Task()
    h2task = nidaqmx.Task()
    h3task = nidaqmx.Task()

    # Main Power on
    mptask.do_channels().add_do_chan(channels["mpchannel"], line_grouping=LineGrouping.CHAN_PER_LINE)
    mptask.start()
    mptask.write(True)
    mptask.stop()

    # Initialize heater tasks
    h1task.do_channels().add_do_chan(channels["h1channel"], line_grouping=LineGrouping.CHAN_PER_LINE)
    h1task.start()
    h2task.do_channels().add_do_chan(channels["h2channel"], line_grouping=LineGrouping.CHAN_PER_LINE)
    h2task.start()
    h3task.do_channels().add_do_chan(channels["h3channel"], line_grouping=LineGrouping.CHAN_PER_LINE)
    h3task.start()

    # Create Duty Cycle threads
    stopthread = threading.Event()
    h1queue = queue.Queue()
    h2queue = queue.Queue()
    h3queue = queue.Queue()

    logging.basicConfig(filename=r'D:\LLE\testing\test.log', level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%m/%d/%Y %H:%M:%S %p",force=True)
    app = ALDControlApp()
    app.mainloop()
