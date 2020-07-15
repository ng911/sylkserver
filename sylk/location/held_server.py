import os
import time
import hashlib
try:
    import gevent
except ImportError:
    print 'Please install gevent and its dependencies and include them in your PYTHONPATH'; import sys; sys.exit(1)
from gevent import monkey, Greenlet, GreenletExit

monkey.patch_socket()

import simplexml
try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger("emergent-ng911")

class HTTPError(Exception):
    '''An exception type for HTTP response.

    The message contains code and reason, e.g., "404 Not Found"
    '''

    def __init__(self, message):
        self.message = message


class LISError(Exception):
    '''An exception type for LIS response.

    The code and message attributes are used in the string representation of this exception. The string representation is
    an XML <error/> element of HELD response.
    '''

    def __init__(self, code, message):
        self.code, self.message = code, message

    def __repr__(self):
        try:
            xml = simplexml.XML(
                '<error xmlns="urn:ietf:params:xml:ns:geopriv:held" code="%s"><message xml:lang="en">%s</message></error>' % (
                self.code, self.message))
            return xml.toprettyxml()
        except:
            log.exception("exception")


def handler(env, start_response):
    '''The HELD server handler function that handles the HTTP request for HELD query or location install.

    This is a WSGI compatible function used in such server.

    It handles the POST and GET request. The POST request to "/location" is used to install a location mapping whereas a POST or
    GET request to "/location/hash" is used to dereference. When installing the location mapping, the XML "locationRequest" element
    is used from the request body of POST. When using GET it assumes a "locationRequest" for non-exact geodetic and civic.

    When hash is present in the URL, the hash must be a 48-character long hex string which represents a 24-byte value. The first
    8 bytes are the long timestamp when the reference expires and the last 16 bytes are the MD5 hash protecting the timestamp
    and the remote IP address. The presence of timestamp allows us to clean up expired references just by looking at the file name
    instead of opening the file.

    For installing the mapping, it just puts the PIDF-LO in the file content. For HELD dereference request, it opens the file and
    uses the XML to respond depending on the request. For example as per appropriate standards (IETF RFCs) it handles the exact
    attribute, list of requested location types and honors the Accept header.
    '''
    try:
        my_secret, expiration = options.secret, options.expires
        method, path, remote = env['REQUEST_METHOD'], env['PATH_INFO'], env['REMOTE_ADDR']
        if not (method == 'POST' and path == '/location' or method in ('GET', 'POST') and re.match(
                r'/location/[0-9a-zA-Z]{48,48}$', path)):
            log.warning('invalid URI %r', path)
            raise HTTPError('404 Not Found')
        if not re.match(r'[a-zA-Z\.0-9_\-]+$', remote):
            log.warning('invalid remote IP %r', remote)
            raise HTTPError('403 Forbidden')
        reference = path[10:]
        if method == 'POST':
            body = env['wsgi.input'].read()
            log.debug('received\n%s' % (body,))
            try:
                xml = simplexml.XML(body)
            except:
                log.exception('parsing XML')
                raise LISError('xmlError', str(sys.exc_info()[1]))
            if xml.tag != 'locationRequest':
                log.error('the top-level tag is not locationRequest')
                raise LISError('unsupportedMessage', 'cannot determinate the request type')
        else:  # GET assumes following request
            xml = simplexml.XML(
                '<locationRequest xmlns="urn:ietf:params:xml:ns:geopriv:held"><locationType exact="false">geodetic civic</locationType></locationRequest>')

        if reference:  # this is for dereferencing, validate time and hash
            tm1, tm2, hash = int(reference[0:8], 16), int(reference[8:16], 16), reference[16:]
            tm = (tm1 << 32) + tm2
            newpath = os.readlink(os.path.join(options.root, reference))
            ignore, remote = os.path.split(newpath)  # get the target presence document
            if hash != hashlib.md5(str(tm) + my_secret + remote).hexdigest():
                log.warning('invalid hash %r != %r', hash,
                               hashlib.md5(str(tm) + 'my-secret-code' + remote).hexdigest())
                raise LISError('requestError', 'the location reference is forged')
            if time.time() > tm:  # reference has expired
                log.warning('time is expired %r > %r', time.time(), tm)
                raise LISError('requestError', 'the location reference has expired')
            if not os.path.exists(os.path.join(options.root, reference)):
                log.warning('file reference does not exists %r', reference)
                raise LISError('requestError', 'the location reference does not exist')

        presence = ''
        if os.path.exists(os.path.join(options.root, remote)):
            with open(os.path.join(options.root, remote), 'r') as fp:
                presence = fp.read()
        if not presence:
            log.warning('cannot read file %r', remote)
            raise LISError('locationUnknown', 'does not have location of this device')

        try:
            pidf = simplexml.XML(presence)
        except:
            log.exception('parsing XML for %r', remote)
            raise LISError('locationUnknown', 'cannot parse the presence document')
        # TODO: perform sanity checks for PIDF-LO
        try:
            location = pidf('tuple')('status')('geopriv')('location-info')[0]
            locations = dict([(node.tag, node) for node in location.elems])
            location.children[:] = []  # clear the children for response
        except:
            log.exception('reading pidf for %r', remote)
            raise LISError('locationUnknown', 'cannot read the PIDF document')

        try:
            location_types = xml('locationType').cdata.strip().split()
            is_exact = bool(xml('locationType')[0]._.exact)
        except:
            location_types, is_exact = ['geodetic', 'civic'], False
        log.debug('location_types=%r is_exact=%r', location_types, is_exact)

        if is_exact:
            for type in location_types:
                if type == 'geodetic' and 'Circle' not in locations and 'Point' not in locations or type == 'civic' and 'civicAddress' not in locations:
                    log.warning('type not found in location, %r not in %r', type, locations.keys())
                    raise LISError('cannotProvideLiType', 'cannot provide the requested type')
        else:
            location_types += [x for x in ('geodetic', 'civic', 'locationURI') if x not in location_types]

        if is_exact and reference and 'locationURI' in location_types:
            raise LISError('cannotProvideLiType', 'cannot provide location reference for an existing reference')

        if not is_exact and reference:  # for reference cannot return another locationURI
            location_types.remove('locationURI')

        # TODO: make sure there are no repeatition in locations

        locationUriSet = simplexml.XML('<locationUriSet xmlns="urn:ietf:params:xml:ns:geopriv:held"/>')

        for type in location_types:
            if type == 'geodetic' and 'Circle' in locations:
                location.children += locations['Circle']
            elif type == 'geodetic' and 'Point' in locations:
                location.children += locations['Point']
            elif type == 'civic' and 'civicAddress' in locations:
                location.children += locations['civicAddress']
            elif type == 'locationURI':
                tm = int(time.time() + expiration)
                tm1, tm2 = (tm >> 32) & 0x7fffffff, tm & 0xffffffff
                hash = hashlib.md5(str(tm) + my_secret + remote).hexdigest()
                new_reference = '%08x%08x' % (tm1, tm2) + hash
                log.info('creating new reference %r=>%r', new_reference, remote)
                if not os.path.exists(os.path.join(options.root, new_reference)):
                    os.symlink(remote, os.path.join(options.root, new_reference))
                if options.tls_port:
                    locationUriSet.children += simplexml.XML('<locationURI>https://%s:%s/location/%s</locationURI>' % (
                    options.ext_ip, options.tls_port, new_reference))
                if options.port:
                    locationUriSet.children += simplexml.XML('<locationURI>http://%s:%s/location/%s</locationURI>' % (
                    options.ext_ip, options.port, new_reference))

        if 'HTTP_ACCEPT' in env:
            accept_types = []
            for type in env['HTTP_ACCEPT'].split(','):
                if type.strip():
                    if type.strip().lower() not in accept_types:
                        accept_types.append(type.strip().lower())
        else:
            accept_types = ['application/held+xml']
        if 'application/held+xml' not in accept_types:
            accept_types.append('appication/held+xml')
        log.debug('accept-types %r', accept_types)
        response = simplexml.XML('<locationResponse xmlns="urn:ietf:params:xml:ns:geopriv:held"/>')
        if location_types[0] == 'locationURI':  # put locationURI before presence
            if len(locationUriSet.children):
                response.children += locationUriSet
            if len(location.children):
                response.children += pidf
        else:
            if len(location.children):
                response.children += pidf
            if len(locationUriSet.children):
                response.children += locationUriSet

        if accept_types and accept_types[0] == 'application/pidf+xml' and len(
                locationUriSet.children) == 0:  # return as pidf
            response = pidf
            start_response('200 OK', [('Content-Type', 'application/pidf+xml')])
        else:  # return as held
            start_response('200 OK', [('Content-Type', 'application/held+xml')])
        response = response.toprettyxml()
        log.debug('responding with XML\n%s', response)
        return [response]

    except LISError, e:
        log.error('error handling %s %s: %s %s', method, path, e.code, e.message)
        start_response('200 OK', [('Content-Type', 'application/held+xml')])
        log.debug('responding\n%r', e)
        return [repr(e)]
    except HTTPError, e:
        log.error('error handling %s %s: %s', method, path, e.message)
        start_response(e.message, [])
        return []
    except:
        log.exception('error handling %s %s', method, path)
        start_response('500 Internal Server Error', [])
        return []


