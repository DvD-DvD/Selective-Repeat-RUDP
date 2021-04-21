# Pranay Tarigopula           2018A7PS0237H
# D Vishal Dheeraj            2018A7PS0239H
# B Rishi Saimshu Reddy       2018A7PS0181H
# Dhruv Adlakha               2018A7PS0303H
# Abhinav Bandaru             2018A7PS0236H
# P Pranav Reddy              2018A7PS0238H

import socket
import RUDP
import os
import sys
import threading
import time
from collections import OrderedDict
import base64
import timeit

## Client Class: Makes a file request to the server
# 
#  Makes a request for the filename, passed as an argument from the GUI, to the server
#  The server should be up and running before running the client
#

class Client:
    mutex = threading.Lock()
    ## requested file name
    request = ""
    ## server ip address
    target_host = ""
    ## server port
    target_port = 0
    ## client ip address
    self_host = ""
    ## client port
    self_port = 0
    ## size of packet received
    packet_size = 0
    ## size of body of the packet received
    body_size =0 
    ## list of all packets received
    packet_list = {}
    ## last received time
    last_received_time = 0
    ## client start time
    start_time = time.time()
    ## list of all bytes
    write_list = b""
    ## has the object timed out
    cl_timeout = 0
    ## Flag to check if data receiving has started
    is_data_received = 0
    is_ack_received = 0

    window_size = 0
    buffer_size = 0
    ## Class constructor: Sends the connection request and recieves the file requested
    #   
    #  Initializes the client, sends connection request to server, recieves files, stores files, ends connection
    #  @param self Object Pointer
    #  @param self_host object ip
    #  @param self_port obejct port
    #  @param target_host target ip
    #  @param target_port target port
    #  @param file_request file name
    #  @param cl_timeout timeout value
    #  @param packet_size packet size
    #  @param body_size body size
    #  @param buffer_size buffer size
    def __init__(self,self_host,self_port,target_host,target_port,file_request,cl_timeout,packet_size,window_size,buffer_size,body_size=8000):
        start = timeit.default_timer()
        self.target_host = str(target_host)
        self.target_port = target_port
        self.self_host = str(self_host)
        self.self_port = self_port
        self.request = str(file_request)
        self.cl_timeout = cl_timeout
        self.packet_size = packet_size
        self.body_size = body_size
        self.window_size = window_size
        self.buffer_size = buffer_size
        self.s = RUDP.Connection(timeoutval=cl_timeout,packet_size=self.packet_size,window_size=self.window_size,buffer_size=self.buffer_size)
        self.s.bind(self.self_host,self.self_port)

        print("Initiating Handshake")


        first_t = threading.Thread(target=self.send_first_packet,args=())
        first_t.start()

        while(True):
            ack_pack = self.s.recv(self.target_host,self.target_port)
            if(ack_pack is not None and ack_pack.packet.split("~")[1]=="True" and ack_pack.packet.split("~")[3]=="True" and ack_pack.packet.split("~")[8]=="ACK Packet"):
                self.mutex.acquire()
                if(self.is_ack_received==0):
                    self.is_ack_received = 1
                self.mutex.release()
                break
            else:
                continue

        third_t = threading.Thread(target=self.send_third_packet,args=())
        third_t.start()


        self.last_received_time = time.time()
        elapsed_thread = threading.Thread(target=self.time_elapsed,args=())
        elapsed_thread.start()
        thread_timer = threading.Thread(target=self.global_timer,args=())
        thread_timer.start()
        while(True):
            line = self.s.recv(target_host,target_port)
            if(line is not None):
                self.mutex.acquire()
                if(self.is_data_received==0):
                    self.is_data_received = 1
                self.mutex.release()
                packet_params = line.packet.split("~")
                self.last_received_time = time.time()
                if(line.packet.split("~")[2]=="True"):
                    print("Received FIN Packet, Server closing connection")
                    finack = RUDP.Packet(0,1,1,0,0,bytes("FIN ACK",encoding='utf-8'))
                    self.s.send(finack,self.target_host,self.target_port)
                    print("Sent FIN ACK to server")
                    break
                elif(packet_params[1]=="False" and packet_params[2]=="False" and packet_params[3]=="False"):  # and packet_params[4]!="4" Add packet number here to check for packet los
                    print(f"Packet {packet_params[4]} ok")
                    ack_pack = RUDP.Packet(0,0,1,(int(packet_params[4])),int(packet_params[4])%self.buffer_size,bytes("ACK Packet", 'utf-8'))
                    self.s.send(ack_pack,self.target_host,self.target_port)
                pno = int(line.packet.split("~")[4])
                temp = line.payload
                self.packet_list[pno] = temp
        self.s.close()
        # print(self.packet_list)
        od = OrderedDict(sorted(self.packet_list.items()))
        for no,body in od.items():
            self.write_list += body
        # print((base64.decodebytes(self.write_list)).decode())
        output_file = "output."
        temp = file_request.split(".")
        output_file += temp[1]
        # final_write_list = final_write_list.decode('ascii')
        # print(self.write_list)
        with open(output_file,"wb") as f:
            final = (base64.decodebytes(self.write_list))
            f.write(final)

        print(f"Written to {output_file}")
        stop = timeit.default_timer()
        f = open("times.txt", "a")
        k = stop - start
        s = str(k)
        f.write(s + '\n')
        f.close()
        os._exit(0)

    ## Used to send the packet to server (first packet of three way handshake)
    #
    #  @param self Object Pointer
    def send_first_packet(self):
        while(True):
            syn_pac = RUDP.Packet(1,0,0,0,0,bytes("First Packet", 'utf-8'))
            self.s.send(syn_pac,self.target_host,self.target_port)
            print("Client Connection Request Sent")
            time.sleep(2)
            if(self.is_ack_received==1):
                print("Server ACK Received")
                break
            else:
                print("Server ACK not received. Resending connection request")
                continue
        return

    ## Used to send the packet to server (third packet of three way handshake). The packet contains the name of the file requested
    #
    #  @param self Object Pointer
    def send_third_packet(self):
        while(True):
            req_pac = RUDP.Packet(0,0,0,0,0,bytes(self.request, 'utf-8'))
            self.s.send(req_pac,self.target_host,self.target_port)
            print("Client Request sent")
            time.sleep(2)
            if(self.is_data_received==1):
                break
            else:
                print("Resending file request to server")
                continue
        return

    ## Global Timer: Used to terminate redundant connections
    #  @param self Obejct pointer 
    def global_timer(self):
        while(True):
            if(time.time() - self.last_received_time) >= self.s.timeoutval:
                print(f"Timeoutval is {self.s.timeoutval}")
                print(f"Time.Time is {time.time()}")
                print(f"Last Received Time is {self.last_received_time}")
                print("Global Timer exceeded")
                od = OrderedDict(sorted(self.packet_list.items()))
                for no,body in od.items():
                    self.write_list += body
                # print((base64.decodebytes(self.write_list)).decode())
                output_file = "output."
                temp = self.request.split(".")
                output_file += temp[1]
                # final_write_list = final_write_list.decode('ascii')
                # print(self.write_list)
                with open(output_file,"wb") as f:
                    final = (base64.decodebytes(self.write_list))
                    f.write(final)
                print(f"Written to {output_file}")
                os._exit(1)


    ## Total time runnning
    #  @param self Obejct pointer
    def time_elapsed(self):
        current_time = time.time()
        elap = current_time - self.start_time
        return elap

## Start program with server ip, port and client ip, port
if __name__ == '__main__':
    # c1 = Client("127.0.0.1",65431,"127.0.0.1",65432,"sample.tnt",30,10024,3,6,8000)

    self_host = sys.argv[1]
    self_port = sys.argv[2]
    target_host = sys.argv[3]
    target_port = sys.argv[4]
    file_request = sys.argv[5]
    global_timer = float(sys.argv[6])
    pkt_size = int(sys.argv[7])
    window_size = int(sys.argv[8])
    buff_size = int(sys.argv[9])
    body_size = int(sys.argv[10])
    c1 = Client(self_host,self_port,target_host,target_port,file_request,global_timer,pkt_size,window_size,buff_size,body_size)

