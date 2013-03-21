#----IMPORTS------------
import serial	#for connecting to serial ports
import os
import sys
import platform
import time
import Queue
import threading
import socket
from gestalt.utilities import notice
from gestalt import packets
from gestalt import functions


#----INTERFACE CLASSES------------
class interfaceShell(object):
	'''Allows both the node and shell node to access the interface by acting as an intermediary.'''
	def __init__(self, Interface = None, owner = None):
		self.set(Interface, owner)
		
	def set(self, Interface, owner = None):
		'''Updates the interface contained by the shell'''
		if owner: self.owner = owner	#update owner
		self.Interface = Interface		#update interface
		if Interface and self.owner: self.Interface.owner = self.owner		#if interface, set owner
		if Interface: Interface.initAfterSet()	#initializes after owner is set, so that owner is reported correctly to user.
	
	def setOwner(self, owner):
		'''Updates the owner of the interface contained by the shell'''
		self.owner = owner	#used in the port acquisition process
		if self.Interface:
			self.Interface.owner = owner
	
	def __getattr__(self, attribute):
		'''Forwards attribute calls to the linked interface.'''
		return getattr(self.Interface, attribute)
	
	
class baseInterface(object):
	''' This base class could eventually provide a common foundation for all interfaces '''
	def initAfterSet(self):
		'''This method gets called when an interface is set into an interface shell.'''
		pass

class socketInterface(baseInterface):
	def __init__(self, IPAddress = '', IPPort = 27272):	#all avaliable interfaces, port 27272
		self.receiveIPAddress = IPAddress
		self.receiveIPPort = IPPort

class socketUDPServer(socketInterface):
	
	def initAfterSet(self):	#gets called once interface is set into shell.
		self.receiveSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)	#UDP, would be socket.SOCK_STREAM for TCP
		self.receiveSocket.bind((self.receiveIPAddress, self.receiveIPPort))	#bind to socket
		notice(self, "opened socket on " + str(self.receiveIPAddress) + " port " + str(self.receiveIPPort))
		self.transmitSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	
	def receive(self):
		data, addr = self.receiveSocket.recvfrom(1024)
		notice(self, "'" + str(data) + "' from " + str(addr))
		return (data, addr)
	
	def transmit(self, remoteIPAddress, remoteIPPort, data):
#		self.transmitSocket.sendto(data, (remoteIPAddress, remoteIPPort))
		self.receiveSocket.sendto(data, (remoteIPAddress, remoteIPPort))
		

class devInterface(baseInterface):
	''' Base class for interfaces mounted in the /dev/ folder.'''
	def deviceScan(self, searchTerm):
		'''returns available ports that match the search term'''
		ports = os.listdir('/dev/')
		matchingPorts = []
		for port in ports:
			if searchTerm in port:
				matchingPorts.append('/dev/' + port)
		return matchingPorts	
	
	def getSearchTerms(self, interfaceType):
		'''returns the likely prefix for a serial port based on the operating system and device type'''
		#define search strings in format {'OperatingSystem':'SearchString'}
		ftdi = {'Darwin':'tty.usbserial-'}
		lufa = {'Darwin':'tty.usbmodem'}
		genericSerial = {'Darwin': 'tty.'}
		
		searchStrings = {'ftdi':ftdi, 'lufa':lufa, 'genericSerial':genericSerial}	
		
		opSys = platform.system()	#nominally detects the system
		
		if interfaceType in searchStrings:
			if opSys in searchStrings[interfaceType]:
				return searchStrings[interfaceType][opSys]
			else:
				notice('getSearchTerm', 'operating system support not found for interface type '+ interfaceType)
				return False
		else:
			notice('getSearchTerm', 'interface support not found for interface type ' + interfaceType)
			return False	

	def waitForNewPort(self, searchTerms = '', timeout = 10):
		'''Scans for a new port to appear in /dev/ and returns the name of the port.
		
		Search terms is a list that can contain several terms. For now only implemented for one term.'''
		timerCount = 0
		devPorts = self.deviceScan(searchTerms)
		numDevPorts = len(devPorts)
		while True:
			time.sleep(0.25)
			timerCount += 0.25
			if timerCount > timeout:
				notice(self.owner, 'TIMOUT in acquiring a port.')
				return False
			currentDevPorts = self.deviceScan(searchTerms)
			numCurrentDevPorts = len(currentDevPorts)
			
			#port has been unplugged... update number of ports
			if numCurrentDevPorts < numDevPorts:
				devPorts = list(currentDevPorts)
				numDevPorts = numCurrentDevPorts
			elif numCurrentDevPorts > numDevPorts:
				return list(set(currentDevPorts) - set(devPorts))	#returns all ports that just appeared
		
