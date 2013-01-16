#----IMPORTS------------
import imp	#for importing files as modules
import random
import threading
import time
import os
import urllib
from gestalt.utilities import notice as notice
from gestalt import interfaces
from gestalt import functions
from gestalt import packets


#----NODE SHELLS------------
class baseNodeShell(object):
	'''	The basic container for all nodes.
		
		Like a room in a hotel, that has different occupants and offers certain amenities to its guests.
		baseNodeShell gets subclassed by more specific shells for one of the four types of gestalt nodes:
		->Solo/Independent: arbitrary interface/ arbitrary protocol
		->Solo/Gestalt: arbitrary interface/ gestalt protocol
		->Networked/Gestalt: networked gestalt interface/ gestalt protocol
		->Managed/Gestalt: hardware synchronized gestalt network/ gestalt protocol'''

	def __init__(self):
		'''Typically this will be overriden, but should be called by the child class.
		
		This behavior is being allowed because the child class will always belong to the nodes module.'''
		#create an interface shell for self.
		self.interface = interfaces.interfaceShell()

	def acquire(self):
		'''gets the identifier for either the interface or the node'''
		pass
	
	
	def hasNode(self):
		'''Checks if shell contains a node.'''
		if hasattr(self, 'node'): return True
		else: return False


	def  __getattr__(self, attribute):
		'''	Forwards any unsupported calls to the shell onto the node.'''
		if self.hasNode():	#Shell contains a node.
			if hasattr(self.node, attribute):	#node contains requested attribute
				return getattr(self.node, attribute)
			else:
				notice(self, "NODE DOESN'T HAVE REQUESTED ATTRIBUTE")
				raise AttributeError(attribute)
		else:
			notice(self, "NODE IS NOT INITIALIZED")
			raise AttributeError(attribute)

	def setNode(self, node):
		'''sets the node'''
		#assign node
		self.node = node
		
		#pass shell references to node
		self.node.shell = self	#give the node a reference to the shell
		self.node.name = self.name	#give node the same name as shell (for notice function)
		self.node.interface = self.interface #give node a reference to the interface

		#finish initializing node
		self.node._init(**self.node.initKwargs)
		self.node.init(**self.node.initKwargs)

	def loadNodeFromFile(self, filename, **kwargs):
		''' Loads a node into the node shell from a provided filename.
		
			Assumes that this is called from a node shell that has defined self.name'''
		try: 
			self.setNode(imp.load_source('', filename).virtualNode(self, **kwargs))
			notice(self, "loaded node from:  " + filename)
			return True
		except IOError:
			notice(self, "error loading file.")
			return False
	
	
	def loadNodeFromURL(self, URL, **kwargs):
		'''Loads a node into the node shell from a provided URL.
		
			Assumes that this is called form a node shell that has defined self.name'''
		try:
			VNFilename = os.path.basename(URL)	#gets filename
			urllib.urlretrieve(URL, VNFilename)
			notice(self, "downloaded " + VNFilename + " from " + URL)
			return self.loadNodeFromFile(VNFilename, **kwargs)	#stores file to local directory for import.
																#same name is used so that local import works if internet is later down.
		except IOError:
			notice(self, "could not load " + VNFilename + " from " + URL)
			notice(self, "Attempting to load file from local directory...")
			return self.loadNodeFromFile(VNFilename, **kwargs)	#attempt to load file locally		

	def loadNodeFromModule(self, module, **kwargs):
		'''Loads a node into the node shell from the provided class.
		
		Note that class itself should be provided, NOT a class instance.'''
		try:
			if hasattr(module, 'virtualNode'):
				self.setNode(module.virtualNode(**kwargs))
			else:
				self.setNode(module(**kwargs))
			notice(self, "loaded module " + str(module.__name__))
			return True
		except AttributeError:
			notice(self, "unable to load module.")
			return False


