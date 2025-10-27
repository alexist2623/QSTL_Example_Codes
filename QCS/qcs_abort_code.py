	"""Abort a running program"""
	import keysight.qcs as qcs
	#################################################################
	# Dummy mapper and backend for aborting a program
	#################################################################
	mapper  = qcs.ChannelMapper()
	backend = qcs.HclBackend(mapper)
	#################################################################
	# Check if there is a running program and abort it
	#################################################################
	if (
	    backend.get_program_state(
	        backend.get_program_execution_history()[0]["accession_id"]
	    ) == "Running"
	):
	    backend.abort_program(backend.get_program_execution_history()[0]["accession_id"])
	    print(
	        backend.get_program_state(
	            backend.get_program_execution_history()[0]["accession_id"]
	        )
	    )
	    print("Aborted running program...")
	else:
	    print("There is no running program...")
	
