#!/usr/bin/env python3
from quick2wire.spi import *
from quick2wire.gpio import Pin
from quick2wire.gpio import In,Out,pi_header_1,Falling
import time
import TCP_Server 
import select

PAYLOAD_SIZE = 32
SMALL_PAUSE  = 0.0
LONG_PAUSE   = 0.0

# Define settings variables for nRF:
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

# nRF registers:
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

R_REGISTER   = 0x00
W_REGISTER   = 0x20
RESET_STATUS = 0x70

W_TX_PAYLOAD = 0xA0
R_RX_PAYLOAD = 0x61

FLUSH_TX    = 0xE1
FLUSH_RX    = 0xE2
NOP         = 0xFF


class NRF24L01P:

    def __init__(self):
        self.nrf24 = SPIDevice(0, 0) 
        self.outfile = open("/home/pi/testit", 'a')

    def run(self):
        # Setup chip-enable pin
        self.ce_pin = pi_header_1.pin(22, direction=Out) 

        # Setup interrupt pin
        self.int_pin = pi_header_1.pin(18, direction=In, interrupt=Falling)

        # Configure epoll for interrupt-handler
        epoll = select.epoll() 

        with self.int_pin:
            epoll.register(self.int_pin, select.EPOLLIN | select.EPOLLET) 

            while True: 
                self.ce_pin.open()   # Open the "CE" GPIO pin for access
                self.ce_pin.value=1  # Set the "CE" pin high (3,3V or 5V) to start listening for data
                time.sleep(LONG_PAUSE)  # Give the radio time to settle
                                
                events = epoll.poll() 
                for fileno, event in events: 
                    if fileno == self.int_pin.fileno(): 
                        self.ce_pin.value=0  # Ground the "CE" pin again, to stop listening
                        self.ce_pin.close()  # Close the CE-pin                        
                        radio.read_data()            


    def _spi_write(self,operation):
        """Do one SPI operation"""

        time.sleep(SMALL_PAUSE)     # Give the radio time to settle
        toReturn = self.nrf24.transaction(operation)    # Sends bytes in "operation" to nRF (first what register, than the bytes)
        return toReturn             # Return bytes received from nRF

    
    def print_reg(self, Register, name, numbers):
        """Function that grabs "numbers" of bytes from the registry "Register" in the nRF and writes them out in terminal as "name....[0xAA,0xBB,0xCC]" """

        bytes = [R_REGISTER|Register]           # First byte in "bytes" will tell the nRF what register to read from 
        for x in range(0, numbers):             # Add "numbers" amount of dummy-bytes to "bytes" to send to nRF
            bytes.append(NOP)                   # For each dummy byte sent to nRF later, a return byte will be collected 
        ret = self._spi_write(duplex(bytes))    # Do the SPI operations (returns a byte-array with the bytes collected)

        Res = [hex(z)[2:] for z in ret[0]]      # Convert byte-array to string list

        # Pad name to 15 characters
        while len(name)<15: name = name + "."

        # Print out the register and bytes like this: "STATUS.........[0x0E]"
        print("{}".format(name), end='')        # First print the name, and stay on same line (end='')        

        for x in range(1, numbers+1):           # Then print out every collected byte
            if len(Res[x]) == 1:                # If byte started with "0" (ex. "0E") the "0" is gone from previous process => (len == 1)
                Res[x]= "0" + Res[x]            # Read the "0" if thats the case
            print("[0x{}]".format(Res[x].upper()), end='') # Print next byte after previous without new line
            print("[0x{}]".format(Res[x].upper()), end='', file=self.outfile) # Print next byte after previous without new line

        print("") 
        print("<br />", file=self.outfile) 
        self.outfile.flush()
        return Res[1].upper()   # Returns the first byte (not the zeroth which is always STATUS)
    

    def read_data(self):
        """Receive one or None messages from module"""

        # Reset Status registry
        bytes = [W_REGISTER|STATUS]         # First byte to send tells nRF tat STATUS register is to be Written to
        bytes.append(RESET_STATUS)          # Add the byte that will be written to the nRF (in this case the Reset command)
        self._spi_write(writing(bytes))     # Execute the SPI command to send "bytes" to the nRF

        # Get the status register as byte-array
        ret = self._spi_write(duplex([STATUS]))    

        # Convert byte-array to string list
        Res = [hex(z)[2:] for z in ret[0]]  

        # Convert the interesting byte to one string, upper case (e.g. "4E")
        Res = Res[0].upper()    
        
        # If string started with "0" (ex. "0E") the "0" is gone from previous process => (len == 1)       
        if len(Res) == 1: Res= "0" + Res

        if(Res != "0E"):                                            # If something is flagged in the STATUS-register            
            self.print_reg(STATUS,"STATUS",1)                       # Print out the status-register
            self.print_reg(R_RX_PAYLOAD,"Received",PAYLOAD_SIZE)    # Print out the received bytes
        else:
            print(".", end='')  # Print out dots to show we are still listening!
            sys.stdout.flush()  # the end='' only puts it in the buffer!


    def write_data(self,toSend):
        """Sends x bytes of data"""

        # Reset Status registry for next transmission
        bytes = [W_REGISTER|STATUS]         # First byte to send tells nRF tat STATUS register is to be Written to
        bytes.append(RESET_STATUS)          # Add the byte that will be written to thr nRF (in this case the Reset command)
        self._spi_write(writing(bytes))     # Execute the SPI command to send "bytes" to the nRF

        # Flush RX Buffer
        self._spi_write(writing([FLUSH_TX]))    # This one is special because it doesn't need any more than one byte SPI-command.
                                                # This is because the FLUSH_TX is located on the top level on the nRF, same as the "W_REGISTER"
                                                # register or the "R_REGISTER". (See datasheet Tabel 8)
        
        # Print out the STATUS registry before transmission
        self.print_reg(STATUS,"STATUS before",1)

        # Print out the transmitting bytes with quotations ("chr(34)"), Payload cannot be read from the nRF! 
        print("Transmitting...[{}{}{},{}{}{},{}{}{}]".format(chr(34), chr(toSend[0]),chr(34),chr(34), chr(toSend[1]), chr(34), chr(34),chr(toSend[2]),chr(34)))

        # This checks if the payload is"900" or "901", 002, 003 or 004, and if so, changes the address on the nRF.
        a = "".join([chr(x) for x in toSend])
        if(a=="900" or a=="901"):
            self.set_address(0x13)    #Calls function located further down
        elif(a=="002" or a=="003" or a=="004"):#
              self.set_address(0x14)

        # Print out the address one more time, to make sure it is sent to the right receiver. 
        self.print_reg(RX_ADDR_P0,"To",5)
        
        # write bytes to send into tx buffer
        bytes = [W_TX_PAYLOAD]  # This one is simular to FLUSH_TX because it is located on the same top level in the nRF,
                                # Even though we want to write to it, we cannot add the "WERITE_REG" command to it!
        bytes.extend(toSend)    # Because we now want to add a byte array to it, we use the "extend(" command instead of "append("
        self._spi_write(writing(bytes)) # Write payload to nRF with SPI

        try:
            self.ce_pin.open()   # Open the "CE" GPIO pin for access
            self.ce_pin.value=1  # Set the "CE" pin high (3,3V or 5V) to start transmission
            time.sleep(0.001)    # Send for 0,5s to make sure it has time to send it all
            self.ce_pin.value=0  # Ground the CE pin again, to stop transmission
            self.ce_pin.close()  # Close the CE-pin
            
        except(KeyboardInterrupt, SystemExit):  # If ctrl+c breaks operation or system shutdown
            try:
                self.ce_pin.close()  # First close the CE-pin, so that it can be opened again without error!
                print("\n\ngpio-pin closed!\n")
            except:
                pass                   
            raise   # continue to break or shutdown!            
        
        self.print_reg(STATUS,"STATUS after",1)  # Read STATUS register that hopefully tells you a successful transmission has occured (0x2E)
        print("")
        
        if(a=="900" or a=="901" or a=="002" or a=="003" or a=="004"):      # If you changed address above, change it back to normal
            self.set_address(0x12)    # Change back address!


    def set_address(self,Addr):
        """Function to change address on both RX and TX"""

        bytes = [W_REGISTER|RX_ADDR_P0]
        bytes.extend([Addr,Addr,Addr,Addr,Addr])
        self._spi_write(writing(bytes))

        bytes = [W_REGISTER|TX_ADDR]
        bytes.extend([Addr,Addr,Addr,Addr,Addr])
        self._spi_write(writing(bytes))
        

    def setup(self):
        """Function that sets the basic settings in the nRF"""

        # Setup EN_AA
        bytes = [W_REGISTER|EN_AA]
        bytes.append(SET_ACK)
        self._spi_write(writing(bytes))

        # Setup ACK RETRIES
        bytes = [W_REGISTER|SETUP_RETR]
        bytes.append(SET_ACK_RETR)
        self._spi_write(writing(bytes))

        # Setup Datapipe
        bytes = [W_REGISTER|EN_RXADDR]
        bytes.append(SET_DATAPIPE)
        self._spi_write(writing(bytes))

        # Setup Address width
        bytes = [W_REGISTER|SETUP_AW]
        bytes.append(SET_ADR_WIDTH)
        self._spi_write(writing(bytes))

        # Setup Freq
        bytes = [W_REGISTER|RF_CH]
        bytes.append(SET_FREQ)
        self._spi_write(writing(bytes))

        # Setup Data speed and power
        bytes = [W_REGISTER|RF_SETUP]
        bytes.append(SET_SETUP)
        self._spi_write(writing(bytes))

        # Setup Receive Address
        bytes = [W_REGISTER|RX_ADDR_P0]
        bytes.extend(SET_RX_ADDR_P0)    # "extend" adds a list to a list, "append" adds one obect to a list
        self._spi_write(writing(bytes))

        # Setup Transmitter Address
        bytes = [W_REGISTER|TX_ADDR]
        bytes.extend(SET_TX_ADDR)
        self._spi_write(writing(bytes))

        # Setup Payload size
        bytes = [W_REGISTER|RX_PW_P0]
        bytes.append(SET_PAYLOAD_S)
        self._spi_write(writing(bytes))
                
        # Setup CONFIG registry
        bytes = [W_REGISTER|CONFIG]
        bytes.append(SET_CONFIG)
        self._spi_write(writing(bytes))
        time.sleep(LONG_PAUSE)

        # Collect print out the registers from the nRF to to make sure thay are allright
        self.print_reg(STATUS,"STATUS",1)
        self.print_reg(EN_AA,"EN_AA",1)
        self.print_reg(SETUP_RETR,"SETUP_RETR",1)
        self.print_reg(EN_RXADDR,"EN_RXADDR",1)
        self.print_reg(SETUP_AW,"SETUP_AW",1)
        self.print_reg(RF_CH,"RF_CH",1)
        self.print_reg(RF_SETUP,"RF_SETUP",1)
        self.print_reg(RX_ADDR_P0,"RX_ADDR_P0",5)
        self.print_reg(TX_ADDR,"TX_ADDR",5)
        self.print_reg(RX_PW_P0,"RX_PW_P0",1)
        self.print_reg(CONFIG,"CONFIG",1)

