import socket, select
import sys
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
import uuid


'''
gevent is not being used here, replaced with twisted
try:
    import gevent
except ImportError:
    print 'Please install gevent and its dependencies and include them in your PYTHONPATH'; import sys; sys.exit(1)
from gevent import monkey, Greenlet, GreenletExit

monkey.patch_socket()
'''

import re
from sylk.applications import ApplicationLogger


if __name__ == '__main__':  # parse command line options, and set the high level properties
    import logging
    global log
    handler = logging.StreamHandler(stream=sys.stdout)

    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter('%(asctime)s.%(msecs)d %(name)s %(levelname)s - %(message)s', datefmt='%d-%m %H:%M:%S'))
    log = logging.getLogger()
    log.addHandler(handler)
    log.setLevel(logging.DEBUG or logging.INFO)
else:
    global log
    log = ApplicationLogger(__package__)

def make_string_divisible_by_8(string):
    sum = 0
    for a in string:
        sum = sum + int(a)
    add_number = 8 - (sum % 8)
    return "%s%d" % (string, add_number)


def read_char_data(sock):
    global query_finished
    timeout = 0
    while (timeout < 4):
        timeout = timeout + 1
        ready = select.select([sock], [], [], 1)
        if ready[0]:
            data = sock.recv(1)
            # print data
            return data

    return -1

def sleep(secs):
    d = defer.Deferred()
    reactor.callLater(secs, d.callback, None)
    return d

def parse_ali_30W_wireless(ali_result):
    if (ali_result == "") or (re.search("NO RECORD FOUND", ali_result) != None):
        return ("", "")
    lines = ali_result.splitlines(True)
    if (len(lines) < 8):
        return ("", "")

    state = ""
    customer_name = ""
    phone_number = ""
    latitude = ""
    longitude = ""
    radius = ""
    otcfield = ""
    company_id = ""
    psap_no = ""
    esn = ""
    city = ""
    postal = ""
    psap_name = ""
    class_of_service = ""
    pilot_no = ""
    company_id = ""
    location = ""
    callback = ""
    agenciesDisplay = ""

    # line 1
    parse_line = lines[1]
    phone_number = parse_line[0:14].strip()
    class_of_service = parse_line[15:19].strip()

    parse_line = lines[2]
    customer_name = parse_line.strip()

    parse_line = lines[3]
    # parse_line = parse_line.strip()
    house_no = parse_line[0:10].strip()
    house_sfx = parse_line[11:15].strip()
    pilot_no = parse_line[19:].strip()

    parse_line = lines[4]
    # parse_line = parse_line.strip()
    # print "parse_line is ", parse_line
    street_direction = parse_line[0:2].strip()
    street_name1 = parse_line[3:].strip()

    parse_line = lines[5]
    parse_line = parse_line.strip()
    street_name2 = parse_line

    parse_line = lines[6]
    # parse_line = parse_line.strip()
    if parse_line[:7] == "CALLBK=":
        npa = parse_line[8:11]
        nxx = parse_line[12:15]
        number = parse_line[16:20]
        callback = npa + nxx + number
    else:
        location = parse_line[:21].strip()
    psap_no = parse_line[22:25].strip()
    esn = parse_line[26:].strip()

    parse_line = lines[7]
    # parse_line = parse_line.strip()
    state = parse_line[0:2].strip()
    city = parse_line[3:].strip()

    parse_line = lines[8]
    # parse_line = parse_line.strip()
    otcfield = parse_line[0:15].strip()
    company_id = parse_line[22:].strip()

    parse_line = lines[9]
    # parse_line = parse_line.strip()
    latitude = parse_line[:11].strip()
    longitude = parse_line[12:23].strip()
    radius = parse_line[24:].strip()

    # parse_line = lines[10]
    # parse_line = parse_line.strip()
    ##psap_name = parse_line[5:].strip()
    # agenciesDisplay = parse_line

    i = 10
    while (i < len(lines)):
        parse_line = lines[i]
        parse_line = parse_line.strip()
        # psap_name = parse_line[5:].strip()
        agenciesDisplay = "%s, %s" % (agenciesDisplay, parse_line)
        i = i + 1

    fire_no = ""
    police_no = ""
    ems_no = ""

    # for line in lines[11:]:
    #	line = line.strip()
    #	if len(line) > 0:
    #		[name, value] = line.split('=')
    #		if name.lower() == 'fire':
    #			fire_no = value.strip()
    #		if name.lower() == 'police':
    #			police_no = value.strip()
    #		if name.lower() == 'ems':
    #			ems_no = value.strip()
    street = (street_name1 + ' ' if len(street_name1) > 0 else '') + street_name2

    housenum = house_no + house_sfx
    if street: street = ((street_direction + ' ') if len(street_direction) > 0 else '') + street
    streetaddr = ('' if len(housenum) == 0 else housenum + ' ') + street
    postal = streetaddr

    civic_address_data = {'state': state, 'name': customer_name, 'phone_number': phone_number,
                          'latitude': latitude, 'longitude': longitude, 'radius': radius,
                          'otcfield': otcfield, 'service_provider': company_id, 'psap_no': psap_no, 'esn': esn,
                          'community': city, 'postal': postal, 'psap_name': psap_name,
                          'class_of_service': class_of_service,
                          'pilot_no': pilot_no, 'service_provider': company_id, 'location': location,
                          "callback": callback,
                          'fire_no': fire_no, 'ems_no': ems_no, 'police_no': police_no,
                          'agencies_display': agenciesDisplay}

    civic_address_xml = ""
    if len(customer_name) > 0: civic_address_xml = "<cl:NAME>%s</cl:NAME>" % (customer_name)
    if len(house_no) > 0: civic_address_xml = "%s<cl:HNO>%s</cl:HNO>" % (civic_address_xml, house_no)
    if len(house_sfx) > 0: civic_address_xml = "%s<cl:HNS>%s</cl:HNS>" % (civic_address_xml, house_sfx)
    if len(street_direction) > 0: civic_address_xml = "%s<cl:PRD>%s</cl:PRD>" % (civic_address_xml, street_direction)
    if len(state) > 0: civic_address_xml = "%s<cl:A1>%s</cl:A1>" % (civic_address_xml, state)
    if len(city) > 0: civic_address_xml = "%s<cl:A3>%s</cl:A3>" % (civic_address_xml, city)
    if len(street) > 0: civic_address_xml = "%s<cl:A6>%s</cl:A6>" % (civic_address_xml, street)
    if len(location) > 0: civic_address_xml = "%s<cl:LOC>%s</cl:LOC>" % (civic_address_xml, location)
    if len(
        longitude) > 0: civic_address_xml = "%s<cl:CIRCLE><cl:POS>%s %s</cl:POS><cl:RADIUS>%s</cl:RADIUS></cl:CIRCLE>" % (
    civic_address_xml, latitude, longitude, radius)

    civic_address_xml = "<cl:civicAddress xmlns:cl='urn:ietf:params:xml:ns:pidf:geopriv10:civicAddr'>%s</cl:civicAddress>" % (
    civic_address_xml)

    return (civic_address_data, civic_address_xml)


