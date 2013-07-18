#----IMPORTS------------
import imp	#for importing files as modules
import random
import threading
import time
import os
import urllib
import math
from gestalt.utilities import notice as notice
from gestalt import interfaces
from gestalt import functions
from gestalt import packets
from gestalt import utilities
from gestalt import core


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
			self.setNode(imp.load_source('', filename).virtualNode(**kwargs))
			notice(self, "loaded node from:  " + filename)
			return True
		except IOError, error:
			notice(self, "error loading file.")
			print error
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
		except AttributeError, err:
			notice(self, "unable to load module: " + str(err))
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
	def __init__(self, name = None, interface = None, filename = None, URL = None, module = None, persistence = lambda:None, **kwargs):
		'''	Initialization procedure for Gestalt Node Shell.
			
			name:		a unique name assigned by the user. This is used by the persistence algorithm to re-acquire the node.
			interface: 	the object thru which the virtual node communicates with its physical counterpart.
			**kwargs:	any additional arguments to be passed to the node during initialization
			
			Methods of Loading Virtual Node:
				filename: an import-able module containing the virtual node.
				URL: a URL pointing to a module as a resource containing the virtual node.
				module: a python module name containing the virtual node.
		
			Networked/Gestalt virtual nodes initialize by associating with their counterparts over the network. A URL pointing to their driver is 
			returned upon association. This driver is then loaded into the shell as the virtual node.
		'''

		#call base class __init__ method
		super(gestaltNodeShell, self).__init__()	#call init on baseNodeShell
		
		#assign parameters to variables
		self.name = name
		self.filename = filename
		self.URL = URL
		self.module = module
		self.persistence = persistence
		
		#connect to interface
		if interface:
			#make sure that node has a gestalt interface
			if type(interface) != interfaces.gestaltInterface:
				#wrap a gestalt interface around the provided interface
				self.interface.set(interfaces.gestaltInterface(interface = interface, owner = self), self)
			else: self.interface.set(interface, self)	#interface isn't shared with other nodes, so owner is self.		
		
			#import base node
			self.setNode(baseStandardGestaltNode())		
			
			if self.persistence(): address = self.persistence.get(self.name)
			else: address = None
			
			if address:	#an IP address was found
				self.interface.assignNode(self.node, address)	#assign node to interface with IP address
				nodeURL = self.node.urlRequest()	#get node URL
			else: #acquire node
				#set node IP address	-- this will be changed later once persistence is added
				address = self.generateIPAddress()	#generate random IP address
				self.interface.assignNode(self.node, address)	#assign node to interface with IP address	
				if type(self) == networkedGestaltNode: notice(self, "please identify me on the network.")
				nodeURL = self.node.setIPRequest(address)	#set real node's IP address, and retrieve URL.		
				if self.persistence(): self.persistence.set(self.name, address)
				
			notice(self, nodeURL)
	
			#try to start node in application mode
			nodeStatus, appValid = self.statusRequest()
			if nodeStatus == 'B' and appValid:	#node is in bootloader mode and application is valid
				if self.runApplication():	#need to reinitialize
					nodeURL = self.urlRequest()
					notice(self, " NOW RUNNING IN APPLICATION MODE")
					notice(self, nodeURL)	#remove
				else:
					notice(self, "ERROR STARTING APPLICATION MODE")
			elif nodeStatus == 'A': notice(self, "RUNNING IN APPLICATION MODE")
			else: notice(self, " RUNNING IN BOOTLOADER MODE")
			
		else:
			#No interface, this can be intentional to allow debugging offline
			notice(self, 'Error - please provide an interface.')		

		#acquire virtual node.
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
		
		if interface:	
			#assign new node with old IP address to interface. This replaces the default node with the imported node.
			self.interface.assignNode(self.node, address)


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
	pass
	
	