def send(data):
    """Function that can be called from other files that wants to send data"""

    radio = NRF24L01P()
    radio.write_data(data)
    print("Enter data to send (3 bytes): ")  # Retype the input-text (input is still on form main-loop) 
                                
if __name__ == "__main__":
    """The magic starts here!"""

    # Receiver or transmitter
    rxtx = input("rx or tx? \n")    
    radio = NRF24L01P()

    # nRF transmitter
    if rxtx == "tx":    
        print('\nTransmitter')
        
        SET_CONFIG = 0x0E   # Transmitter
        radio.setup()       # Setting up radio
        
        TCP-Server.Run_func()    # Calls the "Run_func()" in a TCP-server (that in termes calls the "send(data)" function above with the data)
        while 1:
            package = input("Enter data to send (3 bytes): ")  # If not TCP-server is used, calls for input from user to bee sent
            print("")
            bytesToSend = [ord(str(x)) for x in package] # Convert input to decimal values 
            radio.write_data(bytesToSend)                # Calls the write_data() function with the payload

    # nRF receiver
    else:   
        print('\nReceiver')

        SET_CONFIG = 0x0F   # Receiver
        radio.setup()

        # Start listening
        try:
          radio.run()

        # If ctrl+c breaks operation or system shutdown
        except(KeyboardInterrupt, SystemExit):  
            try:
                # First close the CE-pin, so that it can be opened again without error!             
                self.ce_pin.close()  
                print("\n\ngpio-pin closed!\n")
            except:
                pass
            raise   # continue to break or shutdown!  