class soloIndependentNode(baseNodeShell):
	''' A container shell for Solo/Independent nodes.
	
		Solo/Independent nodes are non-networked and may use an arbitrary communications protocol.
		For example, they could be a third-party device with a python plug-in, etc...
	'''
	def __init__(self, name = None, interface = None, filename = None, URL = None, module = None, **kwargs):
		'''	Initialization procedure for Solo/Independent Node Shell.
			
			name:		a unique name assigned by the user. This is used by the persistence algorithm to re-acquire the node.
			interface: 	the object thru which the virtual node communicates with its physical counterpart.
			**kwargs:	any additional arguments to be passed to the node during initialization
			
			Methods of Loading Virtual Node:
				filename: an import-able module containing the virtual node.
				URL: a URL pointing to a module as a resource containing the virtual node.
				module: a python module name containing the virtual node.
		'''
		
		#call base class __init__ method
		super(soloIndependentNode, self).__init__()
		
		#assign parameters to variables
		self.name = name
		self.filename = filename
		self.URL = URL
		self.module = module
		self.interface.set(interface, self)	#interface isn't shared with other nodes, so owner is self.
		
		#acquire node. For an SI node, some method of acquisition MUST be provided, as it has no protocol for auto-loading.
		#load via filename
		if filename:
			self.loadNodeFromFile(filename, **kwargs)
		#load via URL
		elif URL:
			self.loadNodeFromURL(URL, **kwargs)
		#load via module
		elif module:
			self.loadNodeFromModule(module, **kwargs)
		else:
			notice(self, "no node source was provided.")
			notice(self, "please provide a filename, URL, or class")

class gestaltNodeShell(baseNodeShell):
	'''Base class for all nodes which communicate using the gestalt protocol.'''
	def __init__(self):
		super(gestaltNodeShell, self).__init__()	#call init on baseNodeShell

	def generateIPAddress(self):
		'''Generates a random IP address.'''
		while True:
			IP = [random.randint(0,255), random.randint(0,255)]	
			if self.interface.validateIP(IP): break	#checks with interface to make sure IP address isn't taken.
		return IP

class soloGestaltNode(gestaltNodeShell):
	'''	A container shell for Solo/Gestalt nodes.
	
		Solo/Gestalt nodes are non-networked and use the gestalt communications protocol.
		For example they might make use of the gsArduino library.'''

	def __init__(self, name = None, interface = None, filename = None, URL = None, module = None, **kwargs):
		'''	Initialization procedure for Solo/Independent Node Shell.
			
			name:		a unique name assigned by the user. This is used by the persistence algorithm to re-acquire the node.
			interface: 	the object thru which the virtual node communicates with its physical counterpart.
			**kwargs:	any additional arguments to be passed to the node during initialization
			
			Methods of Loading Virtual Node:
				filename: an import-able module containing the virtual node.
				URL: a URL pointing to a module as a resource containing the virtual node.
				module: a python module name containing the virtual node.
		
			Solo/Gestalt virtual nodes initialize by first connecting to their interface and then requesting
			a driver URL from the node. This driver is then loaded into the shell as the virtual node.
		'''

		#call base class __init__ method
		super(soloGestaltNode, self).__init__()
		
		#assign parameters to variables
		self.name = name
		self.filename = filename
		self.URL = URL
		self.module = module
		
		#connect to interface
		if interface:
			self.interface.set(interface, self)	#interface isn't shared with other nodes, so owner is self.		
		else:
			self.interface.set(interfaces.gestaltInterface(interface = interfaces.serialInterface(baudRate = 76800, interfaceType = 'lufa'), owner = self), self)
		#import base node
		self.setNode(baseSoloGestaltNode())		
		
		#set node IP address	-- this will be changed later once persistence is added
		IP = self.generateIPAddress()	#generate random IP address
		self.interface.assignNode(self.node, IP)	#assign node to interface with IP address
		nodeURL = self.node.setIPRequest(IP)	#set real node's IP address, and retreive URL
		
		#if a virtual node source is provided, use that. Otherwise acquire from URL provided by node.
		if filename:
			if not self.loadNodeFromFile(filename, **kwargs): return
		#load via URL
		elif URL:
			if not self.loadNodeFromURL(URL, **kwargs): return
		#load via module
		elif module:
			if not self.loadNodeFromModule(module, **kwargs): return
		#get URL from node
		else:
			if not self.loadNodeFromURL(nodeURL): return
			
		#assign new node with old IP address to interface
		self.interface.assignNode(self.node, IP)
		

#----VIRTUAL NODES------------
	
class baseVirtualNode(object):
	'''base class for creating virtual nodes'''
	def __init__(self, **kwargs):
		'''	Initializer for virtualNode base class.
		
			Initialization occurs in three steps:
			1) baseVirtualNode gets initialized when instantiated
			2) node shell loads references into node thru setNode method of baseNodeShell class
			3) _init and init are called by setNode method.
			The purpose of this routine is to initialize the nodes once they already have references to their shell.'''
		self.initKwargs = kwargs
		
	def _init(self, **kwargs):
		'''Dummy initializer for child class.'''
		pass
	
	def init(self, **kwargs):
		'''Dummy initializer for terminal child class.'''
		pass
		
		
