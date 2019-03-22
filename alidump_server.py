import sys
import datetime

try:
    import gevent
except ImportError:
    print 'Please install gevent and its dependencies and include them in your PYTHONPATH'; import sys; sys.exit(1)
from gevent import monkey, Greenlet, GreenletExit

monkey.patch_all()
import gevent.select
import logging
from optparse import OptionParser, OptionGroup
import socket, select

logger = logging.getLogger('psap')


class AliDumpServerSimulator:
    def __init__(self, ipAddress, port):
        self.sock, self._gin, self._conn = None, None, {}
        self.port = port
        self.ipAddress = ipAddress
        self.ali_started = False
        self.rawAli = ''

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

    def _alireceiver(self, conn, ipAddress):  # handle the messages on the given TCP connection.
        logger.debug("_alireceiver spawned")
        conn.setblocking(0)
        try:
            phone_data = ""
            while True:
                ready = select.select([conn], [], [], 1)
                if ready[0]:
                    data = conn.recv(1)
                    if data != '':
                        if self.ali_started:
                            phone_data = "%s%c" % (phone_data, data)
                            if data == '\x03':
                                self.ali_started = False
                                self.dumpAliData(self.rawAli)
                                self.rawAli = ''
                            else:
                                self.rawAli = '%s%c' % (self.rawAli, data)
                        elif data == '\x02':
                            self.ali_started = True
                            self.rawAli = ''
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

    def dumpAliData(self, rawAli):
        # append this ali data to a file marked by the time the ali data was received
        file = open('/var/www/html/alidump.txt', 'ab')
        curTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file.write("ali dumo received on %s" % curTime)
        file.write("\n----------------------------------------------\n")
        file.write(rawAli)
        file.write("\n\n")
        file.close()

if __name__ == '__main__':  # parse command line options, and set the high level properties
    parser = OptionParser()  # TODO: add daemon mode
    parser.add_option('', '--port', dest='port', default=11060, type='int',
                      help='port to listen to for ringing sound connections')
    parser.add_option('', '--int-ip1', dest='int_ip1', default="127.0.0.1", help='ip address to listen to')
    parser.add_option('', '--int-ip2', dest='int_ip2', default="159.65.73.31", help='ip address to listen to')

    (options, args) = parser.parse_args()
    # handler = log.ColorizingStreamHandler(sys.stdout)
    # handler = logging.FileHandler("ali_simulator.log")
    handler = logging.StreamHandler()

    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter('%(asctime)s.%(msecs)d %(name)s %(levelname)s - %(message)s', datefmt='%d-%m %H:%M:%S'))
    logging.getLogger().addHandler(handler)
    logger.setLevel(logging.DEBUG or logging.INFO)

    aliDumpServerSimulator1 = AliDumpServerSimulator(options.int_ip1, options.port)
    aliDumpServerSimulator1.start()
    '''
    aliSimulator2 = AliSimulator(options.int_ip2, options.port)
    aliSimulator2.start()

    gevent.wait([aliSimulator1._gin, aliSimulator2._gin])
    '''
    gevent.wait([aliDumpServerSimulator1._gin, ])
    '''	
    line = ""
    while line != "exit":
        gevent.select.select([sys.stdin], [], [])
        line = sys.stdin.readline()
        line = line.rstrip()
    '''

