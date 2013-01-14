#----IMPORTS------------
import serial	#for connecting to serial ports
import os
import platform
import time
from gestalt.utilities import notice as notice


#----CLASSES------------
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
		
	