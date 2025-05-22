import nidaqmx
from nidaqmx.constants import LineGrouping
import queue
import logging
import time
import threading

class pressure_controller:
    def __init__(self):
        pressure_sensor_channel={"Pchannel":"cDAQ1Mod2/ai2"}
        self.ptask = nidaqmx.Task("Pressure")
        self.ptask.ai_channels.add_ai_voltage_chan(pressure_sensor_channel["Pchannel"], min_val=-10.0, max_val=10.0)
        self.ptask.start()
        # Add flow controller functionality?

        #log pressure controller initialized

    #def set_flow_rate():
    
    #def read_cfm():

    #def log_pressure():

    #def log_cfm():

    def read_pressure(self):
        voltage = self.ptask.read()
        pressure = voltage/10
        return pressure
    
    def readPressure_pdr2000(self):
        self.ptask.start(0)
        voltage = self.ptask.read()
        pressure = 0.01*10**(2*voltage)*.001 #from pdr manual
        logging.info("pressure is " + str(pressure))
        self.ptask.stop()
        return pressure
    
    def close(self):
        self.ptask.close()
        print("Pressure Task Closing")
