#----IMPORTS------------

#--PACKETS--------------
#
# A Gestalt class for encoding and decoding data packets

class packetHolder(object):
	def __init__(self):
		self.packet = {}	#empty packet
	def put(self, packet):
		self.packet = packet
	def get(self):
		return self.packet

class packetSet(object):
	'''A collection of packets that should be executed sequentially.'''
	def __init__(self, packet):
		self.packet = packet
	def __call__(self, updateInput):
		if type(updateInput) == dict:	#only one packet in packetSet
			packetSet = [self.packet(updateInput)]
		if type(updateInput) == list:	#multiple packets in packetSet
			packetSet = [self.packet(inputDict) for inputDict in updateInput]
		return packetSet

				
#base class for tokens
class packetToken(object):
	def __call__(self, *args, **kwargs):	#by default, a call to class will return encoded list
		return self.encode(*args, **kwargs)
	def encode(self, *args, **kwargs):
		pass
	def decode(self, *args, **kwargs):
		pass

#converts integers into byte stream, and vice versa
class pInteger(packetToken):
	def __init__(self, keyName, numBytes):
		self.keyName = keyName	#keyName stores the key of the relevant data in the inputDict
		self.numBytes = numBytes	#number of bytes to reserve for the integer
	
	def encode(self, inputDict):
		return utilities.intToBytes(inputDict[self.keyName], self.numBytes)
	
	def decode(self, inputPacket):
		inputSlice = inputPacket[:self.numBytes]	#the component of the packet relevant to this token
		outputSlice = inputPacket[self.numBytes:]	#the component of the packet relevant to future tokens
		return {self.keyName:utilities.bytesToInt(inputSlice)}, outputSlice

#passes thru lists, and converts strings into lists
class pList(packetToken):
	def __init__(self, keyName, numBytes = False):
		self.keyName = keyName
		self.numBytes = numBytes
		
	def encode(self, inputDict):
		inputPhrase=inputDict[self.keyName]	#input phrase to be encoded
		
		if type(inputPhrase) == str:	#input is string, must convert into a list 
			print "WARNING in pList: Expected list, got a string."
			inputPhrase = [ord(char) for char in inputPhrase]
			
		if type(inputPhrase) != list and type(inputPhrase) != packets.packet:
			print "ERROR in pList: Must provide either a list or a string."
			return False
		
		if self.numBytes and (len(inputPhrase) != self.numBytes):	#only complain if number of bytes has been specified
			print "WARNING in pList: " + str(len(inputPhrase)) + " bytes encoded, but "+ str(self.numBytes) + " bytes expected."
			
		return inputPhrase
	
	def decode(self, inputPacket):
		if self.numBytes:
			if len(inputPacket)<self.numBytes:
				print ""
			return {self.keyName:inputPacket[:self.numBytes]}, inputPacket[self.numBytes:]
		else:
			return {self.keyName:inputPacket}, []
	
#passes thru lists, and converts strings into lists
class pString(packetToken):
	def __init__(self, keyName, numBytes = False):
		self.keyName = keyName
		self.numBytes = numBytes
		
	def encode(self, inputDict):
		inputPhrase=inputDict[self.keyName]	#input phrase to be encoded
		
		if type(inputPhrase) == str:	#input is string, must convert into a list 
			inputPhrase = [ord(char) for char in inputPhrase]
		
		if type(inputPhrase) == list:
			print "WARNING in pString: Expected string, got a list."
			
		if type(inputPhrase) != list and type(inputPhrase) != packets.packet:
			print "ERROR in pString: Must provide either a list or a string."
			return False
		
		if self.numBytes and (len(inputPhrase) != self.numBytes):	#only complain if number of bytes has been specified
			print "WARNING in pString: " + str(len(inputPhrase)) + " bytes encoded, but "+ str(self.numBytes) + " bytes expected."
		return inputPhrase
	
	def decode(self, inputPacket):
		
		if self.numBytes:
			inputSlice = inputPacket[:self.numBytes]
			outputSlice = inputPacket[self.numBytes:]
		else:
			inputSlice = inputPacket
			outputSlice = []
		
		return {self.keyName:''.join([chr(char) for char in inputSlice])}, outputSlice


class packet(list): 	#packets are represented as a list subclass with templating abilities
	def __init__(self, template, value = None):
		if type(template) == list: self.template = template
		if type(template) == packets.packet: #inherit packet from provided packet
			self.template = template.template
		if value == None: value = []
		list.__init__(self, value)
	
	def __call__(self, inputDict):
		templatedList = []
		for token in self.template:	#build output list
			templatedList += token(inputDict)
		outputList =[len(templatedList) if type(outputItem)==packets.pLength else outputItem for outputItem in templatedList]
		return packets.packet(self.template, outputList)
	
	def spawn(self, outputList):
		return packets.packet(self.template, outputList)
	
	def decode(self, decodeList = None):
		if decodeList == None: decodeList = list(self)
		decodedDict = {}
		for token in self.template:
			dictFrag, decodeList = token.decode(decodeList)
			decodedDict.update(dictFrag)
		return decodedDict
		
class pLength(packetToken):
	def encode(self, inputDict):
		return [self]

	def decode(self, inputPacket):
		return {}, inputPacket[1:]