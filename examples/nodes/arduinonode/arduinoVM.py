# Forked from DFUnitVM Oct 2013
# set portname
# set location of hex file for bootloader
#

#------IMPORTS-------
from gestalt import nodes
from gestalt import interfaces
from gestalt import machines
from gestalt import functions
from gestalt.machines import elements
from gestalt.machines import kinematics
from gestalt.machines import state
from gestalt.utilities import notice
from gestalt.publish import rpc	#remote procedure call dispatcher
import time


#------VIRTUAL MACHINE------
class virtualMachine(machines.virtualMachine):
	
	def initInterfaces(self):
		self.arduinoInterface = interfaces.serialInterface(baudRate = 38400, interfaceType = 'lufa', portName = '/dev/ttyACM0')
		
	def initControllers(self):
		self.arduinonode = nodes.soloGestaltNode(name = "alice", interface = self.arduinoInterface, filename = "arduinovirtualnode.py")
		pass

	def initCoordinates(self):
		pass
	
	def initKinematics(self):
		pass
	
	def initFunctions(self):
		pass
		
	def initLast(self):
		pass
	
	def publish(self):
		pass


#------IF RUN DIRECTLY FROM TERMINAL------
if __name__ == '__main__':
	arduinoVM = virtualMachine()
	arduinoVM.arduinonode.svcToggleLed()
	time.sleep(1)
	arduinoVM.arduinonode.svcToggleLed()
	time.sleep(1)
	print arduinoVM.arduinonode.svcAddition(1023,2)
	


