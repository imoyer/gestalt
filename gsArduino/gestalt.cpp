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
//  |01/18/13 | LIBRARY FOR ARDUINO UNO                  | ILAN E. MOYER     | gestalt.cpp		             |
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


#ifdef __cplusplus
extern "C"{
#endif

//--INCLUDES--
#include "gestalt.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <inttypes.h>
#include <stdbool.h>
#include <avr/pgmspace.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/eeprom.h>
#include <avr/wdt.h>


// --DEFINE STANDARD PINS AND PORTS--
//--ui--
#define UIPort			        PORTB
#define UIDir								DDRB
#define UIPin								PINB

#define ledPin			5  //PB5

#define UIDirInit		(1<<ledPin)
#define UIPortInit	        0
//--txrx--
#define txrxPort		PORTD
#define	txrxDir			DDRD
#define	txrxPin			PIND

#define rxPin				0  //PD0
#define txPin				1  //PD1

#define txrxDirInit		(1<<txPin)
#define txrxPortInit	        (1<<rxPin)	//enable pullups on rxpin


//--DEFINE NODE VARIABLES--
uint8_t networkAddress[2];	//network address
char defaultURL[] = "http://tq.mit.edu/gestalt/086-000.py";	//node URL
char *url = 0;	//pointer to URL
uint8_t urlLength = 0;	//stores current URL length
const uint8_t persistentIPAddress0 = 0;	//used for EEPROM storage of IP address
const uint8_t persistentIPAddress1 = 1;      //note: changed from uint8_t* to int to use the arduino version of eeprom.read()

const uint8_t applicationValid = 170; //0b10101010

// --DEFINE TRANCEIVER MEMORY--
uint8_t txBuffer[255];  //transmitter buffer
uint8_t rxBuffer[255];  //receiver buffer

//--DEFINE TRANCEIVER STATE VARIABLES--
uint8_t rxPosition = 0;
uint8_t txPosition = 0;
uint8_t watchdogTime = 0;

uint8_t rxData = 0;
uint8_t rxPacketLength = 0;
uint8_t rxPacketChecksum = 0;

uint8_t txData = 0;
uint8_t txPacketLength = 0;
uint8_t txPacketChecksum = 0;

//--DEFINE TRANCEIVER SETTINGS--
const uint8_t watchdogTimeout = 1;  //timeout in units of timer2 - around 1ms with prescalar of 64 @ 16MHz

//--FLAGS--
typedef struct {  //http://www.avrfreaks.net/index.php?name=PNphpBB2&file=viewtopic&t=57006
  bool f0:1;
  bool f1:1;
  bool f2:1;
  bool f3:1;
  bool f4:1;
  bool f5:1;  
  bool f6:1;
  bool f7:1;
} PackedBool;

#define packetReceivedFlag ((volatile PackedBool*)(&GPIOR0))->f7
#define packetInboundFlag ((volatile PackedBool*)(&GPIOR0))->f6
#define packetOutboundFlag ((volatile PackedBool*)(&GPIOR0))->f5


//--DEFINE PACKET FORMAT--
const uint8_t startByteLocation   = 0;
const uint8_t addressLocation     = 1;	//two bytes for address
const uint8_t portLocation        = 3;
const uint8_t lengthLocation      = 4;
const uint8_t payloadLocation     = 5;

const uint8_t unicast             = 72;  //start byte value for unicast packet
const uint8_t multicast		  = 138; //start byte value for multicast packet


// CRC TABLE
// -this gets placed in program memory rather than RAM
uint8_t crcTable[256] PROGMEM = {
  0, 7, 14, 9, 28, 27, 18, 21, 56, 63, 54, 49, 36, 35, 42, 45, 112, 119, 
  126, 121, 108, 107, 98, 101, 72, 79, 70, 65, 84, 83, 90, 93, 224, 231, 
  238, 233, 252, 251, 242, 245, 216, 223, 214, 209, 196, 195, 202, 205, 
  144, 151, 158, 153, 140, 139, 130, 133, 168, 175, 166, 161, 180, 179, 
  186, 189, 199, 192, 201, 206, 219, 220, 213, 210, 255, 248, 241, 246, 
  227, 228, 237, 234, 183, 176, 185, 190, 171, 172, 165, 162, 143, 136, 
  129, 134, 147, 148, 157, 154, 39, 32, 41, 46, 59, 60, 53, 50, 31, 24, 
  17, 22, 3, 4, 13, 10, 87, 80, 89, 94, 75, 76, 69, 66, 111, 104, 97, 102, 
  115, 116, 125, 122, 137, 142, 135, 128, 149, 146, 155, 156, 177, 182, 
  191, 184, 173, 170, 163, 164, 249, 254, 247, 240, 229, 226, 235, 236, 
  193, 198, 207, 200, 221, 218, 211, 212, 105, 110, 103, 96, 117, 114, 
  123, 124, 81, 86, 95, 88, 77, 74, 67, 68, 25, 30, 23, 16, 5, 2, 11, 12, 
  33, 38, 47, 40, 61, 58, 51, 52, 78, 73, 64, 71, 82, 85, 92, 91, 118, 
  113, 120, 127, 106, 109, 100, 99, 62, 57, 48, 55, 34, 37, 44, 43, 6, 1, 
  8, 15, 26, 29, 20, 19, 174, 169, 160, 167, 178, 181, 188, 187, 150, 145, 
  152, 159, 138, 141, 132, 131, 222, 217, 208, 215, 194, 197, 204, 203, 
  230, 225, 232, 239, 250, 253, 244, 243};

// -- FUNCTION: SETUP --
// Basic functionality for communication with the PC is configured here.

void setup(){
	
	//DISABLE SYSTEM WATCHDOG TIMER
  MCUSR = 0;
  wdt_disable();
      
  //INITIALIZE PINS
	UIDir 		= UIDirInit;
	UIPort 		= UIPortInit;
	
	txrxDir 	= txrxDirInit;
	txrxPort 	= txrxPortInit;
  
  
  //INITIALIZE USART
  UBRR0 = 12;  //8 = 115.2kbps, 12 = 76.8kbps NOTE: tried 115200 without success from MacOSX, 76800 worked fine.
  UCSR0B = (1<<RXEN0)|(1<<TXEN0)|(0<<UDRIE0)|(1<<RXCIE0)|(0<<TXCIE0);  //enable transmitter and receiver, rx interrupts
  UCSR0C = (0 << UMSEL00) | (0 << UPM00) | (0 << USBS0) | (3 <<UCSZ00);  //8 data bits, 1 stop bit, no parity

  //CONFIGURE TIMER2 AS WATCHDOG
  TCCR2A = (0 << COM2A1)|(0 << COM2A0)|(0 << COM2B1)|(0 << COM2B0)|(0 << WGM21)|(0 << WGM20); //counter in normal mode
  TCCR2B = (0 << FOC2A)|(0 << FOC2B)|(0 << WGM22)|(4 << CS20);  // C/64 prescalar
  TIMSK2 = (0 << OCIE2B)|(0 << OCIE2A)|(0 << TOIE2);  // Disable interrupts for now
  
  
  
  //LOAD NETWORK ADDRESS
  networkAddress[0]=eeprom_read_byte((uint8_t*)persistentIPAddress0);
  networkAddress[1]=eeprom_read_byte((uint8_t*)persistentIPAddress1);
  
  //SET DEFAULT URL
  setURL(&defaultURL[0], sizeof(defaultURL));
  
  //USER SETUP
  userSetup();		//This should be defined in the user program
  
  //ENABLE GLOBAL INTERRUPTS
  sei();
}

//----RECEIVER CODE-------------------------------------
//--RECEIVER INTERRUPT ROUTINE--
ISR(USART_RX_vect){
	//enable watchdog
  TCNT2 = 0;  //clear timer2
  watchdogTime = 0; //clear watchdog value
  TIMSK2 = (1 << TOIE2);  //enable watchdog interrupt
  
  rxData = UDR0;  //get data byte from receiver
  rxBuffer[rxPosition] = rxData;  //load received byte into rxBuffer
  packetInboundFlag = true; //set mid-transmission flag
  if (rxPosition == lengthLocation){  //check if current byte is packet length byte
    rxPacketLength = rxData;  //set packet length
  }
  
  if ((rxPosition < lengthLocation)||(rxPosition < rxPacketLength)){  //packet is not finished
    rxPacketChecksum = pgm_read_byte(&(crcTable[(rxData^rxPacketChecksum)]));  //calculates new checksum value
    rxPosition ++;  //increments packet position
  }else{  //packet has been received
    if ((rxBuffer[startByteLocation]==multicast)&&(rxPacketChecksum==rxData)){ //multicast packet good
      TIMSK2 = (0 << TOIE2);  //disable watchdog interrupt
      packetReceivedFlag = true;
    }
    if ((rxBuffer[startByteLocation]==unicast)&&(rxPacketChecksum==rxData)&&(rxBuffer[addressLocation]==networkAddress[0])&&(rxBuffer[addressLocation+1]==networkAddress[1])){
      TIMSK2 = (0 << TOIE2);  //disable watchdog interrupt
      packetReceivedFlag = true;
    }
    TIMSK2 = (0 << TOIE2);  //disable watchdog interrupt
    packetInboundFlag = false;
    rxPosition = 0;
    rxPacketChecksum = 0;
  }
}

//--RECEIVER WATCHDOG INTERRUPT ROUTINE--
ISR(TIMER2_OVF_vect){
  if (watchdogTime == watchdogTimeout){
    watchdogTime = 0;
    rxPosition = 0;
    rxPacketChecksum = 0;
    packetInboundFlag = false;
    packetReceivedFlag = false;
    TIMSK2 = (0 <<TOIE2);  //disable watchdog timer
  }else{
    watchdogTime++;
  }
}


//------TRANSMITTER CODE----------------------------------------------
//--TRANSMITTER INTERRUPT-------------
ISR(USART_TX_vect){
  UCSR0A = (1<<TXC0);  //writing 1 to this location clears any potential transmission completion flags
  UCSR0B = (1<<RXEN0)|(1<<TXCIE0)|(1<<TXEN0);  //switches interrupt mode to interrupt on transmission rather than data register empty
  packetOutboundFlag = true;  //set outgoing packet flag
  
  if (txPosition < txPacketLength){ //still in packet
    txData = txBuffer[txPosition];
    UDR0 = txData;
    txPacketChecksum = pgm_read_byte(&(crcTable[(txData^txPacketChecksum)]));  //calculates new checksum value
    txPosition++;
  }else{  //   finished transmitting packet data
    if (txPosition == txPacketLength){  //transmit checksum byte
      UDR0 = txPacketChecksum;
      txPosition++;
    }else{  //close out
      UCSR0B = (1<<RXEN0)|(1<<RXCIE0)|(1<<TXEN0);  //re-enable receiver
      packetOutboundFlag = false;
      txPosition = 0;
      txPacketChecksum = 0;
    }
  }  
}

//--ALIAS TO TRANSMITTER INTERRUPT--
ISR(USART_UDRE_vect, ISR_ALIASOF(USART_TX_vect));


//--START TRANSMISSION OF PACKET
void transmitPacket(){
  txPosition = 0;
  txPacketChecksum = 0;
  txPacketLength = txBuffer[lengthLocation];  //load packet length
  txBuffer[addressLocation] = networkAddress[0];	//load network address into txBuffer
  txBuffer[addressLocation+1] = networkAddress[1];
  UCSR0B = (1<<RXEN0)|(1<<TXEN0)|(1<<UDRIE0);  //enables interrupts on data empty, which triggers the first transmission
}

//------MAIN CODE---------------------------


void loop(){
   packetRouter();
}


void packetRouter(){
  if (packetReceivedFlag == true){
    packetReceivedFlag = false;  //clear packet waiting flag
    uint8_t destinationPort = rxBuffer[portLocation];  //gets destination port
    //--PORT TABLE--
    switch(destinationPort){
      case 1:	//status request
        svcStatus();
        break;		
			case 5: //request URL
				svcRequestURL();
			break;
		
			case 6: //set IP address
				svcSetIPAddress();
				break;
		
			case 7: //identify node
				svcIdentifyNode();
				break;
					
			case 255: //reset node
				svcResetNode();
				break;
			
			default: //try user program
				userPacketRouter(destinationPort);
				break;
    }
  }
}

//------SERVICE ROUTINES---------------------

//--IDENTIFY NODE--
void svcIdentifyNode(){
	uint32_t counter = 0;
	UIPort |= _BV(ledPin);	//turn on LED
	while(true){
		counter++;
		if (counter==5000000){
      UIPort &= ~(_BV(ledPin));	//turn off LED
			return;
		}
	}
	UIPort &= ~(_BV(ledPin));	//turn off LED
}

//--REQUEST URL--
void svcRequestURL(){
	txBuffer[startByteLocation] = unicast;
	txBuffer[portLocation] = 5;
//	txBuffer[lengthLocation] = 5 + urlLength;
	txBuffer[lengthLocation] = 5 + urlLength;
	uint8_t offset = 0;
	for(offset = 0; offset<urlLength; offset++){
		txBuffer[payloadLocation+offset] = *(url + offset);
	}
	transmitPacket();
}

//--SET IP ADDRESS--
void svcSetIPAddress(){
	networkAddress[0] = rxBuffer[payloadLocation];	//load new IP address
	networkAddress[1] = rxBuffer[payloadLocation+1];
	eeprom_write_byte((uint8_t*)persistentIPAddress0, networkAddress[0]);	//store IP address in eeprom
	eeprom_write_byte((uint8_t*)persistentIPAddress1, networkAddress[1]);
	txBuffer[startByteLocation] = multicast;
	txBuffer[portLocation] = 6;
	txBuffer[lengthLocation] = 5 + urlLength;
	uint8_t offset = 0;
	for(offset = 0; offset<urlLength; offset++){	//transmit URL
		txBuffer[payloadLocation+offset] = *(url+offset);
	}
//	UIPort &= ~(_BV(ledPin));	//turn off LED
	transmitPacket();
}	
		

//--STATUS REQUEST--
void svcStatus(){
   txBuffer[startByteLocation] = unicast;
   txBuffer[portLocation] = 1;
   txBuffer[lengthLocation] = 7;  //five header bytes, two payload byte, and checksum
   txBuffer[payloadLocation] = 65;	//send "A" to indicate application space program.
   transmitPacket();
}

void svcResetNode(){
	cli();
	wdt_enable(WDTO_15MS);
	while(1){};
	}

//------UTILITY FUNCTIONS---------------------	

//--SET URL--
void setURL(char *newURL, uint8_t newURLLength){
	//url: pointer to url address
	//urlLength: length of url address
	url = newURL;
	urlLength = newURLLength - 1; //subtract so array pointer starting at 0
	}
	
#ifdef __cplusplus
}	//extern "C"
#endif