class networkedGestaltNode(gestaltNodeShell):
	'''	A container shell for Networked/Gestalt nodes.
	
		Networked/Gestalt nodes are networked and use the gestalt communications protocol.
		Both the older Fabnet hardware as well as boards based on Units of Fab are supported.'''
	pass

		



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
		def __init__(self, virtualNode):
			self.virtualNode = virtualNode
			self.outPorts = {}	#ports for outbound packets {function:port#}
			self.inPorts = {}	#functions for inbound packets {port#:function}

		def __call__(self, port, outboundFunction = None, outboundPacket = None, inboundFunction = None, inboundPacket = None):
			newResponseFlag = threading.Event()
			packetHolder = packets.packetHolder()
			
			#---CREATE FUNCTION INSTANCES AND UPDATE ROUTE DICTIONARIES---				
			if outboundFunction != None:
				if outboundPacket != None: packetSet = packets.packetSet(outboundPacket)	#gives the outbound function a packetSet initialized with the provided packet as a template
				else: packetSet = packets.packetSet(packets.packet(template=[]))	#gives the outbound function a packetSet initialized with a blank packet as a template
				if type(outboundFunction) == type: setattr(self.virtualNode, outboundFunction.__name__, outboundFunction(virtualNode = self.virtualNode, 	#create function instance
																														packetSet = packetSet,	#define packet format
																														responseFlag = newResponseFlag,	#creates a common response flag for outbound and inbound functions
																														packetHolder = packetHolder)) #creates a common packet holder for outbound and inbound functions
				outboundFunction = getattr(self.virtualNode, outboundFunction.__name__)	#update outboundFuncton pointer in event that new instance was created
				self.outPorts.update({outboundFunction:port})	#bind port to outbound instance
				
			if inboundFunction != None:
				if inboundPacket != None: packetSet = packets.packetSet(inboundPacket)	#gives the inbound function a packetSet initialized with the provided packet as a template
				else: packetSet = packets.packetSet(packets.packet(template=[])) #gives the inbound function a packetSet initialized with a blank packet as a template
				if type(inboundFunction) == type: setattr(self.virtualNode, inboundFunction.__name__, inboundFunction(virtualNode = self.virtualNode,	#create function instance
																														packetSet = packetSet,	#define packet format
																														responseFlag = newResponseFlag,	#creates a common response flag for outbound and inbound functions
																														packetHolder = packetHolder)) #creates a common packet holder for outbound and inbound functions
				inboundFunction = getattr(self.virtualNode, inboundFunction.__name__)
				self.inPorts.update({port:inboundFunction})	#bind port to inbound instance
			else:	#create a default inbound function which will handle incoming packets.
				if inboundPacket != None: packetSet = packets.packetSet(inboundPacket)	#use provided inbound packet
				else: packetSet = packets.packetSet(packets.packet(template=[])) #create default blank packet
				inboundFunction = functions.serviceRoutine(virtualNode = self.virtualNode, packetSet = packetSet,
															responseFlag = newResponseFlag, packetHolder = packetHolder)
				self.inPorts.update({port:inboundFunction})



