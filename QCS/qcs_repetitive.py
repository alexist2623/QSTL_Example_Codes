	"""2 hours waveform generation with M5301AWG"""
	import keysight.qcs as qcs
	
	n_shots         = 100000000 # ~1 min
	ns              = 1e-9
	V_max_M5301AWG  = 5
	mV              = 1/(V_max_M5301AWG * 1000)
	
	dc_awgs = qcs.Channels(
	    range(4),
	    "dc_awgs"
	)
	
	mapper = qcs.ChannelMapper()
	program = qcs.Program()
	
	mapper.add_channel_mapping(
	    channels = dc_awgs,
	    addresses = [
	        (1,7,1), (1,7,2), (1,7,3), (1,7,4)
	    ],
	    instrument_types = qcs.InstrumentEnum.M5301AWG
	)
	
	dc_segment1 = qcs.DCWaveform(
	    duration = 2000 * ns,
	    envelope = qcs.ConstantEnvelope(),
	    amplitude = 5000 * mV
	)
	dc_segment2_p = qcs.DCWaveform(
	    duration = 20 * ns,
	    envelope = qcs.ArbitraryEnvelope(
	        [0,1],[0,1]
	    ),
	    amplitude = -5000 * mV
	)
	dc_segment2_n = qcs.DCWaveform(
	    duration = 20 * ns,
	    envelope = qcs.ArbitraryEnvelope(
	        [0,1], [1,0]
	    ),
	    amplitude = 5000 * mV
	)
	dc_segment2 = dc_segment2_n + dc_segment2_p
	dc_segment3 = qcs.DCWaveform(
	    duration = 2000 * ns,
	    envelope = qcs.ConstantEnvelope(),
	    amplitude = -5000 * mV
	)
	dc_segment4_p = qcs.DCWaveform(
	    duration = 20 * ns,
	    envelope = qcs.ArbitraryEnvelope(
	        [0,1],[0,1]
	    ),
	    amplitude = 0 * mV
	)
	dc_segment4_n = qcs.DCWaveform(
	    duration = 20 * ns,
	    envelope = qcs.ArbitraryEnvelope(
	        [0,1], [1,0]
	    ),
	    amplitude = -5000 * mV
	)
	dc_segment4 = dc_segment4_n + dc_segment4_p
	dc_segment5 = qcs.DCWaveform(
	    duration = 2000 * ns,
	    envelope = qcs.ConstantEnvelope(),
	    amplitude = 0 * mV
	)
	
	program.add_waveform(dc_segment1, dc_awgs[2])
	program.add_waveform(dc_segment2, dc_awgs[2])
	program.add_waveform(dc_segment3, dc_awgs[2])
	program.add_waveform(dc_segment4, dc_awgs[2])
	program.add_waveform(dc_segment5, dc_awgs[2])
	
	for i in range(150):
	    program.add_waveform(qcs.Delay(63.333 * ns), dc_awgs[2], new_layer=True)
	    program.extend(program.layers[0])
	
	program.n_shots(n_shots)
	backend = qcs.HclBackend(
	    channel_mapper=mapper,
	    init_time=0,
	    hw_demod=True
	)
	program_result = qcs.Executor(backend).execute(program)
	print("Done - program is finished...")
