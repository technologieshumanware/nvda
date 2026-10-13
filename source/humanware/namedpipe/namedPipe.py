# A part of NonVisual Desktop Access (NVDA)
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2026 Technologies Humanware

import threading
import time
import ctypes
import json
from ctypes import wintypes
from logHandler import log


#Pipe constants

#[in] dwOpenMode
#The open mode.
#The function fails if dwOpenMode specifies anything other than 0 or the flags listed in the following tables.
#This parameter must specify one of the following pipe access modes. The same mode must be specified for each instance of the pipe.
PIPE_ACCESS_DUPLEX = int("0x00000003",16)
PIPE_ACCESS_INBOUND = int("0x00000001",16)
PIPE_ACCESS_OUTBOUND = int("0x00000002",16)

# This parameter can also include one or more of the following flags, which enable the write-through and overlapped modes. These modes can be different for different instances of the same pipe.
FILE_FLAG_FIRST_PIPE_INSTANCE = int("0x00080000",16)
FILE_FLAG_WRITE_THROUGH = int("0x80000000",16)
FILE_FLAG_OVERLAPPED = int("0x40000000",16)

#This parameter can include any combination of the following security access modes. These modes can be different for different instances of the same pipe.
WRITE_DAC = int("0x00040000",16) # 0x00040000L
WRITE_OWNER = int("0x00080000",16) #0x00080000L
ACCESS_SYSTEM_SECURITY = int("0x01000000",16) #0x01000000L

# [in] dwPipeMode
# The pipe mode.
# The function fails if dwPipeMode specifies anything other than 0 or the flags listed in the following tables.
# One of the following type modes can be specified. The same type mode must be specified for each instance of the pipe.

PIPE_TYPE_BYTE = int("0x00000000",16)
PIPE_TYPE_MESSAGE = int("0x00000004",16)

#One of the following read modes can be specified. Different instances of the same pipe can specify different read modes.
PIPE_READMODE_BYTE = int("0x00000000",16)
PIPE_READMODE_MESSAGE = int("0x00000002",16)

#One of the following wait modes can be specified. Different instances of the same pipe can specify different wait modes.
PIPE_WAIT = int("0x00000000",16)
PIPE_NOWAIT = int("0x00000001",16)

#One of the following remote-client modes can be specified. Different instances of the same pipe can specify different remote-client modes.
PIPE_ACCEPT_REMOTE_CLIENTS = int("0x00000000",16)
PIPE_REJECT_REMOTE_CLIENTS = int("0x00000008",16)


WAIT_OBJECT_0 = 0x0  # Wait operation completed successfully; the event was signaled.
WAIT_TIMEOUT = 0x102  # Wait operation timed out; the event was not signaled within the interval.

ULONG_PTR = ctypes.c_uint64
DWORD = wintypes.DWORD
HANDLE = wintypes.HANDLE

class OVERLAPPED(ctypes.Structure):
	"""
	Represents the Windows OVERLAPPED structure used for asynchronous (overlapped) I/O operations.
	This structure is required when performing non-blocking I/O with Windows API functions such as
	ReadFile, WriteFile, and ConnectNamedPipe with the FILE_FLAG_OVERLAPPED flag.
	"""
	_fields_ = [
		("Internal", ULONG_PTR),
		("InternalHigh", ULONG_PTR),
		("Offset", DWORD),
		("OffsetHigh", DWORD),
		("hEvent", HANDLE)
	]
	_pack_ = 8

