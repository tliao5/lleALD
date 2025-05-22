import nidaqmx
from nidaqmx.constants import LineGrouping
import time

# creating a valve_controller object will setup all relevant channels
# access said object in order to run methods on the valves connected to channels defined below

# currently hard coded for the three valves of this ALD system
class valve_controller:
    def __init__(self):
        self.valvechannels = { "AV01": "cDAQ1Mod4/line0", # TMA
                               "AV02": "CDAQ1Mod4/line1", # D20
                               "AV03": "CDAQ1Mod4/line2", # H20
                             }
        self.create_valve_tasks()
                
        # log valve controller initialized
        
    def create_valve_tasks(self):
        self.AV01 = nidaqmx.Task()
        self.AV02 = nidaqmx.Task()
        self.AV03 = nidaqmx.Task()

        self.tasks = [self.AV01, self.AV02, self.AV03]

        self.AV01.do_channels.add_do_chan(self.valvechannels["AV01"], line_grouping=LineGrouping.CHAN_PER_LINE)
        self.AV02.do_channels.add_do_chan(self.valvechannels["AV02"], line_grouping=LineGrouping.CHAN_PER_LINE)
        self.AV03.do_channels.add_do_chan(self.valvechannels["AV03"], line_grouping=LineGrouping.CHAN_PER_LINE)
        
    def open_valve(self,task):
        task.start()
        self.task.write(True)
        time.sleep(0.1)
        #log valve opened
        task.stop()
        
    def close_valve(self,task):
        task.start()
        self.task.write(False)
        time.sleep(0.1)
        #log valve closed
        task.stop()

    def pulse_valve(self,task,pulse_length):
        task.start()
        self.task.write(True)
        time.sleep(pulse_length)
        self.task.write(False)
        #log valve pulsed
        task.stop()

    def close_all(self):
        self.AV01.start()
        self.AV02.start()
        self.AV03.start()
        
        self.AV01.write(False)
        self.AV02.write(False)
        self.AV03.write(False)
        #log valves closed

        self.AV01.stop()
        self.AV02.stop()
        self.AV03.stop()

    def close(self):
        self.close_all()

        self.AV01.close()
        self.AV02.close()
        self.AV03.close()
        print("Valve Controller Tasks Closing")
