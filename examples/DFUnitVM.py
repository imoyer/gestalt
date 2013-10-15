# Desktop Factory Unit Virtual Machine
# Built Using Gestalt

# (C) 2013 ILAN E. MOYER and the MIT CADLAB


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
		else: self.fabnet = interfaces.gestaltInterface('FABNET', interfaces.serialInterface(baudRate = 115200, interfaceType = 'ftdi', portName = '/dev/tty.usbserial-FTVG6FKT'))
		
	def initControllers(self):
		self.xAxisNode = nodes.networkedGestaltNode('X Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.yAxisNode = nodes.networkedGestaltNode('Y Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.zAxisNode = nodes.networkedGestaltNode('Z Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.xyzNode = nodes.compoundNode(self.xAxisNode, self.yAxisNode, self.zAxisNode)

	def initCoordinates(self):
		self.position = state.coordinate(['mm','mm','mm'])	#X,Y,Z
	
	def initKinematics(self):
		self.xAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(0.9), elements.pulley.forward(11.6), elements.invert.forward(True)])
		self.yAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(0.9), elements.pulley.forward(11.6), elements.invert.forward(True)])
		self.zAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2.54), elements.invert.forward(False)])

		self.stageKinematics = kinematics.direct(3)	#direct drive on all three axes
	
	def initFunctions(self):
		self.move = functions.move(virtualMachine = self, virtualNode = self.xyzNode, axes = [self.xAxis, self.yAxis, self.zAxis], kinematics = self.stageKinematics, machinePosition = self.position,
								planner = 'null')
		self.jog = functions.jog(self.move)	#an incremental wrapper for the move function
		pass
		
	def initLast(self):
#		self.machineControl.setMotorCurrents(aCurrent = 0.8, bCurrent = 0.8, cCurrent = 0.8)
		self.xyzNode.setVelocityRequest(0)	#clear velocity on nodes. Eventually this will be put in the motion planner on initialization to match state.
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
	desktopFactory = virtualMachine(persistenceFile = "test.vmp")
#	desktopFactory.xyzNode.setMotorCurrent(1.1)
#	desktopFactory.xyzNode.loadProgram('086-005a.hex')
	desktopFactory.xyzNode.setVelocityRequest(2)
	fileReader = rpc.fileRPCDispatch()
	fileReader.addFunctions(('move',desktopFactory.move),
							('jog', desktopFactory.jog))	#expose these functions on the file reader interface.


	rpcDispatch = rpc.httpRPCDispatch(address = '0.0.0.0', port = 27272)
	notice(desktopFactory, 'Started remote procedure call dispatcher on ' + str(rpcDispatch.address) + ', port ' + str(rpcDispatch.port))
	rpcDispatch.addFunctions(('move',desktopFactory.move),
							('position', desktopFactory.getPosition),
							('jog', desktopFactory.jog),
							('disableMotors', desktopFactory.xyzNode.disableMotorsRequest),
							('loadFile', fileReader.loadFromURL),
							('runFile', fileReader.runFile),
							('setPosition', desktopFactory.setPosition))	#expose these functions on an http interface
	rpcDispatch.addOrigins('http://tq.mit.edu', 'http://127.0.0.1:8000')	#allow scripts from these sites to access the RPC interface
	rpcDispatch.start()