class baseStandardGestaltNode(baseGestaltNode):
	
	def _initParameters(self):
		self.bootPageSize = 128

	def _initPackets(self):
		#status
		self.statusResponsePacket = packets.packet(template = [packets.pString('status', 1), #status is encoded as 'b' for bootloader, 'a' for app.
																packets.pInteger('appValidity', 1)]) #app validity byte, gets set to 170 if app is valid
		
		#bootloader command
		self.bootCommandRequestPacket = packets.packet(template = [packets.pInteger('commandCode', 1)])
		self.bootCommandResponsePacket = packets.packet(template = [	packets.pInteger('responseCode', 1),
																packets.pInteger('pageNumber', 2)])
		#bootloader write
		self.bootWriteRequestPacket = packets.packet(template = [packets.pInteger('commandCode', 1),
															packets.pInteger('pageNumber', 2),
															packets.pList('writeData', self.bootPageSize)])
		self.bootWriteResponsePacket = packets.packet(self.bootCommandResponsePacket)
		
		#bootloader read
		self.bootReadRequestPacket = packets.packet(template = [packets.pInteger('pageNumber', 2)])
		self.bootReadResponsePacket = packets.packet(template = [packets.pList('readData', self.bootPageSize)])
		
		#request URL
		self.urlResponsePacket = packets.packet(template = [packets.pString('URL')])
		
		#set IP address
		self.setIPRequestPacket = packets.packet(template = [packets.pList('setAddress',2)])
		self.setIPResponsePacket = packets.packet(self.urlResponsePacket)
		
		#identify node
		#no packet format
		
		#reset node
		#no packet format
		
	def _initPorts(self):
		#status
		self.bindPort(port = 1, outboundFunction = self.statusRequest, inboundPacket = self.statusResponsePacket)
		#bootloader command
		self.bindPort(port = 2, outboundFunction = self.bootCommandRequest, outboundPacket = self.bootCommandRequestPacket,
							inboundPacket = self.bootCommandResponsePacket)
		#bootloader write
		self.bindPort(port = 3, outboundFunction = self.bootWriteRequest, outboundPacket = self.bootWriteRequestPacket,
							inboundPacket = self.bootWriteResponsePacket)
		#bootloader read
		self.bindPort(port = 4, outboundFunction = self.bootReadRequest, outboundPacket = self.bootReadRequestPacket,
							inboundPacket = self.bootReadResponsePacket)
		#request url
		self.bindPort(port = 5, outboundFunction = self.urlRequest, inboundPacket = self.urlResponsePacket)
		#set IP address
		self.bindPort(port = 6, outboundFunction = self.setIPRequest, outboundPacket = self.setIPRequestPacket,
							inboundPacket = self.setIPResponsePacket)
		#identify node
		self.bindPort(port = 7, outboundFunction = self.identifyRequest)
	
		#reset node
		self.bindPort(port = 255, outboundFunction = self.resetRequest)
	

	def loadProgram(self, filename):
		'''Loads a program into a Gestalt Node via the built-in Gestalt bootloader.'''
		#initialize hex parser
		parser = utilities.intelHexParser()	#Intel Hex Format Parser Object
		parser.openHexFile(filename)
		parser.loadHexFile()
		pages = parser.returnPages(self.bootPageSize)
		#reset node if necessary to switch to bootloader mode
		nodeStatus, appValid = self.statusRequest()			
		if nodeStatus == 'A':	#currently in application, need to go to bootloader
			self.resetRequest()	#attempt to reset node
			nodeStatus, appValid = self.statusRequest()
			if nodeStatus != 'B':
				notice(self, "ERROR IN BOOTLOADER: CANNOT RESET NODE")
				return False
		#initialize bootloader
		if self.initBootload(): notice(self, "BOOTLOADER INITIALIZED!")
		#write hex file to node
		for page in pages:
			pageData = [addressBytePair[1] for addressBytePair in page]
			pageNumber = self.bootWriteRequest(0, pageData)	#send page to bootloader
			if pageNumber != page[0][0]:
				notice(self, "Error in Bootloader: PAGE MISMATCH: SENT PAGE " + str(page[0][0]) + " AND NODE REPORTED PAGE " + str(pageNumber))
				notice(self, "ABORTING PROGRAM LOAD")
				return False
			notice(self, "WROTE PAGE "+ str(pageNumber))# + ": " + str(pageData)
		#verify hex file from node
		for page in pages:
			pageData = [addressBytePair[1] for addressBytePair in page]
			currentPageNumber = page[0][0]
			verifyData = self.bootReadRequest(currentPageNumber)
			for index, item in enumerate(verifyData):
				if item != pageData[index]:
					notice(self, "VERIFY ERROR IN PAGE: "+ str(currentPageNumber)+ " BYTE: "+ str(index))
					notice(self, "VERIFY FAILED")
					return False
			notice(self, "PAGE " + str(currentPageNumber) + " VERIFIED!")
		notice(self, "VERIFY PASSED")
		#start application
		if not self.runApplication():
			notice(self, "COULD NOT START APPLICATION")
			return FALSE
		#register new node with gestalt interface
		#self.target.nodeManager.assignNode(self)	#registers node with target		
		#need something here to import a new node into self.shell based on URL from node	
		return True
	
	
	
	def initBootload(self):
		return self.bootCommandRequest('startBootload')
	
	def runApplication(self):
		return self.bootCommandRequest('startApplication')
	
	
	class statusRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self):
				self.commitAndRelease()	#commit self immediately
				self.waitForChannelAccess()	#wait for channel access
				if self.transmitPersistent():
					return self.getPacket()['status'], (self.getPacket()['appValidity'] == 170) #magic number for app validity


	class bootCommandRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self, command):
				commandSet = {'startBootload': 0, 'startApplication': 1}
				responseSet = {'bootloadStarted':5, 'applicationStarted':9 }	#these numbers are arbitrary and defined in the firmware.
				if command in commandSet:
					self.setPacket({'commandCode':commandSet[command]})
					self.commitAndRelease()	#commit self immediately
					self.waitForChannelAccess()
					if self.transmitPersistent():
						responseCode = self.getPacket()['responseCode']
						if command == 'startBootload' and responseCode == responseSet['bootloadStarted']: return True
						if command == 'startAplication' and responseCode == responseSet['applicationStarted']: return True
					else:
						print "NO RESPONSE TO BOOTLOADER COMMAND "+ command
						return False
				else:
					print "BOOTLOADER COMMAND " + command + " NOT RECOGNIZED."
					return False

			
	class bootWriteRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self, pageNumber, data):
				self.setPacket({'commandCode': 2, 'pageNumber': pageNumber, 'writeData': data})
				self.commitAndRelease()	#commit self immediately
				self.waitForChannelAccess()
				if self.transmitPersistent():
					returnPacket = self.getPacket()
					if returnPacket['responseCode']==1:	#page write OK
						return returnPacket['pageNumber']
					else:
						print "PAGE WRITE NOT SUCCESSFUL ON NODE END"
						return False
				else:
					print "NO RESPONSE RECEIVED TO PAGE WRITE REQUEST"
					return False
	
	
	class bootReadRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self, pageNumber):
				self.setPacket({'pageNumber': pageNumber})
				self.commitAndRelease()	#commit self immediately
				self.waitForChannelAccess()
				if self.transmitPersistent():
					return self.getPacket()['readData']
				else:
					print "NO RESPONSE RECEIVED TO PAGE WRITE REQUEST"
					return False

	
	class urlRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self):
				self.commitAndRelease()	#commit self immediately
				self.waitForChannelAccess()
				if self.transmitPersistent():
					return self.getPacket()['URL']
				else:
					notice(self.virtualNode, 'NO URL RECEIVED')
					return False
	
	
	class setIPRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self, IP):
				self.setPacket({'setAddress':IP}, mode = 'multicast')
				self.commitAndRelease()	#commit self immediately
				self.waitForChannelAccess(5)
				if self.transmitPersistent(timeout = 15):
					time.sleep(1)	#debounce for button press
					return self.getPacket()['URL']
				else:
					notice(self.virtualNode, 'TIMEOUT WAITING FOR BUTTON PRESS')

	class identifyRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self):
				self.commitAndRelease()	#commit self immediately
				self.waitForChannelAccess()
				self.transmit()
				time.sleep(4)	#roughly the time that the LED is on.	
				
	class resetRequest(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self):
				self.commitAndRelease()	#commit self immediately
				self.waitForChannelAccess()
				self.transmit()
				time.sleep(0.1)	#give time for watchdog timer to reset

