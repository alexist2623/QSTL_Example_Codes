	
	"""DC Pulse generation program"""
	import keysight.qcs as qcs
	#################################################################
	# Basic constants for convenience
	#################################################################
	n_shots         = 100000000     # ~1 min
	ns              = 1e-9
	V_max_M5301AWG  = 5             # If termination is 1M -> -5 ~ +5 V,
	                                # 50 Ohm -> -2.5 ~ +2.5 V
	mV              = 1/(V_max_M5301AWG * 1000)
	#################################################################
	# Virtual Channel Definitions
	# dc_awgs : M5301 AWG channels
	#################################################################
	dc_awgs         = qcs.Channels(
	    range(4),
	    "dc_awgs"
	)
	#################################################################
	# Program & Mapper Definition
	#################################################################
	mapper          = qcs.ChannelMapper()
	program         = qcs.Program()
	#################################################################
	# Map virtual channels to physical channels
	# dc_awgs[0] -> M9046A chassis, slot 1, module 7, channel 1  M5301 AWG
	# dc_awgs[1] -> M9046A chassis, slot 1, module 7, channel 2  M5301 AWG
	# dc_awgs[2] -> M9046A chassis, slot 1, module 7, channel 3  M5301 AWG
	# dc_awgs[3] -> M9046A chassis, slot 1, module 7, channel 4  M5301 AWG
	###################################################################
	mapper.add_channel_mapping(
	    channels    = dc_awgs,
	    addresses   = [
	        (1,7,1), (1,7,2), (1,7,3), (1,7,4)
	    ],
	    instrument_types = qcs.InstrumentEnum.M5301AWG
	)
	##################################################################
	# Create the DC waveform for the M5301 AWG
	# dc_segment1 : 200 ns DC pulse at 5 V
	# dc_segment2 : 15 ns DC pulse at -5 V followed by 15 ns DC pulse at 5 V
	# dc_segment3 : 300 ns DC pulse at -5 V
	# dc_segment4 : 15 ns DC pulse at 0 V followed by 15 ns DC pulse at -5 V
	# dc_segment5 : 200 ns DC pulse at 0 V
	##################################################################
	dc_segment1     = qcs.DCWaveform(
	    duration    = 200 * ns,
	    envelope    = qcs.ConstantEnvelope(),
	    amplitude   = 5000 * mV
	)
	dc_segment2_p   = qcs.DCWaveform(
	    duration    = 15 * ns,
	    envelope    = qcs.ArbitraryEnvelope(
	        [0,1],[0,1]
	    ),
	    amplitude = -5000 * mV
	)
	dc_segment2_n   = qcs.DCWaveform(
	    duration    = 15 * ns,
	    envelope    = qcs.ArbitraryEnvelope(
	        [0,1], [1,0]
	    ),
	    amplitude = 5000 * mV
	)
	dc_segment2     = dc_segment2_n + dc_segment2_p
	dc_segment3     = qcs.DCWaveform(
	    duration    = 300 * ns,
	    envelope    = qcs.ConstantEnvelope(),
	    amplitude   = -5000 * mV
	)
	dc_segment4_p   = qcs.DCWaveform(
	    duration    = 15 * ns,
	    envelope    = qcs.ArbitraryEnvelope(
	        [0,1],[0,1]
	    ),
	    amplitude   = 0 * mV
	)
	dc_segment4_n   = qcs.DCWaveform(
	    duration    = 15 * ns,
	    envelope    = qcs.ArbitraryEnvelope(
	        [0,1], [1,0]
	    ),
	    amplitude   = -5000 * mV
	)
	dc_segment4     = dc_segment4_n + dc_segment4_p
	dc_segment5     = qcs.DCWaveform(
	    duration    = 200 * ns,
	    envelope    = qcs.ConstantEnvelope(),
	    amplitude   = 0 * mV
	)
	##################################################################
	# Program Sequence
	##################################################################
	program.add_waveform(dc_segment1, dc_awgs[0])
	program.add_waveform(dc_segment2, dc_awgs[0])
	program.add_waveform(dc_segment3, dc_awgs[0])
	program.add_waveform(dc_segment4, dc_awgs[0])
	program.add_waveform(dc_segment5, dc_awgs[0])
	##################################################################
	# Set the number of shots
	##################################################################
	program.n_shots(n_shots)
	##################################################################
	# Execute the program
	##################################################################
	backend = qcs.HclBackend(
	    channel_mapper=mapper,
	    init_time=0,
	    suppress_rounding_warnings=True,
	    hw_demod=True
	)
	print("Done - program is finished...")
	
