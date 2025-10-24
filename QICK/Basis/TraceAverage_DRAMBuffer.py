"""
Qick DRAM based Trace Average Test
Signal -> Demodulator -> FIR & x8 decimation -> PL DRAM
After decimated signals are saved on DRAM (this measurement is implemented on FPGA),
and we get all trace data from DRAM and average it in software.
Note that data trace data should not exceed 4 GB and virtual memory allocated
for RPC Server in RFSoC (I don't know how can we estimate virtual memory allocation...).
"""
import numpy as np
import math
import matplotlib.pyplot as plt
import time

from qick import *
from qick.pyro import make_proxy

class MultiPulseLoopBackExample(AveragerProgram):
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
            length  = (cfg["pulse_time"] + 100) * 12,       # Readout length
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
        self.add_gauss(
            0,                  # Set output channel number
            name    = "gauss",  # Set envelope name
            sigma   = cfg["pulse_time"] >> 2,  # Sigma of gaussian
            length  = cfg["pulse_time"],       # Total length of envelope. 
                                                    # When envelope is used, lenght
                                                    # of waveform is specified in envelope,
                                                    # rather than pulse register
        )
        # Set ADC DDS
        self.set_readout_registers(
            ch      = 0,        # Readout channel
            freq    = freq_adc, # Readout DDS frequency
            length  = (cfg["pulse_time"] + 100) * 12, # Readout DDS multiplication length
            phrst   = 0         # Readout DDS phase reset
        )
        self.synci(100)
    def body(self):
        cfg = self.cfg
        self.readout(
            ch      = 0,        # Readout channel
            t       = 100       # Readout DDS will start multiplication
                                # @ sync_t + 100
        )
        self.trigger(
            adcs    = [0],      # Readout channels
            adc_trig_offset = 150, # Readout will capture the data @ sync_t + 50
            ddr4    = True
        )
        for i in range(10):
            self.setup_and_pulse(
                ch      = 0,        # Generator channel
                style   = "arb",    # Output is envelope * gain * DDS output
                freq    = self.freq_dac, # Generator DDS frequency
                phase   = self.deg2reg(90, gen_ch = 0),        # Generator DDS phase
                gain    = 2000 // (i+1), # Generator amplitude
                phrst   = 0,        # Generator DDS phase reset
                outsel  = "product",# Output is envelope * gain * DDS output
                waveform= "gauss",  # Set envelope to be multiplied
                t       = (cfg["pulse_time"] + 100) * (i+1) + 100
            )
        self.sync_all(10)


if __name__ == "__main__":
    # Qick version : 0.2.357
    (soc, soccfg) = make_proxy("192.168.2.99")

    # Set DAC Channel 0 attenuation 31 dB and 31 dB, and turn on DAC channel
    soc.rfb_set_gen_rf(0,10,10)
    # Set DAC Channel filter as bypass mode
    soc.rfb_set_gen_filter(0,fc = 2.5, ftype = "highpass")

    # Set ADC Channel attenuation 31 dB, and turn on ADC channel
    soc.rfb_set_ro_rf(0,31)
    # Set ADC Channel filter as bypass mode
    soc.rfb_set_ro_filter(0, fc = 2.5, ftype = "highpass")

    cfg = {
        # Experiment Setup
        "reps"          : 5000,
        # Parameter Setup
        "freq_rf"       : 5100,
        "pulse_time"    : 100,
        "soft_avgs"     : 1
    }
    prog = MultiPulseLoopBackExample(
        soccfg,
        cfg
    )
    LEN = int(3360 / 4 * 3)
    nt = int(LEN  * cfg["reps"] / 128)
    start_time = time.time()
    soc.clear_ddr4()
    soc.arm_ddr4(ch = 0, nt = nt, )
    print(prog)
    prog.run_rounds(soc = soc)
    data = soc.get_ddr4(nt = nt, start = 0)
    mean_start_time = time.time()
    data = np.array([data[i][0] for i in range(len(data))])
    print(len(data))
    data = data[:(len(data) // LEN) * LEN]
    data = data.reshape(-1,LEN).mean(axis=0)
    mean_end_time = time.time()

    plt.figure()
    plt.plot(data)
    plt.show()

    print("Acquisition Time: %.3f s, Mean Time: %.3f s"%(
        mean_start_time - start_time, mean_end_time - mean_start_time
    ))
