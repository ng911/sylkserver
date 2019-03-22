import sys
try: import gevent
except ImportError: print 'Please install gevent and its dependencies and include them in your PYTHONPATH'; import sys; sys.exit(1)
from gevent import monkey, Greenlet, GreenletExit
monkey.patch_all()
import gevent.select
import logging
from optparse import OptionParser, OptionGroup
import socket, select

logger = logging.getLogger('psap')

sample_ali = {
	'4153054541' :
"112\r%s WPH2 08/11 13:17\rUS CELLULAR 800-510-6091    \r      1285       P#515-319-4005\r   Quail Ave - 3S        \r                    \rCALLBK=(415)305-4541      01045\rCA 00070-2-011, SAN FRAN       \r                  TEL=USCC \r+042.657610 -093.273464      46\rPSAP= HAMPTON PD\rVerify PD\r\nVerify FD\r\nVerify EMS",
	'2037274298' :
"112\r%s WPH2 08/11 13:17\rUS CELLULAR 800-510-6092    \r      1285       P#515-319-4005\r   113 Pine Str -        \r                    \rCALLBK=(203)727-4298      01046\rIA 00070-2-011, FRANKLIN       \r                  TEL=USCC \r+042.657610 -093.273464      46\rPSAP= HAMPTON PD\rVerify PD\r\nVerify FD\r\nVerify EMS",
	'2033225119' :
"112\r%s WPH2 08/11 13:17\rUS CELLULAR 800-510-6093    \r      1285       P#515-319-4005\r   200 University Ave    \r                    \rCALLBK=(203)322-5119      01047\rCA 95109-2-011, PALO ALTO      \r                  TEL=USCC \r+041.657610 -091.273464      47\rPSAP= HAMPTON PD\rVerify PD\r\nVerify FD\r\nVerify EMS",
	'4154487340' :
"112\r%s WPH2 08/11 13:17\rUS CELLULAR 800-510-6094    \r      1285       P#515-319-4005\r   555 Market Str        \r                    \rCALLBK=(203)554-2777      01048\rCA 94108-2-011, SAN FRANCISCO  \r                  TEL=USCC \r+042.657610 -092.273464      42\rPSAP= HAMPTON PD\rVerify PD\r\nVerify FD\r\nVerify EMS",
}