def parse_ali_30W_wireline(ali_result):
    if (ali_result == "") or (re.search("NO RECORD FOUND", ali_result) != None):
        return ("", "")
    state = ""
    customer_name = ""
    phone_number = ""
    latitude = ""
    longitude = ""
    radius = ""
    otcfield = ""
    company_id = ""
    psap_no = ""
    esn = ""
    city = ""
    postal = ""
    psap_name = ""
    class_of_service = ""
    pilot_no = ""
    company_id = ""
    location = ""
    callback = ""
    agenciesDisplay = ""

    lines = ali_result.splitlines(True)

    if (len(lines) < 8):
        return ("", "")

    # line 0 or first line is empty line
    # line 1
    parse_line = lines[1]
    phone_number = parse_line[0:14].strip()
    class_of_service = parse_line[15:19].strip()

    parse_line = lines[2]
    customer_name = parse_line.strip()

    parse_line = lines[3]
    # parse_line = parse_line.strip()
    house_no = parse_line[0:10].strip()
    house_sfx = parse_line[11:15].strip()
    pilot_no = parse_line[19:].strip()

    parse_line = lines[4]
    # parse_line = parse_line.strip()
    # print "parse_line is ", parse_line
    street_direction = parse_line[0:2].strip()
    street_name1 = parse_line[3:].strip()

    parse_line = lines[5]
    parse_line = parse_line.strip()
    street_name2 = parse_line

    parse_line = lines[6]
    # parse_line = parse_line.strip()
    location = parse_line[0:21].strip()
    # psap_no = parse_line[22:25].strip()
    esn = parse_line[26:].strip()

    parse_line = lines[7]
    # parse_line = parse_line.strip()
    state = parse_line[0:2].strip()
    city = parse_line[3:31].strip()

    parse_line = lines[8]
    parse_line = parse_line.strip()
    agenciesDisplay = parse_line
    # we will parse this later, when we have more details
    # parse_line = lines[8]
    # parse_line = parse_line.strip()
    ##otcfield = parse_line[0:15].strip()
    # company_id = parse_line[22:].strip()

    # parse_line = lines[10]
    # parse_line = parse_line.strip()
    # psap_name = parse_line[5:].strip()

    fire_no = ""
    police_no = ""
    ems_no = ""

    # for line in lines[11:]:
    #	line = line.strip()
    #	if len(line) > 0:
    #		[name, value] = line.split('=')
    #		if name.lower() == 'fire':
    #			fire_no = value.strip()
    #		if name.lower() == 'police':
    #			police_no = value.strip()
    #		if name.lower() == 'ems':
    #			ems_no = value.strip()
    street = (street_name1 + ' ' if len(street_name1) > 0 else '') + street_name2

    housenum = house_no + house_sfx
    if street: street = ((street_direction + ' ') if len(street_direction) > 0 else '') + street
    streetaddr = ('' if len(housenum) == 0 else housenum + ' ') + street
    postal = streetaddr

    civic_address_data = {'state': state, 'name': customer_name, 'phone_number': phone_number,
                          'latitude': latitude, 'longitude': longitude, 'radius': radius,
                          'otcfield': otcfield, 'service_provider': company_id, 'psap_no': psap_no, 'esn': esn,
                          'community': city, 'postal': postal, 'psap_name': psap_name,
                          'class_of_service': class_of_service,
                          'pilot_no': pilot_no, 'service_provider': company_id, 'location': location,
                          'fire_no': fire_no, 'ems_no': ems_no, 'police_no': police_no, "callback": callback,
                          "agencies_display": agenciesDisplay}

    civic_address_xml = ""
    if len(customer_name) > 0: civic_address_xml = "<cl:NAME>%s</cl:NAME>" % (customer_name)
    if len(house_no) > 0: civic_address_xml = "%s<cl:HNO>%s</cl:HNO>" % (civic_address_xml, house_no)
    if len(house_sfx) > 0: civic_address_xml = "%s<cl:HNS>%s</cl:HNS>" % (civic_address_xml, house_sfx)
    if len(street_direction) > 0: civic_address_xml = "%s<cl:PRD>%s</cl:PRD>" % (civic_address_xml, street_direction)
    if len(state) > 0: civic_address_xml = "%s<cl:A1>%s</cl:A1>" % (civic_address_xml, state)
    if len(city) > 0: civic_address_xml = "%s<cl:A3>%s</cl:A3>" % (civic_address_xml, city)
    if len(street) > 0: civic_address_xml = "%s<cl:A6>%s</cl:A6>" % (civic_address_xml, street)
    if len(location) > 0: civic_address_xml = "%s<cl:LOC>%s</cl:LOC>" % (civic_address_xml, location)
    if len(
        longitude) > 0: civic_address_xml = "%s<cl:CIRCLE><cl:POS>%s %s</cl:POS><cl:RADIUS>%s</cl:RADIUS></cl:CIRCLE>" % (
    civic_address_xml, latitude, longitude, radius)

    civic_address_xml = "<cl:civicAddress xmlns:cl='urn:ietf:params:xml:ns:pidf:geopriv10:civicAddr'>%s</cl:civicAddress>" % (
    civic_address_xml)

    return (civic_address_data, civic_address_xml)

