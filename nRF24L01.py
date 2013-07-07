#!/usr/bin/env python3
from quick2wire.spi import *
from quick2wire.gpio import Pin
from quick2wire.gpio import In,Out,pi_header_1
import time
import TCP_Server 

PAYLOAD_SIZE   = 32

SMALL_PAUSE = 0.05
LONG_PAUSE=0.5

#Define settings variables for nRF:
SET_ACK        = 0x3f  #Auto ack on (EN_AA)
SET_ACK_RETR   = 0x2F  #15 retries, 750us paus in between in auto ack (SETUP_RETR)
SET_DATAPIPE   = 0x03  #Datapipe 0 is used (EN_RXADDR)
SET_ADR_WIDTH  = 0x03  #5 byte address (SETUP_AW)
SET_FREQ       = 0x5a  #2,401GHz (RF_CH)
SET_SETUP      = 0x07  #1Mbps, -0dB, (250kbps = 0x27) (RF_SETUP)
ADDRESS        = 0xe7
SET_RX_ADDR_P0 = [ADDRESS,ADDRESS,ADDRESS,ADDRESS,ADDRESS] #Receiver address( RX_ADDR_P0)
SET_TX_ADDR    = [ADDRESS,ADDRESS,ADDRESS,ADDRESS,ADDRESS] #Transmitter address (TX_ADDR)
SET_PAYLOAD_S  = 0x20  #3byte payload size (32byte = 0x20)(RX_PW_P0)
SET_CONFIG     = 0x0F  #1=mask_MAX_RT (IRQ-vector), E=transmitter, F= Receiver (CONFIG)

#nRF registers:
CONFIG      = 0x00
EN_AA       = 0x01
EN_RXADDR   = 0x02
SETUP_AW    = 0x03
SETUP_RETR  = 0x04
RF_CH       = 0x05
RF_SETUP    = 0x06
STATUS      = 0x07
OBSERVE_TX  = 0x08
CD          = 0x09
RX_ADDR_P0  = 0x0A
RX_ADDR_P1  = 0x0B
RX_ADDR_P2  = 0x0C
RX_ADDR_P3  = 0x0D
RX_ADDR_P4  = 0x0E
RX_ADDR_P5  = 0x0F
TX_ADDR     = 0x10
RX_PW_P0    = 0x11
RX_PW_P1    = 0x12
RX_PW_P2    = 0x13
RX_PW_P3    = 0x14
RX_PW_P4    = 0x15
RX_PW_P5    = 0x16
FIFO_STATUS = 0x17

READ_REG     = 0x00
WRITE_REG    = 0x20
RESET_STATUS = 0x70

WR_TX_PLOAD = 0xA0
RD_RX_PLOAD = 0x61

FLUSH_TX    = 0xE1
FLUSH_RX    = 0xE2
NOP         = 0xFF


