from gestalt import nodes
from gestalt import utilities
from gestalt.utilities import notice
from gestalt import functions as functions
from gestalt import packets as packets
from gestalt import core
import time
import math

class virtualNode(nodes.baseStandardGestaltNode):
	def init(self, **kwargs):
		pass
	
	def initParameters(self):
		#ADC parameters
		self.ADCRefVoltage = 5.0	#voltage divider to ref pin is 5V -> 10K -> REF -> 5K -> GND
		self.motorSenseResistor = 0.1	#ohms

		#stepping parameters
		self.maxSteps = 255	#one byte
		self.clockFrequency 	= 18432000.0	#Hz
		self.timeBaseTicks 		= 921.0	#clock cycles, this works out to around 20KHz
		self.timeBasePeriod 	= self.timeBaseTicks / self.clockFrequency	#seconds
		self.uStepsPerStep		= 1048576	#uSteps

		#axes parameters
		self.numberOfAxes = 1 #three axis driver

	def initFunctions(self):
		pass
		
	def initPackets(self):
		self.getReferenceVoltageResponsePacket = packets.packet(template = [packets.pInteger('voltage',2)])
		
		self.spinRequestPacket = packets.packet(template = [packets.pInteger('majorSteps',1),
															packets.pInteger('directions',1),
															packets.pInteger('steps', 1),
															packets.pInteger('accel',1),
															packets.pInteger('accelSteps',1),
															packets.pInteger('decelSteps',1),
															packets.pInteger('sync', 1)])	#if >0, indicates that move is synchronous
				
		self.spinStatusPacket = packets.packet(template = [packets.pInteger('statusCode',1),
															packets.pInteger('currentKey',1),
															packets.pInteger('stepsRemaining',1),
															packets.pInteger('readPosition',1),
															packets.pInteger('writePosition',1)])
		
		self.setVelocityPacket = packets.packet(template = [packets.pInteger('velocity',2)])
		
		
	def initPorts(self):
		#get reference voltage
		self.bindPort(port = 20, outboundFunction = self.getReferenceVoltageRequest, inboundPacket = self.getReferenceVoltageResponsePacket)
		
		#enable drivers
		self.bindPort(port = 21, outboundFunction = self.enableRequest)

		#disable drivers
		self.bindPort(port = 22, outboundFunction = self.disableRequest)
		
		#move
		self.bindPort(port = 23, outboundFunction = self.spinRequest, outboundPacket = self.spinRequestPacket,
								inboundPacket = self.spinStatusPacket)
		
		#set velocity
		self.bindPort(port = 24, outboundFunction = self.setVelocityRequest, outboundPacket = self.setVelocityPacket)
		
		#spin status
		self.bindPort(port = 26, outboundFunction = self.spinStatusRequest, inboundPacket = self.spinStatusPacket)
		
		#sync
		self.bindPort(port = 30, outboundFunction = self.syncRequest)
	

#----- API FUNCTIONS --------------------
	def setMotorCurrent(self, setCurrent):
		if setCurrent < 0 or setCurrent > 2.0:
			notice(self, "Motor current must be between 0 and 2.0 amps. " + str(setCurrent) + " was requested.")
		setCurrent = round(float(setCurrent), 1)
		while True:
			motorVoltage = self.getReferenceVoltage()
			motorCurrent = round(motorVoltage /(8.0*self.motorSenseResistor),2)	#amps
			if round(motorCurrent,1) > setCurrent:
				notice(self, "Motor current: " + str(motorCurrent) + "A / " + "Desired: " + str(setCurrent) + "A. Turn trimmer CW.")
			elif round(motorCurrent,1) < setCurrent:
				notice(self, "Motor current: " + str(motorCurrent) + "A / " + "Desired: " + str(setCurrent) + "A. Turn trimmer CCW.")
			else:
				notice(self, "Motor current set to: " + str(motorCurrent) + "A")
				break;
			time.sleep(0.5)
		

	def getReferenceVoltage(self):
		ADCReading = self.getReferenceVoltageRequest()
		if ADCReading:
			return self.ADCRefVoltage * ADCReading / 1024.0
		else:
			return False
	
	def enableMotorsRequest(self):
		return self.enableRequest()
	
	def disableMotorsRequest(self):
		return self.disableRequest()
		
