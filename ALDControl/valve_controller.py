import nidaqmx
from nidaqmx.constants import LineGrouping
import time
import threading

# creating a valve_controller object will setup all relevant channels
# access said object in order to run methods on the valves connected to channels defined below

# currently hard coded for the three valves of this ALD system
class valve_controller:
    def __init__(self):
        self.valvechannels = { "AV01": "cDAQ1Mod4/line0", # TMA
                               "AV02": "CDAQ1Mod4/line1", # D20
                               "AV03": "CDAQ1Mod4/line2", # H20
                             }
        self.tasks = self.create_valve_tasks()
        # log valve controller initialized
        
    def create_valve_tasks(self):
        AV01 = nidaqmx.Task("AV01")
        AV02 = nidaqmx.Task("AV02")
        AV03 = nidaqmx.Task("AV03")
        AV01.do_channels.add_do_chan(self.valvechannels["AV01"], line_grouping=LineGrouping.CHAN_PER_LINE)
        AV02.do_channels.add_do_chan(self.valvechannels["AV02"], line_grouping=LineGrouping.CHAN_PER_LINE)
        AV03.do_channels.add_do_chan(self.valvechannels["AV03"], line_grouping=LineGrouping.CHAN_PER_LINE)
        return [AV01, AV02, AV03]

        
    def open_valve(self,task):
        task.start()
        task.write(True)
        time.sleep(0.1)
        #log valve opened
        task.stop()
        
    def close_valve(self,task):
        task.start()
        task.write(False)
        time.sleep(0.1)
        #log valve closed
        task.stop()

    def pulse_valve(self,task,pulse_length):
        task.start()
        task.write(True)
        time.sleep(pulse_length)
        task.write(False)
        #log valve pulsed
        task.stop()

    def close_all(self):
        for task in self.tasks[::]:
            task.start()
            task.write(False)
            task.stop()
        #log valves closed

    def close(self):
        self.close_all()
        for task in self.tasks[::]: task.close()
        print("Valve Controller Tasks Closing")