class compoundNode(object):
	'''A compound node helps distribute and synchronize function calls across multiple nodes.'''
	def __init__(self, *nodes):
		self.nodes = nodes
		self.nodeCount = len(self.nodes)
		self.name = "[" + ''.join([str(node.name) + "," for node in nodes])[:-1] + "]"
		interfaces = [node.interface.Interface for node in nodes]	#nodes have an interface shell
		if all(interface == interfaces[0] for interface in interfaces):
			self.commonInterface = True
		else:
			self.commonInterface = False
			notice(self, "warning: not all members of compound node share a common interface!")
	
	def  __getattr__(self, attribute):
		'''	Forwards all unsupported function calls to a distributor'''
		return self.distributor(self, attribute)
	
	class distributor(object):
		'''The distributor is responsible for forwarding function calls made on the compound node to its constituents.
		
		Arguments provided as tuples will be distributed individually. Non-tuple arguments will be duplicated to all
		nodes.'''
		
		
		def __init__(self, compoundNode, attribute):
			self.attribute = attribute
			self.compoundNode = compoundNode
			self.sync = False	#indicates whether function call is synchronized. This gets set true if any arguments are tuples.
			
		def __call__(self, *compoundArguments, **compoundKWarguments):
			nodeArguments = [[] for i in range(self.compoundNode.nodeCount)]	# a list of arguments for each node 
			nodeKWarguments = [{} for i in range(self.compoundNode.nodeCount)]	#a list of kwarguments for each node
			
			#If a tuple is provided, the items are distributed to respective arguments out lists. Otherwise, the item is copied to all lists.
			
			#compile arguments
			for argument in compoundArguments:
				if type(argument) == tuple:	#tuple provided, should distribute
					if len(argument) != self.compoundNode.nodeCount:	#check to make sure that tuple length matches the number of nodes.
						alert(self.compoundNode, self.attribute + ": not enough arguments provided in tuple.")
						return False
					else:
						self.sync = True	#tuple provided, this will be a synchronized call.
						for nodeArgPair in zip(nodeArguments, list(argument)):	#iterate thru (targetArgumentList, argument)
							currentNodeArguments = nodeArgPair[0]
							currentNodeArguments += [nodeArgPair[1]]
				else:
					for node in nodeArguments:
						node += [argument]

			#compile keyword arguments
			for key, value in compoundKWarguments.iteritems():
				if type(value) == tuple:	#tuple provided, should distribute
					if len(value) != self.compoundNode.nodeCount:
						alert(self.compoundNode, self.attribute + ": not enough arguments provided in tuple.")
						return False
					else:
						self.sync = True
						for nodeArgPair in zip(nodeKWarguments, list(value)):
							currentNodeArguments = nodeArgPair[0]
							currentNodeArguments.update({key:nodeArgPair[1]})
				else:
					for node in nodeKWarguments:
						node.update({key: value})
			
			#if sync, provide a sync token
			if self.sync:
				syncToken = core.syncToken()	#pull a new sync token
				for node in nodeKWarguments:
					node.update({'sync':syncToken})
			#make function calls
			returnValues = [self.nodeFunctionCall(node, self.attribute, args, kwargs) for node, args, kwargs in zip(self.compoundNode.nodes, nodeArguments, nodeKWarguments)]
			
			print returnValues


		def nodeFunctionCall(self, node, attribute, args, kwargs):
			if hasattr(node, attribute):
				return getattr(node, attribute)(*list(args), **kwargs)
			else:
				notice(self.compoundNode, "NODE DOESN'T HAVE REQUESTED ATTRIBUTE")
				raise AttributeError(attribute)
				