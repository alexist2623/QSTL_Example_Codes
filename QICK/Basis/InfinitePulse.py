"""
Qick Periodic signal generation test
"""
import numpy as np
import matplotlib.pyplot as plt

from qick import *
from qick.averager_program import QickSweep, merge_sweeps
from qick.asm_v1 import QickRegister
from qick.pyro import make_proxy

RegisterType = ["freq", "time", "phase", "adc_freq"]

MHz = 1
class InfinitePulse(AveragerProgram):
    def initialize(self):
        freq_rf     = self.cfg["freq_rf"]
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
            length  = self.cfg["duration"] + 100       # Readout length
        )
        # Convert RF frequency to DAC DDS register value
        freq_dac    = self.freq2reg(
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

        # Set DAC DDS
        self.set_pulse_registers(
            ch      = 0,        # Generator channel
            style   = "const",  # Output is gain * DDS output
            freq    = freq_dac, # Generator DDS frequency
            phase   = 0,        # Generator DDS phase
            gain    = 2500,      # Generator amplitude
            length  = self.cfg["duration"], # Pulse length
            phrst   = 0,        # Generator DDS phase reset
            mode    = "periodic"
        )
        self.set_pulse_registers(
            ch      = 2,        # Generator channel
            style   = "const",  # Output is gain * DDS output
            freq    = freq_dac, # Generator DDS frequency
            phase   = 0,        # Generator DDS phase
            gain    = 0,      # Generator amplitude
            length  = self.cfg["duration"], # Pulse length
            phrst   = 0,        # Generator DDS phase reset
            mode    = "periodic"
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
        self.pulse(
            ch      = 0,        # Generator channel
            t       = 100       # Pulse will be output @ sync_t + 100
        )
        self.pulse(
            ch      = 2,        # Generator channel
            t       = 100       # Pulse will be output @ sync_t + 100
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

    # Set DAC Channel 0 attenuation 10 dB and 10 dB, and turn on DAC channel
    soc.rfb_set_gen_rf(0,10,10)
    soc.rfb_set_gen_rf(2,0,0)
    # Set DAC Channel filter as bypass mode
    soc.rfb_set_gen_filter(0,fc = 2.5, ftype = "lowpass")
    soc.rfb_set_gen_filter(2,fc = 2.5, ftype = "lowpass")
    ######################################################
    # 540 MHz
    ######################################################
    # Att : 0dB, 0dB, gain : 30000 : 11.4 dBm
    # Att : 0dB, 0dB, gain : 25000 : 9.9 dBm
    # Att : 0dB, 0dB, gain : 20000 : 8.1 dBm
    # Att : 0dB, 0dB, gain : 15000 : 5.7 dBm
    # Att : 0dB, 0dB, gain : 10000 : 2.3 dBm
    # Att : 0dB, 0dB, gain : 7500 : -0.2 dBm
    # Att : 0dB, 0dB, gain : 5000 : -3.7 dBm
    # Att : 0dB, 0dB, gain : 2500 : -9.72 dBm
    # Att : 0dB, 0dB, gain : 2000 : -11.7 dBm
    # Att : 0dB, 0dB, gain : 1500 : -14.2 dBm
    # Att : 0dB, 0dB, gain : 1000 : -17.6 dBm
    # Att : 0dB, 0dB, gain : 500 : -23.5 dBm
    # Att : 0dB, 0dB, gain : 250 : -29.6 dBm

    # Set ADC Channel attenuation 31 dB, and turn on ADC channel
    soc.rfb_set_ro_rf(0,31)
    # Set ADC Channel filter as bypass mode
    soc.rfb_set_ro_filter(0, fc = 2.5, ftype = "lowpass")

    cfg = {
        # Experiment Setup
        "reps" : 1,
        "duration" : 1500,
        "expts" : 1,
        "freq_rf" : 540
    }
    prog = InfinitePulse(
        soccfg,
        cfg
    )
    prog.acquire(soc)
