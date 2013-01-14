#----IMPORTS------------
import imp	#for importing files as modules
from gestalt.utilities import notice as notice
from gestalt import interfaces


#----NODE SHELLS------------
class baseNodeShell(object):
	'''	The basic container for gestalt nodes.
		
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
			self.setNode(imp.load_source('', filename).virtualNode(self, **kwargs))
			notice(self, "loaded node from:  " + filename)
			return True
		except IOError:
			notice(self, "error loading file.")
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
		except AttributeError:
			notice(self, "unable to load module.")
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

class soloGestaltNode(baseNodeShell):
	'''	A container shell for Solo/Gestalt nodes.
	
		Solo/Gestalt nodes are non-networked and use the gestalt communications protocol.
		For example they might make use of the gsArduino library.'''

	def __init__(self, name = None, interface = None, filename = None, URL = None, module = None, **kwargs):
		'''	Initialization procedure for Solo/Independent Node Shell.
			
			name:		a unique name assigned by the user. This is used by the persistence algorithm to re-acquire the node.
			interface: 	the object thru which the virtual node communicates with its physical counterpart.
			**kwargs:	any additional arguments to be passed to the node during initialization
			
			Methods of Loading Virtual Node:
				filename: an import-able module containing the virtual node.
				URL: a URL pointing to a module as a resource containing the virtual node.
				module: a python module name containing the virtual node.
		
			Solo/Gestalt virtual nodes initialize by first connecting to their interface and then requesting
			a driver URL from the node. This driver is then loaded into the shell as the virtual node.
		'''

		#call base class __init__ method
		super(soloIndependentNode, self).__init__()
		
		#assign parameters to variables
		self.name = name
		self.filename = filename
		self.URL = URL
		self.module = module
		
		#connect to interface
		if interface:
			self.interface.set(interface, self)	#interface isn't shared with other nodes, so owner is self.		
		else:
			self.interface.set(interfaces.serialInterface(baudRate = 115200))
			self.interface.acquirePort('lufa')

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
		
	
	