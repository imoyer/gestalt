# gestalt.functions
#
# Contains the basic elements for building Gestalt functions.

#----IMPORTS------------
from gestalt.machines import coordinates
from gestalt import utilities
from gestalt import core
import time
import Queue
import threading
#----FUNCTIONS--------------

class serviceRoutine(object):
	'''A function which spawns an action item that will eventually be executed on the network.
	
		The expected pattern is as follows:
		1) A call to serviceRoutine causes an actionObject to be created.
		2) This actionObject eventually gets access to the network.
		3) actionObject transmits a packet to its physical counterpart.
		4) When a response arrives, it is routed by the virtual node to the response serviceRoutine.
		5) Response service routine calls its receive method.
		6) Receive method might update machine state, etc.
		7) Receive method sets the responseFlag, signaling to the actionObject that a response has arrived.
		8) actionObject reacts to message, either by returning something to the calling method, transmitting another packet, etc...
		
		Note that because only action object has access to the network at a time, it will block in the channelAccessQueue until a response is received.
		However because serviceRoutine is running in the interface receiver routing queue, it can asynchronously update the machine state.
	'''
	def __init__(self, virtualNode = None, packetSet = None, responseFlag = None, packetHolder = None):
		'''Service routines are instantiated by nodes.baseGestaltNode.bindPort.'''
		self.virtualNode = virtualNode	#reference to owning virtual node
		self.packetSet = packetSet	#The packet encoder
		self.packet = packetSet.Packet #a reference to the packet format for decoding purposes
		self.responseFlag = responseFlag	#responseFlag is shared between serviceRoutine and actionObject
		self.packetHolder = packetHolder	#will contain an inbound packet for transfer between the serviceRoutine and the actionObject	
	
	def __call__(self, *args, **kwargs):
		return self.actionObject(self)._init(*args, **kwargs)	#allows gFunctionObject to return, gFunctionCore is defined by the user
	
	def receiver(self, packet):
		decodedPacket = self.packet.decode(packet)
		self.packetHolder.put(decodedPacket)	#stores packet for use by calling outbound functions
		self.receive(decodedPacket)
		
	def receive(self, packet):	#this should get overridden
		self.responseFlag.set()  #by default, all it does is set the response flag.


class motionPlanner(threading.Thread):
	def __init__(self, virtualMachine):
		self.virtualMachine = virtualMachine
		threading.Thread.__init__(self) #initialize via threading superclass
		self.plannerQueue = Queue.Queue(1)	#new planner queue, max size is 1 because want to control internal size of list

	def run(self):
		while True:
			time.sleep(0.0005)
				
				
				
				
				
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
		
		
		
		
		
		
		
		
		
		