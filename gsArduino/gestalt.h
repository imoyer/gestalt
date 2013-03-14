//  GESTALT FOR ARDUINO
//  SIC PROJECT 086 GESTALT
//  (C) 2013 ILAN E. MOYER + MIT CADLAB
//
//  --REVISION HISTORY---------------------------------
//
//  --------------------------------------------------------------------------------------------------------
//  | DATE    | MODIFICATIONS                            | NAME              | FILENAME                    |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |07/03/12 | CREATED                                  | ILAN E. MOYER     | gsArduino1.pde              |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |07/29/12 | MODIFIED FOR UNITS OF FAB                | ILAN E. MOYER     | 086-001a.c	           	   |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |01/13/13 | UPDATED FOR ARDUINO UNO                  | ILAN E. MOYER     | gsArduinoUno.ino            |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |01/18/13 | LIBRARY FOR ARDUINO UNO                  | ILAN E. MOYER     | gestalt.h		 	       |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |03/14/13 | ADDED USER LOOP.	                     | ILAN E. MOYER     | gestalt.h		 	       |
//  --------------------------------------------------------------------------------------------------------
//
//  --ABOUT GESTALT-------------------------------------
//	Gestalt is a framework for automating physical hardware. The basic concept is that each unit of hardware,
//	called a "node", has a matching python module called a "virtual node." Gestalt provides a means of connecting
//	the physical node with the virtual node along with tools for creating both. This library is designed to assist
// 	in programming nodes in C using the Arduino platform. 

//	Gestalt also supports custom hardware with additional features beyond what is possible using stand-alone Arduino
//	boards. These features include networking and synchronization across multiple nodes to create complex fabrication
//	machines.
//
//	More information on Gestalt is avaliable at www.pygestalt.org


#ifndef gestalt
#define gestalt

#ifdef __cplusplus
extern "C"{
#endif

#include <inttypes.h>


//PACKET FORMAT DEFINITIONS
// const uint8_t startByteLocation   = 0;
// const uint8_t addressLocation     = 1;	//two bytes for address
// const uint8_t portLocation        = 3;
// const uint8_t lengthLocation      = 4;
const uint8_t payloadLocation     = 5;

// --DEFINE TRANCEIVER MEMORY--
extern uint8_t txBuffer[255];  //transmitter buffer
extern uint8_t rxBuffer[255];  //receiver buffer

// --DEFINE IO PORTS AND PINS--
#ifdef standardGestalt
extern volatile uint8_t *IO_ledPORT; //The led which is used to identify nodes on the network.
extern volatile uint8_t *IO_ledDDR;
extern volatile uint8_t *IO_ledPIN;
extern volatile uint8_t IO_ledPin;

extern volatile uint8_t *IO_buttonPORT;  //The button which is used to identify nodes on the network.
extern volatile uint8_t *IO_buttonDDR;   //This is only used by networked nodes.
extern volatile uint8_t *IO_buttonPIN;
extern volatile uint8_t IO_buttonPin;

extern volatile uint8_t *IO_txrxPORT;  //Xceiver 
extern volatile uint8_t *IO_txrxDDR;
extern volatile uint8_t IO_txPin;
extern volatile uint8_t IO_rxPin;

extern volatile uint8_t *IO_txEnablePORT;
extern volatile uint8_t *IO_txEnableDDR;
extern volatile uint8_t IO_txEnablePin; //Transmit enable for RS485
#endif

//PRIVATE FUNCTIONS
void setup();
void loop();
void packetRouter();
void svcIdentifyNode();
void svcRequestURL();
void svcSetIPAddress();
void svcStatus();
void svcResetNode();
void svcBootloaderCommand();
void bootloaderInit();
void applicationStart();
void svcBootloaderData();
void writePage();
void svcBootloaderReadPage();


#ifdef standardGestalt
//This is being compiled as an independent program, not using the arduino IDE.
int main();
#endif

//PUBLIC FUNCTIONS
void transmitPacket();
void transmitUnicastPacket(uint8_t port, uint8_t length);
void transmitMulticastPacket(uint8_t port, uint8_t length);
void userSetup();
void userLoop();
void userPacketRouter(uint8_t destinationPort);
void setURL(char *newURL, uint8_t newURLLength);


#ifdef __cplusplus
}	//extern "C"
#endif

#endif
