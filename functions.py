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
import collections	#for deque in motion planner
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
		return self.actionObject(self)._init(*args, **kwargs)	#allows actionObject to return, actionCore is defined by the user
	
	def receiver(self, packet):
		decodedPacket = self.packet.decode(packet)
		self.packetHolder.put(decodedPacket)	#stores packet for use by calling outbound functions
		self.receive(decodedPacket)
		
	def receive(self, packet):	#this should get overridden
		self.responseFlag.set()  #by default, all it does is set the response flag.
		

class jog(object):
	def __init__(self, move):
		self.move = move
	
	def __call__(self, incrementalPosition = None, velocity = None, acceleration = None):
		currentMachinePosition = self.move.machinePosition.future()
		jogPosition = [(incremental + absolute) for incremental, absolute in zip(incrementalPosition, currentMachinePosition)]
		return self.move(jogPosition, velocity, acceleration)
				
class move(object):
	def __init__(self, virtualMachine = None, virtualNode = None, axes = None, kinematics = None, machinePosition = None, defaultAcceleration = 200):
		'''Configures the move object.'''
		
		#convert inputs to lists where appropriate
		if type(axes) != list: axes = [axes]
		
		self.virtualMachine = virtualMachine #a reference to the virtual machine which owns this function.
		self.virtualNode = virtualNode #a list of nodes which will be used by the function.
		self.axes = axes #a list of axes which connect physical actuators to the machine kinematics. Some nodes support multiple axes.
		self.kinematics = kinematics #a kinematics object which will transform between axis coordinates and machine coordinates
		self.machinePosition = machinePosition #the positional state of the machine.
		self.defaultAcceleration = defaultAcceleration	#the default accel/decel rate in mm/s^2
		
		#configure and start motion planner
		self.planner = self.motionPlanner()	#multi-block lookahead motion planner instance
		self.planner.daemon = True
		self.planner.start()
		
	def __call__(self, *args, **kwargs):
		return moveObject(self, *args, **kwargs)	#returns a move object which can be used by external synchronization methods
	
	class motionPlanner(threading.Thread):
		def __init__(self, queueSize = 50, queueTimeout = 0.1):
			threading.Thread.__init__(self)
			
			self.idleTime = 0.0005	#seconds
			self.queueTimeoutCycles = int(queueTimeout/self.idleTime)
			self.timeoutCount = 0	#when this equals queueTimeoutCycles, the queue is flushed
			
			self.plannerInput = Queue.Queue(1)	#only permit one input at a time.
			self.plannerQueue = collections.deque()
			self.resetMachineState()
			
		def run(self):
			while True:
				queueState, newMoveObject = self.getMoveObject()	#try to fetch a new move object
				if queueState:
					self.processMoves(newMoveObject)
					self.timoutCount = 0
				else:
					self.timeoutCount += 1
					if self.timeoutCount == self.queueTimeoutCycles:
						self.flushPlanner()
						self.timeoutCount = 0
				time.sleep(0.0005)

		def addMove(self, newMoveObject):
			'''Adds a new move to the motion planner queue.'''
			self.plannerInput.put(newMoveObject)
			return

		def processMoves(self, newMoveObject):
			'''Performs multi-block look-ahead algorithm.'''
			#For now, this is just a straight pass-thru.
			newMoveObject.release()
		
		def flushPlanner(self):
			pass
	
	
		def resetMachineState(self, velocity = 0.0, acceleration = 0.0):
			self.currentVelocity = velocity
			self.currentAcceleration = acceleration
		
		def getMoveObject(self):
			'''Will attempt to retrieve a new move object from the planner queue.'''
			try: 
				return True, self.plannerInput.get(block=False)
			except:
				return False, None
			
		

class moveObject(object):
	def __init__(self, move, position = None, velocity = None, acceleration = None):
		#store parameters
		self.move = move	#the calling move class
		self.positionCommand = position
		self.velocityCommand = velocity
		if acceleration:
			self.accelerationCommand = acceleration
		else:
			self.accelerationCommand = self.move.defaultAcceleration
		
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

#		machineDeltas = [x-y for (x,y) in zip(requestedMachinePosition, currentMachinePosition)] #machine position deltas
		motorDeltas = [coordinates.uFloat(x - y, x.units) for (x,y) in zip(requestedMotorPositions, currentMotorPositions)]
		
		actualMotorDeltas = [coordinates.uFloat(int(round(delta,0)), delta.units) for delta in motorDeltas]	#rounds steps down.
		
		#create actionObjects and commit to the channel priority queue
		self.actionObjects = self.move.virtualNode.spinRequest(axesSteps = actualMotorDeltas, accelSteps = 0, decelSteps = 0, accelRate = 0, external = True)
		self.actionObjects.commit()	#this will lock in their place in the transmit queue, however will not release until this move object is run thru the motion planner
		
		#commit self to the path planner.
		self.commit()
		
		#recalculate future machine position
		newMotorPositions = [coordinates.uFloat(x+y, x.units) for (x,y) in zip(actualMotorDeltas, currentMotorPositions)]
		
		transformedNewAxisPositions = []
		for motorIndex, motorPosition in enumerate(newMotorPositions):
			transformedNewAxisPositions += [self.move.axes[motorIndex].forward(motorPosition)]
		
		newMachinePosition = self.move.kinematics.forward(transformedNewAxisPositions)
		self.move.machinePosition.future.set(newMachinePosition)
		
		print "MACHINE POSITION:" + str(self.move.machinePosition.future())
		print "MOTOR DELTAS:" + str(motorDeltas)
		
	
	def commit(self):
		'''Adds this move to the motion planner.'''
		self.move.planner.addMove(self)
	
	def release(self):
		'''Releases all constituent spin objects to the real machine, making them no longer modifiable.'''
		self.actionObjects.release()
		
		
		
		
		