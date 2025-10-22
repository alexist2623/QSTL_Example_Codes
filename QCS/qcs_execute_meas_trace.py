"""QCS execution measurement program"""
import keysight.qcs as qcs
import time

ns = 1e-9
us = 1e-6
MHz = 1e6

program = qcs.Program()
mapper = qcs.ChannelMapper()

awg_channels = qcs.Channels(
    labels = range(4),
    name = "awg_channels",
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

program.add_waveform(
    pulse = qcs.RFWaveform(
        duration = 20 * us,
        envelope = qcs.GaussianEnvelope(),
        amplitude = 1.0,
        rf_frequency = 540 * MHz
    ),
    channels = awg_channels[3],
)
program.add_acquisition(
    integration_filter = 2 * us,
    channels = dig_channels[3]
)

program.n_shots(10000)

backend = qcs.HclBackend(
    channel_mapper=mapper,
    hw_demod = False,
    init_time = 60 * ns,
)

start_time = time.time()
program = qcs.Executor(backend).execute(program)
# program.to_hdf5("test_result")
end_time = time.time()

print(end_time - start_time)

