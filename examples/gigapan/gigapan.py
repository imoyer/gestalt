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
import random

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
		for i in range(NUMCAMERAREADS):
		#the buffer of images needs to be constantly emptied or you get an old image
    			img = cv.QueryFrame(capture)
    		cv.ShowImage("camera", img)
		cv.SaveImage("hi"+str(random.random())[2:]+".jpeg", img)
		
	def takeGigapan(self, vm, capture):
		vm.jog([1.2,0,0])
		#wait for the motor to be still
		vm_status = vm.xAxisNode.spinStatusRequest()
		while vm_status['stepsRemaining'] > 0:
			time.sleep(0.1)
			vm_status = vm.xAxisNode.spinStatusRequest()
			# don't stall the UI while waiting
    			if cv.WaitKey(10) == 27:
        			break
		self.takePhoto()
		
		

class gigapan():
	'''A grid of images and their corresponding moves'''
	
	def __init__(self, x0, y0, x1, y1, image_size):
		self.x0 = x0
		self.y0 = y0
		self.x1 = x1
		self.y1 = y1		
		self.image_size = image_size
		self.currentx = 0
		self.currenty = 0

	def next_move(self):
		pass
		


#------IF RUN DIRECTLY FROM TERMINAL------
if __name__ == '__main__':
	gigmachine = virtualMachine(persistenceFile = "test.vmp")
#	gigmachine.xyzNode.setMotorCurrent(1.1)
#	gigmachine.xyzNode.loadProgram(HEXFILE)
	gigmachine.xyzNode.setVelocityRequest(2)
#	gigmachine.xyzNode.setMotorCurrent(1)
	fileReader = rpc.fileRPCDispatch()
	fileReader.addFunctions(('move',gigmachine.move), ('jog', gigmachine.jog))	#expose these functions on the file reader interface.


	# remote procedure call initialization
	# uncomment if you want to use the tq.mit.edu/pathfinder interface
	#rpcDispatch = rpc.httpRPCDispatch(address = '0.0.0.0', port = 27272)
	#notice(gigmachine, 'Started remote procedure call dispatcher on ' + str(rpcDispatch.address) + ', port ' + str(rpcDispatch.port))
	#rpcDispatch.addFunctions(('move',gigmachine.move),
	#			('position', gigmachine.getPosition),
	#			('jog', gigmachine.jog),
	#			('disableMotors', gigmachine.xyzNode.disableMotorsRequest),
	#			('loadFile', fileReader.loadFromURL),
	#			('runFile', fileReader.runFile),
	#			('setPosition', gigmachine.setPosition))	#expose these functions on an http interface
	#rpcDispatch.addOrigins('http://tq.mit.edu', 'http://127.0.0.1:8000')	#allow scripts from these sites to access the RPC interface
	#rpcDispatch.allowAllOrigins()
	#rpcDispatch.start()
	
	
	capture = cv.CaptureFromCAM(1)
	while True:
		gigmachine.takeGigapan(gigmachine, capture)
    		if cv.WaitKey(10) == 27:
        		break


