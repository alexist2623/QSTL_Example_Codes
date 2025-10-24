"""
Qick Long Duration Pulse Generation and Loop Back Test.
Basically, it generates periodic signal, and makes multiple triggers to
measure the generated pulses. Since IQ value is averaged on FPGA, and 
its register size is limited to 32 bits, so only 2 ** 16 cycles of signal
can be measured with one trigger.

RF Out     ____~~~~~~~~~~~~~~~~~~~~. . . .~~~~~~~~~~~~~~~~~~~~___
Digitizer  ____|‾‾‾‾‾|_|‾‾‾‾‾|_|‾‾‾. . . .‾‾‾|_|‾‾‾‾‾|_|‾‾‾‾‾|___
Measured Data   IQ[0]   IQ[1]      . . . .      IQ[78]  IQ[79]
"""
import numpy as np
import math
import matplotlib.pyplot as plt
import time

from qick import *
from qick.averager_program import QickSweep
from qick.pyro import make_proxy

class LongDurationPulseExample(NDAveragerProgram):
    def initialize(self):
        # set the nyquist zone
        cfg = self.cfg
        freq_rf     = cfg["freq_rf"]
        # Declare RF generation channel
        self.declare_gen(
            ch      = 0,        # Channel
            nqz     = 2         # Nyquist Zone
        )

        # Declare RF input channel
        self.declare_readout(
            ch      = 0,        # Channel
            length  = int(cfg["pulse_time"] * 3/4) - 10,       # Readout length
        )
        # Convert RF frequency to DAC DDS register value
        self.freq_dac = self.freq2reg(
            f       = freq_rf,  # Frequency
            gen_ch  = 0,        # Generator channel
            ro_ch   = 0         # Readout channel for round up
        )
        # Convert RF frequency to ADC DDS register value
        freq_adc    = self.freq2reg_adc(
            f       = freq_rf,  # Frequency
            ro_ch   = 0,        # Readout channel
            gen_ch  = 0         # Generator channel for round up
        )
        # Set demodulator DDS
        self.set_readout_registers(
            ch      = 0,        # Readout channel
            freq    = freq_adc, # Readout DDS frequency
            length  = 16, # Readout DDS multiplication length
            phrst   = 0,        # Readout DDS phase reset
        )
        self.synci(100000)

    def body(self):
        cfg = self.cfg
        self.readout(
            ch      = 0,        # Readout channel
            t       = 100       # Readout DDS will start multiplication
                                # @ sync_t + 100
        )
        self.setup_and_pulse(
            ch      = 0,        # Generator channel
            style   = "const",    # Output is envelope * gain * DDS output
            freq    = self.freq_dac, # Generator DDS frequency
            phase   = self.deg2reg(0, gen_ch = 0),        # Generator DDS phase
            gain    = 2000, # Generator amplitude
            phrst   = 0,        # Generator DDS phase reset
            length  = 100,       # Total length of envelope.
            mode    = "periodic", # Set pulse mode to periodic
            t       = 100
        )
        for i in range(cfg["number_of_pulse"]):
            self.trigger(
                adcs    = [0],      # Readout channels
                adc_trig_offset = 150 + i * cfg["pulse_time"] # Readout will capture the data @ sync_t + 50
            )

        self.sync_all(100)
        self.setup_and_pulse(
            ch      = 0,        # Generator channel
            style   = "const",  # Output is envelope * gain * DDS output
            freq    = self.freq_dac, # Generator DDS frequency
            phase   = self.deg2reg(0, gen_ch = 0),    # Generator DDS phase
            gain    = 0,        # Generator amplitude
            phrst   = 0,        # Generator DDS phase reset
            length  = 100,      # Total length of envelope.
            mode    = "oneshot", # Set pulse mode to periodic
            t       = 100
        )
        self.sync_all(1000)
        self.wait_all()

if __name__ == "__main__":
    # Qick version : 0.2.357
    (soc, soccfg) = make_proxy("192.168.2.99")
    # print(soccfg)

    # Set DAC Channel 0 attenuation 10 dB and 10 dB, and turn on DAC channel
    soc.rfb_set_gen_rf(0,10,10)
    # Set DAC Channel 2 attenuation 31 dB and 31 dB, and turn on DAC channel (For oscilloscope measurement)
    # Note that if attenuation is not set to proper value, and output is not connected to termination impedance, 
    # it make large cross talk to peripheral channel.
    soc.rfb_set_gen_rf(2,31,31)
    # Set DAC Channel filter as bypass mode
    soc.rfb_set_gen_filter(0,fc = 2.5, ftype = "lowpass")
    soc.rfb_set_gen_filter(2,fc = 2.5, ftype = "lowpass")

    # Set ADC Channel attenuation 31 dB, and turn on ADC channel
    soc.rfb_set_ro_rf(0,31)
    # Set ADC Channel filter as bypass mode
    soc.rfb_set_ro_filter(0, fc = 2.5, ftype = "lowpass")

    start_time = time.time()
    cfg = {
        # Experiment Setup
        "reps" : 1,
        "expts" : 1,
        # Parameter Setup
        "freq_rf" : 520,
        "pulse_time" : 65000,
        "number_of_pulse" : 600,
    }
    prog = LongDurationPulseExample(
        soccfg,
        cfg,
    )
    # print(prog)
    expts, avgi, avgq  = prog.acquire(soc = soc, progress = True, start_src = "internal")
    end_time = time.time()
    print(prog)

    print(f"Acquisition time for : {end_time - start_time} s")
    plt.figure()
    # for idx, phase in enumerate(expts):
    #     plt.scatter(avgi[idx], avgq[idx])
        
    plt.scatter(avgi, avgq)
    plt.xlim([-1500, 1500])
    plt.ylim([-1500, 1500])
    plt.show()
