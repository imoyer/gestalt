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
import io


#------VIRTUAL MACHINE------
class virtualMachine(machines.virtualMachine):
	
	def initInterfaces(self):
		if self.providedInterface: self.fabnet = self.providedInterface		#providedInterface is defined in the virtualMachine class.
		else: self.fabnet = interfaces.gestaltInterface('FABNET', interfaces.serialInterface(baudRate = 115200, interfaceType = 'ftdi', portName = '/dev/ttyUSB0'))
		
	def initControllers(self):
		self.xAxisNode = nodes.networkedGestaltNode('X Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.xNode = nodes.compoundNode(self.xAxisNode)

	def initCoordinates(self):
		self.position = state.coordinate(['mm'])
	
	def initKinematics(self):
		self.xAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(6.096), elements.invert.forward(True)])
		
		self.stageKinematics = kinematics.direct(1)	#direct drive on all axes
	
	def initFunctions(self):
		self.move = functions.move(virtualMachine = self, virtualNode = self.xNode, axes = [self.xAxis], kinematics = self.stageKinematics, machinePosition = self.position,planner = 'null')
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
	
	def setPosition(self, position  = [None]):
		self.position.future.set(position)

	def setSpindleSpeed(self, speedFraction):
#		self.machineControl.pwmRequest(speedFraction)
		pass

#------IF RUN DIRECTLY FROM TERMINAL------
if __name__ == '__main__':
	stage = virtualMachine(persistenceFile = "test.vmp")
	#stage.xNode.loadProgram('../../../086-005/086-005a.hex')
	#stage.xNode.setMotorCurrent(1)

	stage.xNode.setVelocityRequest(8)	
	
	#f = open('path.csv','r')
	#supercoords = []
	#for line in f.readlines():
	#	supernum = float(line)
	#	supercoords.append([supernum])

	supercoords = [[10],[20],[10],[0]]

	for coords in supercoords:
		stage.move(coords, 0)
		status = stage.xAxisNode.spinStatusRequest()
		while status['stepsRemaining'] > 0:
			time.sleep(0.001)
			status = stage.xAxisNode.spinStatusRequest()	
	


