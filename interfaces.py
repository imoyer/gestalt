#----IMPORTS------------
import serial	#for connecting to serial ports
import os
import platform
import time
import Queue
from gestalt.utilities import notice as notice


#----INTERFACE CLASSES------------
class interfaceShell(object):
	'''Allows both the node and shell node to access the interface by acting as an intermediary.'''
	def __init__(self, interface = None, owner = None):
		self.set(interface, owner)
		
	def set(self, interface, owner = None):
		'''Updates the interface contained by the shell'''
		if owner: self.owner = owner	#update owner
		self.interface = interface		#update interface
		if interface: self.interface.owner = self.owner		#if interface, set owner
	
	def setOwner(self, owner):
		'''Updates the owner of the interface contained by the shell'''
		self.owner = owner	#used in the port acquisition process
		if self.interface:
			self.interface.owner = owner
	
	def __getattr__(self, attribute):
		'''Forwards attribute calls to the linked interface.'''
		return getattr(self.interface, attribute)
	
	
class baseInterface(object):
	''' This base class could eventually provide a common foundation for all interfaces '''
	pass

	
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
	def __init__(self, baudRate, portName = None, timeOut = 0.2):
		self.baudRate = baudRate
		self.portName = portName
		self.timeOut = timeOut
		self.isConnected = False
		self.owner = None
		#self.owner gets set by the interface shell, and contains a reference to the owning object
		#this is useful to refer to the name of the object when acquiring the interface
		self.port = None	#will be replaced with a serial object when port is acquired
		self.transmitQueue = Queue.Queue()	#a queue is used to allow multiple threads to call transmit simultaneously.
		
		#if port name is provided, auto-connect
		if self.portName:
			self.connect(self.portName)
	
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
	
	def startTransmitter(self):
		'''Starts the transmit thread.'''
		self.transmitter = self.transmitThread(self.transmitQueue, self.port)
		self.transmitter.daemon = True
		self.transmitter.start()
	
	def transmit(self, data):
		'''Sends request for data to be transmitted over the serial port. Format is as a list.'''
		self.transmitQueue.put(data)	#converts to list in case data comes in as a string.
		
	class transmitThread(threading.Thread):
		'''Handles transmitting data over the serial port.'''
		def __init__(self, transmitQueue, port):
			threading.Thread.__init__(self)	#initialize threading superclass
			self.transmitQueue = transmitQueue
			self.port = port
		
		def run(self):
			'''Code run by the transmit thread.'''
			while true:
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
			'''Grabs one byte from the serial port with no timeout.'''
			if self.port: return self.port.read()
			else: return None
		
		
class gestaltInterface(baseInterface):
	'''Interface to Gestalt nodes based on the Gestalt protocol.'''
	def __init__(self, name = None, interface = None):
		self.interface = interfaceShell(interface, self)		#uses the interfaceShell object for connecting to sub-interface
		self.name = name
		
		
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