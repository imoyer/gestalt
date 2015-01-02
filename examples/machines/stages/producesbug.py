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
		if self.providedInterface: self.fabnet = self.providedInterface		#providedInterface is defined in the virtualMachine class.
		else: self.fabnet = interfaces.gestaltInterface('FABNET', interfaces.serialInterface(baudRate = 115200, interfaceType = 'ftdi', portName = '/dev/ttyUSB0'))
		
	def initControllers(self):
		self.xAxisNode = nodes.networkedGestaltNode('X Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.yAxisNode = nodes.networkedGestaltNode('Y Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.uAxisNode = nodes.networkedGestaltNode('U Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.vAxisNode = nodes.networkedGestaltNode('V Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)

		#self.xyNode = nodes.compoundNode(self.xAxisNode, self.yAxisNode)
		#self.uvNode = nodes.compoundNode(self.uAxisNode, self.vAxisNode)
		
		self.xyuvNode = nodes.compoundNode(self.xAxisNode, self.yAxisNode, self.uAxisNode, self.vAxisNode)

	def initCoordinates(self):
		self.position = state.coordinate(['mm','mm','mm', 'mm'])
	
	def initKinematics(self):
		self.xAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(True)])
		self.yAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(True)])
		self.uAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(True)])
		self.vAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(True)])

		self.stageKinematics = kinematics.direct(4)	#direct drive on all axes
	
	def initFunctions(self):
		self.move = functions.move(virtualMachine = self, virtualNode = self.xyuvNode, axes = [self.xAxis, self.yAxis, self.uAxis, self.vAxis], kinematics = self.stageKinematics, machinePosition = self.position,planner = 'null')
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
	stages = virtualMachine(persistenceFile = "test.vmp")
#	stages.xyNode.setMotorCurrent(.8)
#	stages.uvNode.setMotorCurrent(.8)
#	stages.xyNode.loadProgram('../../../086-005/086-005a.hex')
#	stages.uvNode.loadProgram('../../../086-005/086-005a.hex')
	#stages.xyNode.setVelocityRequest(8)
	#stages.uvNode.setVelocityRequest(8)
	stages.xyuvNode.setVelocityRequest(8)	

	stages.move([1,1,0,0],0)
	time.sleep(1)
	print "xy"
	stages.move([2,2,0,0],0)
	time.sleep(1)
	print "xy"
	stages.move([3,3,0,0],0)
	time.sleep(1)
	print "xy"
	stages.move([3,3,1,1],0)
	time.sleep(1)
	print "u"
	stages.move([3,3,2,2],0)
	time.sleep(1)
	print "u"
	stages.move([3,3,3,3],0)
	time.sleep(1)
	print "u"
	#stages.move([0,0,1,0],0)
	#time.sleep(1)
#	print "u"
#	stages.move([0,0,1,0],0)
#	time.sleep(1)
#	print "u"
#	stages.move([0,0,1,0],0)
#	time.sleep(1)
#	print "u"
#	stages.move([0,0,0,1],0)
#	time.sleep(1)
#	print "v"
#	stages.move([0,0,0,1],0)
#	time.sleep(1)
#	print "v"
#	stages.move([0,0,0,1],0)
#	time.sleep(1)
#	print "v"
#	time.sleep(1)

