# Forked from DFUnitVM Oct 2013

PORT = '/dev/ttyUSB0'
HEXFILE = '../../../086-005/086-005a.hex'
# tune this depending on how many frames are captured during the move
NUMCAMERAREADS = 15

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
import cv2.cv as cv
import sys

#------VIRTUAL MACHINE------
class virtualMachine(machines.virtualMachine):
	
	def initInterfaces(self):
		if self.providedInterface: self.fabnet = self.providedInterface		#providedInterface is defined in the virtualMachine class.
		else: self.fabnet = interfaces.gestaltInterface('FABNET', interfaces.serialInterface(baudRate = 115200, interfaceType = 'ftdi', portName = PORT))
		
	def initControllers(self):
		self.xAxisNode = nodes.networkedGestaltNode('X Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.yAxisNode = nodes.networkedGestaltNode('Y Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.zAxisNode = nodes.networkedGestaltNode('Z Axis', self.fabnet, filename = '086-005a.py', persistence = self.persistence)
		self.xyzNode = nodes.compoundNode(self.xAxisNode, self.yAxisNode, self.zAxisNode)

	def initCoordinates(self):
		self.position = state.coordinate(['mm','mm','mm'])	#X,Y,Z
	
	def initKinematics(self):
		self.xAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(True)])
		self.yAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(True)])
		self.zAxis = elements.elementChain.forward([elements.microstep.forward(4), elements.stepper.forward(1.8), elements.leadscrew.forward(2), elements.invert.forward(False)])

		self.stageKinematics = kinematics.direct(3)	#direct drive on all three axes
	
	def initFunctions(self):
		self.move = functions.move(virtualMachine = self, virtualNode = self.xyzNode, axes = [self.xAxis, self.yAxis, self.zAxis], kinematics = self.stageKinematics, machinePosition = self.position,planner = 'null')
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

#	def setSpindleSpeed(self, speedFraction):
#		self.machineControl.pwmRequest(speedFraction)
#		pass

	def autofocus(self):
		pass

	def takePhoto(self):
		pass

	def takeGigapan(self):
		pass




#------IF RUN DIRECTLY FROM TERMINAL------
if __name__ == '__main__':
	gigapan = virtualMachine(persistenceFile = "test.vmp")
#	gigapan.xyzNode.setMotorCurrent(1.1)
#	gigapan.xyzNode.loadProgram(HEXFILE)
	gigapan.xyzNode.setVelocityRequest(2)
	gigapan.xyzNode.setMotorCurrent(1)
	fileReader = rpc.fileRPCDispatch()
	fileReader.addFunctions(('move',gigapan.move), ('jog', gigapan.jog))	#expose these functions on the file reader interface.


	# remote procedure call initialization
	#rpcDispatch = rpc.httpRPCDispatch(address = '0.0.0.0', port = 27272)
	#notice(gigapan, 'Started remote procedure call dispatcher on ' + str(rpcDispatch.address) + ', port ' + str(rpcDispatch.port))
	#rpcDispatch.addFunctions(('move',gigapan.move),
	#			('position', gigapan.getPosition),
	#			('jog', gigapan.jog),
	#			('disableMotors', gigapan.xyzNode.disableMotorsRequest),
	#			('loadFile', fileReader.loadFromURL),
	#			('runFile', fileReader.runFile),
	#			('setPosition', gigapan.setPosition))	#expose these functions on an http interface
	#rpcDispatch.addOrigins('http://tq.mit.edu', 'http://127.0.0.1:8000')	#allow scripts from these sites to access the RPC interface
	#rpcDispatch.allowAllOrigins()
	#rpcDispatch.start()

	cv.NamedWindow("camera", 1)

	capture = cv.CaptureFromCAM(2)

	gigapan.jog([0,0,-0.1])
	time.sleep(1)
	sys.exit()

	while True:
		for i in range(NUMCAMERAREADS):
    			img = cv.QueryFrame(capture)
    		cv.ShowImage("camera", img)
		gigapan.jog([-1.2,0,0])
		gigapan_status = gigapan.xAxisNode.spinStatusRequest()
		while gigapan_status['stepsRemaining'] > 0:
			time.sleep(0.1)
			gigapan_status = gigapan.xAxisNode.spinStatusRequest()
			# don't stall the UI while waiting
    			if cv.WaitKey(10) == 27:
        			break

    		if cv.WaitKey(10) == 27:
        		break