from twisted.internet.protocol import Protocol, ReconnectingClientFactory

ali_parsers = { '30WWireless' : parse_ali_30W_wireless,
                '30WWireline' : parse_ali_30W_wireline}

'''
    This class uses Twisted 
'''

ali_factories = {
}

ali_requests = {}


class AliRequestTimeout(Exception):
    def __init__(self, room_number, reason):
        self.room_number = room_number
        self.reason = reason


class AliRequestProtocol(Protocol):
    def __init__(self, ali_format, ali_factory, pending_ali_requests):
        global ali_protocols
        self.is_connected = False
        self.start_char_recvd = False
        self.recvd_ali_data = ''
        self.pending_ali_requests = pending_ali_requests
        self.ali_format = ali_format
        self.ali_requests = {}
        self.ali_factory = ali_factory

    def send_ali_request(self, id, number, d):
        data_to_send = "%s0101" % number
        data_to_send = make_string_divisible_by_8(data_to_send)
        data_to_send = "%s\r" % data_to_send
        self.transport.write(data_to_send)
        log.info("AliRequestProtocol data_to_send %r", data_to_send)
        self.ali_requests[id] = (number, d)

    def connectionMade(self):
        log.info("inside AliRequestProtocol connectionMade")
        self.is_connected = True
        if len(self.pending_ali_requests) > 0:
            for id, ali_request in self.pending_ali_requests.copy().iteritems():
                (number, d) = ali_request
                self._send_ali_request(id, number, d)
                del self.pending_ali_requests[id]

    def process_ali_data(self, ali_data):
        log.info("process_ali_data %r", ali_data)
        # discard the first 3 characters (message_type, pos1 and pos2)
        ali_data = ali_data[3:]
        recvd_number = ali_data[0:15]
        # check which request this matches to
        i = 0
        d = None

        for (id, ali_request) in self.ali_requests.copy().iteritems():
            (number, d) = ali_request
            formatted_number = '\r' + '(' + number[0:3] + ") " + number[3:6] + "-" + number[6:]
            log.info("formatted_number %r, recvd_number %r", formatted_number, recvd_number)
            if formatted_number == recvd_number:
                ali_parser = ali_parsers[self.ali_format]
                if ali_parser is not None:
                    (ali_result, ali_result_civic_xml) = ali_parser(ali_data)
                    del self.ali_requests[id]
                    log.debug("ali result for number %r is %r", number, ali_result)
                    d.callback((self.ali_factory, id, number, self.ali_format, ali_result, ali_result_civic_xml, ali_data))
                else:
                    log.error("no parser found for format %r", self.ali_format)

    def cancel_ali_request(self, id):
        if id in self.pending_ali_requests:
            del self.pending_ali_requests[id]
        if id in self.ali_requests:
            del self.ali_requests[id]

    def dataReceived(self, data):
        log.info("dataReceived %r", data)
        i = 0
        for c in data:
            i = i + 1
            if not self.start_char_recvd:
                if c == '\x02':
                    self.start_char_recvd = True
            else:
                if c == '\x03':
                    self.process_ali_data(self.recvd_ali_data)
                    self.recvd_ali_data = ''
                    self.start_char_recvd = False
                else:
                    self.recvd_ali_data = "%s%c" % (self.recvd_ali_data, c)

