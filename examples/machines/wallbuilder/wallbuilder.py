# Forked from wallbuilder july 2014
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
		if self.providedInterface: self.fabnet = self.providedInterface		#providedInterface is defined in the virtualMachine class.
		else: self.fabnet = interfaces.gestaltInterface('FABNET', interfaces.serialInterface(baudRate = 115200, interfaceType = 'ftdi', portName = '/dev/ttyUSB0'))
		
	def initControllers(self):
		self.pAxisNode = nodes.networkedGestaltNode('P Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.qAxisNode = nodes.networkedGestaltNode('Q Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.rAxisNode = nodes.networkedGestaltNode('R Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.sAxisNode = nodes.networkedGestaltNode('S Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)

		self.pqNode = nodes.compoundNode(self.pAxisNode, self.qAxisNode)
		self.rsNode = nodes.compoundNode(self.rAxisNode, self.sAxisNode)
		
		self.pqrsNode = nodes.compoundNode(self.pAxisNode, self.qAxisNode, self.rAxisNode, self.sAxisNode)

	def initCoordinates(self):
		self.position = state.coordinate(['mm','mm','mm', 'mm'])
	
	def initKinematics(self):
		self.pAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(True)])
		self.qAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(True)])
		self.rAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(True)])
		self.sAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(True)])

		self.stageKinematics = kinematics.direct(4)	#direct drive on all axes
	
	def initFunctions(self):
		self.move = functions.move(virtualMachine = self, virtualNode = self.pqrsNode, axes = [self.pAxis, self.qAxis, self.rAxis, self.sAxis], kinematics = self.stageKinematics, machinePosition = self.position,planner = 'null')
		self.jog = functions.jog(self.move)	#an incremental wrapper for the move function
		pass
		
	def initLast(self):
#		self.machineControl.setMotorCurrents(aCurrent = 0.8, bCurrent = 0.8, cCurrent = 0.8)
#		self.xyzNode.setVelocityRequest(0)	#clear velocity on nodes. Eventually this will be put in the motion planner on initialization to match state.
		pass
	
	def publish(self):
#		self.publisher.addNodes(self.machineControl)
		pass
	
	def getPosition(self):
		return {'position':self.position.future()}
	
	def setPosition(self, position  = [None, None, None]):
		self.position.future.set(position)

	def setSpindleSpeed(self, speedFraction):
#		self.machineControl.pwmRequest(speedFraction)
		pass

#------IF RUN DIRECTLY FROM TERMINAL------
if __name__ == '__main__':
	wallbuilder = virtualMachine(persistenceFile = "test.vmp")
#	wallbuilder.pqNode.setMotorCurrent(.8)
#	wallbuilder.rsNode.setMotorCurrent(.8)
#	wallbuilder.pqNode.loadProgram('../../../086-005/086-005a.hex')
#	wallbuilder.rsNode.loadProgram('../../../086-005/086-005a.hex')
	wallbuilder.pqNode.setVelocityRequest(8)
	wallbuilder.rsNode.setVelocityRequest(8)
	wallbuilder.pqrsNode.setVelocityRequest(8)

	fun = [] #add some moves here

	for coords in fun:
		wallbuilder.move(coords, 0)
		status = wallbuilder.xAxisNode.spinStatusRequest()
		while status['stepsRemaining'] > 0:
			time.sleep(0.01)
			status = wallbuilder.xAxisNode.spinStatusRequest()	
