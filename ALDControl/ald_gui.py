import tkinter as tk
from tkinter import filedialog
import csv
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
from collections import deque

import nidaqmx
from nidaqmx.constants import (
    AcquisitionType,
    CJCSource,
    TemperatureUnits,
    ThermocoupleType,
    LineGrouping
)
import logging

import random, threading, time


from valve_controller import valve_controller
from temp_controller import temp_controller
from pressure_controller import pressure_controller
from ald_controller import ald_controller

# Constants
BG_COLOR = "grey95"
TEXT_COLOR = "white"
ON_COLOR = "green"
OFF_COLOR = "red"
BUTTON_STYLE = "raised"
BUTTON_TEXT_COLOR = "white"
BORDER_COLOR = "black"
FONT = ("Helvetica", 16)

#Pressure plot default y min and max
Y_MIN_DEFAULT = 0.4
Y_MAX_DEFAULT = 0.8

MAIN_POWER_CHANNEL = "CDAQ1Mod4/line11"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tkinter Application")
        self.geometry("800x600")
        self.configure(bg=BG_COLOR)

        # Initialize valve_controller
        self.valve_controller = valve_controller()
        self.temp_controller = temp_controller()
        self.pressure_controller = pressure_controller()
        self.ald_controller=ald_controller()


        # Top pane with "Main Power" button
        top_pane = tk.PanedWindow(self, orient=tk.VERTICAL, bg=BG_COLOR, bd=0, sashwidth=5, sashpad=2)
        top_pane.pack(fill=tk.BOTH, expand=True)
        
        self.mptask = self.create_main_power()
        
        top_frame = tk.Frame(top_pane, bg=BG_COLOR, height=50, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.main_power_button = tk.Button(top_frame, text='Main Power OFF',fg=BUTTON_TEXT_COLOR, bg=OFF_COLOR, relief=BUTTON_STYLE, command=lambda:self.toggle_main_power(self.mptask))
        self.main_power_button.pack(pady=10)
        top_pane.add(top_frame)

        # Main content area
        main_pane = tk.PanedWindow(top_pane, orient=tk.VERTICAL, bg=BG_COLOR, bd=0, sashwidth=5)
        main_pane.grid_rowconfigure(0, weight=1)
        main_pane.grid_columnconfigure(0, weight=1)
        top_pane.add(main_pane)
        
        # Horizontal PanedWindow
        horizontal_pane = tk.PanedWindow(main_pane, orient=tk.HORIZONTAL, bg=BG_COLOR, bd=0, sashwidth=5)
        main_pane.add(horizontal_pane)
        horizontal_pane.add(self.create_plot_panel("Left Panel Plot"))
        horizontal_pane.add(self.create_number_display_panel())
        horizontal_pane.grid_rowconfigure(0, weight=1)
        horizontal_pane.grid_columnconfigure(0, weight=1)
        horizontal_pane.grid_columnconfigure(1, weight=1)

        # Bottom pane
        bottom_pane = tk.PanedWindow(main_pane, orient=tk.HORIZONTAL, bg=BG_COLOR, bd=0, sashwidth=5)
        main_pane.add(bottom_pane)
        self.file_panel = tk.Frame(bottom_pane, bg=BG_COLOR, width=200, highlightbackground=BORDER_COLOR, highlightthickness=1)
        bottom_pane.add(self.file_panel)
        self.csv_panel = tk.Frame(bottom_pane, bg=TEXT_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        bottom_pane.add(self.csv_panel)
        self.create_file_controls()

        self.ald_panel = tk.Frame(bottom_pane, bg=TEXT_COLOR, highlightbackground=BORDER_COLOR,highlightthickness=1)
        self.create_ald_panel()
    
    def create_ald_panel(self):
        tk.Button(self.ald_panel, text="Run Recipe",font=FONT, bg=TEXT_COLOR, relief=BUTTON_STYLE, command=lambda:self.ald_controller.aldRun(100,self.valve_controller)).pack(pady=5, anchor=tk.NW)
        
    def create_number_display_panel(self):
        frame = tk.Frame(bg=BG_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        d1 = tk.StringVar()
        d2 = tk.StringVar()
        d3 = tk.StringVar()
        d = [d1, d2, d3]
        b1 = tk.Button()
        b2 = tk.Button()
        b3 = tk.Button()
        self.heater_buttons= ["","",""]
        
        for i in range(3):
            d[i].set(0)
            row = tk.Frame(frame, bg=BG_COLOR, pady=10)
            row.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(row, text=f"Heater {i+1}:", bg=BG_COLOR, font=FONT).pack(side=tk.LEFT, padx=5)
            tk.Entry(row, width=10, font=FONT, textvariable=d[i]).pack(side=tk.LEFT, padx=5)
            
            # Create the button and assign it to self.heater_buttons[i]
            button = tk.Button(row, text="Set", font=FONT, bg=OFF_COLOR,fg=BUTTON_TEXT_COLOR, relief=BUTTON_STYLE, 
                                command=lambda i=i: self.set_duty_value(i, self.temp_controller.queues[i], d[i]))
            button.pack(side=tk.LEFT, padx=5)  # Pack the button
            self.heater_buttons[i] = button  # Assign the button to the list
            
        return frame
       
    def set_duty_value(self,i,t,d):
        self.temp_controller.update_duty_cycle(t,d)
        if int(d.get()) == 0:
            print(d.get())
            self.heater_buttons[i].config(bg=OFF_COLOR)
        else: 
            self.heater_buttons[i].config(bg=ON_COLOR)

    def create_plot_panel(self, title):
        self.task = self.temp_controller.thermocoupletask
        frame = tk.Frame(bg=TEXT_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.fig, self.ax, self.pressure, self.t_array, self.t_start, self.sensors = self.plotinitialize()
        ani = animation.FuncAnimation(self.fig, self.animate, interval=500)
        tempplot = FigureCanvasTkAgg(self.fig, frame)
        tempplot.draw()
        tempplot.get_tk_widget().grid(row=0, column=0, rowspan=40, columnspan=30, padx=10, pady=10, sticky=tk.NSEW)
        
        # Add toolbar below the plot
        toolbarFrame = tk.Frame(master=frame)
        toolbarFrame.grid(row=41, column=0, columnspan=30, pady=5)
        NavigationToolbar2Tk(tempplot, toolbarFrame)

        # Initialize y-min and y-max variables
        self.ymin = tk.StringVar()
        self.ymin.set(Y_MIN_DEFAULT)
        self.ymax = tk.StringVar()
        self.ymax.set(Y_MAX_DEFAULT)

        # Dynamically determine the next row and columnspan
        next_row = frame.grid_size()[1]  # Get the next available row
        columnspan = frame.grid_size()[0]  # Get the total number of columns

        # Create row for y-min and y-max inputs
        row = tk.Frame(frame, bg=TEXT_COLOR, pady=10)
        row.grid(row=next_row, column=0, columnspan=columnspan, pady=10)  # Place the row dynamically

        # Add y-min and y-max labels and entry widgets
        tk.Label(row, text="y-min:", relief=BUTTON_STYLE, bg=BG_COLOR, font=FONT).pack(side=tk.LEFT, padx=5)
        tk.Entry(row, width=10, textvariable=self.ymin, font=FONT).pack(side=tk.LEFT, padx=5)
        tk.Label(row, text="y-max:", relief=BUTTON_STYLE, bg=BG_COLOR, font=FONT).pack(side=tk.LEFT, padx=5)
        tk.Entry(row, width=10, textvariable=self.ymax, font=FONT).pack(side=tk.LEFT, padx=5)

        return frame

    def plotinitialize(self):
        plt.rcParams["figure.figsize"] = [13.00, 6.50]
        plt.rcParams["figure.autolayout"] = True
        plt.rcParams['font.size'] = 14
        fig, ax = plt.subplots()
        pressure = deque([0.1], maxlen=200)
        t_start = time.time()
        t_array = deque([0], maxlen=200)
        sensors = ["main reactor", "inlet lower", "inlet upper", "exhaust", "TMA", "Trap", "Gauges", "Pressure"]
        return fig, ax, pressure, t_array, t_start, sensors

    def animate(self, i):
        try:
            # Read data from controllers
            tempdata = self.temp_controller.read_thermocouples()
            pressuredata = self.pressure_controller.read_pressure()
            logging.info([tempdata, pressuredata])

            # Update pressure and time arrays
            self.pressure.append(round(pressuredata / 10, 5))
            self.t_array.append(time.time() - self.t_start)

            # Clear and update the plot
            self.ax.clear()
            self.ax.plot(self.t_array, self.pressure)

            # Set y-axis limits and scale
            ymin = float(self.ymin.get())
            ymax = float(self.ymax.get())
            self.ax.set_ylim(ymin, ymax)
            self.ax.set_yscale('log')

            # Set plot title and x-axis limits
            self.ax.set_title("Press q to quit")
            self.ax.set_xlim(left=self.t_array[0], right=self.t_array[0] + 300)

            # Dynamically position text annotations based on log scale
            for j, sensor in enumerate(self.sensors[:-1]):
                # Calculate y-position for text annotations
                y_position = ymin * (ymax / ymin) ** (0.6 + 0.05 * j)  # Scale based on log range
                self.ax.text(self.t_array[0] + 250, y_position, f"{sensor}, {str(tempdata[j])[:5]}")
            self.fig.tight_layout()
        except Exception as e:
            logging.error("Error during animation: %s", e)

    def create_file_controls(self):
        tk.Button(self.file_panel, text="Load File",font=FONT, bg=TEXT_COLOR, relief=BUTTON_STYLE, command=self.load_file).pack(pady=5, anchor=tk.NW)
        self.file_label = tk.Label(self.file_panel, text="", bg=BG_COLOR, font=FONT)
        self.file_label.pack(pady=5, anchor=tk.NW)
        
        # Add Manual Control Button
        tk.Button(self.file_panel, text="Manual Control",font=FONT, bg=TEXT_COLOR, relief=BUTTON_STYLE, command=self.open_manual_control).pack(pady=5, anchor=tk.NW)

    def create_main_power(self):
        task = nidaqmx.Task("Main Power")
        task.do_channels.add_do_chan(MAIN_POWER_CHANNEL, line_grouping=LineGrouping.CHAN_PER_LINE)
        task.start()
        task.write(False)
        task.stop()
        return task

    def toggle_main_power(self,task):
        if self.main_power_button.config('text')[-1] == 'Main Power ON':
            task.start()
            task.write(False)
            task.stop()
            self.main_power_button.config(text='Main Power OFF',bg="red")
        else:
            task.start()
            task.write(True)
            task.stop()
            self.main_power_button.config(text='Main Power ON',bg=ON_COLOR)

    def open_manual_control(self):
        manual_control_window = tk.Toplevel(self)
        manual_control_window.title("Manual Control")
        manual_control_window.geometry("400x300")
        manual_control_window.configure(bg=BG_COLOR)

        for valve_name, task in zip(self.valve_controller.valvechannels.keys(), self.valve_controller.tasks):
            frame = tk.Frame(manual_control_window, bg=BG_COLOR, pady=10)
            frame.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(frame, text=valve_name, bg=BG_COLOR, font=FONT).pack(side=tk.LEFT, padx=5)
            tk.Button(frame, text="Open",font=FONT, bg=TEXT_COLOR, relief=BUTTON_STYLE, command=lambda t=task: self.valve_controller.open_valve(t)).pack(side=tk.LEFT, padx=5)
            tk.Button(frame, text="Close",font=FONT, bg=TEXT_COLOR, relief=BUTTON_STYLE, command=lambda t=task: self.valve_controller.close_valve(t)).pack(side=tk.LEFT, padx=5)
            tk.Button(frame, text="Pulse",font=FONT, bg=TEXT_COLOR, relief=BUTTON_STYLE, command=lambda t=task: self.valve_controller.pulse_valve(t, 1)).pack(side=tk.LEFT, padx=5)

    def load_file(self):
        file_path = filedialog.askopenfilename(title="Select a File", filetypes=[("CSV Files", "*.csv")])
        if file_path:
            self.file_label.config(text=f"Loaded: {file_path.split('/')[-1]}")
            self.display_csv(file_path)
        self.ald_controller.file = file_path.split('/')[-1]

    def display_csv(self, file_path):
        for widget in self.csv_panel.winfo_children():
            widget.destroy()
        text_widget = tk.Text(self.csv_panel, wrap=tk.NONE, bg=TEXT_COLOR, height=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    text_widget.insert(tk.END, "\t".join(row) + "\n")
        except Exception as e:
            text_widget.insert(tk.END, f"Error reading file: {e}")

    def on_closing(self):
        print("GUI closing")
        plt.close(self.fig)
        self.temp_controller.close()
        self.pressure_controller.close()
        self.valve_controller.close()
        self.ald_controller.close()
        
        self.mptask.write(False)
        self.mptask.close()
        
        self.destroy()
        print("Program Closed")



if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)

    app.mainloop()
