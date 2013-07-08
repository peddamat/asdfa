#!/usr/bin/env python3
from quick2wire.spi import *
from quick2wire.gpio import Pin
from quick2wire.gpio import In,Out,pi_header_1,Falling
import time
import select
from nRF24L01p import *


if __name__ == "__main__":
    """ The magic starts here!

    """

    # Receiver or transmitter
    # rxtx = input("rx or tx? \n")    
    radio = NRF24L01P()

    # # nRF transmitter
    # if rxtx == "tx":    
    #     print('\nTransmitter')
        
    #     SET_CONFIG = 0x0E   # Transmitter
    #     radio.setup()       # Setting up radio
        
    #     # TCP-Server.Run_func()    # Calls the "Run_func()" in a TCP-server (that in termes calls the "send(data)" function above with the data)
    #     while 1:
    #         package = input("Enter data to send (3 bytes): ")  # If not TCP-server is used, calls for input from user to bee sent
    #         print("")
    #         bytesToSend = [ord(str(x)) for x in package] # Convert input to decimal values 
    #         radio.write_data(bytesToSend)                # Calls the write_data() function with the payload

    # # nRF receiver
    # else:   
    #     print('\nReceiver')

    int_pin = pi_header_1.pin(18, direction=In, interrupt=Falling)

    # SET_CONFIG = 0x0F   # Receiver
    radio.setup()

    # Start listening
    try:
        # Configure epoll for interrupt-handler
        epoll = select.epoll() 

        with int_pin:

            epoll.register(int_pin, select.EPOLLIN | select.EPOLLET) 

            while True: 
                radio.start_listening()
                                
                events = epoll.poll() 
                for fileno, event in events: 
                    if fileno == int_pin.fileno(): 
                        # radio.CE(LOW)
                        # radio.read_data()            
                        radio.read_payload(32)

    # If ctrl+c breaks operation or system shutdown
    except(KeyboardInterrupt, SystemExit):  
        try:
            radio.shutdown()
        except:
            pass
        raise