class NRF24L01P:
    def __init__(self):
        """__init__ function is allways run first, when the class is called!"""
        self.nrf24 = SPIDevice(0, 0) #Define SPI-unit (used in doOperation)

        self.radio_pin = pi_header_1.pin(22, direction=Out) #"CE" on nRF, output
        

    def doOperation(self,operation):
        """Do one SPI operation"""
        time.sleep(SMALL_PAUSE)     #Make sure the nrf is ready
        toReturn = self.nrf24.transaction(operation)    #Sends bytes in "operation" to nRF (first what register, than the bytes)
        return toReturn             #Return bytes received from nRF

    
    def ReadPrintReg(self, Register, name, numbers):
        """Function that grabs "numbers" of bytes from the registry "Register" in the nRF
      and writes them out in terminal as "name....[0xAA,0xBB,0xCC]" """
        bytes = [READ_REG|Register]     #First byte in "bytes" will tell the nRF what register to read from 
        for x in range(0, numbers):     #Add "numbers" amount of dummy-bytes to "bytes" to send to nRF
            bytes.append(NOP)           #For each dummy byte sent to nRF later, a return byte will be collected 
        ret = self.doOperation(duplex(bytes))   #Do the SPI operations (returns a byte-array with the bytes collected)
        #print(ret[0])           #debug
        #print(hex(ord(ret[0]))) #debug
        #print(bin(ord(ret[0]))) #debug

        Res = [hex(z)[2:] for z in ret[0]]  #convert byte-array to string list
        #print(Res) #debug

        while len(name)<15:         #Fill the name with "." so it allways becomes 15 char long (e.g. "STATUS.........")
            name = name + "."

        #Print out the register and bytes like this: "STATUS.........[0x0E]"
        print("{}".format(name), end='')  #First print the name, and stay on same line (end='')        

        for x in range(1, numbers+1):   #Then print out every collected byte
            if len(Res[x]) == 1:        #if byte started with "0" (ex. "0E") the "0" is gone from previous process => (len == 1)
                Res[x]= "0" + Res[x]    #Readd the "0" if thats the case
            print("[0x{}]".format(Res[x].upper()), end='') #Print next byte after previous without new line

        print("") #Finnish with an empty print to contiune on new line and flush the print (no end='')
        return Res[1].upper()   #Returns the first byte (not the zeroth which is allways STATUS)
    

    def receiveData(self):
        """Receive one or None messages from module"""
        #Reset Status registry
        bytes = [WRITE_REG|STATUS]  #first byte to send tells nRF tat STATUS register is to be Written to
        bytes.append(RESET_STATUS)  #add the byte that will be written to thr nRF (in this case the Reset command)
        self.doOperation(writing(bytes))    #execute the SPI command to send "bytes" to the nRF

        try:
            self.radio_pin.open()   #Open the "CE" GPIO pin for access
            self.radio_pin.value=1  #Set the "CE" pin high (3,3V or 5V) to start listening for data
            time.sleep(LONG_PAUSE)  #Listen 0,5s for incomming data
            self.radio_pin.value=0  #Ground the "CE" pin again, to stop listening
            self.radio_pin.close()  #Close the CE-pin
            
        except(KeyboardInterrupt, SystemExit):  #If ctrl+c breaks operation or system shutdown
            try:
                self.radio_pin.close()  #First close the CE-pin, so that it can be opened again without error!
                print("\n\ngpio-pin closed!\n")
            except:
                pass
            raise   #continue to break or shutdown!                    

        ret = self.doOperation(duplex([STATUS]))    #Get the status register as byte-array
        
        Res = [hex(z)[2:] for z in ret[0]]  #convert byte-array to string list

        Res = Res[0].upper()    #Convert the interesting byte to one string, upper case (e.g. "4E")
        
        if len(Res) == 1:       #if string started with "0" (ex. "0E") the "0" is gone from previous process => (len == 1)
            Res= "0" + Res      #Readd the "0" if thats the case

        print("Moo: " + Res)
            
        if(Res != "0E"):  #If something is flagged in the STATUS-register            
            self.ReadPrintReg(STATUS,"STATUS",1)    #Print out the status-register
            #if Res == "4E": #If data is received correctly
            self.ReadPrintReg(RD_RX_PLOAD,"Received",PAYLOAD_SIZE)    #Print out the received bytes
        else:
            print(".", end='')  #Print out dots to show we are still listening!
            sys.stdout.flush()  #the end='' only puts it in the buffer!

    def sendData(self,toSend):
        """Sends x bytes of data"""
        #Reset Status registry for next transmission
        bytes = [WRITE_REG|STATUS]  #first byte to send tells nRF tat STATUS register is to be Written to
        bytes.append(RESET_STATUS)  #add the byte that will be written to thr nRF (in this case the Reset command)
        self.doOperation(writing(bytes))    #execute the SPI command to send "bytes" to the nRF

        #Flush RX Buffer
        self.doOperation(writing([FLUSH_TX]))   #This one is special because it doesn't need any more than one byte SPI-command.
                                                #This is because the FLUSH_TX is located on the top level on the nRF, same as the "WRITE_REG"
                                                #register or the "READ_REG". (See datasheet Tabel 8)
        
        #Print out the STATUS registry before transmission
        self.ReadPrintReg(STATUS,"STATUS before",1)

        #Print out the transmitting bytes with quotations ("chr(34)"), Payload cannot be read from the nRF! 
        print("Transmitting...[{}{}{},{}{}{},{}{}{}]".format(chr(34), chr(toSend[0]),chr(34),chr(34), chr(toSend[1]), chr(34), chr(34),chr(toSend[2]),chr(34)))

        #This checks if the payload is"900" or "901", 002, 003 or 004, and if so, changes the address on the nRF.
        a = "".join([chr(x) for x in toSend])
        #print(a)
        if(a=="900" or a=="901"):
            self.changeAddress(0x13)    #Calls function located further down
        elif(a=="002" or a=="003" or a=="004"):#
              self.changeAddress(0x14)

        #Print out the address one more time, to make sure it is sent to the right receiver. 
        self.ReadPrintReg(RX_ADDR_P0,"To",5)
        
        #write bytes to send into tx buffer
        bytes = [WR_TX_PLOAD]   #This one is simular to FLUSH_TX because it is located on the same top level in the nRF,
                                #Even though we want to write to it, we cannot add the "WERITE_REG" command to it!
        bytes.extend(toSend)    #Because we now want to add a byte array to it, we use the "extend(" command instead of "append("
        self.doOperation(writing(bytes)) #Write payload to nRF with SPI

        try:
            self.radio_pin.open()   #Open the "CE" GPIO pin for access
            self.radio_pin.value=1  #Set the "CE" pin high (3,3V or 5V) to start transmission
            time.sleep(0.001)  #Send for 0,5s to make sure it has time to send it all
            self.radio_pin.value=0  #Ground the CE pin again, to stop transmission
            self.radio_pin.close()  #Close the CE-pin
            
        except(KeyboardInterrupt, SystemExit):  #If ctrl+c breaks operation or system shutdown
            try:
                self.radio_pin.close()  #First close the CE-pin, so that it can be opened again without error!
                print("\n\ngpio-pin closed!\n")
            except:
                pass                   
            raise   #continue to break or shutdown!            
        
        self.ReadPrintReg(STATUS,"STATUS after",1)  #Read STATUS register that hopefully tells you a successful transmission has occured (0x2E)
        print("")
        
        if(a=="900" or a=="901" or a=="002" or a=="003" or a=="004"):      #If you changed address above, change it back to normal
            self.changeAddress(0x12)    #Change back address!


    def changeAddress(self,Addr):
        """Function to change address on both RX and """
        bytes = [WRITE_REG|RX_ADDR_P0]
        bytes.extend([Addr,Addr,Addr,Addr,Addr])
        self.doOperation(writing(bytes))

        bytes = [WRITE_REG|TX_ADDR]
        bytes.extend([Addr,Addr,Addr,Addr,Addr])
        self.doOperation(writing(bytes))
        
    def setupRadio(self):
        """Function that sets the basic settings in the nRF"""
        #Setup EN_AA
        bytes = [WRITE_REG|EN_AA]
        bytes.append(SET_ACK)
        self.doOperation(writing(bytes))

        #Setup ACK RETRIES
        bytes = [WRITE_REG|SETUP_RETR]
        bytes.append(SET_ACK_RETR)
        self.doOperation(writing(bytes))

        #Setup Datapipe
        bytes = [WRITE_REG|EN_RXADDR]
        bytes.append(SET_DATAPIPE)
        self.doOperation(writing(bytes))

        #Setup Address width
        bytes = [WRITE_REG|SETUP_AW]
        bytes.append(SET_ADR_WIDTH)
        self.doOperation(writing(bytes))

        #Setup Freq
        bytes = [WRITE_REG|RF_CH]
        bytes.append(SET_FREQ)
        self.doOperation(writing(bytes))

        #Setup Data speed and power
        bytes = [WRITE_REG|RF_SETUP]
        bytes.append(SET_SETUP)
        self.doOperation(writing(bytes))

        #Setup Receive Address
        bytes = [WRITE_REG|RX_ADDR_P0]
        bytes.extend(SET_RX_ADDR_P0)    #"extend" adds a list to a list, "append" adds one obect to a list
        self.doOperation(writing(bytes))

        #Setup Transmitter Address
        bytes = [WRITE_REG|TX_ADDR]
        bytes.extend(SET_TX_ADDR)
        self.doOperation(writing(bytes))

        #Setup Payload size
        bytes = [WRITE_REG|RX_PW_P0]
        bytes.append(SET_PAYLOAD_S)
        self.doOperation(writing(bytes))
                
        #Setup CONFIG registry
        bytes = [WRITE_REG|CONFIG]
        bytes.append(SET_CONFIG)
        self.doOperation(writing(bytes))
        time.sleep(LONG_PAUSE)

        #Collect print out the registers from the nRF to to make sure thay are allright
        self.ReadPrintReg(STATUS,"STATUS",1)
        self.ReadPrintReg(EN_AA,"EN_AA",1)
        self.ReadPrintReg(SETUP_RETR,"SETUP_RETR",1)
        self.ReadPrintReg(EN_RXADDR,"EN_RXADDR",1)
        self.ReadPrintReg(SETUP_AW,"SETUP_AW",1)
        self.ReadPrintReg(RF_CH,"RF_CH",1)
        self.ReadPrintReg(RF_SETUP,"RF_SETUP",1)
        self.ReadPrintReg(RX_ADDR_P0,"RX_ADDR_P0",5)
        self.ReadPrintReg(TX_ADDR,"TX_ADDR",5)
        self.ReadPrintReg(RX_PW_P0,"RX_PW_P0",1)
        self.ReadPrintReg(CONFIG,"CONFIG",1)

        #self.radio_pin.close()
                
