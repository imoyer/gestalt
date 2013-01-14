def notice(source = None, message = ""):
	''' Sends a notice to the user.
	
	For now, this just prints to the screen. But eventually, could re-route via a web interface.'''
	#check for name attribute
	if hasattr(source, 'name'):
		print str(getattr(source, 'name')) + ": " + message
	#if not found, check for an owner and recursively call notice
	elif hasattr(source, 'owner'):
		notice(source.owner, message)
	else:
		print str(source) + ": " + message
	return

	