"""QCS execution measurement program"""
from matplotlib import pyplot as plt
import numpy as np
import h5py

import keysight.qcs as qcs

ns = 1e-9
us = 1e-6
MHz = 1e6

program = qcs.Program()
mapper = qcs.ChannelMapper()
awg_amp = qcs.Scalar(
    name = "awg_amp",
    value = 0.5,
    dtype = float
)
dc_amp = qcs.Scalar(
    name = "dc_amp",
    value = 0.3,
    dtype = float
)

awg_channels = qcs.Channels(
    labels = range(4),
    name = "awg_channels",
)
dc_channels = qcs.Channels(
    labels = range(4),
    name = "dc_channels"
)
dig_channels = qcs.Channels(
    labels = range(4),
    name = "dig_channels",
)

mapper.add_channel_mapping(
    awg_channels,
    [
        (1,4,1), (1,4,2), (1,4,3), (1,4,4)
    ],
    instrument_types = qcs.InstrumentEnum.M5300AWG,
)
mapper.add_channel_mapping(
    dc_channels,
    [
        (1,7,1), (1,7,2), (1,7,3), (1,7,4)
    ],
    instrument_types = qcs.InstrumentEnum.M5301AWG
)
mapper.add_channel_mapping(
    dig_channels,
    [
        (1,18,1), (1,18,2), (1,18,3), (1,18,4)
    ],
    instrument_types = qcs.InstrumentEnum.M5200Digitizer
)
mapper.set_lo_frequencies(
    (1,4,4),
    lo_frequency=0
)

physical_digs = mapper.get_physical_channels(dig_channels)
physical_digs[2].settings.range.value = 1.8

program.add_waveform(
    pulse = qcs.RFWaveform(
        duration = 1 * us,
        envelope = qcs.GaussianEnvelope(),
        amplitude = awg_amp,
        rf_frequency = 10 * MHz
    ),
    channels = awg_channels[3],
    pre_delay= 0.4 * us
)
program.add_waveform(
    pulse = qcs.DCWaveform(
        duration = 300 * ns,
        envelope = qcs.ArbitraryEnvelope(
            times = [0, 1],
            amplitudes= [0, 1],
        ),
        amplitude = dc_amp,
    ),
    channels = dc_channels[0],
)
program.add_waveform(
    pulse = qcs.DCWaveform(
        duration = 1.4 * us,
        envelope = qcs.ConstantEnvelope(),
        amplitude = dc_amp,
    ),
    channels = dc_channels[0],
)
program.add_waveform(
    pulse = qcs.DCWaveform(
        duration = 300 * ns,
        envelope = qcs.ArbitraryEnvelope(
            times = [0, 1],
            amplitudes= [1, 0],
        ),
        amplitude = dc_amp,
    ),
    channels = dc_channels[0],
)
program.add_acquisition(
    integration_filter = 2 * us,
    channels = dig_channels[3]
)
program.add_acquisition(
    integration_filter = 2 * us,
    channels = dig_channels[2]
)

program.n_shots(1)

dc_amps = qcs.Array(
    name = "dc_amps",
    value = [0.1, 0.2, 0.3]
)
awg_amps = qcs.Array(
    name = "awg_amps",
    value = [0.2, 0.5, 1.0]
)
program.sweep(
    [dc_amps, awg_amps],
    [dc_amp, awg_amp]
)

backend = qcs.HclBackend(
    channel_mapper=mapper,
    hw_demod = False,
    init_time = 60 * ns,
)

program = qcs.Executor(backend).execute(program)
program.to_hdf5("./QCS/test_result.h5")

with h5py.File("./QCS/test_result.h5") as f:
    dc_trace = f["DutChannel_3_Acquisition_0"]["trace"][:] - 1.0
    rf_trace = f["DutChannel_4_Acquisition_0"]["trace"][:]
t_axis = np.linspace(0, 0.001/4.8 * len(dc_trace), len(dc_trace))

plt.figure()
plt.plot(t_axis, dc_trace, label = "DC pulse")
plt.plot(t_axis, rf_trace, label = "RF pulse")
plt.xlim([0, 0.001/4.8 * len(dc_trace)])
plt.legend()
plt.xlabel("t [us]")
plt.ylabel("V [V]")
plt.savefig("./QCS/test_pule.png")
plt.show()
