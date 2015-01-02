# Forked from DFUnitVM Oct 2013

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
import cv2
import sys
import time

#------VIRTUAL MACHINE------
class virtualMachine(machines.virtualMachine):

        def __init__(self,camnum):
                self.camnum = camnum
                self.windowname = "camera"
                cv.NamedWindow(self.windowname, 1)
                self.capture = cv.CaptureFromCAM(self.camnum)
                self.PORT = '/dev/ttyUSB0'
                self.HEXFILE = '../../../086-005/086-005a.hex'
                # tune this depending on how many frames are captured during the move
                self.NUMCAMERAREADS = 15

                self.calibtarget_dim = (7,4)
                
                # TODO check and store undistortion info
                self.undistortinfo = False

        def __del__(self):
                cv.DestroyWindow(self.windowname)

	def initInterfaces(self):
		if self.providedInterface: self.fabnet = self.providedInterface		#providedInterface is defined in the virtualMachine class.
		else: self.fabnet = interfaces.gestaltInterface('FABNET', interfaces.serialInterface(baudRate = 115200, interfaceType = 'ftdi', portName = self.PORT))
		
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
        
        def setLightIntensity(self):
                pass

	def autofocus(self):
		pass
		
	def takePhoto(self, showImg=False, saveImg=False):
		for i in range(NUMCAMERAREADS):
		#the buffer of images needs to be constantly emptied or you get an old image
    			img = cv.QueryFrame(self.capture)
			time.sleep(.1)
                img = self.correctImg(img)
                if(showImg):
                        cv.ShowImage(self.windowname, img)
                if(saveImg):
                        pos = self.getPosition()
                        cv.SaveImage("images/hi%.03f-%.03f-%.03f.jpg", img) % pos
                        #cv.SaveImage("images/hi"+str(time.time())[6:]+".jpeg", img)
                return img

        def captureUndistortMap(self):
                img = cv.QueryFrame(self.capture)
                cv.ShowImage(self.windowname,img)
                [found corners] = cv2.findCirclesGrid(img, self.calibtarget_dim, flags = cv2.CALIB_CB_ASYMMETRIC_GRID)
                cv2.drawChessboardCorners(img, self.calibtarget_dim, corners, found)

                if cv.WaitKey(10) & 0xff == 'c':
                        return (corners)

        def initUndistort(self)
                captured_corners = [cv2.findCirclesGrid(img, self.calibtarget_dim, flags = cv2.CALIB_CB_ASYMMETRIC_GRID) for img in captured_image_list]
                #load camera intrinsic params
                #get optimal camera matrix (cv2 equiv)
                #init undistorm rectify map (cv2 equiv)
                #store it
                pass

        def correctImage(self,img):
                if(not undistortmap):
                        #capture undistort map
                        #init undistort map
                        undistortmap = True
                #remap image
                return img

	def takeGigapan(self):
                #move to each location and take image
                #nadya did this already?
		pass

        def stitchGigapan(self,gigastack):
                #rectify/correct all images
                #create large canvas
                #place all images in canvas
                #blending?
                pass

        def bar(self):
		gigapan_status = self.xAxisNode.spinStatusRequest()
		while gigapan_status['stepsRemaining'] > 0:
			time.sleep(0.1)
			gigapan_status = self.xAxisNode.spinStatusRequest()
			# don't stall the UI while waiting
    			if cv.WaitKey(10) == 27:
        			break
        
        def barMove(self,pos):
                curr = self.getPosition()
                #this is stupid but I can't remember map syntax w/o google
                a = curr['position']
                for i in range(len(pos)):
                        pos[i]+=a[i]
                barMoveAbs(pos)

        def barMoveAbs(self,pos):
                setPosition(pos)
                bar()

        def takeFocalStack(self,rangetop,rangebottom,nstack):
                r = rangetop-rangebottom
                step = r/nstack
                focalstack = []
                self.barMove((0,0,-r/2));
                for pos in range(1,nstack):
                        self.barMove([0,0,step])
                        focalstack.append(self.takePhoto())
                return focalstack
	
	def nextImageLoc(self, vm, gigapan, x, y):
		print "moving to %i %i"%(x,y)
		vm.move([x,y,0],0) #FIX this is a dummy velocity 0
		#wait for the motor to be still
		vm_status = vm.xAxisNode.spinStatusRequest()
		while vm_status['stepsRemaining'] > 0:
			time.sleep(0.1)
			vm_status = vm.xAxisNode.spinStatusRequest()
			# don't stall the UI while waiting
    			if cv.WaitKey(10) == 27:
        			break

	def takeGigapan(self, vm, capture):
		gig = gigapan(0,0,10,10,1,1) # x0,y0,x1,y1,imgsizex,imgsizey
		locs = gig.locations()
		for (x,y) in locs:
			self.nextImageLoc(vm, gig, x, y)
			self.takePhoto(capture, x, y)
		
		

class gigapan():
	'''A grid of images and their corresponding moves'''
	
	def __init__(self, x0, y0, x1, y1, image_sizex, image_sizey):
		self.x0 = x0
		self.y0 = y0
		self.x1 = x1
		self.y1 = y1		
		self.image_sizex = image_sizex
		self.image_sizey = image_sizey
		self.x = 0.0
		self.y = 0.0

	def next_move(self):
		self.currentx = self.currentx + self.incrementx
		self.currenty = self.currenty + self.incrementy
		return (x,y)

	def locations(self):
		binsx = self.x1-self.x0/self.image_sizex
		binsy = self.y1-self.y0/self.image_sizey
		locations = []
		for i in range(0, binsx):
			for j in range(0, binsy):
				locations.append((i*self.image_sizex, j*self.image_sizey))
		return locations
			
#------IF RUN DIRECTLY FROM TERMINAL------
if __name__ == '__main__':
	gigamachine = virtualMachine(persistenceFile = "test.vmp", camnum = 2)
#	gigamachine.xyzNode.setMotorCurrent(1.1)
#	gigamachine.xyzNode.loadProgram(HEXFILE)
	gigamachine.xyzNode.setVelocityRequest(2)
#	gigamachine.xyzNode.setMotorCurrent(1)
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

	while True:
                img = gigamachine.getCurrentFrame()
    		cv.ShowImage(gigamachine.windowname, img)
		gigamachine.barMove([-1.2,0,0])

    		if cv.WaitKey(10) == 27:
        		break
	#while True:
	#	gigmachine.takeGigapan(gigmachine, capture)
    	#	if cv.WaitKey(10) == 27:
        #		break