class baseSoloIndependentNode(baseVirtualNode):
	'''base class for solo/independent virtual nodes'''
	pass
		
class baseGestaltNode(baseVirtualNode):
	'''base class for all gestalt nodes'''
	def _init(self, **kwargs):
		self.bindPort = self.bindPort(self)	#create binder function for node

		self._initParameters()
		self.initParameters()
		self._initFunctions()
		self.initFunctions()
		self._initPackets()
		self.initPackets()
		self._initPorts()
		self.initPorts()
		#//FIX// need to make response flags specific to ports, otherwise packets can be recognized cross-port
		self.responseFlag = threading.Event()	#this object is used for nodes to wait for a response
		
	def _initParameters(self):
		return
	def initParameters(self):
		return
	def _initFunctions(self):
		return
	def initFunctions(self):
		return
	def _initPorts(self):
		return
	def initPorts(self):
		return
	def _initPackets(self):
		return
	def initPackets(self):
		return
	def _initLast(self):
		return
	def initLast(self):
		return
	
	def transmit(self, nodeSet, mode = 'unicast'):
		self.interface.transmit(nodeSet, mode)
	
	def route(self, port, packet = None):
		if packet == None: packet = []
		if port in self.bindPort.inPorts: destinationFunction = self.bindPort.inPorts[port]
		else:
			print str(self)+ " RECEIVED A PACKET TO UNKOWN PORT " + str(port)
			return
		destinationFunction.receiver(packet)
		return
	
	
	class bindPort():
		def __init__(self, nodeInstance):
			self.nodeInstance = nodeInstance
			self.outPorts = {}	#ports for outbound packets {function:port#}
			self.inPorts = {}	#functions for inbound packets {port#:function}

		def __call__(self, port, outboundFunction = None, outboundPacket = None, inboundFunction = None, inboundPacket = None):
			newResponseFlag = threading.Event()
			packetHolder = packets.packetHolder()
			
			#---CREATE FUNCTION INSTANCES AND UPDATE ROUTE DICTIONARIES---				
			if outboundFunction:
				if type(outboundFunction) == type: setattr(self.nodeInstance, outboundFunction.__name__, outboundFunction())	#create function instance
				outboundFunction = getattr(self.nodeInstance, outboundFunction.__name__)	#update in event that new instance was created
				self.outPorts.update({outboundFunction:port})	#bind port to outbound instance
				outboundFunction.packetSet = packets.packetSet(outboundPacket)
				outboundFunction.virtualNode = self.nodeInstance
				outboundFunction.responseFlag = newResponseFlag	#creates a common response flag for outbound and inbound functions
				outboundFunction.packetHolder = packetHolder #creates a common packet holder for outbound and inbound functions
				
			if inboundFunction:
				if type(inboundFunction) == type: setattr(self.nodeInstance, inboundFunction.__name__, inboundFunction())	#create function instance
				inboundFunction = getattr(self.nodeInstance, inboundFunction.__name__)
				self.inPorts.update({port:inboundFunction})	#bind port to inbound instance
				inboundFunction.packet = inboundPacket
				inboundFunction.virtualNode = self.nodeInstance
				inboundFunction.responseFlag = newResponseFlag	#creates a common response flag for outbound and inbound functions
				inboundFunction.packetHolder = packetHolder #creates a common packet holder for outbound and inbound functions
				
class baseSoloGestaltNode(baseGestaltNode):
	
	def _initParameters(self):
		self.bootPageSize = 128

	def _initFunctions(self):	#can add custom function initializations here.
		pass
		
	def _initPackets(self):
		#status
		self.statusRequestPacket = packets.packet(template = [])
		self.statusResponsePacket = packets.packet(template = [packets.pString('status', 1), #status is encoded as 'b' for bootloader, 'a' for app.
																packets.pInteger('appValidity', 1)]) #app validity byte, gets set to 170 if app is valid
		
