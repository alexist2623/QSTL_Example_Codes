"""Qick P1dB Measurement with FPGA"""

import numpy as np
import matplotlib.pyplot as plt

from qick import *
from qick.averager_program import QickSweep, merge_sweeps
from qick.asm_v1 import QickRegister
from qick.pyro import make_proxy

RegisterType = ["freq", "time", "phase", "adc_freq"]
MHz = 1

class P1dB_Meas(RAveragerProgram):
    def initialize(self):
        freq_rf     = self.cfg["start"]
        # Declare RF generation channel
        self.declare_gen(
            ch      = 0,        # Channel
            nqz     = 2         # Nyquist Zone
        )

        # Declare RF input channel
        self.declare_readout(
            ch      = 0,        # Channel
            length  = self.cfg["pulse_time"] + 100      # Readout length
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
            gain    = 5000,     # Generator amplitude
            length  = self.cfg["pulse_time"],       # Pulse length
            phrst   = 0         # Generator DDS phase reset
        )

        # Set ADC DDS
        self.set_readout_registers(
            ch      = 0,        # Readout channel
            freq    = freq_adc, # Readout DDS frequency
            length  = self.cfg["pulse_time"],       # Readout DDS multiplication length
            phrst   = 0         # Readout DDS phase reset
        )
        self.synci(100)
        (self.ro_rp, self.ro_freq) = self._ro_regmap[0, "freq"]
        (self.gen_rp, self.gen_freq) = self._gen_regmap[0, "freq"]

    def body(self):
        self.pulse(
            ch      = 0,        # Generator channel
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

    def update(self): 
        # Update readout frequency register 
        self.mathi(
            self.ro_rp, self.ro_freq, self.ro_freq, '+',
            self.freq2reg_adc(self.cfg["step"], 0, 0)
        )
        # Update generator frequency register
        self.mathi(
            self.gen_rp, self.gen_freq, self.gen_freq, '+',
            self.freq2reg(self.cfg["step"], 0, 0)
        )
        self.synci(10)

 

if __name__ == "__main__": 
    # Qick version : 0.2.357
    (soc, soccfg) = make_proxy("192.168.2.99")
    # Set DAC Channel 0 attenuation 20 dB and 20 dB, and turn on DAC channel
    soc.rfb_set_gen_rf(0,10,10)
    # Set DAC Channel filter as bypass mode
    soc.rfb_set_gen_filter(0,fc = 2.5, ftype = "lowpass")
    # Set ADC Channel attenuation 20 dB, and turn on ADC channel
    soc.rfb_set_ro_rf(0,10)
    # Set ADC Channel filter as bypass mode
    soc.rfb_set_ro_filter(0, fc = 2.5, ftype = "lowpass")
    cfg = {
        # Experiment Setup
        "reps" : 1000,
        "freq_sweep_num" : 20,
        "duration_sweep_num" : 10,
        "start" : 100,
        "step" : 5,
        "expts" : 500,
        # Parameter Setup
        "pulse_time" : 2000
    } 

    prog = P1dB_Meas(
        soccfg,
        cfg
    )
    print(prog)
    expts, avgi, avgq = prog.acquire(soc, progress = True)
    plt.figure()
    plt.plot(expts, avgi[0][0] * avgi[0][0] + avgq[0][0] * avgq[0][0], '.-')
    plt.show()
