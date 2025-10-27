	
	"""RF+DC Waveform Program"""
	import keysight.qcs as qcs
	#################################################################
	# Basic constants for convenience
	#################################################################
	GHz             = 1e9
	ns              = 1e-9
	digitizer_range = 1.8
	lo_freq         = 1.23 * GHz
	if_freq         = 0.92 * GHz
	#################################################################
	# Virtual Channel Definitions
	# awgs : M5300 AWG channels
	# digs : M5200 Digitizer channels
	# dcs  : M5301 AWG channels
	#################################################################
	awgs            = qcs.Channels(
	    range(4),
	    "awgs"
	)
	digs            = qcs.Channels(
	    range(4),
	    "digs"
	)
	dcs             = qcs.Channels(
	    range(4),
	    "dcs"
	)
	#################################################################
	# Program & Mapper Definition
	#################################################################
	mapper          = qcs.ChannelMapper("192.168.19.2")
	program         = qcs.Program()
	################################################################
	# Set LO frequencies for M5300 AWG and map virtual channel to 
	# physical channel mapping
	# awgs[0] -> M9046A chassis, slot 1, module 4, channel 1  M5300 AWG
	# awgs[1] -> M9046A chassis, slot 1, module 4, channel 2  M5300 AWG
	# awgs[2] -> M9046A chassis, slot 1, module 4, channel 3  M5300 AWG
	# awgs[3] -> M9046A chassis, slot 1, module 4, channel 4  M5300 AWG
	# digs[0] -> M9046A chassis, slot 1, module 18, channel 1 M5200 Digitizer
	# digs[1] -> M9046A chassis, slot 1, module 18, channel 2 M5200 Digitizer
	# digs[2] -> M9046A chassis, slot 1, module 18, channel 3 M5200 Digitizer
	# digs[3] -> M9046A chassis, slot 1, module 18, channel 4 M5200 Digitizer
	# dcs[0]  -> M9046A chassis, slot 1, module 7, channel 1  M5301 AWG
	# dcs[1]  -> M9046A chassis, slot 1, module 7, channel 2  M5301 AWG
	# dcs[2]  -> M9046A chassis, slot 1, module 7, channel 3  M5301 AWG
	# dcs[3]  -> M9046A chassis, slot 1, module 7, channel 4  M5301 AWG
	################################################################
	mapper.add_channel_mapping(
	    awgs,
	    [
	        (1, 4, 1),
	        (1, 4, 2),
	        (1, 4, 3),
	        (1, 4, 4)
	    ],
	    qcs.InstrumentEnum.M5300AWG
	)
	mapper.set_lo_frequencies(
	    addresses   = [
	        (1, 4, 1),
	        (1, 4, 2),
	        (1, 4, 3),
	        (1, 4, 4)
	    ],
	    lo_frequency= lo_freq
	)
	mapper.add_channel_mapping(
	    dcs,
	    [
	        (1, 7, 1),
	        (1, 7, 2),
	        (1, 7, 3),
	        (1, 7, 4)
	    ],
	    qcs.InstrumentEnum.M5301AWG
	)
	mapper.add_channel_mapping(
	    digs,
	    [
	        (1, 18, 1),
	        (1, 18, 2),
	        (1, 18, 3),
	        (1, 18, 4)
	    ],
	    qcs.InstrumentEnum.M5200Digitizer
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
	# Declare saclar vairable which can be sweeped
	##################################################################
	rf_duration     = qcs.Scalar(
	    name        = "rf_duration",
	    value       = 200 * ns,
	    dtype       = float
	)
	dc_duration     = qcs.Scalar(
	    name        = "dc_duration",
	    value       = 400 * ns,
	    dtype       = float
	)
	################################################################
	# Waveform Definitions
	################################################################
	gauss_awg       = qcs.RFWaveform(
	    duration    = rf_duration,
	    envelope    = qcs.GaussianEnvelope(),
	    amplitude   = 1.0,
	    rf_frequency= if_freq,
	    instantaneous_phase= 0.0,
	    name        = "gauss_awg"
	)
	arb_envelope    = qcs.ArbitraryEnvelope(
	    [0.0, 0.1, 0.9, 1.0],
	    [0.0, 1.0, 1.0, 0.0]
	)
	arb_waveform    = qcs.DCWaveform(
	    duration    = dc_duration,
	    envelope    = arb_envelope,
	    amplitude   = 0.2,
	    name        = "arb_waveform"
	)
	################################################################
	# Program Sequence for M5300 AWG
	################################################################
	program.add_waveform(
	    qcs.Delay(100 * ns),
	    awgs[0]
	)
	program.add_waveform(
	    gauss_awg,
	    awgs[0]
	)
	program.add_waveform(
	    qcs.Delay(100 * ns),
	    awgs[0]
	)
	#################################################################
	# Program Sequence for M5301 AWG
	#################################################################
	program.add_waveform(
	    arb_waveform,
	    dcs[1]
	)
	##################################################################
	# Program Sequence for M5200 Digitizer (Readout)
	##################################################################
	program.add_acquisition(
	    500 * ns,
	    digs[3]
	)
	################################################################
	# Program run
	################################################################
	backend         = qcs.HclBackend(
	    channel_mapper=mapper,
	    init_time   = 0.001
	)
	print(f"{backend.is_system_ready()}")
	program_run     = qcs.Executor(backend).execute(program)
	
	################################################################
	# Save the Result
	################################################################
	program_run.to_hdf5("rf_dc_test.hdf5")
	
