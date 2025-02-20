import time
import nidaqmx
from nidaqmx.constants import AcquisitionType, LineGrouping

with nidaqmx.Task() as task:
    # Try to turn on the whole system
    mainpower = "CDAQ1Mod4/line11"
    heater1 = "CDAQ1Mod4/port0/line5"

    task.do_channels.add_do_chan(mainpower, line_grouping=LineGrouping.CHAN_PER_LINE)
    task.start()
    task.write(True)
    task.stop()
    # Create a waveform
    data = [1] * 400 + [0] * 600

    task.do_channels.add_do_chan(heater1, line_grouping=LineGrouping.CHAN_FOR_ALL_LINES) # unsure what this does exactly, does it assign the channel?
    task.timing.cfg_samp_clk_timing(1000.0, sample_mode=AcquisitionType.CONTINUOUS) # access hardware timer, tell Acquisition type - CONTINUOUS to repeat
    task.write(data) # send wave to the channel

    task.start() # Run Tasks

    input("Generating voltage. Press Enter to stop.\n")

    task.stop()

    # Turn off main power supply
    task.start()
    task.do_channels.add_do_chan(mainpower, line_grouping=LineGrouping.CHAN_PER_LINE)
    task.write(False)

    task.stop()