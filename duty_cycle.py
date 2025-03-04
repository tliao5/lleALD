import threading
import queue
import time
import nidaqmx

""" Duty Cycle function
    stopthread - thread.Event() -- Event allows cycle to be stopped from the main
    duty_queue - queue.Queue() -- buffer of inputs to thread, use this to update the duty of the cycle
    task - DAQ channel that the duty cycle is associated with
"""
def duty_cycle(stopthread,duty_queue,task):
    voltageold=False
	# Get duty from duty_queue passed in, duty_queue must be set before thread is started
    duty = duty_queue.get(block=True)
    while not stopthread.is_set():
    # Check for user input to change Duty Cycle
        if not duty_queue.empty():
            duty = duty_queue.get(block=False)

		# Duty cycle logic, only send a trigger to the daq if the voltage must be flipped
        for i in range(100):
            if i < duty:
                voltage=True
            else:
                voltage=False
            if voltageold!=voltage:
                voltageold = voltage
                task.write(voltage)
            time.sleep(0.1)
    task.write(False)
    task.stop()

""" Set Duty of duty cycle -- Asks user for input of duty (0-100)
    duty_queue - queue.Queue() -- inputs which queue to pass user input to
"""
def setDuty(duty_queue):
	while True:
		try:
			dutyin = int(input("Set a duty (0-100)"))
			if 0 <= dutyin <= 100:
				duty_queue.put(dutyin)
				break
		except ValueError:
			print("Invalid Input")