class AliClientFactory(ReconnectingClientFactory):
    def __init__(self, ali_format):
        self.ali_format = ali_format
        self.connected = False
        self.protocol = None
        self.pending_ali_requests = []

    def startedConnecting(self, connector):
        log.info('AliClientFactory Started to connect.')

    def cancel_ali_request(self, id):
        if id in self.pending_ali_requests:
            del self.pending_ali_requests[id]
        if self.protocol is not None:
            self.protocol.cancel_ali_request(id)

    # returns a deferred
    def send_ali_request(self, id, number):
        log.info("AliRequestProtocol send_ali_request id %r, number %r", id, number)
        d = defer.Deferred()
        if not self.connected:
            self.pending_ali_requests[id] = (number, d)
        else:
            self.protocol.send_ali_request(id, number, d)
        return d

    def buildProtocol(self, addr):
        log.info('AliClientFactory buildProtocol.')
        log.info('AliClientFactory Resetting reconnection delay')
        self.connected = True
        self.protocol = AliRequestProtocol(self.ali_format, self, self.pending_ali_requests)
        self.resetDelay()
        self.pending_ali_requests = {}
        return self.protocol

    def clientConnectionLost(self, connector, reason):
        log.info('AliClientFactory Lost connection. Reason %r:', reason)
        self.connected = False
        self.protocol = None
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        log.info('AliClientFactory Connection failed. Reason: %r', reason)
        self.connected = False
        self.protocol = None
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

def init_ali_links(link_array):
    global ali_factories
    for link in link_array:
        (host, port, ali_format) = link
        log.info("init_ali_links host %r, port %r, ali_format %r", host, port, ali_format)
        ali_factory = AliClientFactory(ali_format)
        if ali_format not in ali_factories:
            ali_factories[ali_format] = []
        ali_factories[ali_format].append(ali_factory)
        reactor.connectTCP(host, port, ali_factory)

g_ali_requests = {}

def on_timeout(id):
    log.debug("ali request timedout for id %r", id)
    global g_ali_requests
    if id in g_ali_requests:
        (my_d, room_number, protocols, timer) = g_ali_requests[id]
        del g_ali_requests[id]
        for protocol in protocols:
            protocol.cancel_ali_request(id)
        my_d.errback(AliRequestTimeout(room_number, "request timedout"))

def process_ali_result(result):
    (factory, id, number, ali_format, ali_result, ali_result_civic_xml, ali_data) = result
    if id in g_ali_requests:
        (my_d, room_number, factories, timer) = g_ali_requests[id]
        del g_ali_requests[id]
        timer.cancel()

        for _factory in factories:
            if _factory != factory:
                factory.cancel_ali_request(id)
        my_d.callback((room_number, number, ali_format, ali_result, ali_result_civic_xml, ali_data))