class serialInterface(devInterface):
	'''Provides an interface to nodes connected thru a serial port on the host machine.'''
	def __init__(self, baudRate, portName = None, interfaceType = None, owner = None, timeOut = 0.2):
		self.baudRate = baudRate
		self.portName = portName
		self.timeOut = timeOut
		self.isConnected = False
		self.owner = owner
		#self.owner gets set by the interface shell, and contains a reference to the owning object
		#this is useful to refer to the name of the object when acquiring the interface
		self.port = None	#will be replaced with a serial object when port is acquired
		self.interfaceType = interfaceType
		self.transmitQueue = Queue.Queue()	#a queue is used to allow multiple threads to call transmit simultaneously.

	def initAfterSet(self):		
		#if port name is provided, auto-connect
		if self.portName:
			self.connect(self.portName)
		elif self.interfaceType: #if an interface type is provided, auto-acquire
			self.acquirePort(self.interfaceType)
	
	def getAvailablePorts(self, ports):
		'''tests all provided ports and returns a subset of ports that are available'''
		availablePorts = []
		for port in ports:
			try:
				openPort = serial.Serial(port)
				openPort.close()
				availablePorts += [port]
			except serial.SerialException, e:
				continue
		return availablePorts
				
	def acquirePort(self, interfaceType = None):
		'''Discovers and connects to a port by waiting for a new device to be plugged in.'''
		#get search terms
		if interfaceType:
			searchTerm = self.getSearchTerms(interfaceType)
		else:
			searchTerm = self.getSearchTerms('genericSerial')
		
		#try to find a single port that's open. This is good for when only a single device is attached.
#		availablePorts = self.getAvailablePorts(self.deviceScan(searchTerm))
#		if len(availablePorts) == 1:
#			self.portName = availablePorts[0]
#			return self.connect()
#		else:
		notice(self.owner, "trying to acquire. Please plug me in.")
		newPorts = self.waitForNewPort(searchTerm, 10) #wait for new port
		if newPorts:
			if len(newPorts) > 1:
				notice(self.owner, 'Could not acquire. Multiple ports plugged in simultaneously.')
				return False
			else:
				self.portName = newPorts[0]
				return self.connect()
		else: return False
	
	def connect(self, portName = None):
		'''Locates port for interface on host machine.'''
			
		#check if port has been provided explicitly to connect function
		if portName:
			self.connectToPort(portName)
			return True
		
		#port hasn't been provided to connect function, check if assigned on instantiation
		elif self.portName:
			self.connectToPort(self.portName)
			return True
			
		#no port name provided
		else:
			notice(self, 'no port name provided.')
			return False
			
	def connectToPort(self, portName):
		'''Actually connects the interface to the port'''
		try:
			self.port = serial.Serial(portName, self.baudRate, timeout = self.timeOut)
			self.port.flushInput()
			self.port.flushOutput()
			notice(self, "port " + str(portName) + " connected succesfully.")
			time.sleep(2)	#some serial ports require a brief amount of time between opening and transmission
			self.isConnected = True
			self.startTransmitter()
			return True
		except:
			notice(self, "error opening serial port "+ str(portName))
			return False

	def disconnect(self):
		'''Disconnects from serial port.'''
		self.port.close()
		self.isConnected = False
		
	def setDTR(self):
		'''Used to reset the Arduino hardware.'''
		if self.port:
			self.port.setDTR()
		return	
	
	def setTimeout(self, timeout):
		'''Sets timeout for receiving on port.'''
		if self.port:
			try:
				self.port.timeout = timeout
			except:
				notice(self, "could not set timeout: " + sys.exc_info()[0])
				
	def startTransmitter(self):
		'''Starts the transmit thread.'''
		self.transmitter = self.transmitThread(self.transmitQueue, self.port)
		self.transmitter.daemon = True
		self.transmitter.start()
	
	def transmit(self, data):
		'''Sends request for data to be transmitted over the serial port. Format is as a list.'''
		if self.isConnected:
			self.transmitQueue.put(data)	#converts to list in case data comes in as a string.
		else: notice(self, 'serialInterface is not connected.')
	class transmitThread(threading.Thread):
		'''Handles transmitting data over the serial port.'''
		def __init__(self, transmitQueue, port):
			threading.Thread.__init__(self)	#initialize threading superclass
			self.transmitQueue = transmitQueue
			self.port = port
		
		def run(self):
			'''Code run by the transmit thread.'''
			while True:
				transmitState, transmitPacket = self.getTransmitPacket()
				if transmitState:
					if self.port:
						self.port.write(serialize(transmitPacket))
					else: notice(self, 'Cannot Transmit - No Serial Port Initialized')
				time.sleep(0.0005)

		def getTransmitPacket(self):
			'''Tries to fetch a packet from the transmit queue.'''
			try:
				return True, self.transmitQueue.get()
			except:
				return False, None

	def receive(self):
		'''Grabs one byte from the serial port.'''
		if self.port: 
			return self.port.read()
		else:
			return None
	
	def flushInput(self):
		'''Flushes the input buffer.'''
		self.port.flushInput()
		return
		
		
