import socket
import threading
import socketserver
import time
import nRF24L01p 

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    """Thread class"""
    def handle(self):
        while 1:
            try:
                data = str(self.request.recv(1024), 'ascii')    #Receive bytes to from TCP-client to buffer of 1024 bytes

                cur_thread = threading.current_thread()     #Get thread information
                print("Received: {} \n                           in: {}\n".format(data, cur_thread.name))    #Print out received bytes and thread name

                bytesToSend = [ord(str(x)) for x in data] #Convert received bytes to type: Decimal (ord("1")=49)Convert input to decimal values 
                
                nRF24L01p.Send(bytesToSend) #Send the bytes to the nRF-program (transmitter) (in decimal form)

                self.request.sendall(bytes("{}".format(data), 'ascii'))     #Resend the data to TCP-client

            except:
                break #Break from while-loop
            
        print("{} is now closed".format(cur_thread.name))
        print("\nEnter data to send (3 bytes): ")  #Retype the input-text (input is still on form main-loop) 

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Starts a new thread for each request"""
    pass

def Run_func():
    """Gets called on from nRF-script"""
    # HOST='' accepts all incoming ip
    HOST, PORT = '', 1234 

    #Setup server on different thread
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address

    # Start a thread with the server -- the function will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True     #Run in background thread = true
    server_thread.start()

    print("\nServer loop running in background thread!\n")

if __name__ == "__main__":
    Run_func()
