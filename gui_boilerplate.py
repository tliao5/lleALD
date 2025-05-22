import tkinter as tk
from tkinter import filedialog
import csv
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random, threading, time

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
        horizontal_pane.add(self.create_plot_panel("Pressure"))
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
            threading.Thread(target=self.update_number, args=(number_label,), daemon=True).start()
        return frame

    def update_number(self, label):
        while True:
            label.config(text=str(random.randint(0, 100)))
            time.sleep(1)

    def create_plot_panel(self, title):
        frame = tk.Frame(bg=TEXT_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        fig = Figure(figsize=(5, 2), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot([0, 1, 2, 3], [3, 2, 1, 0])
        ax.set_title(title)
        FigureCanvasTkAgg(fig, frame).get_tk_widget().pack(fill=tk.BOTH, expand=True)
        return frame

    def create_file_controls(self):
        tk.Button(self.file_panel, text="Load File", bg=TEXT_COLOR, relief="flat", command=self.load_file).pack(pady=5,anchor=tk.NW)
        self.file_label = tk.Label(self.file_panel, text="", bg=BG_COLOR, font=FONT)
        self.file_label.pack(pady=5,anchor=tk.NW)

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

if __name__ == "__main__":
    app = App()
    app.mainloop()