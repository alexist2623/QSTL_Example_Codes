"""Baseband IQ modulation and demodulation example using Keysight QCS."""
import keysight.qcs as qcs
import numpy as np
#################################################################
# Basic constants for convenience
#################################################################
ns              = 1e-9
GHz             = 1e9
n_shots         = 100

#################################################################
# Virtual Channel Definitions
# awgs : M5300 AWG channels
# digs : M5200 Digitizer channels
#################################################################
awgs            = qcs.Channels(
    range(4),
    "awgs",
    absolute_phase=False
)
digs            = qcs.Channels(
    range(4),
    "dig",
    absolute_phase=False
)
#################################################################
# Parameter setup
#################################################################
run_on_hw       = True
lo_freq         = 1.126 * GHz
rf_freq         = 1.371 * GHz
digitizer_range = 1.7
duration        = 800 * ns
##################################################################
# Declare saclar vairable which can be sweeped
##################################################################
iq_amp          = qcs.Scalar(
    name        ="iq_amp",
    value       = 1.0,
    dtype       = float
)
iq_phase        = qcs.Scalar(
    name        = "iq_phase",
    value       = 0.0,
    dtype       = float
)
#################################################################
# Program & Mapper Definition
#################################################################
program         = qcs.Program()
mapper          = qcs.ChannelMapper()
##################################################################
# Create the waveform for the M5300 AWG, and integration filter
# function to get IQ demodulated data from the M5200 digitizer
##################################################################
gauss_awg       = qcs.RFWaveform(
    duration,
    qcs.GaussianEnvelope(),
    iq_amp,
    rf_freq,
    iq_phase
)
gauss_dig       = qcs.RFWaveform(
    duration,
    qcs.GaussianEnvelope(),
    iq_amp,
    rf_freq,
    0.0
)
#################################################################
# Set LO frequencies for M5300 AWG and map virtual channels
# to physical channels
# awgs[0] -> M9046A chassis, slot 1, module 4, channel 1  M5300 AWG
# awgs[1] -> M9046A chassis, slot 1, module 4, channel 2  M5300 AWG
# awgs[2] -> M9046A chassis, slot 1, module 4, channel 3  M5300 AWG
# awgs[3] -> M9046A chassis, slot 1, module 4, channel 4  M5300 AWG
# digs[0] -> M9046A chassis, slot 1, module 18, channel 1 M5200 Digitizer
# digs[1] -> M9046A chassis, slot 1, module 18, channel 2 M5200 Digitizer
# digs[2] -> M9046A chassis, slot 1, module 18, channel 3 M5200 Digitizer
# digs[3] -> M9046A chassis, slot 1, module 18, channel 4 M5200 Digitizer
#################################################################
mapper.add_channel_mapping(
    awgs,
    [
        (1,4,1),
        (1,4,2),
        (1,4,3),
        (1,4,4)
    ],
    qcs.InstrumentEnum.M5300AWG
)
mapper.add_channel_mapping(
    digs,
    [
        (1,18,1),
        (1,18,2),
        (1,18,3),
        (1,18,4)
    ],
    qcs.InstrumentEnum.M5200Digitizer
)
mapper.set_lo_frequencies(
    [
        (1,4,1),
        (1,4,2),
        (1,4,3),
        (1,4,4)
    ],
    lo_freq
)
#################################################################
# Set input voltage range of M5200 digitizer channels
#################################################################
dig_phys_channels = mapper.get_physical_channels(digs)
dig_phys_channels[0].settings.range.value = digitizer_range
dig_phys_channels[1].settings.range.value = digitizer_range
dig_phys_channels[2].settings.range.value = digitizer_range
dig_phys_channels[3].settings.range.value = digitizer_range
##################################################################
# Program Sequence
##################################################################
program.add_waveform(
    gauss_awg,
    awgs[3]
)
program.add_acquisition(
    gauss_dig,
    digs[3],
    pre_delay=20 * ns
)
##################################################################
# Set the number of shots
##################################################################
program.n_shots(n_shots)
##################################################################
# Variable for sweep
##################################################################
iq_sweep_amps = qcs.Array(
    name = "iq_sweep_amps",
    value = [(i+1.0)/5.0 for i in range(5)]
)
iq_sweep_phases = qcs.Array(
    name = "iq_sweep_phases",
    value = [i * np.pi/4 for i in range(8)]
)
##################################################################
# Sweep the qcs.Scalar variable with qcs.Array variable
##################################################################
program.sweep(iq_sweep_amps, iq_amp)
program.sweep(iq_sweep_phases, iq_phase)

if run_on_hw:
    backend = qcs.HclBackend(
        channel_mapper      =mapper,
        # Demodulate singnal to IQ data on FPGA. So we cannot
        # get raw trace data from digitizer, and only IQ data is
        # available.
        hw_demod            =True,
        init_time           =0.001,
        reset_phase_every_shot=True
    )
    program_executed    = qcs.Executor(backend).execute(program)
    program_executed.to_hdf5("qcs_IQ_test.hdf5")
    html_str            = program_executed.plot_iq().to_html()
    file_name           = "plot_iq.html"
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(html_str)
    print(f"HTML content successfully saved to {file_name}")
