#----IMPORTS------------
from gestalt.utilities import notice as notice
from gestalt import nodes
from gestalt import interfaces


#----VIRTUAL NODE-------

class virtualNode(nodes.baseSoloIndependentNode):
	'''Contains the code for the Printrboard Virtual Node'''
	def init(self, **kwargs):
		#connect to the printrboard
		self.interface.set(interfaces.serialInterface(baudRate = 200000))
		self.interface.acquirePort('lufa')
		
		
