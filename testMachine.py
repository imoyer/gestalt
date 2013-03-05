from gestalt.Nodes import printrboard
from gestalt import nodes
from gestalt.Nodes import dummyNode
from gestalt import interfaces

#myPrintrboard = nodes.soloIndependentNode(name = 'myPrintrboard', module = printrboard)
#gsArduino = nodes.soloGestaltNode(name = 'gsArduino1')

myInterface = interfaces.gestaltInterface('myInterface', interfaces.serialInterface(baudRate = 115200, interfaceType = 'ftdi', portName = '/dev/tty.usbserial-FTVG67VT'))
myFabUnit = nodes.networkedGestaltNode('myFabUnit', myInterface, module = dummyNode)

#gsArduino = nodes.soloGestaltNode(name = 'gsArduino', interface = interfaces.serialInterface(baudRate = 76800, interfaceType = 'lufa', 
#																								portName = "/dev/tty.usbmodemfa131"), module = dummyNode)

#gsArduino.identifyRequest()

#print gsArduino.urlRequest()