class AliSimulator:
	def __init__(self, ipAddress, port):
		self.sock, self._gin, self._conn = None, None, {}
		self.port = port
		self.ipAddress = ipAddress
		
	def start(self):
		self.sock = socket.socket(type=socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		logger.debug("port is %r", self.port)
		self.sock.bind((self.ipAddress, self.port))
		self.sock.listen(5)
		logger.debug('created listening socket %r', self.sock.getsockname())
		self._gin = gevent.spawn(self._receiver)

	def stop(self):
		if self._gin:
			self._gin.kill()
			self._gin = None
		for conn in self._conn.itervalues():
			conn.close()
		self._conn = {}
		if self.sock is not None:
			self.sock.close()
			self.sock = None
		
	# listen for TCP connections
	def _receiver(self): 
		logger.debug('inside _receiver')
		while True:
			logger.debug('waiting on sock.accept %r', self.sock)
			conn, remote = self.sock.accept()
			if conn:
				logger.debug('remote connected')
				(ipAddress, port) = remote
				logger.debug('ipAddress %r, port %r', ipAddress, port)
				self._conn["%s:%s" % (ipAddress, port)] = conn
				gevent.spawn(self._alireceiver, conn, ipAddress)

	def get_phone_number_from_recvd_data(self, phone_data):
		logger.debug("get_phone_number_from_recvd_data %s", phone_data)
		if phone_data[-6:-2] != '0101':
			logger.error("Error in recvd phone data %r 0101 missing", phone_data)
		return phone_data[:-6]
				
	def _alireceiver(self, conn, ipAddress): # handle the messages on the given TCP connection.
		logger.debug("_alireceiver spawned")
		conn.setblocking(0)
		try:
			phone_data = ""
			while True:
				ready = select.select([conn], [], [], 1)
				if ready[0]:
					data = conn.recv(1)
					if data != '':
						phone_data = "%s%c" % (phone_data, data)
						if data == '\r':
							phone_number = self.get_phone_number_from_recvd_data(phone_data)
							logger.debug("recvd phone_number is %r", phone_number)
							self.send_ali_data(conn, phone_number, ipAddress)
							phone_data = ""
		except socket.error:
			logger.debug("_sipreceiver socket error")
			conn.close()
			del self._conn[ipAddress]

	'''
	def isConnected(self, ipAddress):
		if ipAddress in self._conn:
			return True;
		else:
			return False
	'''

	def send_ali_data(self, conn, phone_number, ipAddress):
		logger.debug("send_ali_data for phone_number %s", phone_number)
		formatted_phone = "(%s) %s-%s" % (phone_number[:3], phone_number[-7:-4], phone_number[-4:])
		#sample_ali = "112\r(415) 555-1212 WPH2 08/11 13:17\rUS CELLULAR 800-510-6091    \r      1285       P#515-319-4005\r   Quail Ave - 3S        \r                    \rCALLBK=(712)210-0213      01045\rIA 00070-2-011, FRANKLIN       \r                  TEL=USCC \r+042.657610 -093.273464      46\rPSAP= HAMPTON PD\rVerify PD\r\nVerify FD\r\nVerify EMS"
		if phone_number in sample_ali:
			#ali_result = "112\r%s WPH2 08/11 13:17\rUS CELLULAR 800-510-6091    \r      1285       P#515-319-4005\r   Quail Ave - 3S        \r                    \rCALLBK=(712)210-0213      01045\rIA 00070-2-011, FRANKLIN       \r                  TEL=USCC \r+042.657610 -093.273464      46\rPSAP= HAMPTON PD\rVerify PD\r\nVerify FD\r\nVerify EMS" % formatted_phone
			ali_result = sample_ali[phone_number] % formatted_phone
		else:
			logger.debug("no ali found")
			ali_result = "112\r%s NO RECORD FOUND" % formatted_phone

		try:
			data = '\x02'
			gevent.sleep(2)
			conn.send(data)
			gevent.sleep(2)
			
			logger.debug("send_ali_data %r, data %r", ipAddress, data)
			#conn.send(sample_ali)
			conn.send(ali_result)

			logger.debug("send_ali_data %r, data %r", ipAddress, ali_result)
			
			gevent.sleep(2)
			data = '\x03'
			conn.send(data)
			
			logger.debug("send_ali_data done")
		except socket.error:
			logger.debug("send_ali_data socket closed")
			del self._conn[ipAddress]
	
if __name__ == '__main__': # parse command line options, and set the high level properties
	parser = OptionParser() # TODO: add daemon mode
	parser.add_option('', '--port',   dest='port', default=11010, type='int', help='port to listen to for ringing sound connections')
	parser.add_option('', '--int-ip1',   dest='int_ip1', default="127.0.0.1", help='ip address to listen to')
	parser.add_option('', '--int-ip2',   dest='int_ip2', default="192.168.1.6", help='ip address to listen to')

	(options, args) = parser.parse_args()
	# handler = log.ColorizingStreamHandler(sys.stdout)
	#handler = logging.FileHandler("ali_simulator.log")
	handler = logging.StreamHandler()

	handler.setLevel(logging.DEBUG)
	handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)d %(name)s %(levelname)s - %(message)s', datefmt='%d-%m %H:%M:%S'))
	logging.getLogger().addHandler(handler)
	logger.setLevel(logging.DEBUG or logging.INFO)

	aliSimulator1 = AliSimulator(options.int_ip1, options.port)
	aliSimulator1.start()

	aliSimulator2 = AliSimulator(options.int_ip2, options.port)
	aliSimulator2.start()

	gevent.wait([aliSimulator1._gin, aliSimulator2._gin])
	'''	
	line = ""
	while line != "exit":
		gevent.select.select([sys.stdin], [], [])
		line = sys.stdin.readline()
		line = line.rstrip()
	'''

