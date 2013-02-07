#----IMPORTS------------
from gestalt.utilities import notice as notice
from gestalt import nodes
from gestalt import interfaces
import time
import threading
import xml.etree.ElementTree as ET
import math


#----VIRTUAL NODE-------

class virtualNode(nodes.baseSoloIndependentNode):
	'''Contains the code for the KUKA virtual node'''
	def init(self, **kwargs):
		#connect to the KUKA
		self.interface.set(interfaces.socketUDPServer(IPAddress = "192.168.10.3", IPPort = 27272))
		self.realTime = self.kukaRealTime(self)
		
	class kukaRealTime(threading.Thread):
		def __init__(self, virtualNode):
			threading.Thread.__init__(self)
			self.daemon = True
			self.virtualNode = virtualNode
			self.start()
		
		def run(self):
			interpolatorMark = 0
			amplitude = 100 #mm
			xPeriod = 11.0	#seconds
			yPeriod = 15.0
			zPeriod = 8.0
			
			currentXTime = 0.0
			currentYTime = 0.0
			currentZTime = 0.0
			
			#real time loop
			while True:
				(inboundPacket, (inboundAddress, inboundPort)) = self.virtualNode.interface.receive()
				iterStartTime = time.clock()
				xmlFromKuka = parseXMLString(inboundPacket)
				interpolatorMark = xmlFromKuka['IPOC']['value']
#				print interpolatorMark
				
				xPosition = math.sin(currentXTime*2.0 * 3.1415 / xPeriod) * amplitude
				xPosition = str(round(xPosition, 2))
				currentXTime = (currentXTime+0.012) % xPeriod
				print "X POSITION: " + xPosition
				
				yPosition = math.sin(currentYTime*2.0 * 3.1415 / yPeriod) * amplitude
				yPosition = str(round(yPosition, 2))
				currentYTime = (currentYTime+0.012) % yPeriod
				print "Y POSITION: " + yPosition
				
				zPosition = math.sin(currentZTime*2.0 * 3.1415 / zPeriod) * amplitude
				zPosition = str(round(zPosition, 2))
				currentZTime = (currentZTime+0.012) % zPeriod
				print "Z POSITION: " + zPosition
				
				
				
				xmlToKuka = generateXMLString({'IPOC':{'attributes':{}, 'value':interpolatorMark},
											   'XCOR': {'attributes':{},'value':xPosition},
											   'YCOR': {'attributes':{},'value':yPosition},
											   'ZCOR': {'attributes':{},'value':zPosition}}, "SEN", {'Type':'ImFree'})
				self.virtualNode.interface.transmit(inboundAddress, inboundPort, xmlToKuka)
				iterEndTime = time.clock()
				
				
				
#----XML INTERFACE----
def parseXMLString(inputXML):
	rootElement = ET.fromstring(inputXML)
	outputDictionary = {}
	for child in rootElement:
		outputDictionary.update({child.tag:{'attributes':child.attrib, 'value':child.text}})
	return outputDictionary

def generateXMLString(inputDictionary, rootTag = "SEN", rootAttrib = {}):
	rootElement = ET.Element(rootTag, rootAttrib)
	for key in inputDictionary:
		subElement = ET.SubElement(rootElement, key, inputDictionary[key]['attributes'])
		subElement.text = inputDictionary[key]['value']
	return ET.tostring(rootElement)
	