#include <gestalt.h>

char myurl[] = "http://www.myurl.com/myVirtualNode.py";

void userSetup(){
  setURL(&myurl[0], sizeof(myurl));
};

void userLoop(){
};

void userPacketRouter(uint8_t destinationPort){
  
};