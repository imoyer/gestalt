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
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |02/28/13 | MODIFIED TO SUPPORT EXTERNAL IO DEF      | ILAN E. MOYER     | gestalt.cpp                 |
//  |---------|------------------------------------------|-------------------|-----------------------------|
//  |03/14/13 | ADDED USER LOOP.                         | ILAN E. MOYER     | gestalt.cpp                 |
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
#include <gestalt.h>
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
#include <avr/delay.h>
#include <avr/boot.h>

//--DEFINE IO--
// These values get initialized in setup()
volatile uint8_t *IO_ledPORT; //The led which is used to identify nodes on the network.
volatile uint8_t *IO_ledDDR;
volatile uint8_t *IO_ledPIN;
volatile uint8_t IO_ledPin;

volatile uint8_t *IO_buttonPORT;  //The button which is used to identify nodes on the network.
volatile uint8_t *IO_buttonDDR;   //This is only used by networked nodes.
volatile uint8_t *IO_buttonPIN;
volatile uint8_t IO_buttonPin;

volatile uint8_t *IO_txrxPORT;  //Xceiver 
volatile uint8_t *IO_txrxDDR;
volatile uint8_t IO_txPin;
volatile uint8_t IO_rxPin;

#ifdef standardGestalt
volatile uint8_t *IO_txEnablePORT;
volatile uint8_t *IO_txEnableDDR;
volatile uint8_t IO_txEnablePin; //Transmit enable for RS485
#endif


//--DEFINE NODE VARIABLES--
uint8_t networkAddress[2];	//network address
char defaultURL[] = "http://tq.mit.edu/gestalt/086-000.py";	//node URL
char *url = 0;	//pointer to URL
uint8_t urlLength = 0;	//stores current URL length

//--EEPROM LOCATIONS--
const uint8_t persistentIPAddress0 = 0;	//used for EEPROM storage of IP address
const uint8_t persistentIPAddress1 = 1;      //note: changed from uint8_t* to int to use the arduino version of eeprom.read()
const uint8_t applicationValidationByte = 2; //eeprom address for app valid byte

const uint8_t applicationValid = 170; //0b10101010

//--BOOTLOADER--
#ifdef bootloader
//--BOOTLOADER CONSTANTS--
const uint8_t pageSize = 128; //length in bytes of each page
//--BOOTLOADER STATE VARIABLES--
uint16_t pageAddress;   //current page address for programming
#endif

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

//--DEFINE PACKET FORMAT--
const uint8_t startByteLocation   = 0;
const uint8_t addressLocation     = 1;	//two bytes for address
const uint8_t portLocation        = 3;
const uint8_t lengthLocation      = 4;
//const uint8_t payloadLocation     = 5;	defined in header

const uint8_t unicast             = 72;  //start byte value for unicast packet
const uint8_t multicast		  = 138; //start byte value for multicast packet
const uint8_t basePacketLength			= 5; //[start, address1, address0, port, length, checksum]

//--DEFINE PORTS----
const uint8_t statusPort		        = 1;
const uint8_t bootloaderCommandPort = 2;
const uint8_t bootloaderDataPort    = 3;
const uint8_t bootloaderReadPort    = 4;
const uint8_t urlPort				        = 5;
const uint8_t setIPPort			        = 6;
const uint8_t identifyPort	        = 7;
const uint8_t resetPort			        = 255;

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

#ifdef bootloader
#define inPageLoad ((volatile PackedBool*)(&GPIOR0))->f4 //flag set when page load in progress
#define inBootload ((volatile PackedBool*)(&GPIOR0))->f3  //flag set when bootload in progress
#endif

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

#ifdef standardGestalt
//This is being compiled as an independent program, not using the arduino IDE.
int main(){
  setup();
  while(true){
    loop();
  }
}
#endif




// -- FUNCTION: SETUP --
// Basic functionality for communication with the PC is configured here.

