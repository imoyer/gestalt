class publisher(object):
	def __init__(self, portNumber = None):
		self.nodes = []
		self.interfaces = []
		
	def addNodes(self, *nodes):
		#check whether node is already in node list
		for node in nodes:
			if not node in self.nodes:
				self.nodes += [node]
				self.addInterfaces(node.interface.Interface)
				
	def addInterfaces(self, *interfaces):
		for interface in interfaces:
			if type(interface) == gestalt.interfaceShell:
				interface = interface.Interface
			if not interface in self.interfaces:
				self.interfaces += [interface]
				
	def evaluateNode(self, node):
		pass
	
	def evaluateInterface(self, interface):
		if type(inteface) == gestsalt.interfaceShell:
			interface = interface.Interface
		interfaceName = interface.name