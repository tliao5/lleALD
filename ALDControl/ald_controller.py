import pandas as pd
import logging
import time

class ald_controller:
    #def __init__():
        
    def fileInput():
        # Prompt the user to enter the file name 
        file_name = input("Please enter the name of the file you want to open: ") 
        try: 
            # Attempt to open the file in read mode 
            with open(file_name, 'r') as file: 
                # Read the content of the file 
                content = file.read() 
        except FileNotFoundError: 
            print(f"The file '{file_name}' does not exist.") 
        except Exception as e: 
            print(f"An error occurred while trying to read the file: {e}") 
        return file_name

    ### 
    # aldRun(file, loops, gvc) - executes an ALD Run
    # file - recipe file read in to program
    # loops - number of times to loop through the recipe
    # gvc - gas_valve_controller() object
    ###
    def aldRun(self, file, loops, gvc):
        data = pd.read_csv(file)
        dataNP = data.to_numpy()
        print(dataNP)
        # log run starting and recipe order

        for i in range(loops): #This is the number of loops the user wants to iterate the current file (ie - number of ALD cycles)
            for j in range(0,len(dataNP),1):#For each row in the .csv file, we want to set the experimental parameters accordingly
                if j >> 0: #Sending the current line and previous line for comparison in setVar
                    for k in range(len(dataNP[j])-1): #Ignore the sleep column for this, but iterate through the rest of the line.
                        if int(dataNP[j][k]) == -1: #If the cell has value -1, ignore it
                            pass
                        elif dataNP[j][k] > 0.04: #Any cell that is over 0.04s we do a pulsevalve. Note that means a 40ms pulse is the fastest.
                            gvc.pulseValve(gvc.tasks[k],dataNP[j][6]) #pulse DOx where x is the DO line. This works with the k variable because AV01 is line 0, AV02 is line 1, etc.
                        else: 
                            pass #For most of the 2s sleeps, this is where I'll be.
                    logging.info('going to sleep for {} seconds'.format(dataNP[j][6]))
                    time.sleep(dataNP[j][6]) #I had to move the sleep for the ALD pulses into the pulseValve, so we have a redundant sleep here on recipe lines where the ald valves cycle. But, this one happens after the ald valve opens and closes, so it shouldn't be a big deal.
                elif j == 0: #sending the first line and the first line changed by a bit to ensure all values are set. This condition will be triggered once per loop, when we go to the first row in the recipe file.
                    for k in range(len(dataNP[j])-1):
                        if int(dataNP[j][k]) == -1: #If the cell has value -1, ignore it
                            pass
                        else:
                            gvc.pulse_Valve(gvc.tasks[k],dataNP[j][6]) #test
        gvc.close_all() # make sure all valves are shut off at the end of a run