void setup(){

	//DISABLE SYSTEM WATCHDOG TIMER
  MCUSR = 0;
  wdt_disable();

  //DEFINE DEFAULT PINS AND PORTS FOR ARDUINO
  IO_ledPORT = &PORTB;
  IO_ledDDR = &DDRB;
  IO_ledPIN = &PINB;
  IO_ledPin = 1<<5;

  IO_txrxPORT = &PORTD;
  IO_txrxDDR = &DDRD;
  IO_txPin = 1<<1;
  IO_rxPin = 1<<0;

  //PIN AND PORT CONFIGURATION FOR UNITS OF FAB
  #ifdef unitOfFab
  IO_ledPORT = &PORTB;
  IO_ledDDR = &DDRB;
  IO_ledPIN = &PINB;
  IO_ledPin = 1<<1;

  IO_buttonPORT = &PORTB;
  IO_buttonDDR = &DDRB;
  IO_buttonPIN = &PINB;
  IO_buttonPin = 1<<0;

  IO_txrxPORT = &PORTD;
  IO_txrxDDR = &DDRD;
  IO_rxPin = 1<<0;
  IO_txPin = 1<<1;

  IO_txEnablePORT = &PORTA;
  IO_txEnableDDR = &DDRA;
  IO_txEnablePin = 1<<4;
  #endif 
  
  
  //INITIALIZE USART
  #ifdef standardGestalt
  UBRR0 = 9;  //9 = 115.2kbps, 14 = 76.8kbps @18.432MHz NOTE: standard gestalt nodes with a 18.432MHz clock communicate at 115.2kbps
  #else
  UBRR0 = 12;  //8 = 115.2kbps, 12 = 76.8kbps @16MHz NOTE: tried 115200 without success from MacOSX, 76800 worked fine.
  #endif
  UCSR0B = (1<<RXEN0)|(1<<TXEN0)|(0<<UDRIE0)|(1<<RXCIE0)|(0<<TXCIE0);  //enable transmitter and receiver, rx interrupts
  UCSR0C = (0 << UMSEL00) | (0 << UPM00) | (0 << USBS0) | (3 <<UCSZ00);  //8 data bits, 1 stop bit, no parity

  //CONFIGURE TIMER2 AS WATCHDOG
  TCCR2A = (0 << COM2A1)|(0 << COM2A0)|(0 << COM2B1)|(0 << COM2B0)|(0 << WGM21)|(0 << WGM20); //counter in normal mode
  TCCR2B = (0 << FOC2A)|(0 << FOC2B)|(0 << WGM22)|(4 << CS20);  // C/64 prescalar
  TIMSK2 = (0 << OCIE2B)|(0 << OCIE2A)|(0 << TOIE2);  // Disable interrupts for now
  
  
  
  //LOAD NETWORK ADDRESS
  networkAddress[0]=eeprom_read_byte((uint8_t*)persistentIPAddress0);
  networkAddress[1]=eeprom_read_byte((uint8_t*)persistentIPAddress1);
  
  //BOOTLOADER SUPPORT
  #if defined(bootloader) //positions interrupt vector table in boot space
    MCUCR = (1<<IVCE);
    MCUCR = (1<<IVSEL);
  #elif defined(standardGestalt)
    eeprom_update_byte((uint8_t*)applicationValidationByte, applicationValid);  //mark application code as valid  
  #endif

  //SET DEFAULT URL
  setURL(&defaultURL[0], sizeof(defaultURL));
  
  //USER SETUP
  userSetup();		//This should be defined in the user program
  
  //INITIALIZE PORTS AND PINS
  *IO_ledDDR |= IO_ledPin;  //led pin is an output
  *IO_ledPORT &= ~(IO_ledPin);   //led is initially off


  *IO_txrxDDR |= IO_txPin; //tx pin is an output
  *IO_txrxDDR &= ~(IO_rxPin);  //rx pin is an input

  #ifdef standardGestalt
  *IO_buttonDDR &= ~(IO_buttonPin);  //button pin as an input
  *IO_txEnableDDR |= IO_txEnablePin;
  *IO_txEnablePORT &= ~(IO_txEnablePin);
  #endif


  //ENABLE GLOBAL INTERRUPTS
  sei();
}

