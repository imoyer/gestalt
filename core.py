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
		'''Returns a packet waiting in the packet holder.'''
		return self.serviceRoutine.packetHolder.get()
	
	def __actionSequence__(self, *argLists):
		'''Returns an actionSequence filled with recursively called actionObjects using parameters stored in argLists.'''
		return actionSequence(actionObjects = [self.new(*args) for args in zip(*argLists)], parent = self)
	

class actionSequence(object):
	'''Stores a series of action objects which should get executed sequentially.'''
	def __init__(self, actionObjects = None, parent = None):
		self.actionObjects = actionObjects
		self.parent = parent	#this is the spawning action object
	
	def  __getattr__(self, attribute):
		'''	Forwards all unsupported calls to the parent actionObject.'''
		if hasattr(self.parent, attribute):	#parent actionObject contains requested attribute
			return getattr(self.parent, attribute)
		else:
			notice(self, "ActionObject DOESN'T HAVE REQUESTED ATTRIBUTE")
			raise AttributeError(attribute)
	
	def commit(self):
		'''Commits all member actionObjects to their interface's priority queue.'''
		for actionObject in self.actionObjects:
			actionObject.commit()
	
	def release(self):
		for actionObject in self.actionObjects:
			actionObject.release()

class actionSet(object):
	'''Stores a set of actionObjects which should be executed simultaneously.'''
	def __init__(self, actionObjects):
		self.actionObjects = actionObjects
		
	def commit(self):
		for actionObject in self.actionObjects:
			actionObject.commit()
	
	def update(self, *args, **kwargs):
		for actionObject in self.actionObjects:
			actionObject.update(*args, **kwargs)
	def release(self, *args, **kwargs):
		
		for actionObject in self.actionObjects:
			actionObject.release(*args, **kwargs)


class syncToken(object):
	'''Contains tokens used by nodes to synchronize with each other.'''
	def __init__(self):
		self.tokens = {}
		
	def push(self, tokenName, tokenValue):
		if tokenName in self.tokens:
			#token exists, add a value to it.
			self.tokens[tokenName] += [tokenValue]
		else:
			self.tokens.update({tokenName:[tokenValue]})
	
	def pull(self, tokenName):
		if tokenName in self.tokens:
			return self.tokens[tokenName]
		else:
			return None
			
			