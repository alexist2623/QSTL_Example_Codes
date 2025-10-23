"""
Qick DC Pulse Generation Example
"""
import numpy as np
import matplotlib.pyplot as plt

from qick import *
from qick.averager_program import QickSweep, merge_sweeps
from qick.asm_v1 import QickRegister
from qick.pyro import make_proxy

RegisterType = ["freq", "time", "phase", "adc_freq"]

MHz = 1
class DCPulse(AveragerProgram):
    def initialize(self):
        freq_rf     = self.cfg["freq_rf"]
        # Declare RF generation channel
        self.declare_gen(
            ch      = self.cfg["dc_ch"],        # Channel
            nqz     = 1         # Nyquist Zone
        )
        # Declare RF input channel
        self.declare_readout(
            ch      = 0,        # Channel
            length  = self.cfg["duration"] + 100       # Readout length
        )
        # Convert RF frequency to ADC DDS register value
        freq_adc    = self.freq2reg_adc(
            f       = freq_rf,  # Frequency
            ro_ch   = 0,        # Readout channel
            gen_ch  = self.cfg["dc_ch"] # Generator channel for round up
        )
        self.add_gauss(
            ch      = self.cfg["dc_ch"],                  # Set output channel number
            name    = "gauss",  # Set envelope name
            sigma   = self.cfg["duration"] >> 2,  # Sigma of gaussian
            length  = self.cfg["duration"],       # Total length of envelope. 
                                                    # When envelope is used, lenght
                                                    # of waveform is specified in envelope,
                                                    # rather than pulse register
        )
        # Set ADC DDS
        self.set_readout_registers(
            ch      = 0,        # Readout channel
            freq    = freq_adc, # Readout DDS frequency
            length  = self.cfg["duration"], # Readout DDS multiplication length
            phrst   = 0         # Readout DDS phase reset
        )
        self.synci(100)

    def body(self):
        self.setup_and_pulse(
            ch      = self.cfg["dc_ch"],        # Generator channel
            style   = "flat_top", # Output is gain * DDS output
            freq    = 0, # Generator DDS frequency
            phase   = 0,        # Generator DDS phase
            gain    = -32767,     # Generator amplitude
            phrst   = 0,        # Generator DDS phase reset
            waveform = "gauss",# Use the defined envelope (gaussian)
            length  = self.cfg["duration"], # Pulse length
            t       = 100,      # Pulse will be output @ sync_t + 100
        )
        self.setup_and_pulse(
            ch      = self.cfg["dc_ch"],        # Generator channel
            style   = "flat_top", # Output is gain * DDS output
            freq    = 0, # Generator DDS frequency
            phase   = 0,        # Generator DDS phase
            gain    = +32767,     # Generator amplitude
            phrst   = 0,        # Generator DDS phase reset
            waveform = "gauss",# Use the defined envelope (gaussian)
            length  = self.cfg["duration"], # Pulse length
            t       = 2 * self.cfg["duration"] + 100,      # Pulse will be output @ sync_t + 100
        )
        self.readout(
            ch      = 0,        # Readout channel
            t       = 100       # Readout DDS will start multiplication
                                # @ sync_t + 100
        )
        self.trigger(
            adcs    = [0],      # Readout channels
            adc_trig_offset = 50 # Readout will capture the data @ sync_t + 50
        )
        self.sync_all(100)

if __name__ == "__main__":
    # Qick version : 0.2.357
    (soc, soccfg) = make_proxy("192.168.2.99")

    # Set DAC Channel 0 attenuation 31 dB and 31 dB, and turn on DAC channel
    soc.rfb_set_gen_rf(0,0,0)
    # Set DAC Channel filter as bypass mode
    soc.rfb_set_gen_filter(0,fc = 2.5, ftype = "bypass")

    # Set ADC Channel attenuation 31 dB, and turn on ADC channel
    soc.rfb_set_ro_rf(0,31)
    # Set ADC Channel filter as bypass mode
    soc.rfb_set_ro_filter(0, fc = 2.5, ftype = "bypass")
    soc.rfb_set_gen_dc(8)

    cfg = {
        # Experiment Setup
        "dc_ch" : 11,
        "reps" : 1,
        "duration" : 100,
        "expts" : 1,
        "freq_rf" : 200
    }
    prog = DCPulse(
        soccfg,
        cfg
    )
    prog.acquire(soc)
    # print(soccfg)
