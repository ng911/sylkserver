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

def get_incoming_link(ip_address, port, called_number, calling_number):
    # we first try to match ip address
    log.info("get_incoming_link ip_address %r, port %r, called_number %r", ip_address, port, called_number)
    found_ip_address = False

    # first try to validate with port
    for incoming_link in IncomingLink.objects(ip_address=ip_address, port=port):
        found_ip_address = True
        log.info("get_incoming_link found ip_address %r", ip_address)
        log.info("get_incoming_link port %r, called_number %r", incoming_link.port, incoming_link.called_no)
        if incoming_link.called_no is None:
            log.info("get_incoming_link found link")
            return incoming_link

        called_number_to_check = called_number
        if hasattr(incoming_link, "use_called_number_for_ani") and incoming_link.use_called_number_for_ani:
            called_number_to_check = calling_number

        if (incoming_link.called_no is not None):
            if (not incoming_link.regex):
                if (incoming_link.called_no == called_number_to_check):
                    return incoming_link
            else:
                # we match by regex
                p = re.compile(incoming_link.called_no)
                if p.match(called_number_to_check) is not None:
                    return incoming_link

    for incoming_link in IncomingLink.objects(ip_address=ip_address):
        found_ip_address = True
        log.info("get_incoming_link found ip_address %r", ip_address)
        log.info("get_incoming_link port %r, called_number %r", incoming_link.port, incoming_link.called_no)
        if incoming_link.port is not None:
            continue

        if (incoming_link.port is None) and (incoming_link.called_no is None):
            log.info("get_incoming_link found link")
            return incoming_link

        if (incoming_link.port is not None) and (incoming_link.port != port):
            continue

        called_number_to_check = called_number
        if hasattr(incoming_link, "use_called_number_for_ani") and incoming_link.use_called_number_for_ani:
            called_number_to_check = calling_number

        if (incoming_link.called_no is not None):
            if (not incoming_link.regex):
                if (incoming_link.called_no == called_number_to_check):
                    return incoming_link
            else:
                # we match by regex
                p = re.compile(incoming_link.called_no)
                if p.match(called_number_to_check) is not None:
                    return incoming_link

    if found_ip_address or (called_number is None) or (called_number == ''):
        log.info("get_incoming_link found ip address but not authenticated")
        return None

    for incoming_link in IncomingLink.objects(called_no__exists = True):
        if ('ip_address' in incoming_link) and (incoming_link.ip_address is not None) and (incoming_link.ip_address != '') :
            continue
        log.info("get_incoming_link check non ip incoming_link.regex %r, incoming_link.called_no %r", incoming_link.regex, incoming_link.called_no)
        called_number_to_check = called_number
        if hasattr(incoming_link, "use_called_number_for_ani") and incoming_link.use_called_number_for_ani:
            called_number_to_check = calling_number
        if (not incoming_link.regex):
            if (incoming_link.called_no == called_number_to_check):
                return incoming_link
        else:
            # we match by regex
            p = re.compile(incoming_link.called_no)
            if p.match(called_number_to_check) is not None:
                return incoming_link

    return None


def get_calltaker_user(username):
    try:
        calltaker_obj = User.objects.get(username=username)
        return calltaker_obj
    except Exception as e:
        return None

def authenticate_call(ip_address, port, called_number, calling_uri, conf_rooms):
    incoming_link = get_incoming_link(ip_address, port, called_number, calling_uri.user)

    # we may need to transform the called and calling numbers based on link rules (remove prefix, suffix, switch etc.)
    to_number = called_number
    ani = calling_uri.user
    if incoming_link is None:
        return (False, None, None, None, ani, to_number)

    if hasattr(incoming_link, "use_called_number_for_ani") and incoming_link.use_called_number_for_ani:
        ani = called_number
        to_number = calling_uri.user

    if hasattr(incoming_link, "strip_ani_prefix") and (incoming_link.strip_ani_prefix > 0):
        ani = ani[incoming_link.strip_ani_prefix:]

    if hasattr(incoming_link, "strip_ani_suffix") and (incoming_link.strip_ani_suffix > 0):
        ani = ani[0: -incoming_link.strip_ani_suffix]

    if hasattr(incoming_link, "strip_from_prefix") and (incoming_link.strip_from_prefix > 0):
        to_number = to_number[incoming_link.strip_from_prefix:]

    if hasattr(incoming_link, "strip_from_suffix") and (incoming_link.strip_from_suffix > 0):
        to_number = to_number[0: -incoming_link.strip_from_suffix]

    if incoming_link.is_origination_calltaker():
        log.info("authenticate_call incoming link is calltaker gateway")
        log.info("authenticate_call user is %r", calling_uri.user)
        calltaker_obj = get_calltaker_user(calling_uri.user)
        if calltaker_obj is not None:
            log.info("authenticate_call found calltaker_obj %r", calltaker_obj)
            # we need to check if the calltaker tried to join a conference room
            if called_number in conf_rooms:
                log.info("authenticate_call send to sos_room")
                return (True, 'sos_room', incoming_link, calltaker_obj, to_number, ani)
            elif get_calltaker_user(called_number) is not None:
                log.info("authenticate_call send to outgoing calltaker")
                return (True, 'outgoing_calltaker', incoming_link, calltaker_obj, to_number, ani)
            else:
                log.info("authenticate_call send to outgoing number")
                return (True, 'outgoing', incoming_link, calltaker_obj, to_number, ani)

    if incoming_link.is_origination_sos():
        return (True, 'sos', incoming_link, None, to_number, ani)

    if incoming_link.is_origination_admin():
        return (True, 'admin', incoming_link, None, to_number, ani)

    return (False, None, None, None, to_number, ani)

