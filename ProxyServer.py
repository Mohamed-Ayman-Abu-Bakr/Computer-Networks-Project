from socket import *
from datetime import datetime, date
import sys
import string
import socket

offset = -2 # Adjust to your OS (Windows: -2, MacOS: -1)
# Maximum duration for cached pages
CACHE_TIMOUT = 1 * 60
# Connection Port
port = 8888
# Maximum number of connections
max_connections = 1

def isBlockedURL(url):
	# opening the blacklist file.
	f = open("blacklist.txt", "rb")
	outputdata = f.readlines()
	# check whether the url is in the blacklist
	for s in outputdata:
		s = s[:offset]
		if (s == url):
			return True

	return False

def renderPage(tcpCliSock,msg):
	# Send Page Header
	tcpCliSock.send(b'HTTP/1.0 200 OK\nContent-Type: text/html\n\n')
	# Send Page Body
	tcpCliSock.send(("""
		<html>
		<body>
		<h1>"""+msg+"""</h1>
		</body>
		</html>
	""").encode('utf-8'))
 
def timeExceeded(cachedTime):
	# Get the time when the page was cached
	cachedTime = datetime.strptime(cachedTime[:-2].decode(), "%Y-%m-%d %H:%M:%S.f")
	# Get Current time
	now = datetime.now()
	# Find time since the page was cached
	elapsedTime = (now - cachedTime).total_seconds()
	# Check if the page exceeded the cache timeout
	if (elapsedTime > CACHE_TIMOUT):
		return True
	return False

def handleErrorCodes(resp):
	# check if the response has a status code that is deemed an error by the server
	if resp[9:10]==b'4' or resp[9:10]==b'5' or resp[9:12] == b"204":
		msg = resp[9:].split(b"\r\n")[0]
		print("Status Code:", msg, "\n")
		raise Exception("Error "+msg.decode())


if len(sys.argv) <= 1:
	print(
		'Usage : "python ProxyServer.py server_ip"\n[server_ip : It is the IP Address Of Proxy Server]')
	sys.exit(2)

# Create a server socket, bind it to a port and start listening
tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpSerSock.bind((sys.argv[1], port))
tcpSerSock.listen(max_connections)

while True:

	# Start receiving data from the client
	print('\n\nReady to serve...\n\n')

	tcpCliSock, addr = tcpSerSock.accept()
	print('Received a connection from:', addr, "\n")

	message = tcpCliSock.recv(1024)
	print("Message", message, "\n")
	if len(message) == 0:
		continue
	
	# Extract the filename from the given message
	filename = message.split()[1].partition(b"//")[2]
	# Extract the hostname from the given message
	hostn = filename.split(b'/')[0].replace(b"www.",b"",1)

	# check if the hostname is in the url blacklist
	if isBlockedURL(hostn):
		print(hostn,"was blocked","\n")
		# Show a page that says that the url is blocked
		renderPage(tcpCliSock=tcpCliSock,msg="This URL is Blocked")
		tcpCliSock.close()
		continue
	
	fileExist = "false"
	filetouse = b"/" + filename.replace(b"/",b"")
	
	try:
		# Check whether the file exist in the cache
		f = open(b"./cache/"+filetouse[1:], "rb")
		outputdata = f.readlines()

		# ProxyServer finds a cache hit and generates a response message
		resp = b""

		# Check if the file exceeded the cache timeout
		if (timeExceeded(outputdata[0])):
			print("Cached Page expired, Fetching from server!\n")
			# ignore the cached page and fetch from the server
			raise IOError

		# Read the contents of the cached page
		for i in range(1,len(outputdata)):
			resp += outputdata[i]
		
		# Send the cached page to the browser
		tcpCliSock.send(resp)
		# Close Socket
		f.close()
		print ('Read from cache')
 
	# Error handling for file not found in cache
	except IOError:
		# Create a socket on the proxyserver
		c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		print ("Hostname:",hostn,"\n")
		try:
			try:
				# Connect to the socket to port 80
				c.connect((hostn, 80))
			except:
				# The hostname can't be reached
				raise Exception(hostn.decode()+" Can't be reached")
			
			# Send request to the host
			request = b"GET " + b"http://" + filename + b" HTTP/1.0\r\n\r\n"
			c.send(request)

			# Show what request was made
			print("Request:",request,"\n")

			# Read the response into buffer
			resp = c.recv(4096)
			handleErrorCodes(resp)
			
			response = b""
			# Keep reading until you receive an empty response
			while True:
				if len(resp) <= 0:
					break
				response += resp
				resp = c.recv(4096)

			# Create a new file in the cache for the requested file.
			# Also send the response in the buffer to client socket and the corresponding file in the cache
			if(filename[-1:] == b'/'):
				filename = filename[:-1]
			# Open Cache file
			tmpFile = open(b"./cache/" + filename.replace(b"/",b"") ,"wb")
			# Generate custom time header when the response was received
			now = datetime.now()
			date_time = now.strftime("%Y-%m-%d %H:%M:%S.f\r\n")
			date_time = date_time.encode()
			
			# Append the custome time header to the response and write to cache file
			tmpFile.write(date_time + response)
			print("Wrote response to cache\n")
			# Close cache file
			tmpFile.close()
			# Send the response to the browser
			tcpCliSock.send(response)
			print("Sent response to browser\n")

		except Exception as e:
			print ("Illegal request")
			print(str(e))
			# Send a page saying what did go wrong to the browser
			renderPage(tcpCliSock,str(e))
 
	# Close the client and the server sockets
	tcpCliSock.close()
 