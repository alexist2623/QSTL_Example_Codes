"""Qick Software Average test"""
import numpy as np
import math
import matplotlib.pyplot as plt
import time

from qick import *
from qick.pyro import make_proxy

class LongDurationPulseExample(AveragerProgram):
    def initialize(self):
        # set the nyquist zone
        cfg = self.cfg
        freq_rf     = cfg["freq_rf"]
        # Declare RF generation channel
        self.declare_gen(
            ch      = 0,        # Channel
            nqz     = 2         # Nyquist Zone
        )
        self.declare_gen(
            ch      = 2,        # Channel
            nqz     = 2         # Nyquist Zone
        )
        # Declare RF input channel
        self.declare_readout(
            ch      = 0,        # Channel
            length  = cfg["pulse_time"],       # Readout length
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
        # Set ADC DDS
        self.set_readout_registers(
            ch      = 0,        # Readout channel
            freq    = freq_adc, # Readout DDS frequency
            length  = 16, # Readout DDS multiplication length
            phrst   = 0,        # Readout DDS phase reset
        )
        self.synci(10000)

    def body(self):
        cfg = self.cfg
        self.readout(
            ch      = 0,        # Readout channel
            t       = 100       # Readout DDS will start multiplication
                                # @ sync_t + 100
        )
        self.trigger(
            adcs    = [0],      # Readout channels
            adc_trig_offset = 0 # Readout will capture the data @ sync_t + 50
        )
        self.setup_and_pulse(
            ch      = 0,        # Generator channel
            style   = "const",    # Output is envelope * gain * DDS output
            freq    = self.freq_dac, # Generator DDS frequency
            phase   = self.deg2reg(180, gen_ch = 0),        # Generator DDS phase
            gain    = 2000, # Generator amplitude
            phrst   = 0,        # Generator DDS phase reset
            length  = 100,       # Total length of envelope.
            mode    = "periodic", # Set pulse mode to periodic
            t       = 100
        )
        self.setup_and_pulse(
            ch      = 2,        # Generator channel
            style   = "const",    # Output is envelope * gain * DDS output
            freq    = self.freq_dac, # Generator DDS frequency
            phase   = self.deg2reg(180, gen_ch = 0),        # Generator DDS phase
            gain    = 12000, # Generator amplitude
            phrst   = 0,        # Generator DDS phase reset
            length  = 113,       # Total length of envelope.
            mode    = "periodic", # Set pulse mode to periodic
            t       = 100
        )
        self.sync_all(cfg["long_duration"])
        self.setup_and_pulse(
            ch      = 0,        # Generator channel
            style   = "const",    # Output is envelope * gain * DDS output
            freq    = self.freq_dac, # Generator DDS frequency
            phase   = self.deg2reg(180, gen_ch = 0),        # Generator DDS phase
            gain    = 0, # Generator amplitude
            phrst   = 0,        # Generator DDS phase reset
            length  = 100,       # Total length of envelope.
            mode    = "oneshot", # Set pulse mode to periodic
            t       = 100
        )
        self.setup_and_pulse(
            ch      = 2,        # Generator channel
            style   = "const",    # Output is envelope * gain * DDS output
            freq    = self.freq_dac, # Generator DDS frequency
            phase   = self.deg2reg(180, gen_ch = 0),        # Generator DDS phase
            gain    = 0, # Generator amplitude
            phrst   = 0,        # Generator DDS phase reset
            length  = 113,       # Total length of envelope.
            mode    = "oneshot", # Set pulse mode to periodic
            t       = 100
        )

if __name__ == "__main__":
    # Qick version : 0.2.357
    (soc, soccfg) = make_proxy("192.168.2.99")
    # print(soccfg)

    # Set DAC Channel 0 attenuation 31 dB and 31 dB, and turn on DAC channel
    soc.rfb_set_gen_rf(0,31,31)
    soc.rfb_set_gen_rf(2,10,10)
    # Set DAC Channel filter as bypass mode
    soc.rfb_set_gen_filter(0,fc = 1.0, ftype = "bypass")
    soc.rfb_set_gen_filter(2,fc = 2.5, ftype = "bypass")

    # Set ADC Channel attenuation 31 dB, and turn on ADC channel
    soc.rfb_set_ro_rf(0,31)
    # Set ADC Channel filter as bypass mode
    soc.rfb_set_ro_filter(0, fc = 2.5, ftype = "bypass")

    start_time = time.time()
    cfg = {
        # Experiment Setup
        "reps" : 1,
        "expts" : 1,
        # Parameter Setup
        "freq_rf" : 520,
        "pulse_time" : 300,
        "number_of_pulse" : 10,
        "long_duration" : int(0.1 * 400e6)
    }
    prog = LongDurationPulseExample(
        soccfg,
        cfg,
    )
    print(prog)
    data = prog.acquire(soc = soc, progress = True, start_src = "external")[0][0]
    end_time = time.time()

    print(f"Acquisition time for : {end_time - start_time} s")
    plt.figure()
    plt.plot(data)
    plt.show()
