import sys
import urllib3
import treq
#import simplexml
from xml.dom.minidom import parseString
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger("emergent-ng911")


def held_client_async(options):
    from application.notification import IObserver, NotificationCenter, NotificationData
    def on_response(response):
        log.info("inside held_client_async on_response %r", response)
        try:
            xml = parseString(response)
        except Exception as e:
            log.error("startConversation jsom parse error %r", str(e))
            return

    def process_response(response):
        log.info('process_response')
        treq.text_content(response).addCallback(on_response)

    missing = [attr for attr in 'held_url accept timeout response_time location_type exact'.split() if
               not hasattr(options, attr)]
    if missing: raise RuntimeError('missing options: %s' % (', '.join(missing),))

    headers = {}
    if options.accept:
        headers['Accept'] = options.accept
    if options.method == 'GET':
        d = treq.get(options.held_url,
                      headers=headers, timeout=options.timeout)
    else:
        headers['Content-Type'] = 'application/held+xml'
        xml = parseString('<locationRequest xmlns="urn:ietf:params:xml:ns:geopriv:held"/>')
        '''
        if options.response_time:
            xml._.responseTime = options.response_time
        if options.location_type:
            xml.children += simplexml.XML('<locationType/>')
            xml.children['locationType'][0].children += '\n    '.join(options.location_type)
            if options.exact:
                xml.children['locationType'][0]._.exact = options.exact
        if options.device:
            xml.children += simplexml.XML('<device xmlns="urn:ietf:params:xml:ns:geopriv:held:id"/>')
            tag, value = options.device.split(':', 1) if ':' in options.device else ('ip', options.device)
            xml.children['device'][0].children += simplexml.XML('<%s>%s</%s>' % (tag, value, tag))
        '''
        data = xml.toprettyxml()
        d = treq.post(options.held_url,
                  headers=headers, data=data, timeout=options.timeout)
    d.addCallback(process_response)

locationRequest = """ 
    <locationRequest xmlns="urn:ietf:params:xml:ns:geopriv:held">
        <locationType exact="true">
            any
            civic
            geodetic
            locationURI
        </locationType>
        <device xmlns="urn:ietf:params:xml:ns:geopriv:held:id">
            <uri>sip:7757535912@nv.nga911.com</uri>
        </device>
    </locationRequest>
"""

def held_client(options):
    '''Send GET or POST request to an HELD URI to retrieve the location data or dereference a location URI.

    This is the main function to do HELD dereference query or HELD client request.

    @param options: these attributes are used -- held_url, accept, timeout, response_time, location_type, exact.
    Please see the command line options description for details on these attributes.
    '''
    try:
        missing = [attr for attr in 'held_url accept timeout response_time location_type exact'.split() if
                   not hasattr(options, attr)]
        if missing: raise RuntimeError('missing options: %s' % (', '.join(missing),))
        http = urllib3.PoolManager()
        #req = urllib3.Request(options.held_url)
        held_url = options.held_url
        headers = {}
        if options.accept:
            headers['Accept'] = options.accept
        if options.method == 'GET':
            log.info("makeing http get to %s", held_url)
            r = http.request('GET', held_url, timeout=options.timeout, headers=headers)
        else:  # POST
            headers['Content-Type'] = 'application/held+xml'
            xml = parseString(locationRequest)
            #xml = parseString('<locationRequest xmlns="urn:ietf:params:xml:ns:geopriv:held"/>')
            '''
            if options.response_time:
                xml._.responseTime = options.response_time
            if options.location_type:
                xml.children += simplexml.XML('<locationType/>')
                xml.children['locationType'][0].children += '\n    '.join(options.location_type)
                if options.exact:
                    xml.children['locationType'][0]._.exact = options.exact
            if options.device:
                xml.children += simplexml.XML('<device xmlns="urn:ietf:params:xml:ns:geopriv:held:id"/>')
                tag, value = options.device.split(':', 1) if ':' in options.device else ('ip', options.device)
                xml.children['device'][0].children += simplexml.XML('<%s>%s</%s>' % (tag, value, tag))
            '''
            data = xml.toprettyxml()
            log.info('sending XML\n%s', data)
            log.info("makeing http post to %s", held_url)
            r = http.request('POST', held_url, timeout=options.timeout, headers=headers, body=data)
            #req.add_data(data)
            #f = urllib3.urlopen(req, timeout=options.timeout)
        response = r.data.decode('utf-8')
        log.info("response is %s", response)
        try:
            xml = parseString(response)
            return xml.toprettyxml()
        except:
            log.exception('cannot parse the received XML\n%s', response)
    except urllib3.exceptions.NewConnectionError:
        log.error('connecting to %r: %s', options.held_url, sys.exc_info()[1])
    except:
        log.exception('exception')
    return None

def test_pidf(geolocation_url):
    class Options(object):
        pass
    from .pidf_lo import xml2display
    opt = Options();
    opt.__dict__ = dict(held_url=geolocation_url, method='POST', accept='', timeout=5, response_time='', location_type=(),
                        exact='', device='')
    held = held_client(opt)
    if held:
        locref = \
            ([child.cdata for child in held('locationUriSet')('locationURI') if child.cdata.startswith('http:')] + [None])[
                0]
        if not locref: locref = \
            ([child.cdata for child in held('locationUriSet')('locationURI') if child.cdata.startswith('https:')] + [None])[
                0]
        log.debug('found loc ref %r', locref)
        pidf = held('presence')[0]
        postal, community, state, latitude, longitude, radius, name = xml2display(pidf)

def test_pidf_file():
    from .pidf_lo import xml2display
    filename = "test-pidf-lo.xml"
    file = open(filename, "r")
    pidf = file.read()
    print("pidf length is %d" % len(pidf))
    postal, community, state, latitude, longitude, radius, name = xml2display(pidf)
    print ("postal %s, community %s, state %s, latitude %r, longitude %r, radius %r, name %r" %
           (postal, community, state, latitude, longitude, radius, name))

