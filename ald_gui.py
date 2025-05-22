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

# Constants
BG_COLOR = "grey95"
TEXT_COLOR = "white"
BORDER_COLOR = "black"
FONT = ("Arial", 14)

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

        # Top pane with "Main Power" button
        top_pane = tk.PanedWindow(self, orient=tk.VERTICAL, bg=BG_COLOR, bd=0, sashwidth=5, sashpad=2)
        top_pane.pack(fill=tk.BOTH, expand=True)

        top_frame = tk.Frame(top_pane, bg=BG_COLOR, height=50, highlightbackground=BORDER_COLOR, highlightthickness=1)
        tk.Button(top_frame, text="Main Power", bg=TEXT_COLOR, relief="flat").pack(pady=10)
        top_pane.add(top_frame)

        # Main content area
        main_pane = tk.PanedWindow(top_pane, orient=tk.VERTICAL, bg=BG_COLOR, bd=0, sashwidth=5)
        top_pane.add(main_pane)

        # Horizontal PanedWindow
        horizontal_pane = tk.PanedWindow(main_pane, orient=tk.HORIZONTAL, bg=BG_COLOR, bd=0, sashwidth=5)
        main_pane.add(horizontal_pane)
        horizontal_pane.add(self.create_plot_panel("Left Panel Plot"))
        horizontal_pane.add(self.create_number_display_panel())

        # Bottom pane
        bottom_pane = tk.PanedWindow(main_pane, orient=tk.HORIZONTAL, bg=BG_COLOR, bd=0, sashwidth=5)
        main_pane.add(bottom_pane)
        self.file_panel = tk.Frame(bottom_pane, bg=BG_COLOR, width=200, highlightbackground=BORDER_COLOR, highlightthickness=1)
        bottom_pane.add(self.file_panel)
        self.csv_panel = tk.Frame(bottom_pane, bg=TEXT_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        bottom_pane.add(self.csv_panel)
        self.create_file_controls()

    def create_number_display_panel(self):
        frame = tk.Frame(bg=BG_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        for _ in range(3):
            row = tk.Frame(frame, bg=BG_COLOR, pady=10)
            row.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(row, text="Set Value:", bg=BG_COLOR, font=FONT).pack(side=tk.LEFT, padx=5)
            tk.Entry(row, width=10).pack(side=tk.LEFT, padx=5)
            tk.Button(row, text="Set", bg=TEXT_COLOR, relief="flat").pack(side=tk.LEFT, padx=5)
            number_label = tk.Label(row, text="0", font=("Arial", 24), bg=BG_COLOR)
            number_label.pack(side=tk.LEFT, padx=10)
            #threading.Thread(target=self.update_number, args=(number_label,), daemon=True).start()
        return frame

    def update_number(self, label):
        while True:
            label.config(text=str(random.randint(0, 100)))
            time.sleep(1)

    def create_plot_panel(self, title):
        self.task = self.temp_controller.thermocoupletask
        frame = tk.Frame(bg=TEXT_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.fig, self.ax, self.pressure, self.t_array, self.t_start, self.sensors = self.plotinitialize()
        ani = animation.FuncAnimation(self.fig, self.animate, interval=500)
        tempplot = FigureCanvasTkAgg(self.fig, frame)
        tempplot.draw()
        tempplot.get_tk_widget().grid(row=0, column=5, rowspan=40, columnspan=30, padx=10, pady=10, sticky=tk.EW)
        toolbarFrame = tk.Frame(master=frame)
        toolbarFrame.grid(row=41, column=5)
        NavigationToolbar2Tk(tempplot, toolbarFrame)
        return frame

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
            tempdata = self.temp_controller.read_thermocouples()
            pressuredata = self.pressure_controller.read_pressure()
            logging.info([tempdata,pressuredata])
            self.pressure.append(round(pressuredata / 10, 5))
            self.t_array.append(time.time() - self.t_start)
            self.ax.clear()
            self.ax.plot(self.t_array, self.pressure)
            self.ax.set_ylim(0.4, .8)
            self.ax.set_yscale('log')
            self.ax.set_title("Press q to quit")
            self.ax.set_xlim(left=self.t_array[0], right=self.t_array[0] + 300)
            for j, sensor in enumerate(self.sensors[:-1]):
                self.ax.text(self.t_array[0] + 200, .6 + .03 * j, f"{sensor}, {str(tempdata[j])[:5]}")
        except Exception as e:
            logging.error("Error during animation: %s", e)

    def create_file_controls(self):
        tk.Button(self.file_panel, text="Load File", bg=TEXT_COLOR, relief="flat", command=self.load_file).pack(pady=5, anchor=tk.NW)
        self.file_label = tk.Label(self.file_panel, text="", bg=BG_COLOR, font=FONT)
        self.file_label.pack(pady=5, anchor=tk.NW)
        
        # Add Manual Control Button
        tk.Button(self.file_panel, text="Manual Control", bg=TEXT_COLOR, relief="flat", command=self.open_manual_control).pack(pady=5, anchor=tk.NW)

    def open_manual_control(self):
        manual_control_window = tk.Toplevel(self)
        manual_control_window.title("Manual Control")
        manual_control_window.geometry("400x300")
        manual_control_window.configure(bg=BG_COLOR)

        for valve_name, task in zip(self.valve_controller.valvechannels.keys(), self.valve_controller.tasks):
            frame = tk.Frame(manual_control_window, bg=BG_COLOR, pady=10)
            frame.pack(fill=tk.X, padx=10, pady=5)
            tk.Label(frame, text=valve_name, bg=BG_COLOR, font=FONT).pack(side=tk.LEFT, padx=5)
            tk.Button(frame, text="Open", bg=TEXT_COLOR, relief="flat", command=lambda t=task: self.valve_controller.open_valve(t)).pack(side=tk.LEFT, padx=5)
            tk.Button(frame, text="Close", bg=TEXT_COLOR, relief="flat", command=lambda t=task: self.valve_controller.close_valve(t)).pack(side=tk.LEFT, padx=5)
            tk.Button(frame, text="Pulse", bg=TEXT_COLOR, relief="flat", command=lambda t=task: self.valve_controller.pulse_valve(t, 1)).pack(side=tk.LEFT, padx=5)

    def load_file(self):
        file_path = filedialog.askopenfilename(title="Select a File", filetypes=[("CSV Files", "*.csv")])
        if file_path:
            self.file_label.config(text=f"Loaded: {file_path.split('/')[-1]}")
            self.display_csv(file_path)

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
        self.valve_controller.close()
        self.temp_controller.close()
        self.pressure_controller.close()
        plt.close(self.fig)
        self.destroy()



if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)

    app.mainloop()