class gestaltInterface(baseInterface):
	'''Interface to Gestalt nodes based on the Gestalt protocol.'''
	def __init__(self, name = None, interface = None, owner = None):
		self.name = name	#name becomes important for networked gestalt
		self.owner = owner
		self.interface = interfaceShell(interface, self)		#uses the interfaceShell object for connecting to sub-interface
		
		self.receiveQueue = Queue.Queue()
		self.CRC = CRC()
		self.nodeManager = self.nodeManager()	#used to map network addresses (physical devices) to nodes
		
		self.startReceiver()
		
		#define standard gestalt packet
		self.gestaltPacket = packets.packet(template = [	packets.pInteger('startByte', 1),
										packets.pList('address', 2),
										packets.pInteger('port', 1),
										packets.pLength(),
										packets.pList('payload')])
	
	def validateIP(self, IP):
		'''Makes sure that an IP address isn't already in use on the interface.'''
		if str(IP) in self.nodeManager.address_node: return False
		else: return True
		
	class nodeManager(object):
		'''Manages all nodes under the control of this interface.'''
		def __init__(self):
			self.node_address = {}	#node : address
			self.address_node = {}	#address: node

		def updateNodesAddresses(self, node, address):
			oldNode = None
			oldAddress = None
			
			if str(address) in self.address_node: oldNode = self.address_node[str(address)]
			if node in self.node_address: oldAddress = self.node_address[node]
			
			if str(oldAddress) in self.address_node: self.address_node.pop(str(oldAddress))
			if oldNode in self.node_address: self.node_address.pop(oldNode)
			
			self.address_node.update({str(address):node})
			self.node_address.update({node:address})
		
		def getIP(self, node):
			'''Returns IP address for a given node.'''
			if node in self.node_address: return self.node_address[node]
			else: return False
		
		def getNode(self, IP):
			IP = str(IP)
			if IP in self.address_node: return self.address_node[IP]
			else: return False
	
	def assignNode(self, node, address):
		'''Assigns a given node to the interface on a particular address.'''
		self.nodeManager.updateNodesAddresses(node, address)
	
	def transmit(self, nodeSet, mode = 'unicast'):
		'''Transmits a packet set over the interface.'''
		#--BUILD START BYTE TABLE--
		startByteTable = {'unicast': 72, 'multicast': 138}	#unicast transmits to addressed node, multicast to all nodes on network
		if mode in startByteTable:
			startByte = startByteTable[mode]
		else:
			startByte = startByteTable['unicast']

		#--TRANSMIT PACKETS--
		#//FIX// doesn't yet support synchrony
		for functionCore in nodeSet:	#iterate over nodes in the nodeSet
			packetSet = functionCore.getPacketSet()	#get packetSet from command object
			port = functionCore.getPort()
			address = self.nodeManager.getIP(functionCore.virtualNode)
			for packet in packetSet:
				packetRoutable = self.gestaltPacket({'startByte':startByte, 'address': address, 'port':port, 'payload':packet})	#build packet
				packetWChecksum = self.CRC(packetRoutable)	#generate CRC
				self.interface.transmit(packetWChecksum)	#transmit packet thru interface
		
	def startReceiver(self):
		'''Initiates the receiver thread.'''
		#START RECEIVE THREAD
		self.receiver = self.receiveThread(self)
		self.receiver.daemon = True
		self.receiver.start()
		self.packetRouter = self.packetRouterThread(self)
		self.packetRouter.daemon = True
		self.packetRouter.start()		

	class receiveThread(threading.Thread):
		def __init__(self, interface):
			threading.Thread.__init__(self)
			self.interface = interface
