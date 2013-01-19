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
//  |07/29/12 | MODIFIED FOR UNITS OF FAB                | ILAN E. MOYER     | 086-001a.c	           			 |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |01/13/13 | UPDATED FOR ARDUINO UNO                  | ILAN E. MOYER     | gsArduinoUno.ino            |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |01/18/13 | LIBRARY FOR ARDUINO UNO                  | ILAN E. MOYER     | gestalt.h		 	             |
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
  
//PRIVATE FUNCTIONS
void setup();
void loop();
void packetRouter();
void svcIdentifyNode();
void svcRequestURL();
void svcSetIPAddress();
void svcStatus();
void svcResetNode();

//PUBLIC FUNCTIONS
void transmitPacket();
void userSetup();
void userPacketRouter(uint8_t destinationPort);
void setURL(char *newURL, uint8_t newURLLength);

#ifdef __cplusplus
}	//extern "C"
#endif

#endif
