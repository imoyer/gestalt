#include <gestalt.h>
#include delay

//--- URL ---
// When a physical node is associated with a virtual node, the physical node reports a URL pointing to where the
// virtual node file can be found online. This allows the author of the physical node to publish a virtual node
// 'driver' online, and have it automatically loaded by the Gestalt framework.
char myurl[] = "http://www.myurl.com/myVirtualNode.py"; //URL that will be reported to virtual node on acquisition

//--- GESTALT PORT DEFINITIONS ---
// Once a packet has been received by the node, it is directed to a specific service routine handler. A port number
// is used to associate the packet with its handler. Ports 0 -> 9 and 255 are reserved by the gestalt firmware library,
// but you are free to use any other port.
#define examplePort    10 

void userSetup(){
  // The Gestalt version of the typical Arduino setup() function. Put anything here that you want to be called
  // just once on startup.
  setURL(&myurl[0], sizeof(myurl)); //Registers URL with Gestalt library
};

void userLoop(){
  // The Gestalt version of the typical Arduino loop() function. Code placed here will be called in an infinite loop.
};

void userPacketRouter(uint8_t destinationPort){
  // This function is responsible for calling the appropriate service routine for a given inbound packet.
  //    destinationPort -- the port number of the inbound packet
  
  switch(destinationPort){
    case examplePort: //a message was sent to the example port
      svcExampleMessage();
      break;
    // add additional case statements for new ports here, following the pattern immediately above.
  }
};

//--- SERVICE ROUTINES ---
// These are functions that get called by the userPacketRouter function
// when a message is received over the gestalt interface.

void svcExampleMessage(){
  //UNSIGNED INTEGER, bytes 0-1
  uint16_t exampleUnsignedInteger = 12345;
  //load message into transmission buffer. Note that byte order is little endian.
  txBuffer[payloadLocation] = uint8_t((exampleMessage&0xFF)); //mask LSB
  txBuffer[payloadLocation+1] = uint8_t((exampleMessage&0xFF00)>>8); //mask MSB

  

  transmitUnicastPacket(examplePort, 2); //transmit as unicast packet with 2 payload bytes
}

