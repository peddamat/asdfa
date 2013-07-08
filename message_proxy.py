#!/usr/bin/env python3
from quick2wire.spi import *
from quick2wire.gpio import Pin
from quick2wire.gpio import In,Out,pi_header_1,Falling
import time
import select
from nRF24L01p import *


if __name__ == "__main__":

    # Setup radio
    radio = NRF24L01P()
    radio.setup()

    try:
        # Setup the interrupt-pin
        interrupt_pin = pi_header_1.pin(18, direction=In, interrupt=Falling)

        # Monitor the radio's interrupt pin using epoll
        epoll = select.epoll() 

        with interrupt_pin:

            # Register the interrupt-pin as an edge-triggered input
            epoll.register(interrupt_pin, select.EPOLLIN | select.EPOLLET) 

            # The main event-loop
            while True: 
                radio.start_listening()
                                
                # An interrupt indicates the radio has incoming data
                events = epoll.poll() 
                for fileno, event in events: 
                    if fileno == interrupt_pin.fileno(): 

                        # Handle incoming data
                        (pipe, payload) = radio.read_payload(32)
                        # payload = ''.join([hex(z)[2:] for z in payload[0]])
                        print("Pipe: %i" % pipe)
                        print("GOT: 0x" + str(payload))

                        radio.stop_listening()

                        radio.write(10)
                        

                # Handle outgoing data

    # If ctrl+c breaks operation or system shutdown
    except(KeyboardInterrupt, SystemExit):  
        try:
            radio.shutdown()
        except:
            pass
        raise