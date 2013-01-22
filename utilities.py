def notice(source = None, message = ""):
	''' Sends a notice to the user.
	
	For now, this just prints to the screen. But eventually, could re-route via a web interface.'''
	#check for name attribute
	if hasattr(source, 'name'):
		name = getattr(source, 'name')
		if name:
			print name + ": " + str(message)
		elif hasattr(source, 'owner'):
			owner = getattr(source, 'owner')
			if owner:
				notice(source.owner, message)
			else:
				print str(source) + ": " + str(message)
		else:
			print str(source) + ": " + str(message)
	else:
		if hasattr(source, 'owner'):
			owner = getattr(source, 'owner')
			if owner:
				notice(source.owner, message)
			else:
				print str(source) + ": " + str(message)
		else:
			print str(source) + ": " + str(message)

def intToBytes(integer, numbytes):
	bytes = range(numbytes)
	for i in bytes:
		bytes[i] = integer%256
		integer -= integer%256
		integer = integer//256
		
	if integer>0: print "ERROR in PACKET COMPOSER: BYTE OVERFLOW"
	return bytes

def bytesToInt(bytes):
	integer = 0
	order = 0
	for i in bytes:
		integer += i*(256**order)
		order += 1
	return integer

def listToString(numList):
	strList = [chr(x) for x in numList]
	return ''.join(strList)

def vectorAbs(vector):
	output = range(len(vector))
	for i in output:
		output[i] = abs(vector[i])
	return output
	
def vectorInt(vector):
	output = range(len(vector))
	for i in output:
		output[i] = int(vector[i])
	return output
	
def vectorMultiply(vector1, vector2):
	if len(vector1) != len(vector2):
		print "ERROR in vectorMultiply: vectors have dissimilar lengths"
	output = range(len(vector1))
	for i in output:
		output[i] = vector1[i]*vector2[i]
	return output
	
def vectorDivide(vector1, vector2):
	if len(vector1) != len(vector2):
		print "ERROR in vectorDivide: vectors have dissimilar lengths"
	output = range(len(vector1))
	for i in output:
		output[i] = vector1[i]/float(vector2[i])
	return output

def vectorSign(vector):
	output = range(len(vector))
	for i in output:
		if vector[i] > 0: output[i] = 1
		if vector[i] < 0: output[i] = -1
		if vector[i] == 0: output[i] = 0
	return output		
	
def vectorMCUSign(vector):
	output = range(len(vector))
	for i in output:
		if vector[i] > 0: output[i] = 1
		if vector[i] <= 0: output[i] = 0
	return output
	
def vectorLength(vector):		
	sum = 0.0
	for i in vector:
		sum += i**2	#squares power
	return math.sqrt(sum)
	
def vectorMax(vector):
	vMax = 0.0
	for i in vector:
		if i > vMax: vMax = i
	return vMax

class intelHexParser(object):
	'''Parses Intel Hex Files for Bootloading and Memory Programming.'''
	def __init__(self):
		self.filename = None
		self.hexFile = None
		self.resetParser()
	
	def openHexFile(self, filename = None):
		if filename != None:
			self.hexFile = open(filename, 'r')
			return self.hexFile
		else:
			print "intelHexParser: please provide a filename!"
			return False
		
	def resetParser(self):
		self.baseByteLocation = 0	#always initialize at location 0, this can be changed by the hex file during reading
		self.parsedFile = []
		self.codeStart = 0
		self.terminated = False	#gets set when end of file record is reached
	
	def loadHexFile(self):
		parseVectors = {0:self.processDataRecord, 1: self.processEndOfFileRecord, 2: self.processExtendedSegmentAddressRecord,
					3:self.processStartSegmentAddressRecord, 4: self.processExtendedLinearAddressRecord, 5: self.processStartLinearAddressRecord}

		for index, record in enumerate(self.hexFile):	#enumerate over lines in hex file
			integerRecord = self.integerRecord(self.recordParser(record))
			parseVectors[integerRecord['RECTYP']](integerRecord)
#		print self.parsedFile
		self.checkAddressContinuity()
		
	def returnPages(self, pageSize):
		numPages = int(math.ceil(len(self.parsedFile)/float(pageSize)))	#number of pages
		pages = [self.parsedFile[i*pageSize:(i+1)*pageSize] for i in range(numPages)]	#slice parsed data into pages of size pageSize
		
		#fill in last page
		lastPage = pages[-1]
		delta = pageSize - len(lastPage)
		lastAddress = lastPage[-1][0]	#address of last entry in last page
		makeUp = [[lastAddress+i+1, 0] for i in range(delta)]
		pages[-1] += makeUp	#fill last page
		
		return pages
		
		
			
	def recordParser(self, record):
		record = record.rstrip()
		length = len(record)
		return {'RECLEN':record[1:3], 'OFFSET':record[3:7], 'RECTYP':record[7:9], 'DATA':record[9:length-2], 'CHECKSUM':record[length-2: length]}
			
			
	def integerRecord(self, record):
		return {'RECLEN':int(record['RECLEN'],16), 'OFFSET':int(record['OFFSET'], 16), 'RECTYP':int(record['RECTYP'],16),
			 'CHECKSUM': int(record['CHECKSUM'], 16), 'DATA': self.dataList(record['DATA'])}
		
		
	def dataList(self, data):
		return [int(data[i:i+2], 16) for i in range(0, len(data), 2)]
	
	
	def processDataRecord(self, record):
		codeLocation = record['OFFSET'] + self.baseByteLocation
		for index, byte in enumerate(record['DATA']):
			self.parsedFile +=[[codeLocation + index, byte]]
	
	def processEndOfFileRecord(self, record):
		self.terminated = True
	
	def processExtendedSegmentAddressRecord(self, record):
		self.baseByteLocation = (record['DATA'][0]*256 + record['DATA'][1])*16	#value is shifted by four bits
	
	def processStartSegmentAddressRecord(self, record):
		print "Start Segment Address Record Encountered and Ignored"
	
	def processExtendedLinearAddressRecord(self, record):
		print "Extended Linear Address Record Encountered and Ignored"
	
	def processStartLinearAddressRecord(self, record):
		print "Start Linear Address Record Encountered and Ignored"
		
	def checkAddressContinuity(self):
		baseAddress = self.parsedFile[0][0]	#inital address entry
		for byte in self.parsedFile[1::]:
			if byte[0] == baseAddress + 1:
				baseAddress += 1
				continue
			else:
				print "CONTINUITY CHECK FAILED"
				return False
		
		print "CONTINUITY CHECK PASSED"