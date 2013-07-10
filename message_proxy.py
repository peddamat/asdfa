#!/usr/bin/env python3
from quick2wire.spi import *
from quick2wire.gpio import Pin
from quick2wire.gpio import In,Out,pi_header_1,Falling
import time
import select
from nRF24L01p import *
from struct import *

# Graphite
import socket
import time

CARBON_SERVER = '127.0.0.1'
CARBON_PORT = 2003

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

                        # Handle HELO requests on pipe 0
                        if pipe == 0:
                            radio.stop_listening()
                            radio.write(10)

                        mode, temperature = struct.unpack_from('<cf', payload)

                        print("Temperature: " + str(temperature))

                        message = 'local.sensie.1.temperature %f %d\n' % (temperature, int(time.time()))

                        #print('sending message:\n%s' % message)
                        sock = socket.socket()
                        sock.connect((CARBON_SERVER, CARBON_PORT))
                        sock.sendall(bytes(message,'UTF-8'))
                        sock.close()

                        # Convert the bytearray into hex
                        #payload = [hex(z)[2:] for z in payload]
                        #print("Pipe: %i" % pipe)
                        #print("GOT: 0x" + str(payload))

                # Handle outgoing data

    # If ctrl+c breaks operation or system shutdown
    except(KeyboardInterrupt, SystemExit):  
        try:
            radio.shutdown()
        except:
            pass
        raise