class NamedPipeServer :

	def __init__(self, pipeName=None, buffer_size=4096, timeout=100000, max_instances=1, security_attributes=None):
		"""
		Initializes the pipe server with optional configuration parameters.

		:param pipeName: The name of the pipe. Default is None.
		:param buffer_size: The buffer size for both input and output. Default is 4096 bytes.
		:param timeout: Timeout for pipe connection, default is 10000 ms.
		:param max_instances: Maximum number of simultaneous pipe instances. Default is 1.
		:param security_attributes: Security attributes for the pipe. Default is None.
		"""
		self.pipeName = pipeName
		self.buffer_size = buffer_size
		self.timeout = timeout
		self.max_instances = max_instances
		self.security_attributes = security_attributes

		# Initialization of internal state variables
		self.clientConnected = False
		self.handle = None
		self.shutdown_event = threading.Event()

	def startServer(self, pipeName=None):
		try:
			self.close()

			# If pipeName is provided to startServer, override the class's pipeName
			if pipeName is None and self.pipeName is None:
				raise ValueError("pipeName must be specified either in the class constructor or in startServer method.")

			pipeName = pipeName or self.pipeName

			# Create a named pipe server
			self.handle = ctypes.windll.kernel32.CreateNamedPipeW(
				pipeName,
				PIPE_ACCESS_OUTBOUND | FILE_FLAG_OVERLAPPED,
				PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT,
				self.max_instances,
				self.buffer_size,
				self.buffer_size,
				self.timeout,
				self.security_attributes
			)

			log.debug(f"Waiting for client to connect to {pipeName} (overlapped)...")

			# Create an event for overlapped I/O and wait for a client to connect
			overlapped_event = ctypes.windll.kernel32.CreateEventW(None, True, False, None)
			overlapped = OVERLAPPED()
			overlapped.hEvent = overlapped_event

			result = ctypes.windll.kernel32.ConnectNamedPipe(self.handle, ctypes.byref(overlapped))
			error = ctypes.GetLastError()

			if result == 0 and error == 997:  # ERROR_IO_PENDING
				log.debug("Client connection is pending, waiting for connection to complete...")

				# Wait for the client to connect or for the shutdown event to be set
				while not self.shutdown_event.is_set():
					wait_result = ctypes.windll.kernel32.WaitForSingleObject(overlapped_event, 1000)  # Wait for 1 second
					if wait_result == WAIT_OBJECT_0:
						log.debug("Client connected.")
						self.clientConnected = True
						break
					elif wait_result == WAIT_TIMEOUT:
						log.debug("Waiting for client connection timed out, checking shutdown event...")
						continue
					else:
						log.debug(f"Error waiting for client connection: {wait_result}")
						return

				if self.shutdown_event.is_set():
					log.debug("Shutdown event set while waiting for client connection, stopping server.")
					return

			elif result > 0:
				log.debug("Client connected immediately (overlapped).")
				self.clientConnected = True

		except Exception as e:
			log.debug(f"Error in server: {e}")

	def sendMessage(self, msgType, message, errorCode):
		# Write a message to the pipe
		data = {
			"MessageType": msgType,
			"Message": message,
			"ErrorCode": errorCode
		}
		jsonMessage = json.dumps(data) + '\r\n'
		if self.clientConnected:
			log.debug(f"Pipe server sending message: {msgType} {message} {errorCode}")
			ctypes.windll.kernel32.WriteFile(self.handle, jsonMessage.encode('utf-8'),len(jsonMessage),None,None)
		else:
			log.debug(f"Tried to send message {msgType} {message} {errorCode} but client was not connected")

	def close(self):
		if self.clientConnected and self.handle:
			ctypes.windll.kernel32.FlushFileBuffers(self.handle)
			ctypes.windll.kernel32.DisconnectNamedPipe(self.handle)
			self.clientConnected = False
			log.debug("Server connection closed.")
		else:
			log.debug("No client connected or no open pipe handle.")

	def isConnected(self):
		return self.clientConnected

	def waitForConnection(self, interval=5, timeout=7200): # Default timeout of 2 hours
		start = time.time()
		while not self.isConnected() and time.time() - start < timeout:
			log.debug("Waiting for named pipe client connection...")
			time.sleep(interval)

	def shutdown(self):
		self.shutdown_event.set()
		self.close()
