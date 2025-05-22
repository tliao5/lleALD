import pandas as pd
import logging
import time
import threading

class ald_controller:
    ### 
    # aldRun(file, loops, gvc) - executes an ALD Run
    # file - recipe file read in to program
    # loops - number of times to loop through the recipe
    # vc - gas_valve_controller() object
    ###
    def create_run_thread(self,loops,vc):
        self.aldRunThread = threading.Thread(target=self.aldrun, args=(self.file, loops, vc))
        self.aldRunThread.start()

    def aldRun(self,loops, vc):
        data = pd.read_csv(self.file)
        dataNP = data.to_numpy()
        print(vc.tasks)
        print(dataNP)
        # log run starting and recipe order
        print("Run Starting")
        for i in range(loops): #This is the number of loops the user wants to iterate the current file (ie - number of ALD cycles)
            for j in range(0,len(dataNP),1):#For each row in the .csv file, we want to set the experimental parameters accordingly
                if j >> 0: #Sending the current line and previous line for comparison in setVar
                    for k in range(len(dataNP[j])-1): #Ignore the sleep column for this, but iterate through the rest of the line.
                        if int(dataNP[j][k]) == -1: #If the cell has value -1, ignore it
                            pass
                        elif dataNP[j][k] > 0.04: #Any cell that is over 0.04s we do a pulsevalve. Note that means a 40ms pulse is the fastest.
                            vc.pulseValve(vc.tasks[k],dataNP[j][6]) #pulse DOx where x is the DO line. This works with the k variable because AV01 is line 0, AV02 is line 1, etc.
                        else: 
                            pass #For most of the 2s sleeps, this is where I'll be.
                    logging.info('going to sleep for {} seconds'.format(dataNP[j][6]))
                    time.sleep(dataNP[j][6]) #I had to move the sleep for the ALD pulses into the pulseValve, so we have a redundant sleep here on recipe lines where the ald valves cycle. But, this one happens after the ald valve opens and closes, so it shouldn't be a big deal.
                elif j == 0: #sending the first line and the first line changed by a bit to ensure all values are set. This condition will be triggered once per loop, when we go to the first row in the recipe file.
                    for k in range(len(dataNP[j])-1):
                        if int(dataNP[j][k]) == -1: #If the cell has value -1, ignore it
                            pass
                        else:
                            vc.pulse_valve(vc.tasks[k],dataNP[j][6]) #test
        vc.close_all() # make sure all valves are shut off at the end of a run

    def close(self):
        if 'self.aldRunThread' in locals():
            self.aldRunThread.join()
        print("ALD Recipe Controller Closing")