def cleanup_thread():
    '''Periodically cleanup the expired locations that were installed in this HELD server.

    It uses these attributes from options -- expires, root.
    Please see the command line options description for details on these attributes.

    Periodically, this task iterates through all the paths in the location root directory and if the path is a reference and
    is expired then it removes the path. The path for HELD references is a 24 byte value in hex hence the length of 48 characters.
    The first 8 bytes out of 24 is the long timestamp when the reference expires.
    '''
    while True:
        gevent.sleep((options.expires / 2) if options.expires > 0 else 1800)
        for reference in os.listdir(options.root):
            path = os.path.join(options.root, reference)
            if len(reference) == 48 and os.path.islink(path):
                tm1, tm2, hash = int(reference[0:8], 16), int(reference[8:16], 16), reference[16:]
                tm = (tm1 << 32) + tm2
                if time.time() > tm:  # reference has expired
                    log.info('removing expired reference %r', reference)
                    os.unlink(path)


def start_server(options):
    '''Start the HELD server.

    Depending on the options it starts the TCP and/or TLS web servers, and creates the top level directory for storing locations.

    @param options: there attributes are used -- root, int_ip, port, tls_port, server_key, server_cert.
    Please see the command line options description for details on these attributes.
    '''
    from gevent import pywsgi
    if options.root and not os.path.exists(options.root):
        log.info('creating top-dir %s', options.root)
        os.makedirs(options.root)
    if options.port:
        server = pywsgi.WSGIServer((options.int_ip, options.port), handler)
        log.info('starting HTTP server on %s:%d', options.int_ip, options.port)
        gevent.spawn(server.serve_forever)
    if options.tls_port:
        secure_server = pywsgi.WSGIServer((options.int_ip, options.tls_port), handler, keyfile=options.server_key,
                                          certfile=options.server_cert)
        log.info('starting HTTPS server on %s:%d', options.int_ip, options.tls_port)
        gevent.spawn(secure_server.serve_forever)
    gevent.spawn(cleanup_thread)


if __name__ == '__main__':
    try:
        # if this is an HELD client, invoke the HELD query and print the XML result.
        if options.held_url:
            response = held_client(options)
            if response:
                print response.toprettyxml()
        # if this is a LoST client, invoke the LoST query and print the list of services and source elements.
        elif options.lost_url:
            response = lost_client(options)
            if response and response.tag == 'listServicesResponse':
                try:
                    print 'services: ', ', '.join(response('serviceList').cdata.split())
                except:
                    pass
                try:
                    print 'source: ', response('path')('via')[0].source
                except:
                    pass
        # if this is not a HELD or LoST client then this is a server for HELD.
        else:
            start_server(options)
            while True: gevent.sleep(10)
    except KeyboardInterrupt:
        print ''  # to print a new line after ^C
