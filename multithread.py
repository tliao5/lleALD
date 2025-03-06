import threading
import time
import queue

def threadB(stopevent):
	while not stopevent.is_set():
		time.sleep(0.5)
		if printevent.is_set():
			print('B')

def threadA(stopevent,task_queue):
	userinput = 'A'
	while not stopevent.is_set():
		if not task_queue.empty():
			userinput = task_queue.get(block=False)
		if printevent.is_set():
			print(userinput)
		time.sleep(1)
		
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

def setDuty(duty_queue):
	while True:
		try:
			dutyin = int(input("Set a duty (1-100)"))
			if 1 <= dutyin <= 100:
				duty_queue.put(dutyin)
				break
		except ValueError:
			print("Invalid Input")

task_queue = queue.Queue()
duty_queue = queue.Queue()
stopevent = threading.Event()
printevent = threading.Event()
printevent.set()
tA = threading.Thread(target=threadA,args=(stopevent,task_queue))
tA.daemon = True
dutyThread = threading.Thread(target=duty_cycle,args=(stopevent,duty_queue,task))
dutyThread.daemon = True

tA.start()
dutyThread.start()
userinput = ' '

setDuty(duty_queue)

while userinput != "":
	userinput = input("Options: \n Enter - stop loop \n d - new input \n")
	if userinput == 'd':
		setDuty(duty_queue)
	elif userinput == "":
		pass
	else:
		print("Invalid input")


stopevent.set()
tA.join()
dutyThread.join()

print("Done!")