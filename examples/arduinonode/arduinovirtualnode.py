from gestalt import nodes
from gestalt import utilities
from gestalt.utilities import notice
from gestalt import functions as functions
from gestalt import packets as packets
from gestalt import core
import time
import math

class virtualNode(nodes.baseStandardGestaltNode):
	def init(self, **kwargs):
		pass
	
	def initParameters(self):
		pass

	def initFunctions(self):
		pass
		
	def initPackets(self):
		self.additionRequestPacket = packets.packet(template = [packets.pInteger('a',2),
									packets.pInteger('b',2)])
		self.additionResponsePacket = packets.packet(template = [packets.pInteger('response',2)])
		pass
		
	def initPorts(self):
		self.bindPort(port = 10, outboundFunction = self.svcToggleLed) # port number is set in the node firmware, port numbers above 10
		self.bindPort(port = 11, outboundFunction = self.svcAddition, outboundPacket = self.additionRequestPacket, inboundPacket = self.additionResponsePacket)
		pass
	

#----- API FUNCTIONS --------------------

#----- SERVICE ROUTINES -----------------
	class svcToggleLed(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self):
				self.setPacket({})
				self.commitAndRelease()
				self.waitForChannelAccess()
				if self.transmitPersistent(): 
					notice(self.virtualNode, "LED toggled")
					return True
				else: 
					notice(self.virtualNode, "halp doesn't toggle")
					return False
	

	class svcAddition(functions.serviceRoutine):
		class actionObject(core.actionObject):
			def init(self, a, b):
				self.setPacket({'a':a, 'b':b})
				self.commitAndRelease()
				self.waitForChannelAccess()
				if self.transmitPersistent():
					notice(self.virtualNode, "adding")
					responsePacket = self.getPacket()
					return responsePacket['response'] #set by the initpackets routine
				else:
					notice(self.virtualNode, "computer says no")
					return False
