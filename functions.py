#----IMPORTS------------
from gestalt.machines import coordinates
from gestalt import utilities
#----FUNCTIONS--------------
#
# A Gestalt class for building methods for Gestalt

class gFunction(object):
	def __call__(self, *args, **kwargs):
		return self.gFunctionCore(self)._init(*args, **kwargs)	#allows gFunctionObject to return, gFunctionCore is defined by the user
	
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
	
class move(object):
	def __init__(self, virtualMachine = None, virtualNodes = None, axes = None, kinematics = None, machinePosition = None):
		'''Configures the move object.'''
		
		#convert inputs to lists where appropriate
		if type(virtualNodes) != list: virtualNodes = [virtualNodes]
		if type(axes) != list: axes = [axes]
		
		self.virtualMachine = virtualMachine #a reference to the virtual machine which owns this function.
		self.virtualNodes = virtualNodes #a list of nodes which will be used by the function.
		self.axes = axes #a list of axes which connect physical actuators to the machine kinematics. Some nodes support multiple axes.
		self.kinematics = kinematics #a kinematics object which will transform between axis coordinates and machine coordinates
		self.machinePosition = machinePosition #the positional state of the machine.
		
	def __call__(self, *args, **kwargs):
		return moveObject(self, *args, **kwargs)	#returns a move object which can be used by external synchronization methods

class moveObject(object):
	def __init__(self, move, position, velocity = None, acceleration = None):
		#store parameters
		self.move = move	#the calling move class
		self.positionCommand = position
		self.velocityCommand = velocity
		self.accelerationCommand = acceleration
		
		#calculate deltas
		currentMachinePosition = self.move.machinePosition.future()	#get the current machine position
		
		requestedMachinePosition = []	#build up the requested machine position based on what is provided and what is left as 'None'.
		for axisIndex, axisPosition in enumerate(self.positionCommand):
			requestedMachinePosition += [coordinates.uFloat(axisPosition if axisPosition else currentMachinePosition[axisIndex], currentMachinePosition[axisIndex].units)]	#anything left as none is unchanged
			
		transformedCurrentAxisPositions = self.move.kinematics.reverse(currentMachinePosition)	#calculates the current axis positions based on the kinematics transformation matrix
		transformedRequestedAxisPositions = self.move.kinematics.reverse(requestedMachinePosition)	#calculates the requested axis positions based on the kinematics transformation matrix
		
		currentMotorPositions = []
		for axisIndex, axisPosition in enumerate(transformedCurrentAxisPositions):
			currentMotorPositions += [self.move.axes[axisIndex].reverse(axisPosition)]
		
		requestedMotorPositions = []
		for axisIndex, axisPosition in enumerate(transformedRequestedAxisPositions):
			requestedMotorPositions += [self.move.axes[axisIndex].reverse(axisPosition)]

		machineDeltas = [x-y for (x,y) in zip(requestedMachinePosition, currentMachinePosition)] #machine position deltas
		motorDeltas = [coordinates.uFloat(x - y, x.units) for (x,y) in zip(requestedMotorPositions, currentMotorPositions)]
		
		
		
		
		
		
		
		
		
		