def Send(data):
    """Function that can be called from other files that wants to send data"""
    SendObj = NRF24L01P()
    SendObj.sendData(data)
    print("Enter data to send (3 bytes): ")  #Retype the input-text (input is still on form main-loop) 

                                
if __name__ == "__main__":
    """Gets called upon when running the file"""
    rxtx = input("rx or tx? \n")    #Receiver or transmitter
    SendObj = NRF24L01P()   #Start class 
    
    if rxtx == "tx":    #nRF transmitter
        print('\nTransmitter')
        
        SET_CONFIG = 0x1E   #Transmitter
        SendObj.setupRadio()    #Setting up radio
        
        TCP-Server.Run_func()    #Calls the "Run_func()" in a TCP-server (that in termes calls the "Send(data)" function above with the data)
        while 1:
            package = input("Enter data to send (3 bytes): ")  #If not TCP-server is used, calls for input from user to bee sent
            print("")
            #print(package)
            bytesToSend = [ord(str(x)) for x in package] #Convert input to decimal values 
            #print(bytesToSend)
            SendObj.sendData(bytesToSend)  #calls the sendData() function with the payload

    else:   #nRF receiver
        print('\nReceiver')

        SET_CONFIG = 0x1F   #Receiver
        SendObj.setupRadio()
        print("\nReceiving data")
        i=0
        while 1:
            SendObj.receiveData()
            time.sleep(SMALL_PAUSE)
            
