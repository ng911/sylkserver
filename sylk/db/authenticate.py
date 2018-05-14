'''
Authenticate a call
'''

import re
from schema import IncomingLink, Queue, User
from sylk.applications import ApplicationLogger

'''
Authenticate a call

Args:
    ip_address:
    port:
    from_uri:
    to_uri:

Returns:
    returns {
        success: true or false.
        queue_id,
        acd,
        ring_time
        backup_queue_id:
        backup_queue_ring_time
    }.

'''
log = ApplicationLogger(__package__)

def get_incoming_link(ip_address, port, called_number):
    # we first try to match ip address
    log.info("get_incoming_link ip_address %r, port %r, called_number %r", ip_address, port, called_number)
    found_ip_address = False
    for incoming_link in IncomingLink.objects(ip_address=ip_address):
        found_ip_address = True
        log.info("get_incoming_link found ip_address %r", ip_address)
        log.info("get_incoming_link port %r, called_number %r", incoming_link.port, incoming_link.called_no)
        if (incoming_link.port is None) and (incoming_link.called_no is None):
            log.info("get_incoming_link found link")
            return incoming_link

        if (incoming_link.port is not None) and (incoming_link.port != port):
            continue

        if (incoming_link.called_no is not None):
            if (not incoming_link.regex):
                if (incoming_link.called_no == called_number):
                    return incoming_link
            else:
                # we match by regex
                p = re.compile(incoming_link.called_no)
                if p.match(called_number) is not None:
                    return incoming_link

    if found_ip_address or (called_number is None) or (called_number == ''):
        log.info("get_incoming_link found ip address but not authenticated")
        return None

    for incoming_link in IncomingLink.objects(called_no__exists = True):
        if ('ip_address' in incoming_link) and (incoming_link.ip_address is not None) and (incoming_link.ip_address != '') :
            continue
        log.info("get_incoming_link check non ip incoming_link.regex %r, incoming_link.called_no %r", incoming_link.regex, incoming_link.called_no)
        if (not incoming_link.regex):
            if (incoming_link.called_no == called_number):
                return incoming_link
        else:
            # we match by regex
            p = re.compile(incoming_link.called_no)
            if p.match(called_number) is not None:
                return incoming_link

    return None


def get_calltaker_user(username):
    try:
        calltaker_obj = User.objects.get(username=username)
        return calltaker_obj
    except Exception as e:
        return None

def authenticate_call(ip_address, port, called_number, calling_uri, conf_rooms):
    incoming_link = get_incoming_link(ip_address, port, called_number)

    if incoming_link is None:
        return (False, None, None)

    if incoming_link.is_origination_calltaker():
        log.info("authenticate_call incoming link is calltaker gateway")
        log.info("authenticate_call user is %r", calling_uri.user)
        calltaker_obj = get_calltaker_user(calling_uri.user)
        if calltaker_obj is not None:
            log.info("authenticate_call found calltaker_obj %r", calltaker_obj)
            # we need to check if the calltaker tried to join a conference room
            if called_number in conf_rooms:
                log.info("authenticate_call send to sos_room")
                return (True, 'sos_room', calltaker_obj)
            else:
                log.info("authenticate_call send to outgoing")
                return (True, 'outgoing', calltaker_obj)

    if incoming_link.is_origination_sos():
        return (True, 'sos', incoming_link)

    if incoming_link.is_origination_admin():
        return (True, 'admin', incoming_link)

    return (False, None, None)

