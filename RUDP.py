# Pranay Tarigopula           2018A7PS0237H
# D Vishal Dheeraj            2018A7PS0239H
# B Rishi Saimshu Reddy       2018A7PS0181H
# Dhruv Adlakha               2018A7PS0303H
# Abhinav Bandaru             2018A7PS0236H
# P Pranav Reddy              2018A7PS0238H


import socket
import threading
from _thread import *
from socketserver import ThreadingMixIn
import base64
import mmh3
import time
import os

## Used to create a connection, transfer data between server and client
#
#  Creates a udp connection with reliability between the server and the client.
#
#  Starts with a 3 way handshake and then the file trnasfer starts
#  It checks for acknowledgement for each packet sent
#  After a time of 3 seconds, if an ack for a packet is still not received, then the packet is sent again
#  This can take place for a maximum of 5 times or maximum time of 30s (default values), whichever comes first
#  
class Connection:

	## packet size
	packet_size = 0
	## socket
	s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	## timeout value
	timeoutval = 0

	window_size = 0

	buffer_size = 0

	## Class constructor
	# 
	#  @param self The object pointer
	#  @param packet_size packet size
	#  @param max_retransmits max no of retransmits
	def __init__(self,packet_size=10024,timeoutval=30,window_size = 3,buffer_size=6):
		self.packet_size = packet_size
		self.timeoutval = timeoutval
		self.window_size = window_size
		self.buffer_size = buffer_size

	## Send packet to client or send acknowledgement to server
	#
	#  send the requested file to the client
	#  uses utf-8 encoding 
	#  @param packet a Packet @see Packet Class
	#  @param target_host server/client ip
	#  @param port server/client port
	def send(self,packet,target_host,port):
		packet_params = packet.packet.split('~')
		pno = packet_params[4]
		self.s.sendto(bytes(packet.packet, encoding="utf-8"),(str(target_host),int(port)))
		if(packet_params[3]=="False" and packet_params[1]!="True" and packet_params[2]!="True"):
			print(f"Sent packet {pno}")
		elif(packet_params[3]=="True" and packet_params[1]!="True" and packet_params[2]!="True"):
			print(f"Sent ACK {packet_params[5]}")

	## Bind server/client
	#
	#  @param self The object pointer
	#  @param target_host server/client ip
	#  @param port server/client port
	def bind(self,target_host,port):
		self.s.bind((str(target_host),int(port)))

	## Receive packet from server
	#
	#  Receive packet from server and send acknowledgement
	#  Verifies if packet is not damaged
	#  @param self The object pointer
	#  @param target_host server ip
	#  @param port server port
	def recv(self,target_host,port):
		chunk,addr = self.s.recvfrom(self.packet_size)
		chunk = chunk.decode(encoding='utf-8')
		chunk = str(chunk)
		packet_params = chunk.split("~")
		pno = packet_params[4]
		checksum = packet_params[6]
		if(self.verifyChecksum(chunk,packet_params[6])==False):
			print(f"Packet {pno} compromised")
			return None
		recvd_packet = Packet(packet_params[1],packet_params[2],packet_params[3],packet_params[4],packet_params[5],bytes(packet_params[8],'utf-8'))
		return recvd_packet

	## Close socket
	#
	#  @param self The object pointer
	def close(self):
		self.s.close()

	## Verify if packet is not damaged
	#
	#  @param self The object pointer
	#  @param packet a Packet @see Packet Class
	#  @param chk an integer to check if packet is not damaged
	def verifyChecksum(self,packet,chk):
		packet_params = packet.split("~")
		temp = ""
		temp += packet_params[0]
		temp += "~"
		temp += packet_params[1]
		temp += "~"
		temp += packet_params[2]
		temp += "~"
		temp += packet_params[3]
		temp += "~"
		temp += packet_params[4]
		temp += "~"
		temp += packet_params[5]
		temp += "~"
		temp += packet_params[7]
		temp += "~"
		temp += packet_params[8]
		cc =  (((mmh3.hash(temp))) % (1<<16))
		print(cc)
		print(chk)
		if(int(cc)==int(chk)):
			return True
		else:
			return False


## Packet Class: Used to store some information about the 
#
#  Contains headers and body. Headers ensure the packet has safely reached. Body contains a part of the information to be sent
class Packet:
	## payload of the packet
	payload = b""
	## header of the packet
	header = "True~"
	## packet string
	packet = ""
	## SYN bit
	SYN = 0
	## FIN bit
	FIN = 0
	## ACK bit
	ACK = 0
	## PNO bit
	PNO = 0
	## ANO bit
	ANO = 0
	## body size
	body_length = 0
	## check sum value
	checksum = ""


	## Class constructor
	#  
	#  Assembles the body and header of the packet
	#  @param self The object pointer
	#  @param SYN the SYN bit
	#  @param FIN the FIN bit
	#  @param ACK the ACK bit
	#  @param PNO the PNO bit
	#  @param ANO the ANO bit
	#  @param payload the payload of the packet
	def __init__(self,SYN,FIN,ACK,PNO,ANO,payload):
		if(SYN==1 or SYN=="True"):
			self.SYN = True
		else:
			self.SYN = False
		
		if(FIN==1 or FIN=="True"):
			self.FIN = True
		else:
			self.FIN = False

		if(ACK==1 or ACK=="True"):
			self.ACK = True
		else:
			self.ACK = False

		self.header += str(self.SYN)
		self.header += "~"
		self.header += str(self.FIN)
		self.header += "~"
		self.header += str(self.ACK)
		self.header += "~"
		self.header += str(PNO)
		self.header += "~"
		self.header += str(ANO)
		self.header += "~"
		self.payload = payload
		temp_str = str(self.payload.decode(encoding='utf-8'))
		self.checksum = self.computeChecksum()
		self.header += str(self.checksum)
		self.header += "~"
		self.body_length = len(temp_str)
		self.header += str(self.body_length)
		self.header += "~"
		self.packet += self.header
		self.packet += temp_str



	## print packet
	def printPacket(self):
		print(self.packet)

	## computes checksum value after decoding the packet
	def computeChecksum(self):
		temp = self.header + str(len(str(self.payload.decode(encoding='utf-8')))) + "~" + str(self.payload.decode(encoding='utf-8'))
		return (((mmh3.hash(temp))) % (1<<16))



#comcast --device lo0 --stop