#			print "GESTALT INTERFACE RECEIVE THREAD INITIALIZED"
			
		def run(self):
			packet = []
			inPacket = False
			packetPosition = 0
			packetLength = 5	
			
			while True:
				byte = self.interface.interface.receive()	#get byte
				if byte:
					byte = ord(byte) #converts char to byte
					if not inPacket:
						if byte == 72 or byte == 138:	#waits for start byte
							inPacket = True
							packet += [byte]	#adds start byte to packet
							packetPosition += 1	#increment packet position
							continue	#otherwise rejects packet
					else:	#in a packet
						packet += [byte] #append byte to packet
						
						if packetPosition == 4:	#byte 2 contains the packet position
							packetLength = byte
							packetPosition += 1 #increment packet position
							continue
						
						if packetPosition < packetLength:
							packetPosition += 1 #increment packet position
							continue
						
						if packetPosition == packetLength:
							if self.interface.CRC.validate(packet): self.interface.packetRouter.routerQueue.put(packet[:len(packet)-1])	#check CRC, then send to router (minus CRC)
							
				#initialize packet
				packet = []
				inPacket = False
				packetPosition = 0
				packetLength = 5
				
				time.sleep(0.0005)
		
	class packetRouterThread(threading.Thread):
		def __init__(self, interface):
			threading.Thread.__init__(self)
			self.interface = interface
			self.routerQueue = Queue.Queue()
#			print "GESTALT INTERFACE PACKET ROUTER THREAD INITIALIZED"
		
		def run(self):
			while True:
				routerState, routerPacket = self.getRouterPacket()
				if routerState:
					parsedPacket = self.interface.gestaltPacket.decode(routerPacket)
					address = parsedPacket['address']
					port = parsedPacket['port']
					data = parsedPacket['payload']
					destinationNode = self.interface.nodeManager.getNode(address)
					if not destinationNode:
						print "PACEKT RECEIVED FOR UNKNOWN ADDRESS "+ str(address)
						continue
					destinationNode.route(port, data)
					
				time.sleep(0.0005)

		def getRouterPacket(self):
			try:
				return True, self.routerQueue.get()
			except:
				return False, None
		
#----UTILITY CLASSES---------------
class CRC():
	'''Generates CRC bytes and checks CRC validated packets.'''
	def __init__(self):
		self.polynomial = 7		#CRC-8: ATM=7, Dallas-Maxim = 49
		self.crcTableGen()
	
	def calculateByteCRC(self, byteValue):
		'''Calculates Bytes in the CRC Table.'''
		for i in range(8):
			byteValue = byteValue << 1
			if (byteValue//256) == 1:
				byteValue = byteValue - 256
				byteValue = byteValue ^ self.polynomial
		return byteValue
	
	def crcTableGen(self):
		'''Generates a CRC table to make CRC generation faster.'''
		self.crcTable = []
		for i in range(256):
			self.crcTable += [self.calculateByteCRC(i)]
	
	def __call__(self, packet):
		'''Generates CRC for an input packet.'''
		#INITIALIZE CRC ALGORITHM
		crc = 0
		crcByte = 0
		
		#CALCULATE CRC AND CONVERT preOutput BYTES TO CHR
		output = []
		for byte in packet:
			crcByte = byte^crc
			crc = self.crcTable[crcByte]
			output += [byte]
		output += [crc]	#write crc to output
		return output	#NOTE: OUTPUT HAS BEEN CONVERTED TO A STRING
	
	def validate(self, packet): #NOTE: ASSUMES INPUT IS A LIST OF NUMBERS
		'''Checks CRC byte against packet.'''
		crc = 0
		crcByte = 0
		packetLength = len(packet)
		
		for char in packet[0:packetLength]:
			crcByte = char^crc
			crc = self.crcTable[crcByte]
		
		if crc != 0:	return False	#CRC doesn't match
		else:	return True	#CRC matches
	
#----METHODS-----------------------
def serialize(packet):
	'''Converts packet into a string for transmission over a serial port.'''
	if type(packet) == list:
		return ''.join([chr(byte) for byte in packet])		
	elif type(packet) == str:
		return packet
	else:
		print "Error: Packet must be either a list or a string."
		return False