//----RECEIVER CODE-------------------------------------
//--RECEIVER INTERRUPT ROUTINE--
#if defined(gestalt324)
ISR(USART0_RX_vect){  //atmega324
#else
ISR(USART_RX_vect){   //atmega328, default for arduino
#endif
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
#ifdef gestalt324
ISR(USART0_TX_vect){//atmega324
#else
ISR(USART_TX_vect){ 
#endif

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
      #ifdef standardGestalt
      *IO_txEnablePORT &= ~(IO_txEnablePin);  //enable transmit pin
      #endif 
    }
  }  
}

//--ALIAS TO TRANSMITTER INTERRUPT--
#ifdef gestalt324
ISR(USART0_UDRE_vect, ISR_ALIASOF(USART0_TX_vect));
#else
ISR(USART_UDRE_vect, ISR_ALIASOF(USART_TX_vect));
#endif

//--START TRANSMISSION OF PACKET
void transmitPacket(){
  txPosition = 0;
  txPacketChecksum = 0;
  txPacketLength = txBuffer[lengthLocation];  //load packet length
  txBuffer[addressLocation] = networkAddress[0];	//load network address into txBuffer
  txBuffer[addressLocation+1] = networkAddress[1];
  #ifdef standardGestalt
  *IO_txEnablePORT |= IO_txEnablePin;  //enable transmit pin
  #endif
  UCSR0B = (1<<RXEN0)|(1<<TXEN0)|(1<<UDRIE0);  //enables interrupts on data empty, which triggers the first transmission
}

void transmitUnicastPacket(uint8_t port, uint8_t length){
  txBuffer[startByteLocation] = unicast;
  txBuffer[portLocation] = port;
  txBuffer[lengthLocation] = basePacketLength + length;
  transmitPacket();
  }

void transmitMulticastPacket(uint8_t port, uint8_t length ){
  txBuffer[startByteLocation] = multicast;
  txBuffer[portLocation] = port;
  txBuffer[lengthLocation] = basePacketLength + length;
  transmitPacket();
  }
	

//------MAIN CODE---------------------------


void loop(){
  packetRouter();
  userLoop();
}


void packetRouter(){
  if (packetReceivedFlag == true){
    packetReceivedFlag = false;  //clear packet waiting flag
    uint8_t destinationPort = rxBuffer[portLocation];  //gets destination port
    //--PORT TABLE--
    switch(destinationPort){
      case statusPort:	//status request
        svcStatus();
        break;		
			case urlPort: //request URL
				svcRequestURL();
			break;
		
			case setIPPort: //set IP address
				svcSetIPAddress();
				break;
		
			case identifyPort: //identify node
				svcIdentifyNode();
				break;
					
			case resetPort: //reset node
				svcResetNode();
				break;

      #if defined(bootloader) //these functions should only work if the bootloader is active
      case bootloaderCommandPort: //bootloader command
        svcBootloaderCommand();
        break;
      case bootloaderDataPort: //bootloader data
        svcBootloaderData();
        break;
      case bootloaderReadPort: //bootloader read page
        svcBootloaderReadPage();
        break;
      #endif

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
  *IO_ledPORT |= IO_ledPin;  //turn on LED
	while(counter < 1500000){
		_delay_us(1);
    counter++;
	}
	*IO_ledPORT &= ~(IO_ledPin);	//turn off LED
}

//--REQUEST URL--
void svcRequestURL(){
	uint8_t offset = 0;
	for(offset = 0; offset<urlLength; offset++){
		txBuffer[payloadLocation+offset] = *(url + offset);
	}
	transmitUnicastPacket(urlPort, urlLength);
}

//--SET IP ADDRESS--
void svcSetIPAddress(){
  #ifdef standardGestalt
  if (rxBuffer[startByteLocation] == multicast){ //wait for button press
    volatile uint32_t counter = 0; //this variable for blinking
    volatile uint8_t counter2 = 0; //this variable for escaping out of function
    *IO_ledPORT |= IO_ledPin;  //turn on led
    while(*IO_buttonPIN & IO_buttonPin){
      counter++;
      if (counter == 500000){  //blink frequency
        *IO_ledPIN |= IO_ledPin; //strobe LED
        counter2++;
        counter = 0;
      }
      if ((counter2 == 15)||(packetReceivedFlag==true)){  //exit condition, n blinks or packet received (presumeably from other responding node)
        *IO_ledPORT &= ~(IO_ledPin); //turn off LED
        packetReceivedFlag = false;  //clear packet waiting flag
        return;
      }
    }
  }
  networkAddress[0] = rxBuffer[payloadLocation];  //load new IP address
  networkAddress[1] = rxBuffer[payloadLocation+1];
  eeprom_update_byte((uint8_t*)persistentIPAddress0, networkAddress[0]);  //store IP address in eeprom
  eeprom_update_byte((uint8_t*)persistentIPAddress1, networkAddress[1]);
  uint8_t offset = 0;
  for(offset = 0; offset<urlLength; offset++){  //transmit URL
    txBuffer[payloadLocation+offset] = url[offset];
  }
  *IO_ledPORT &= ~(IO_ledPin); //turn off LED
  transmitMulticastPacket(setIPPort, urlLength);
  return;
  #else
	networkAddress[0] = rxBuffer[payloadLocation];	//load new IP address
	networkAddress[1] = rxBuffer[payloadLocation+1];
	eeprom_write_byte((uint8_t*)persistentIPAddress0, networkAddress[0]);	//store IP address in eeprom
	eeprom_write_byte((uint8_t*)persistentIPAddress1, networkAddress[1]);
	uint8_t offset = 0;
	for(offset = 0; offset<urlLength; offset++){	//transmit URL
		txBuffer[payloadLocation+offset] = *(url+offset);
	}
//	UIPort &= ~(_BV(ledPin));	//turn off LED
	transmitMulticastPacket(setIPPort, urlLength);
  return;
  #endif
}	
		

//--STATUS REQUEST--
void svcStatus(){

  #if defined(bootloader)
  txBuffer[payloadLocation] = 66;  //send "B" to indicate bootloader.
  #else
  txBuffer[payloadLocation] = 65; //send "A" to indicate application space program.
  #endif

  #ifdef standardGestalt
  txBuffer[payloadLocation+1] = eeprom_read_byte((uint8_t*)applicationValidationByte); //send application validation byte
  #endif

   transmitUnicastPacket(statusPort, 2);
}

void svcResetNode(){
	cli();
	wdt_enable(WDTO_15MS);
	while(1){};
	}

//--BOOTLOADER FUNCTIONS--
#ifdef bootloader
void svcBootloaderCommand(){
  uint8_t command = rxBuffer[payloadLocation];
  txBuffer[startByteLocation] = unicast;
  txBuffer[portLocation] = 2;
  txBuffer[lengthLocation] = 8; //five header bytes, three payload bytes, and checksum
  txBuffer[payloadLocation +1] = 0;
  txBuffer[payloadLocation +2] = 0;
  if (command == 0){
    txBuffer[payloadLocation] = 5;  //response to indicate bootloader has been initialized
    transmitPacket();
    bootloaderInit();
  }
  if (command == 1){
    txBuffer[payloadLocation] = 9; //response to indicate that application has been launched
    transmitPacket();
    applicationStart();
  }
}

void bootloaderInit(){
  inBootload = true;  //sets bootload flag
  pageAddress = 0;  //resets page address
  eeprom_update_byte((uint8_t*)applicationValidationByte, 0); //mark application code as invalid
  }
  
void applicationStart(){
  while (packetOutboundFlag == true){ //wait for response packet to be sent
  }
  
  //CLEAR PROCESSOR STATE
  cli();  //disable interrupts
  UCSR0B = 0; //clear USART interrupt enables
  TIMSK2 = 0; //clear timer2 interrupt enables

  //shift interrupts to application space
  MCUCR = (1<<IVCE);
  MCUCR = (0<<IVSEL);
  
  asm("jmp 0000");  //jump to start of application space
  
}

void svcBootloaderData(){
  //TODO: add safety to prevent writing without an init
  //      either check for address match internally, or allow writing to arbitrary pages
  //      interlocks
  txBuffer[startByteLocation] = unicast;
  txBuffer[portLocation] = 3;
  txBuffer[lengthLocation] = 8;
  txBuffer[payloadLocation] = 1;  //indicate programming page now
  txBuffer[payloadLocation+1] = (pageAddress & 0x00FF);
  txBuffer[payloadLocation+2] = ((pageAddress & 0xFF00)>>8);
  writePage();
  transmitPacket();
  }
  
void writePage(){   //note: code based on http://www.nongnu.org/avr-libc/user-manual/group_avr_boot.html
                    //      and suggestions from Brad Schick's AVR Bootloader FAQ
  
  uint16_t i;
  uint8_t sreg;
//  uint8_t *bootData; 
//  bootData = &rxBuffer[payloadLocation+3];  //start of boot data.
  
  //disable interrupts
  sreg = SREG;  //store global interrupt flag state
  cli();  //disable interrupts
  
  eeprom_busy_wait();
  
  boot_page_erase_safe(pageAddress);
  boot_spm_busy_wait(); //wait for page to be erased
  
  for (i=0; i<pageSize; i+=2){
    //set up little-endian word from data bytes
    uint16_t w = rxBuffer[payloadLocation+3+i];
    w += (rxBuffer[payloadLocation+4+i]) << 8;

    boot_page_fill_safe(pageAddress + i, w);  //fill page
  }
  
  boot_page_write_safe(pageAddress);  //store buffer in flash page
  boot_spm_busy_wait(); //wait for memory to be written
  
  boot_rww_enable();
  SREG = sreg;
  
  pageAddress+=pageSize;
  }
  
void svcBootloaderReadPage(){ //returns page
  txBuffer[startByteLocation] = unicast;
  txBuffer[portLocation] = 4;
  txBuffer[lengthLocation] = pageSize+5;
  
  uint16_t readAddress = rxBuffer[payloadLocation];
  readAddress += (rxBuffer[payloadLocation+1])<<8;
  
  uint16_t i;
  for (i=0; i<pageSize; i++){
    txBuffer[payloadLocation+i] = pgm_read_byte(readAddress+i);
  } 
  transmitPacket();
}

#endif
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