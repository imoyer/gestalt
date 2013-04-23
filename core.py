# gestalt.core
# 
# This module provides the core functionality of gestalt: compiling a series of function calls and executing them on a distributed hardware network.

#--IMPORTS-----
import threading
from gestalt.utilities import notice as notice

class actionObject(object):
	def __init__(self, serviceRoutine):
		self.serviceRoutine = serviceRoutine	#the service routine which created this actionObject.
		self.virtualNode = serviceRoutine.virtualNode	#the virtual node which owns the service routine which created this actionObject
		self.interface = self.virtualNode.interface	#reference to the interface for the virtual node
		self.packetEncoder = self.serviceRoutine.packetSet
		self.packetSet = [[]]	#initialize packet set to a blank packet for now.
		self.mode = 'unicast'	#mode determines whether the packet is transmitted as unicast or multicast
		self.port = self.virtualNode.bindPort.outPorts[self.serviceRoutine]	#this is the port to be used in communicating with the matching service routine in hardware
		self.clearToRelease = threading.Event()	#when set, this flag indicates that the action object is cleared to gain channel access
		self.channelAccessGranted = threading.Event() #when set, this flag indicates that the action object has been granted channel access
		self._type_ = 'actionObject'	#used by the channelPriority queue
	
	def _init(self, *args, **kwargs):
		returnObject = self.init(*args, **kwargs) #run user provide initialization function
		if returnObject != None: return returnObject	#return whatever is returned by the user
		else: return self	#otherwise return self
	
	def new(self, *args, **kwargs):
		'''Will create a new instance of self, duplicating references created on instantiation.'''
		return self.__class__(self.serviceRoutine)._init(*args, **kwargs)	#this is the same as what's called by the serviceRoutine
	
	def setPacket(self, packet, mode = 'unicast'):
		self.packetSet = self.packetEncoder(packet)
		self.mode = mode

	def transmit(self):
		'''Sends a packet over the interface to the matching physical node.
		Note that this method will only be called within the interface channelAccess thread, which guarantees that the channel is avaliable.'''
		if self.channelAccessGranted.is_set():
			self.interface.transmit(virtualNode = self.virtualNode, port = self.port, packetSet = self.packetSet, mode = self.mode)
		else:
			notice(self.virtualNode, 'tried to transmit without channel access!')

	def transmitPersistent(self, tries = 10, timeout = 0.2):
		'''Transmit a packet until a response is received.'''
		for i in range(tries):
			self.transmit()
			if self.waitForResponse(timeout): return True
			notice(self.virtualNode, 'Could not reach virtual node. Retrying (#' + str(i+2) + ')')	#i starts at 0, and when this gets called already tried once.
		return False

	def waitForResponse(self, timeout = None):
		if self.serviceRoutine.responseFlag.wait(timeout):
			self.serviceRoutine.responseFlag.clear()	#clears response flag in case it wasn't cleared by the response service routine
			return True	#response was received
		return False #response wasn't received
	
	def release(self):
		self.clearToRelease.set()
		return True
	
	def isReleased(self):
		return self.clearToRelease.is_set()
	
	def init(self):
		'''This method gets called when the action object is instantiated.
		
		It should be overridden by the user.'''
		pass
	
	def waitForChannelAccess(self, timeout = None):
		'''Can be called by the user init function if it needs to return a response.'''
		if self.channelAccessGranted.wait(timeout):
			return True #access has been granted
		return False #access was not received in time.
	
	def grantAccess(self):
		'''This method gets called by the interface when this actionObject has been granted access to the channel.'''
		self.channelAccessGranted.set()	#sets the channel access flag
		self.channelAccess() #calls the user function. This is most useful for when the node call doesn't return anything.
	
	def channelAccess(self):
		'''The user method that gets called when the actionObject has been granted access to the channel.'''
		pass
	
	def commit(self):
		'''Commits this actionObject to its interface's priority queue'''
		self.interface.commit(self)
		
	def commitAndRelease(self):
		'''Commits this actionObject to its interface's priority queue and releases for channel access.'''
		self.release()
		self.interface.commit(self)
		
	
	def getPacket(self):
		return self.serviceRoutine.packetHolder.get()


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