def send_ali_request(room_number, number, ali_format):
    log.info("inside send_ali_request for room_number %r, number %r, ali_format %r", room_number, number, ali_format)
    my_d = defer.Deferred()
    id = str(uuid.uuid4())
    factories = ali_factories[ali_format]
    timer = reactor.callLater(20, on_timeout, id)
    g_ali_requests[id] = (my_d, room_number, factories, timer)
    log.info("facories length is %r", len(factories))
    for factory in factories:
        d = factory.send_ali_request(id, number)
        d.addCallback(process_ali_result)
    return my_d, id



def get_sample_ali_result():
    sample_ali = """
(415) 305-4541 WPH1z05/14 02:30
Cingular Wireless
123        3     P#415-555-1212
E  North Point Street          
Apt 403         
Cross Van Ness        112 9099
IA Franklin      
OTC1122           TEL=QWST
7190521     7190522     8900
PSAP=Franklin County
Police=4154554011

Fire=4154554012

EMS=4154554013
"""
    return sample_ali


def get_sample_ali_wireline_result():
    sample_ali = """

(641) 456-2187 RESD 05/30 09:44
DEIKE, STEVE                
1016             P#641-456-2187
NE 1ST ST                

                          00677
IA HAMPTON                     
HAMPTON PD                      HAMPTON FIRE DEPT               FRANKLIN GEN. AMB                                                                                                                                         
"""
    return sample_ali


def get_sample_ali_xml(phone_number):
    sampleXml = "<?xml version='1.0'?>  \
				<presence xmlns='urn:ietf:params:xml:ns:pidf' \
				xmlns:gp='urn:ietf:params:xml:ns:pidf:geopriv10' \
				xmlns:cl='urn:ietf:params:xml:ns:pidf:geopriv10:civicAddr' \
				entity='pres:%s\@emergent.com'>  \
					<tuple id='123456'>  \
						<status> \
							<gp:geopriv> \
								<gp:location-info> \
									<cl:civicAddress> \
										<cl:country>US</cl:country> \
										<cl:A1>NY</cl:A1>  \
										<cl:A3>Columbus</cl:A3> \
										<cl:RD>2424 14th Street</cl:RD> \
										<cl:HNO></cl:HNO> \
										<cl:NAM>Mike Tedder</cl:NAM> \
									</cl:civicAddress> \
								</gp:location-info> \
							</gp:geopriv>  \
						</status> \
					<timestamp>2012-07-17T12:00:00Z</timestamp> \
					</tuple> \
				</presence>" \
                % (phone_number,)

    return sampleXml


def get_sample_ali(phone_number):
    state = "CA"
    city = "San Francisco"
    road = "1545 Eddy Str"
    hno = '#405'
    name = 'Tarun Mehta'
    latitude = ''
    longitude = ''
    radius = ''
    community = ''
    postal = "94102"

    ali_result = {'state': state, 'city': city, 'road': road, 'hno': hno, 'name': name,
                  'latitude': latitude, 'longitude': longitude, 'radius': radius, 'community': community,
                  'postal': postal}
    return ali_result


def test_process_ali_error(exception):
    log.info("test_process_ali_error %r", exception)
    log.info("test_process_ali_error room_number %s, error %s", exception.room_number, exception.reason)

def test_process_ali_result(result):
    log.debug("test_process_ali_result %r", result)
    if result is not None:
        (room_number, number, ali_format, ali_result, ali_result_civic_xml, ali_data) = result
        log.info("got test_process_ali_result room_number %r, number %r, ali_result %r, ali_result_civic_xml %r, ali_data %r",
                 room_number, number, ali_result, ali_result_civic_xml, ali_data)


def test_send_ali_request(room_number, number, format):
    d = send_ali_request(room_number, number, format)
    def on_error(err):
        log.info("error in test_send_ali_request for room_number %r", room_number)
    d.addErrback(on_error)
    d.addCallback(test_process_ali_result)


def runTests():
    log.info("start running tests")
    ali_links = [("127.0.0.1", 11010, "30WWireless"), ("192.168.1.6", 11010, "30WWireless"), ]
    init_ali_links(ali_links)
    #send_ali_request(room_number='1100', number='4153055512', ali_format="30WWireless")
    reactor.callLater(5, test_send_ali_request, '1100', '4153055512', "30WWireless")

if __name__ == '__main__':  # parse command line options, and set the high level properties
    log.info("starting aliquery")
    reactor.callLater(0, runTests)
    log.info("starting reactor.run")
    reactor.run()
    log.info("all done")
