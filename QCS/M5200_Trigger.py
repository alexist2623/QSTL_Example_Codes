import keysight_ktm5200x
import numpy as np
import matplotlib.pyplot as plt
from time import sleep

m5200_visa_addr = "PXI0::12-0.0::INSTR"

idQuery = False
reset   = True
options = "Simulate=False"

digitizer = keysight_ktm5200x.KtM5200x(
    m5200_visa_addr,
    idQuery,
    reset,
    options
)
print("Digitizer Initialized")

print(" identifier: ",  digitizer.identity.identifier)
print(" revision: ",    digitizer.identity.revision)
print(" vendor: ",      digitizer.identity.vendor)
print(" description:",  digitizer.identity.description)
print(" model: ",       digitizer.identity.instrument_model)
print(" resource: ",    digitizer.driver_operation.io_resource_descriptor)
print(" options: ",     digitizer.system.options)
print(" simulate: ",    digitizer.driver_operation.simulate)

print("Digitizer Connection is completed")

number_of_samples = 4800

digitizer.smb_channels[0].direction = keysight_ktm5200x.ChannelDirection.IN
digitizer.channels[0].set_daq_config(
    1,
    number_of_samples,
    keysight_ktm5200x.TriggerMode.HW_DIG_TRIG,
    0
)
digitizer.channels[0].external_trigger_config(
    keysight_ktm5200x.TriggerSource.SMB_TRIG1,
    keysight_ktm5200x.ExternalTriggerMode.RISING_EDGE,
    keysight_ktm5200x.SyncMode.IMMEDIATE
)
print("External trigger is set")

digitizer.channels[0].daq_flush()
print("DAQ is flushed")
print(f"Current DAQ data : {digitizer.channels[0].daq_counter}")
print("M5200A is waiting for trigger...")
digitizer.channels[0].daq_start()

while True:
    print(f"Current DAQ data : {digitizer.channels[0].daq_counter}")
    sleep(1)
    if digitizer.channels[0].daq_counter !=0:
        break
digitizer.close()
