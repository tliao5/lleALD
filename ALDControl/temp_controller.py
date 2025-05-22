import nidaqmx
from nidaqmx.constants import (
    AcquisitionType,
    CJCSource,
    TemperatureUnits,
    ThermocoupleType,
    LineGrouping
)
import queue
import logging
import time
import threading

class temp_controller:
    def __init__(self):
        # log temperature controller intialized
        print("Temperature Controller Initializing")

        #removed pressure reading
        '''
        self.channels = { "Pchannel": "cDAQ1Mod2/ai2", # pressure reading
                          "h1channel": "CDAQ1Mod4/port0/line5", # heater 1
                          "h2channel": "CDAQ1Mod4/port0/line6", # heater 2
                          "h3channel": "CDAQ1Mod4/port0/line7"} # heater 3
        '''
        self.channels = { "h1channel": "CDAQ1Mod4/port0/line5", # heater 1
                          "h2channel": "CDAQ1Mod4/port0/line6", # heater 2
                          "h3channel": "CDAQ1Mod4/port0/line7"} # heater 3
        self.tempchannels = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6"]

        self.tps = 200 # ticks per second for duty cycles

        self.create_heater_queue()
        self.create_heater_tasks()
        self.start_threads()
        self.thermocoupletask = self.create_thermocouple_tasks()

    def create_heater_queue(self):
        self.h1queue = queue.Queue()
        self.h2queue = queue.Queue()
        self.h3queue = queue.Queue()

    def create_heater_tasks(self):
        self.h1task = nidaqmx.Task("Heater 1")
        self.h2task = nidaqmx.Task("Heater 2")
        self.h3task = nidaqmx.Task("Heater 3")

        self.h1task.do_channels.add_do_chan(self.channels["h1channel"], line_grouping=LineGrouping.CHAN_PER_LINE)
        self.h2task.do_channels.add_do_chan(self.channels["h2channel"], line_grouping=LineGrouping.CHAN_PER_LINE)
        self.h3task.do_channels.add_do_chan(self.channels["h3channel"], line_grouping=LineGrouping.CHAN_PER_LINE)

    def start_threads(self):
        # Create Duty Cycle threads
        self.stopthread = threading.Event()

        self.h1dutycycle = threading.Thread(target=self.duty_cycle, args=(self.stopthread, self.h1queue, self.h1task, self.tps))
        self.h2dutycycle = threading.Thread(target=self.duty_cycle, args=(self.stopthread, self.h2queue, self.h2task, self.tps))
        self.h3dutycycle = threading.Thread(target=self.duty_cycle, args=(self.stopthread, self.h3queue, self.h3task, self.tps))
        self.h1dutycycle.start()
        self.h2dutycycle.start()
        self.h3dutycycle.start()
    
    def create_thermocouple_tasks(self):
        logging.info("main reactor,inlet lower, inlet upper, exhaust,TMA,Trap,Gauges")
        #logging.info("main reactor,inlet lower, inlet upper, exhaust,TMA,Trap,Gauges,Pressure")
        tempchannels = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5", "ai6"]
        task = nidaqmx.Task("Thermocouple")
        for channel_name in tempchannels:
            task.ai_channels.add_ai_thrmcpl_chan(
                f"cDaq1Mod1/{channel_name}", min_val=0.0, max_val=200.0,
                units=TemperatureUnits.DEG_C, thermocouple_type=ThermocoupleType.K,
                cjc_source=CJCSource.CONSTANT_USER_VALUE, cjc_val=20.0
            )
        task.start()
        return task
    
    def read_thermocouples(self):
        return self.thermocoupletask.read()

    #def log_temps

    def duty_cycle(self,stopthread, duty_queue, task, tps):
        task.start()
        voltageold = False # default voltage state
        duty_queue.put(0) # default duty
        while not stopthread.is_set(): # loop until tc.stopthread.set()
            if not duty_queue.empty(): # check for updates in queue
                duty = duty_queue.get(block=False)

            # Duty Cycle
            for i in range(tps):
                voltage = i < duty
                if voltageold != voltage: # check if voltage should change from 1->0 or 0->1
                    voltageold = voltage
                    task.write(voltage) # send update signal to DAQ
                time.sleep(1/tps)
        
        # Close tasks after loop is told to stop by doing tc.stopthread.set() in main program
        logging.info(f"Task {task.name}: Task Closing, Voltage set to False")
        task.write(False)
        task.stop()
        task.close()
        print(f"Task {task.name}: Task Closing, Voltage set to False")

    def update_duty_cycle(self, queue, duty):
        try:
            duty_value = int(duty.get()) ## fix back when updating for ttk interface
            if 0 <= duty_value <= self.tps:
                print("Duty cycle updated")
                # log duty cycle updated
                queue.put(duty_value)
            else:
                raise Exception()
        except:
            print(f"Invalid Input. Please enter an integer between 0 and {self.tps}.")   # turn into a log warning
  
    def close(self):
        self.stopthread.set()
        self.h1dutycycle.join()
        self.h2dutycycle.join()
        self.h3dutycycle.join()
        self.thermocoupletask.close()
        print("Thermocouple Task closing")