#----- SERVICE ROUTINES -----------------
	class enableRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self):
				self.setPacket({})
				self.commitAndRelease()
				self.waitForChannelAccess()
				if self.transmitPersistent(): 
					notice(self.virtualNode, "Stepper motor enabled.")
					return True
				else: 
					notice(self.virtualNode, "Stepper motor could not be enabled.")
					return False
	
	class disableRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self):
				self.setPacket({})
				self.commitAndRelease()
				self.waitForChannelAccess()
				if self.transmitPersistent(): 
					notice(self.virtualNode, "Stepper motor disabled.")
					return True
				else: 
					notice(self.virtualNode, "Stepper motor could not be disabled.")
					return False

	class getReferenceVoltageRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self):
				self.setPacket({})
				self.commitAndRelease()
				self.waitForChannelAccess()
				if self.transmitPersistent(): return self.getPacket()['voltage']
				else: return False
	
	class spinStatusRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self):
				self.setPacket({})
				self.commitAndRelease()
				self.waitForChannelAccess()
				if self.transmitPersistent():
					return self.getPacket()
				else:
					notice(self.virtualNode, 'unable to get status from node.')	

	class setVelocityRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self, velocity):
				#velocity is in steps/sec
				velocity = int(round((velocity * self.virtualNode.uStepsPerStep * self.virtualNode.timeBasePeriod)/16.0,0)) #convert into 16*uSteps/timebase
				print velocity
				self.setPacket({'velocity': velocity})
				self.commitAndRelease()
				self.waitForChannelAccess()
				if self.transmitPersistent():
					return True
				else:
					notice(self.virtualNode, 'unable to set velocity.')
					return False

	class spinRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self, axesSteps, accelSteps = 0, decelSteps = 0, accelRate = 0, external = False, sync = False, majorSteps = None):
				# axesSteps: a list containing the number of steps which each axis of the node should take in synchrony.
				# accelSteps: number of virtual major axis steps during which acceleration should occur.
				# deccelSteps: number of virtual major axis steps during which deceleration should occur.
				# accelRate: accel/decel rate in steps/sec^2 
				# external: indicates whether the actionObject will be commited to its interface externally.
				#			When False, the actionObject will self commit and release.
				#			When True, the actionObject will prepare a packet but will need to be commited and release externally.
				# sync: indicates that this actionObject will be synchronized externally and that parameters might change. This will prevent it from spawning.
				# majorSteps: this parameter is only called internally when a request calls for too many steps for one actionObject and the actionObject needs to spawn.
				if type(axesSteps) != list and type(axesSteps) != tuple: axesSteps = [axesSteps]
				self.axesSteps = [int(axis) for axis in axesSteps]	#list of steps to take in each axis e.g. [x, y, z]. May be provided as a tuple.
				self.accelSteps = accelSteps
				self.decelSteps = decelSteps
				self.accelRate = accelRate
				self.external = external
				self.sync = sync
				self.actionSequence = False #start out with no action sequence
				self.sequenceMajorSteps = None	#if this actionObject becomes an actionSequence parent, this will store the list of major axes
				
				#calculate virtual major axis
				if majorSteps:	#if provided externally, use that.
					self.majorSteps = majorSteps
				else:	#generate majorSteps from provided axes.
					self.majorSteps = max([abs(axis) for axis in self.axesSteps])
				
				if self.majorSteps > self.virtualNode.maxSteps:	#check if step request exceeds maximum length
					if not sync:	#no other anticipated recalculations, so go ahead and generate actionSequence
						#need to generate an actionSequence with multiple new actionObjects
						self.actionSequence = self.actionSequenceGen()
						return self.actionSequence
					else:	#the majorSteps has not yet been synchronized, so cannot generate an action sequence yet.
						return self
					
				else: #step request is executable by this action object. Either initial request met this criteria, or this actionObject was initialized by actionSequence().
					#calculate directions
					directions = [1 if axis>0 else 0 for axis in self.axesSteps]
					directionMultiplexer = [2**b for b in range(self.virtualNode.numberOfAxes-1, -1, -1)] #generates [2^n, 2^n-1,...,2^0]
					self.directionByte = sum(map(lambda x,y: x*y, directionMultiplexer, directions))	#directionByte is each term of directionMultiplexer multiplied by the directions and then summed.					

					if external or sync:	#actionObject is being managed by an external function and shouldn't auto-commit
						return self
					else:
						#set packet
						accelRate = self.tbAccelRate(self.accelRate)	#convert accel rate into timebase
						self.setPacket({'majorSteps':self.majorSteps, 'directions':self.directionByte, 'steps':abs(self.axesSteps[0]), 'accel':accelRate, 
									'accelSteps':accelSteps, 'decelSteps':decelSteps})
						
						self.commitAndRelease()
						self.waitForChannelAccess()
						moveQueued = False
						while not moveQueued:
							if self.transmitPersistent():
								responsePacket = self.getPacket()
								moveQueued = bool(responsePacket['statusCode'])	#False if move was not queued
								time.sleep(0.02)
							else: 
								notice(self.virtualNode, "got no response to spin request")
								return False
						return responsePacket
			
			def syncPush(self):
				'''Stores this actionObject's sync tokens to the provided syncToken.'''
				if self.sync:
					self.sync.push('majorSteps', self.majorSteps)
			
			def syncPull(self):
				'''Actually does the synchronization based on the tokens stored in self.sync.'''
				if self.sync:
					self.majorSteps = int(max(self.sync.pull('majorSteps')))
					if self.majorSteps > self.virtualNode.maxSteps:
						self.actionSequence = self.actionSequenceGen()
						return self.actionSequence
					else:
						return self
				
			
			def channelAccess(self):
				'''This gets called when channel access is granted. 
				To prevent double-transmission, only transmit if external is True.'''				
				if self.external:
						#set packet
					accelRate = self.tbAccelRate(self.accelRate)	#convert accel rate into timebase
					self.setPacket({'majorSteps':self.majorSteps, 'directions':self.directionByte, 'steps':abs(self.axesSteps[0]), 'accel':accelRate, 
								'accelSteps':self.accelSteps, 'decelSteps':self.decelSteps, 'sync':int(bool(self.sync))})
					#since this node was instantiated under external control, it did not auto-transmit.
					moveQueued = False
					while not moveQueued:
						if self.transmitPersistent():
							responsePacket = self.getPacket()
							print responsePacket
							moveQueued = bool(responsePacket['statusCode']) #False if move was not queued, meaning buffer is full
							if not moveQueued: time.sleep(0.02)	#wait before retransmitting
						else:
							notice(self.virtualNode, "got no response to spin request")


			def splitNumber(self, value, segments):
				'''Returns a list of integers (length segments) whose sum is value.
				
				This algorithm should produce similar results to the bresenham algorithm without needing to iterate.'''
				#e.g. splitNumber(800, 7)
				integers = [int(value/segments) for i in range(segments)]	#[114, 114, 114, 114, 114, 114, 114]
				remainder = value - sum(integers)	#2
				distributedRemainder = remainder/float(segments)	#0.285...
				remainderSequence = [0] + [distributedRemainder*i - round(distributedRemainder*i,0) for i in range(1, 1+segments)]	#[0.285, -0.428, -0.142, 0.142, 0.428, -0.285, 0.0]
				extraSteps = map(lambda x,y: 1 if x>y else 0, remainderSequence[:-1], remainderSequence[1:]) #[0, 1, 0, 0, 0, 1, 0] passes negative steps
				return map(lambda x,y: x+y, integers, extraSteps) #[114, 115, 114, 114, 114, 115, 114]

			def fillFront(self, fillNumber, binSizes):
				'''Fills a series of bins whose size are specified by fillList, starting with the first bin.'''
				filledBins = [0 for bin in binSizes]
				for binIndex, binSize in enumerate(binSizes):
					if fillNumber > binSize:
						filledBins[binIndex] = binSize
						fillNumber -= binSize
					else:
						filledBins[binIndex] = fillNumber
						fillNumber = 0
				return filledBins
			
			def fillBack(self, fillNumber, binSizes):
				'''Fills a series of bins whose size are specified by fillList, starting with the last bin.'''
				reversedBinSizes = list(binSizes)	#makes a copy
				reversedBinSizes.reverse()
				filledBins = self.fillFront(fillNumber, reversedBinSizes)
				filledBins.reverse()
				return filledBins
			

			def actionSequenceGen(self):	#need to generate an action sequence to accommodate the request
				'''Returns an actionSequence which contains a sequential set of actionObjects.'''
				segments = int(math.ceil(self.majorSteps/float(self.virtualNode.maxSteps)))	#number of actionObjects needed to address requested number of steps
				axesSteps = zip(*[self.splitNumber(axisSteps, segments) for axisSteps in self.axesSteps])	#a list of axesSteps lists which are divided into the necessary number of segments
				majorSteps = self.splitNumber(self.majorSteps, segments)	#a list of majorSteps which are divided into the necessary number of segments
				self.sequenceMajorSteps = majorSteps	#store at the actionObject level for when parameters need to be updated later.
				accelSteps = self.fillFront(self.accelSteps, majorSteps)	#a list of accelSteps which fills bins of maximum size majorSteps starting from the front
				decelSteps = self.fillBack(self.decelSteps, majorSteps)	#a list of decelSteps which fills bins of maximum size majorSteps starting from the back
				accelRate = [self.accelRate for segment in range(segments)]
				external = [self.external for segment in range(segments)]
				sync = [self.sync for segment in range(segments)]
				
				return self.__actionSequence__(axesSteps, accelSteps, decelSteps, accelRate, external, sync, majorSteps)
			
			def update(self, accelSteps = 0, decelSteps = 0, accelRate = 0):
				'''Updates the acceleration and deceleration parameters for the spin actionObject.'''
				
				if self.actionSequence:	#this actionObject is the parent of an actionSequence. Update the whole sequence
					accelSteps = self.fillFront(accelSteps, self.sequenceMajorSteps)
					decelSteps = self.fillBack(decelSteps, self.sequenceMajorSteps)
					accelRates = [accelRate for majorSteps in self.sequenceMajorSteps]
					
					for actionObject, args in zip(self.actionSequence.actionObjects, zip(accelSteps, decelSteps, accelRates)):
						actionObject.update(*args)
				else:
					self.accelSteps = accelSteps
					self.decelSteps = decelSteps
					self.accelRate = accelRate

			
			def tbAccelRate(self, accelRate):
				'''Converts acceleration from steps/sec^2 to uSteps/timeBase^2.'''
				return int(round(accelRate * self.virtualNode.uStepsPerStep * self.virtualNode.timeBasePeriod * self.virtualNode.timeBasePeriod,0)) #uSteps/timePeriod^2

	class syncRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self):
				self.mode = 'multicast'
			def channelAccess(self):
				self.transmit()
