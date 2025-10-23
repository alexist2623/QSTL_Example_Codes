"""
Qick based qubit measurement example (maybe LC tank?)

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

class LongDurationPulseExample(RAveragerProgram):
    def initialize(self):
        # set the nyquist zone
        cfg = self.cfg
        freq_rf     = cfg["start"]
        # Declare RF generation channel
        self.declare_gen(
            ch      = 0,        # Channel
            nqz     = 2         # Nyquist Zone
        )
        # Declare RF input channel
        self.declare_readout(
            ch      = 0,        # Channel
            length  = int(cfg["pulse_time"] * 3/4) - 10,    # Readout length
                                                            # 10 is subtracted to
                                                            # make margin in timing
        )
        (self.ro_rp, self.ro_freq) = self._ro_regmap[0, "freq"]
        (self.gen_rp, self.gen_freq) = self._gen_regmap[0, "freq"]
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
            length  = 16,       # Dummy length
            phrst   = 0,        # Readout DDS phase reset
        )
        # Make endless pulse
        self.set_pulse_registers(
            ch      = 0,            # Generator channel
            style   = "const",      # Output is envelope * gain * DDS output
            freq    = self.freq_dac, # Generator DDS frequency
            phase   = self.deg2reg(0, gen_ch = 0),        # Generator DDS phase
            gain    = cfg["gain"],  # Generator amplitude
            phrst   = 0,            # Generator DDS phase reset
            length  = 100,          # Dummy length
            mode    = "periodic",   # Set pulse mode to periodic
        )
        self.synci(100000)

    def body(self):
        cfg = self.cfg
        self.mathi(self.gen_rp, 6, self.gen_freq, '+', 0)
        self.readout(
            ch      = 0,        # Readout channel
            t       = 100       # Readout DDS will start multiplication
                                # @ sync_t + 100
        )
        # Make endless pulse
        self.set_pulse_registers(
            ch      = 0,            # Generator channel
            style   = "const",      # Output is envelope * gain * DDS output
            freq    = self.freq_dac,    # Generator DDS frequency
            phase   = self.deg2reg(0, gen_ch = 0),        # Generator DDS phase
            gain    = cfg["gain"],  # Generator amplitude
            phrst   = 0,            # Generator DDS phase reset
            length  = 100,          # Dummy length
            mode    = "periodic",   # Set pulse mode to periodic
        )
        self.mathi(self.gen_rp, self.gen_freq, 6, '+', 0)
        self.pulse(
            ch      = 0,        # Generator channel
            t       = 100
        )
        # Make measurement triggers and shift t_sync
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
        self.mathi(self.gen_rp, self.gen_freq, 6, '+', 0)
        self.sync_all(1000)
        # Make sure that do not read buffer before experiment ends
        self.wait_all()
    
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
    # print(soccfg)

    # Set DAC Channel 0 attenuation 10 dB and 10 dB, and turn on DAC channel
    soc.rfb_set_gen_rf(0,10,10)
    # Set DAC Channel filter as bypass mode
    soc.rfb_set_gen_filter(0,fc = 2.5, ftype = "lowpass")

    # Set ADC Channel attenuation 31 dB, and turn on ADC channel
    soc.rfb_set_ro_rf(0,31)
    # Set ADC Channel filter as bypass mode
    soc.rfb_set_ro_filter(0, fc = 2.5, ftype = "lowpass")

    start_time = time.time()
    cfg = {
        # Experiment Setup
        "reps" : 1,
        "expts" : 60,
        "start" : 500,
        "step" : 10,
        "gain" : 2000,
        # Parameter Setup
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
    avgi = np.array(avgi[0]).mean(axis = 0)
    avgq = np.array(avgq[0]).mean(axis = 0)
    meas_power = avgi * avgi + avgq * avgq

    print(f"Acquisition time for : {end_time - start_time} s")
    plt.figure()
    plt.plot(expts, meas_power)
    plt.show()
