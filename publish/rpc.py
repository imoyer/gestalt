# gestalt.publish.rpc
#
# REMOTE PROCEDURE CALL LIBRARY
# A component of Gestalt.

#--imports---
import BaseHTTPServer
import urlparse
import ast	#abstract syntax trees, for parsing query inputs
import sys
import json

class httpRPCDispatch(object):
	'''Receives remote procedure calls over HTTP and calls them from the server thread.'''
	def __init__(self, address = 'localhost', port = 7272):
		self.address = address
		self.port = port
		self.functions = {}	#contains a dictionary of functions which can be accessed externally {functionString:function}
		self.allowOrigins = []	#contains a list of origins which are permitted to access the rpc interface
		self.HTTPHandler.functions = self.functions
		self.HTTPHandler.allowOrigins = self.allowOrigins
		
		self.httpServer = BaseHTTPServer.HTTPServer((address, port), self.HTTPHandler)
		
	def addFunctions(self, *args):
		'''Adds functions provided as arguments to the list of externally accessible functions.
		
		Input to the function is a series of tuples (externalName, function).'''
		for arg in args:
			externalName, internalFunction = arg
			self.functions.update({externalName: internalFunction})
			
	def addOrigins(self, *args):
		'''Adds origins provided as arguments to the list of origins which can access the rpc interface.'''
		self.allowOrigins += list(args)
		
	def start(self):
		self.httpServer.serve_forever()
	
	class HTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
		'''RPC Handler for requests using an HTTP protocol.'''
		
		functions = {}		#these are class variables which get updated by the httpRPCDispatch
		allowOrigins = []
		jsonEncoder = json.JSONEncoder()
		
		def do_GET(self):
			inboundIP, inboundPort = self.client_address
			parsedURL = urlparse.urlparse(self.path)
			
			#get the name of the requested procedure
			procedure = parsedURL.path[1:]	#removes forward slash at beginning
			
			#parse and evaluate the parameters passed to the procedure
			parameters = {}
			for parameter, value in urlparse.parse_qs(parsedURL.query).iteritems():
				try:
					parameters.update({parameter:ast.literal_eval(value[0])})
				except:
					pass

			#check the functions list for the requested procedure
			if procedure in self.functions:
				procedureObject = self.functions[procedure]
				try:
					procedureName = procedureObject.__name__	#a function was provided
				except:
					procedureName = procedureObject.__class__.__name__	#a class object was provided
					
				#note that RPC only supports keyword arguments because the order is not guaranteed.
				try:
					returnValues = procedureObject(**parameters)	#make procedure call
					print "REMOTE PROCEDURE CALL: " + procedureName + "(" + ''.join([parameterName + '=' + str(parameterValue) + ',' for parameterName, parameterValue in parameters.iteritems()])[:-1] + ')'
					print self.jsonEncoder.encode(returnValues)
				except:
					print sys.exc_info()[0]
			else:
				self.send_error(404)
				
				
			
				
				
	