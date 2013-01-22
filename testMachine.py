from gestalt.Nodes import printrboard
from gestalt import nodes
from gestalt import interfaces

#myPrintrboard = nodes.soloIndependentNode(name = 'myPrintrboard', module = printrboard)
#gsArduino = nodes.soloGestaltNode(name = 'gsArduino1')

myInterface = interfaces.gestaltInterface('myInterface', interfaces.serialInterface(baudRate = 115200, interfaceType = 'ftdi', portName = '/dev/tty.usbserial-FTSEUEOG'))
myFabUnit = nodes.networkedGestaltNode('myFabUnit', myInterface)
