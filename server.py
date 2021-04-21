# Pranay Tarigopula           2018A7PS0237H
# D Vishal Dheeraj            2018A7PS0239H
# B Rishi Saimshu Reddy       2018A7PS0181H
# Dhruv Adlakha               2018A7PS0303H
# Abhinav Bandaru             2018A7PS0236H
# P Pranav Reddy              2018A7PS0238H


import socket
import RUDP
import math
import time
import threading
import os
import sys
import base64

##  Server class
#
# Listens for and then accepts the clients request for a file and sends the file using the RUDP protocol as designed in the project 
class Server:
    mutex = threading.Lock()
    ## target host
    target_host = ""
    ## target's port
    target_port = 0
    ## self host
    self_host = ""
    ## self port
    self_port = 0
    ## total packets
    total_packets = 0
    ## Number Of packets ACKed 
    number_of_acked_packets = 0
    ## Last recieved time
    last_received_time = 0
    ## Size of each packet
    packet_size = 300
    ## Size of the body
    body_size = 200
    ## Index of the last packet sent
    last_sent_index = 0
    ## the counter
    retransmission_counter = 4
    ## Array whose indices are the packet packet numbers and the value stored is whether they are ACKed or not
    ack_array = list()
    ## All the thread --
    all_threads = list()
    ## sleep time set for the threads
    sleep_time = 3
    ## Sliding window size
    window_size = 0
    ## Pointer to the packet to be sent
    send_head = 0
    ## Pointer to the base packet of the sliding window on the sender side
    send_base = 0
    ## server timeout
    serv_timeout = 0
    ## Filename
    filename = 0

    buffer_size = 0


    ## The constructor for the Server class
    #
    # This constructor fills in the values for the class variables and starts with the process of sending the file to the client.
    # It reads the filename from the request and starts reading the file in the folder and encodes it using base64. It then starts sending the encoded file in packets of defined size. It creates threads for sending each of the packets and then wait for ACKs and acts accordingly based on the response. 
    # After all the packets have been sent and ACKed the process of terminating the connection starts and then the connection between server and client is closed.
    #
    # @param self is the object pointer
    # @param self_host server ip
    # @param self_port server port
    # @param target_host client ip
    # @param target_port client port
    # @param retransmission_counter number of times retransmitted
    # @param window_size window size
    # @param sleep_time sleep time: waiting time for an acknowledgement
    # @param serv_timeout server timeout time in seconds
    # @param packet_size packet size
    # @param body_size body size
    # @param buffer_size buffer size
    def __init__(self,self_host,self_port,target_host,target_port,retransmission_counter,window_size,sleep_time,serv_timeout=30,packet_size=10024,buffer_size=6,body_size=8000):
        self.target_host = str(target_host)
        self.target_port = target_port
        self.self_host = str(self_host)
        self.self_port = self_port
        self.retransmission_counter = retransmission_counter
        self.window_size = window_size
        self.send_head = self.send_base + self.window_size - 1
        self.sleep_time = sleep_time
        self.serv_timeout = serv_timeout
        self.packet_size = packet_size
        self.body_size = body_size
        self.buffer_size = buffer_size
        self.s = RUDP.Connection(timeoutval=self.serv_timeout,packet_size=self.packet_size,window_size=self.window_size,buffer_size=self.buffer_size)
        self.s.bind(self.self_host,self.self_port)
        self.is_fin_acked = 0

        while(True):
            conn_pac = self.s.recv(self.target_host,self.target_port)
            if(conn_pac is not None and conn_pac.packet.split("~")[1]=="True" and conn_pac.packet.split("~")[8]=="First Packet"):
                print("Client Connection Request Received")
                ack_pac = RUDP.Packet(1,0,1,0,0,bytes("ACK Packet", 'utf-8'))
                self.s.send(ack_pac,self.target_host,self.target_port)
                continue
            elif(conn_pac is not None and conn_pac.packet.split("~")[1]=="False"):
                self.filename = conn_pac.packet.split("~")[8]
                print(f"Filename requested is {self.filename}")
                break
        count = 0
        try:
            with open(self.filename,"rb") as file:
                string_data = file.read()
                self.total_data = base64.encodebytes(string_data)
        except IOError:
            print(f"Error File {self.filename} not found")
            self.end_connection()
            finack = self.s.recv(self.target_host,self.target_port)
            if(finack.packet.split("~")[2]=="True" and finack.packet.split("~")[3]=="True"):
                print("Received Client termination ACK")
            os._exit(3)
        self.total_packets = math.ceil(len(self.total_data)/(self.body_size))
        print(f"Total packets are {self.total_packets}")
        for i in range(0,self.total_packets):
            self.ack_array.append(0)
        thread_ack = threading.Thread(target=self.listen_for_ack,args=())
        thread_ack.start()
        self.last_received_time = time.time()
        thread_timer = threading.Thread(target=self.global_timer,args=())
        thread_timer.start()
        thread_counter = 0
        while(thread_counter < self.total_packets):
            if(thread_counter >= self.send_base and thread_counter <= self.send_head):
                tx = threading.Thread(target=self.send_this_packet,args=(thread_counter,))
                tx.start()
                self.all_threads.append(tx)
                thread_counter += 1
            else:
                continue

        for i in range(self.total_packets):
            self.all_threads[i].join()
        thread_ack.join()
        print("Server ending connection")
        self.end_connection()
        finack = self.s.recv(self.target_host,self.target_port)
        if(finack.packet.split("~")[2]=="True" and finack.packet.split("~")[3]=="True"):
            print("Received Client termination ACK")
        self.s.close()
        # print(self.total_data)
        os._exit(0)

    ## send_this_packet Method
    # @param self is the object pointer
    # @param packet_no is the packet number to be sent among all the packets
    #
    # This method when invoked creates the packet, send it and waits for an ACK. Based on the response from the client, the method acts accordingly (as specified in the design documentation) 
    def send_this_packet(self,packet_no):
        retries = 0
        while(True):
            packet_body = self.total_data[(self.body_size*packet_no):min(self.body_size*(packet_no+1),len(self.total_data))]
            sending_packet = RUDP.Packet(0,0,0,packet_no,(packet_no % self.buffer_size),packet_body)
            self.s.send(sending_packet,self.target_host,self.target_port)
            time.sleep(self.sleep_time)
            if(self.ack_array[packet_no]==1):
                break
            elif(retries < self.retransmission_counter):
                print(f"ACK for packet {packet_no} is not received, resending packet again ({retries})")
                retries += 1
                self.s.send(sending_packet,self.target_host,self.target_port)
                continue
            else:
                print("Exceeded maximum retransmits, terminating connection......")
                self.end_connection()
                os._exit(2)
        return
    
    ## listen_for_ack Method
    # @param self is the object pointer
    #
    # This method is invoked to listen for ACKs from the client after sending packets
    def listen_for_ack(self):
        while(self.number_of_acked_packets < self.total_packets):
            response = self.s.recv(self.target_host,self.target_port)
            if(response.packet.split("~")[3]=="True"):
                ack_no = int(response.packet.split("~")[4])
                print(f"Received ACK for packet {ack_no}")
                self.mutex.acquire()
                if(self.ack_array[ack_no]==0):
                    self.ack_array[ack_no] = 1
                    self.number_of_acked_packets += 1
                self.last_received_time = time.time()
                self.mutex.release()
                if((self.ack_array[self.send_base]==1)):
                    self.mutex.acquire()
                    try:
                        if((self.send_base < self.total_packets - self.window_size)):
                            self.send_base += 1
                            self.send_head += 1
                            print(f"Send base is now {self.send_base}")
                            print(f"Send head is now {self.send_head}")
                    finally:
                        self.mutex.release()
        print("All ACKS Received. Initiating termination")
        return

    ## global_timer Method
    # @param self is the object pointer
    # 
    # A global timer that is run to check for timeouts. 
    def global_timer(self):
        while(True):
            if(time.time() - self.last_received_time) >= self.s.timeoutval:
                print(f"Timeoutval is {self.s.timeoutval}")
                print(f"Time.Time is {time.time()}")
                print(f"Last Received Time is {self.last_received_time}")
                print("Global Timer exceeded, ending connection")
                self.end_connection()
                os._exit(1)

    ## end_connection Method
    # @param self is the object pointer
    # 
    # This method when invoked initiates the closing of the connection between the server and the client
    def end_connection(self):
        fin_packet = RUDP.Packet(0,1,0,0,0,bytes("End Connection", 'utf-8'))
        self.s.send(fin_packet,self.target_host,self.target_port)
        return

if __name__ == '__main__':
    # s1 = Server("127.0.0.1",65432,"127.0.0.1",65431,5,3,3)
        
    self_host = sys.argv[1]
    self_port = sys.argv[2]
    target_host = sys.argv[3]
    target_port = sys.argv[4]
    rtc = int(sys.argv[5])
    window = int(sys.argv[6])
    rtt = float(sys.argv[7])
    global_timer = float(sys.argv[8])
    pkt_size = int(sys.argv[9])
    buffer_size = int(sys.argv[10])
    bodysize = int(sys.argv[11])
    s1 = Server(self_host,self_port,target_host,target_port,rtc,window,rtt,global_timer,pkt_size,buffer_size,bodysize)

