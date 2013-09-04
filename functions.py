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
import math	#for path length calculations
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
	def __init__(self, move, defaultJogSpeed = 20):	#20mm/s
		self.move = move
		self.defaultJogSpeed = defaultJogSpeed
	
	def __call__(self, incrementalPosition = None, velocity = None, acceleration = None):
		if velocity == None:
			velocity = self.defaultJogSpeed
		currentMachinePosition = self.move.machinePosition.future()
		jogPosition = [(incremental + absolute) for incremental, absolute in zip(incrementalPosition, currentMachinePosition)]
		return self.move(jogPosition, velocity, acceleration)
				
class move(object):
	def __init__(self, virtualMachine = None, virtualNode = None, axes = None, kinematics = None, machinePosition = None, defaultAcceleration = coordinates.uFloat(2000, "steps/s^2"), pullInSpeed = 4000, planner = None):
		'''Configures the move object.'''
		
		#convert inputs to lists where appropriate
		if type(axes) != list: axes = [axes]
		
		self.virtualMachine = virtualMachine #a reference to the virtual machine which owns this function.
		self.virtualNode = virtualNode #a list of nodes which will be used by the function.
		self.axes = axes #a list of axes which connect physical actuators to the machine kinematics. Some nodes support multiple axes.
		self.kinematics = kinematics #a kinematics object which will transform between axis coordinates and machine coordinates
		self.machinePosition = machinePosition #the positional state of the machine.
		self.defaultAcceleration = defaultAcceleration	#if no units are provided, it will be assumed in mm/s^2.
														#However, the default is in steps/s^2, corresponding to motor inertia dominance.
		self.pullInSpeed = pullInSpeed	#this is the maximum step rate at which the motors can change direction instantaneously.
										#Eventually, this should support different rates for each motor.
										#The default was chosen because a 400 step/rev stepper motor with 51oz-in driven at 24V and driving a small mechanical
										#load thru an 18T MXL pulley could pull in at 200mm/s or 2200 steps/sec. Assuming microstepping of 4, the pull-in speed
										#derated by 50% is 4000 uSteps/sec. 

		#configure and start motion planner										
		if planner == 'null':
			self.planner = self.nullMotionPlanner(self)
		else:	#use default planner
			self.planner = self.motionPlanner(self)	#multi-block lookahead motion planner instance

		self.planner.daemon = True
		self.planner.start()
		
	def __call__(self, *args, **kwargs):
		return moveObject(self, *args, **kwargs)	#returns a move object which can be used by external synchronization methods
	
	class motionPlanner(threading.Thread):
		def __init__(self, move, queueSize = 50, queueTimeout = 0.1):
			threading.Thread.__init__(self)
			
			self.move = move	#link to parent move function
			self.idleTime = 0.0005	#seconds
			self.queueTimeoutCycles = int(queueTimeout/self.idleTime)
			self.queueSize = queueSize
			self.timeoutCount = 0	#when this equals queueTimeoutCycles, the queue is flushed
			self.pullInAccelRate = math.pow(self.move.pullInSpeed,2)	#steps/sec in a period of time per step or 1/(steps/sec)
			
			self.plannerInput = Queue.Queue(1)	#only permit one input at a time.
			self.plannerQueue = collections.deque()
			self.resetMachineState()
			
			self.debugFile = open('motionPlannerDebugFile.txt', 'w')
			
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
				time.sleep(self.idleTime)

		def addMove(self, newMoveObject):
			'''Adds a new move to the motion planner queue.'''
			self.plannerInput.put(newMoveObject)
			return

		def processMoves(self, newMoveObject):
			'''Performs multi-block look-ahead algorithm.'''
			if newMoveObject.majorSteps > 0:	#only accept moves with a positive length
				self.plannerQueue.append(newMoveObject)	#add new object to the move queue
				
				#if more than one item in the queue, calculate junction velocity
				if len(self.plannerQueue)>1:
					self.generateJunctionVelocity(self.plannerQueue[-2], self.plannerQueue[-1])
				else:
					newMoveObject.entryJunctionMaxStepRate = self.currentStepRate
				
				self.forwardPass()
				self.reversePass()
				
				if len(self.plannerQueue) > self.queueSize:
					self.updateAndRelease(self.plannerQueue.popleft())	#pops and releases the oldest move in the planner queue.
			else:
				self.release(newMoveObject)
		
		def generateJunctionVelocity(self, entryMoveObject, exitMoveObject):
			'''Calculates the maximum junction velocity based on the pull in velocity limit and the directions of the entry and exit vectors.'''
			#calculate normalized entry and exit vectors
			entryNormalizedVector = self.normalizeVector(entryMoveObject.actualMotorDeltas)
			exitNormalizedVector = self.normalizeVector(exitMoveObject.actualMotorDeltas)
			
			#calculate maximum change in velocity over a single step based on direction change
			normalizedDeltas = [exit - entry for exit, entry in zip(exitNormalizedVector, entryNormalizedVector)]
			maxNormalizedDelta = max([abs(delta) for delta in normalizedDeltas])
			# given a junction speed of Vj, a change in velocity due to change in direction would occur over the period of a single step
			# which is 1/Vj. Thus the acceleration is Vj^2 * maximum change in normal vector. This latter component will vary between
			# -2 (complete reversal), -1 (corner), 0 (no change), 1 (corner), 2 (complete reversal)
			
			if maxNormalizedDelta != 0:
				maximumJunctionVelocity = math.sqrt(float(self.pullInAccelRate)/float(maxNormalizedDelta))
			else:
				maximumJunctionVelocity = 1000000000.0	#very big
			
			#this is the exit junction of the entry object, and the entry junction of the exit object
			entryMoveObject.exitJunctionMaxStepRate = maximumJunctionVelocity
			exitMoveObject.entryJunctionMaxStepRate = maximumJunctionVelocity
			

		def forwardPass(self):
			thisSegment = self.plannerQueue[-1]
				
			#choose the entry velocity for the segment.
			if len(self.plannerQueue)>1:
				priorSegment = self.plannerQueue[-2]
				thisSegment.forwardPassEntryStepRate = min(priorSegment.forwardPassExitStepRate, thisSegment.entryJunctionMaxStepRate,
															thisSegment.segmentMaxStepRate)
			else:
				thisSegment.forwardPassEntryStepRate = min(thisSegment.entryJunctionMaxStepRate, thisSegment.segmentMaxStepRate)
		
		
			accelLength = self.distanceFromVelocities(finalVelocity = thisSegment.segmentMaxStepRate,
												initialVelocity = thisSegment.forwardPassEntryStepRate,
												acceleration = thisSegment.segmentAccelRate)
		
			#restrict accel length accelLength < majorSteps
			if accelLength > thisSegment.majorSteps: accelLength = thisSegment.majorSteps
			thisSegment.accelSteps = int(accelLength)
		
			#update forward pass velocity for next segment
			thisSegment.forwardPassExitStepRate = self.velocityFromDistance(distance = thisSegment.accelSteps,
																		initialVelocity = thisSegment.forwardPassEntryStepRate,
																		acceleration = thisSegment.segmentAccelRate)


		def reversePass(self):
		
			#iterate thru the motion queue in reverse
			for segmentIndex, thisSegment in enumerate(reversed(self.plannerQueue)):
				if segmentIndex > 0:
					priorSegment = self.plannerQueue[-segmentIndex]
					thisSegment.reversePassExitStepRate = min(priorSegment.reversePassEntryStepRate, priorSegment.forwardPassEntryStepRate)
				else:
					thisSegment.reversePassExitStepRate = thisSegment.exitJunctionMaxStepRate
		
				#number of steps to decelerate from the segment entry velocity to the segment exit velocity 
				maxDecelLength = self.distanceFromVelocities(finalVelocity = thisSegment.forwardPassEntryStepRate,
														initialVelocity = thisSegment.reversePassExitStepRate,
														acceleration = thisSegment.segmentAccelRate)
		
				#decelerating for entire move
				if maxDecelLength > thisSegment.majorSteps:
					thisSegment.decelSteps = int(thisSegment.majorSteps)
					thisSegment.reversePassEntryStepRate = self.velocityFromDistance(distance = thisSegment.decelSteps,
																				initialVelocity = thisSegment.reversePassExitStepRate,
																				acceleration = thisSegment.segmentAccelRate)
					continue
		
				#decelerating for partial move
				decelLength = self.distanceFromVelocities(finalVelocity = thisSegment.segmentMaxStepRate,
													initialVelocity = thisSegment.reversePassExitStepRate,
													acceleration = thisSegment.segmentAccelRate)
		
				if decelLength + thisSegment.accelSteps < thisSegment.majorSteps:
					#profile reaches a steady velocity before deceleration
					thisSegment.decelSteps = int(decelLength)
					thisSegment.reversePassEntryStepRate = thisSegment.forwardPassEntryStepRate
				else:
					thisSegment.decelSteps = int(self.intersectionPoint(initialVelocity = thisSegment.forwardPassEntryStepRate,
																finalVelocity = thisSegment.reversePassExitStepRate,
																acceleration = thisSegment.segmentAccelRate,
																seperationDistance = thisSegment.majorSteps))
					thisSegment.reversePassEntryStepRate = thisSegment.forwardPassEntryStepRate

			
		def normalizeVector(self, inputVector):
			totalLength = math.sqrt(sum([float(math.pow(axis, 2)) for axis in inputVector]))
			if totalLength > 0:
				return [float(axis)/totalLength for axis in inputVector]
			else: return [0 for axis in inputVector]	#prevent divide by zero errors by returning a unit vector 
			
		@staticmethod
		def distanceFromVelocities(finalVelocity, initialVelocity, acceleration):
			distance = round((math.pow(finalVelocity,2) - math.pow(initialVelocity,2))/(2*acceleration))
			# Here we use the constant linear acceleration equation (Xf - Xi) = (Vf^2 - Vi^2)/2a
			if distance>0: return distance
			else: return 0.0
			
		@staticmethod
		def velocityFromDistance(distance, initialVelocity, acceleration):
			try:
				finalVelocity = math.sqrt(math.pow(initialVelocity, 2) + 2*float(acceleration)*float(distance))
				return finalVelocity
			except ValueError:
				return 0.0
		
		@staticmethod
		def intersectionPoint(initialVelocity, finalVelocity, acceleration, seperationDistance):
			'''This calculates the intersection point of two acceleration curves. The first
				starts at initial velocity and increases with acceleration, and the second
				starts at final velocity and increases with acceleration. The starting
				points are seperated by seperationDistance, and the return value is
				the distance of the intersection point from the final velocity position.'''
			return round((math.pow(initialVelocity,2) - math.pow(finalVelocity,2))/(4.0*acceleration) + seperationDistance / 2.0)			
		
		def updateAndRelease(self, segment):
			if segment.accelSteps + segment.decelSteps > segment.majorSteps:
				segment.accelSteps = int(segment.majorSteps - segment.decelSteps)	#decel steps are dominant

			self.debugFile.write("\n")
			self.debugFile.write("SEGMENT " + str(self.debugCount) + "\n")
			self.debugFile.write("---------------------------\n")
			self.debugFile.write("Major Steps: " + str(segment.majorSteps) + "\n")
			self.debugFile.write("Accel Steps: " + str(segment.accelSteps) + "\n")
			self.debugFile.write("Decel Steps: " + str(segment.decelSteps) + "\n")
			self.debugFile.write("Entry Junction Max Velocity: " + str(segment.entryJunctionMaxStepRate) + "\n")
			self.debugFile.write("Exit Junction Max Velocity: " + str(segment.exitJunctionMaxStepRate) + "\n")
			self.debugFile.write("Segment Velocity Limit: " + str(segment.segmentMaxStepRate) + "\n")
			self.debugFile.write("Starting Velocity: " + str(self.currentVelocity) + "\n")
			self.currentVelocity = self.velocityFromDistance(segment.accelSteps, self.currentVelocity, segment.segmentAccelRate)
			self.debugFile.write("Peak Velocity " + str(self.currentVelocity) + "\n")
			self.currentVelocity = self.velocityFromDistance(segment.decelSteps, self.currentVelocity, -segment.segmentAccelRate)
			self.debugFile.write("Ending Velocity: " + str(self.currentVelocity) + "\n")				
			self.debugCount += 1
			
			segment.update()
			segment.release()
		
		def release(self, segment):
			segment.release()
		
		def flushPlanner(self):
			if len(self.plannerQueue)>0:
				self.currentStepRate = self.plannerQueue[-1].reversePassExitStepRate	#store the closing step rate
				#release all objects in the queue
				for moveObject in self.plannerQueue:
					self.updateAndRelease(moveObject)
				#clear the queue
				self.plannerQueue.clear()
				self.debugFile.flush()
	
		def resetMachineState(self, velocity = 0.0, acceleration = 0.0):
			self.currentStepRate = velocity
			self.currentVelocity = 0
			self.debugCount = 0
		
		def getMoveObject(self):
			'''Will attempt to retrieve a new move object from the planner queue.'''
			try: 
				return True, self.plannerInput.get(block=False)
			except:
				return False, None
			
	class nullMotionPlanner(threading.Thread):	#performs no path planning, just releases objects as they arrive
		def __init__(self, move, queueSize = 50, queueTimeout = 0.1):
			threading.Thread.__init__(self)
			
			self.move = move	#link to parent move function
			self.idleTime = 0.0005	#seconds
			self.queueTimeoutCycles = int(queueTimeout/self.idleTime)
			self.queueSize = queueSize
			self.timeoutCount = 0	#when this equals queueTimeoutCycles, the queue is flushed
			
			self.plannerInput = Queue.Queue(1)	#only permit one input at a time.
			self.plannerQueue = collections.deque()
			self.resetMachineState()
			
			self.debugFile = open('motionPlannerDebugFile.txt', 'w')
			
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
				time.sleep(self.idleTime)

		def addMove(self, newMoveObject):
			'''Adds a new move to the motion planner queue.'''
			self.plannerInput.put(newMoveObject)
			return

		def processMoves(self, newMoveObject):
				self.release(newMoveObject)
		
		def release(self, segment):
			segment.release()
		
		def flushPlanner(self):
			if len(self.plannerQueue)>0:
				self.currentStepRate = self.plannerQueue[-1].reversePassExitStepRate	#store the closing step rate
				#release all objects in the queue
				for moveObject in self.plannerQueue:
					self.updateAndRelease(moveObject)
				#clear the queue
				self.plannerQueue.clear()
				self.debugFile.flush()
	
		def resetMachineState(self, velocity = 0.0, acceleration = 0.0):
			self.currentStepRate = velocity
			self.currentVelocity = 0
			self.debugCount = 0
		
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
		self.velocityCommand = float(velocity)
		if acceleration:
			self.accelerationCommand = acceleration
		else:
			self.accelerationCommand = self.move.defaultAcceleration

		if type(self.accelerationCommand) != coordinates.uFloat:
			self.accelerationCommand = coordinates.uFloat(self.accelerationCommand, "mm/s^2")
		#note: need to decide here whether rotor inertia or stage inertia is dominant.
		# If rotor inertia, the accel rate should be specified in steps/sec^2 rather than mm/sec^2
		# Default accel can be set in steps/sec^2
		# The typical stepper motor (I = 0.3 oz-in^2) has an equivalent inertia of 134kg thru a 10TPI leadscrew, or 0.6kg thru an 18T MXL pulley
		
		
		#calculate deltas
		currentMachinePosition = self.move.machinePosition.future()	#get the current machine position
		
		requestedMachinePosition = []	#build up the requested machine position based on what is provided and what is left as 'None'.
		for axisIndex, axisPosition in enumerate(self.positionCommand):
			requestedMachinePosition += [coordinates.uFloat(axisPosition if axisPosition != None else currentMachinePosition[axisIndex], currentMachinePosition[axisIndex].units)]	#anything left as none is unchanged
		
		#transform between machine and axis coordinates
		transformedCurrentAxisPositions = self.move.kinematics.reverse(currentMachinePosition)	#calculates the current axis positions based on the kinematics transformation matrix
		transformedRequestedAxisPositions = self.move.kinematics.reverse(requestedMachinePosition)	#calculates the requested axis positions based on the kinematics transformation matrix

		currentMotorPositions = []
		for axisIndex, axisPosition in enumerate(transformedCurrentAxisPositions):
			currentMotorPositions += [self.move.axes[axisIndex].reverse(axisPosition)]

		requestedMotorPositions = []
		for axisIndex, axisPosition in enumerate(transformedRequestedAxisPositions):
			requestedMotorPositions += [self.move.axes[axisIndex].reverse(axisPosition)]


		machineDeltas = [end - start for end, start in zip(requestedMachinePosition, currentMachinePosition)]
		machineLength = math.sqrt(sum([math.pow(position, 2) for position in machineDeltas]))	#gets cartesian length of move


		motorDeltas = [coordinates.uFloat(x - y, x.units) for (x,y) in zip(requestedMotorPositions, currentMotorPositions)]
		self.actualMotorDeltas = [coordinates.uFloat(int(round(delta,0)), delta.units) for delta in motorDeltas]	#rounds steps down.
		self.majorSteps = max([abs(delta) for delta in self.actualMotorDeltas])	#note: this gets used by the path planner
		if machineLength != 0:
			parameterRatio = float(self.majorSteps) / float(machineLength)	#this ratio relates velocities and accelerations between the coordinate systems
		else:
			parameterRatio = 0.0
		
		#calculate maximum step rates
		self.segmentMaxStepRate = self.velocityCommand * parameterRatio		#units of steps/sec
		
		#motion planner parameters. These will be modified by the motion planner
		self.entryJunctionMaxStepRate = 0	#default to zero in case this move is the first one
		self.exitJunctionMaxStepRate = 200	#need to fix this eventually, but a minimum rate is necessary to not stall the planner. This is the min exit rate.
		self.forwardPassEntryStepRate = 0	#used by the forward pass of the path planner
		self.forwardPassExitStepRate = 0
		self.reversePassEntryStepRate = 0	#used by the reverse pass of the path planner
		self.reversePassExitStepRate = 0
		self.accelSteps = 0
		self.decelSteps = 0
		
		if self.accelerationCommand.units == "mm/s^2":
			self.segmentAccelRate = self.accelerationCommand * parameterRatio	#transform along major axis, now in steps^s^2
		elif self.accelerationCommand.units == "steps/s^2":
			self.segmentAccelRate = self.accelerationCommand	#motor inertia dominant, don't change.
		
		#create actionObjects and commit to the channel priority queue
		self.actionObjects = self.move.virtualNode.spinRequest(axesSteps = tuple(self.actualMotorDeltas), accelSteps = 0, decelSteps = 0, accelRate = 0, external = True, majorSteps = self.majorSteps)	#note conversion to tuple.
		self.actionObjects.commit()	#this will lock in their place in the transmit queue, however will not release until this move object is run thru the motion planner
		
		#commit self to the path planner.
		self.commit()
		
		#recalculate future machine position
		newMotorPositions = [coordinates.uFloat(x+y, x.units) for (x,y) in zip(self.actualMotorDeltas, currentMotorPositions)]
		
		transformedNewAxisPositions = []
		for motorIndex, motorPosition in enumerate(newMotorPositions):
			transformedNewAxisPositions += [self.move.axes[motorIndex].forward(motorPosition)]
		
		newMachinePosition = self.move.kinematics.forward(transformedNewAxisPositions)
		self.move.machinePosition.future.set(newMachinePosition)
		
	
	def commit(self):
		'''Adds this move to the motion planner.'''
		self.move.planner.addMove(self)
	
	def update(self):
		'''Updates all action objects with new parameters.'''
		self.actionObjects.update(self.accelSteps, self.decelSteps, self.segmentAccelRate)
	
	def release(self):
		'''Releases all constituent spin objects to the real machine, making them no longer modifiable.'''
		self.actionObjects.release()
		
		
		
		
		