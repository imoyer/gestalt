#----IMPORTS------------

#----FUNCTIONS--------------
#
# A Gestalt class for building methods for Gestalt

class gFunction(object):
	def __call__(self, *args, **kwargs):
		return self.gFunctionCore(self)._init(*args, **kwargs)	#allows gFunctionObject to return
	
	def receiver(self, packet):
		decodedPacket = self.packet.decode(packet)
		self.packetHolder.put(decodedPacket)	#stores packet for use by calling outbound functions
		self.receive(decodedPacket)
		
	def receive(self, packet):	#this should get overridden
		self.responseFlag.set()

class gFunctionObject(object):
	def __init__(self, gFunc):
		self.gFunction = gFunc
		self.packetSet = [] #initialize with an empty packet set
		self.virtualNode = self.gFunction.virtualNode
		
	def _init(self, *args, **kwargs):
		returnObject = self.init(*args, **kwargs) #run user init function
		if returnObject != None: return returnObject
		else: return self
		
	def updatePacketSet(self, updateInput):
		self.packetSet = self.gFunction.packetSet(updateInput)
	
	def getPacketSet(self):
		return self.packetSet
	
	def getPort(self):
		return self.virtualNode.bindPort.outPorts[self.gFunction]
	
	def transmit(self, mode = 'unicast'):
		self.gFunction.responseFlag.clear()	#clears flag, in case it wasn't cleared by a responding function
		self.virtualNode.transmit([self], mode)	#transmit 
	
	def waitForResponse(self, timeout = None):
		if self.gFunction.responseFlag.wait(timeout):
			self.gFunction.responseFlag.clear()
			return True
		return False
	
	def getPacket(self):
		return self.gFunction.packetHolder.get()
		
	
	def init(self):
		pass
	def sync(self):
		pass
	def calculate(self):
		pass
	def commit(self):
		pass
	def callback(self):
		pass