#		#bootloader command
#		self.bootCommandRequestPacket = packets.packet(template = [packets.pInteger('commandCode', 1)])
#		self.bootCommandResponsePacket = packets.packet(template = [	packets.pInteger('responseCode', 1),
#																packets.pInteger('pageNumber', 2)])
#		#bootloader write
#		self.bootWriteRequestPacket = packets.packet(template = [packets.pInteger('commandCode', 1),
#															packets.pInteger('pageNumber', 2),
#															packets.pList('writeData', self.bootPageSize)])
#		self.bootWriteResponsePacket = packets.packet(self.bootCommandResponsePacket)
#		
#		#bootloader read
#		self.bootReadRequestPacket = packets.packet(template = [packets.pInteger('pageNumber', 2)])
#		self.bootReadResponsePacket = packets.packet(template = [packets.pList('readData', self.bootPageSize)])
		
		#request URL
		self.urlRequestPacket = packets.packet(template = [])
		self.urlResponsePacket = packets.packet(template = [packets.pString('URL')])
		
		#set IP address
		self.setIPRequestPacket = packets.packet(template = [packets.pList('setAddress',2)])
		self.setIPResponsePacket = packets.packet(self.urlResponsePacket)
		
		#identify node
		self.identifyRequestPacket = packets.packet(template = [])
		
		#reset node
		self.resetRequestPacket = packets.packet(template = [])
		
	def _initPorts(self):
		#status
		self.bindPort(port = 1, outboundFunction = self.statusRequest, outboundPacket = self.statusRequestPacket,
							inboundFunction = self.statusResponse, inboundPacket = self.statusResponsePacket)

#		#bootloader command
#		self.bindPort(port = 2, outboundFunction = self.bootCommandRequest, outboundPacket = self.bootCommandRequestPacket,
#							inboundFunction = self.bootCommandResponse, inboundPacket = self.bootCommandResponsePacket)
#		#bootloader write
#		self.bindPort(port = 3, outboundFunction = self.bootWriteRequest, outboundPacket = self.bootWriteRequestPacket,
#							inboundFunction = self.bootWriteResponse, inboundPacket = self.bootWriteResponsePacket)
#		#bootloader read
#		self.bindPort(port = 4, outboundFunction = self.bootReadRequest, outboundPacket = self.bootReadRequestPacket,
#							inboundFunction = self.bootReadResponse, inboundPacket = self.bootReadResponsePacket)

		#request url
		self.bindPort(port = 5, outboundFunction = self.urlRequest, outboundPacket = self.urlRequestPacket,
							inboundFunction = self.urlResponse, inboundPacket = self.urlResponsePacket)
		#set IP address
		self.bindPort(port = 6, outboundFunction = self.setIPRequest, outboundPacket = self.setIPRequestPacket,
							inboundFunction = self.setIPResponse, inboundPacket = self.setIPResponsePacket)
		#identify node
		self.bindPort(port = 7, outboundFunction = self.identifyRequest, outboundPacket = self.identifyRequestPacket)
	
		#reset node
		self.bindPort(port = 255, outboundFunction = self.resetRequest, outboundPacket = self.resetRequestPacket)
	
	class statusRequest(functions.gFunction):
		class gFunctionCore(functions.gFunctionObject):
			def init(self):
				self.updatePacketSet({})
				self.transmit('unicast')
				if self.waitForResponse(0.2):
					return self.getPacket()['status'], (self.getPacket()['appValidity'] == 170) #magic number for app validity
		
	class statusResponse(functions.gFunction):
		pass
	
	class urlRequest(functions.gFunction):
		class gFunctionCore(functions.gFunctionObject):
			def init(self):
				self.updatePacketSet({})
				self.transmit('unicast')	#sends packet unicast	
				if self.waitForResponse(0.2):
					return self.getPacket()['URL']
				else:
					print "TIMEOUT WAITING FOR BUTTON PRESS"
					return False
											
	class urlResponse(functions.gFunction):
		pass
	
	
	class setIPRequest(functions.gFunction):
		class gFunctionCore(functions.gFunctionObject):
			def init(self, IP):
				self.updatePacketSet({'setAddress':IP})
				self.transmit('multicast')
				if self.waitForResponse(1):
					time.sleep(1)	#debounce for button press
					return self.getPacket()['URL']
				else:
					print "TIMEOUT WAITING FOR BUTTON PRESS"
				
	class setIPResponse(functions.gFunction):
		pass

	class identifyRequest(functions.gFunction):
		class gFunctionCore(functions.gFunctionObject):
			def init(self):
				self.updatePacketSet({})
				self.transmit('unicast')	#sends packet multicast
				time.sleep(4)	#roughly the time that the LED is on.	
				
	class resetRequest(functions.gFunction):
		class gFunctionCore(functions.gFunctionObject):
			def init(self):
				self.updatePacketSet({})
				self.transmit('unicast')
				time.sleep(0.1)	#give time for watchdog timer to reset	