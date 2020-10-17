import traceback
from mongoengine import DoesNotExist
from .schema import User, Psap, CalltakerProfile, Queue, QueueMember

try:
    from sylk.applications import ApplicationLogger
    log = ApplicationLogger(__package__)
except:
    import logging
    log = logging.getLogger("emergent-ng911")


def add_update_calltaker(payload, user_id):
    create_kamailio_user = False
    if user_id == None:
        create_kamailio_user = True
        userObj = User()
        psap_id = payload['psap_id']
        userObj.psap_id = psap_id
    else:
        userObj = User.objects.get(user_id=user_id)
        psap_id = userObj.psap_id
    log.info("payload is %r", payload)
    if payload['username'] != None:
        userObj.username = payload['username']
    if payload['fullname'] != None:
        userObj.fullname = payload['fullname']
    if payload['password'] != None:
        password = payload['password']
        userObj.password_hash = User.generate_password_hash(password)
    if payload['extension'] != None:
        userObj.extension = payload['extension']
    if (payload['role'] != None) and (payload['role'] != ""):
        log.info("userObj.roles setting to %r", payload['role'])
        userObj.roles = [payload['role']]
    log.info("userObj.roles is %r", userObj.roles)
    userObj.save()
    username = userObj.username
    if user_id == None:
        user_id = str(userObj.user_id)
    try:
        userProfile = CalltakerProfile.objects.get(user_id=user_id)
        if (payload['auto_respond'] != None) or (payload['auto_respond_after'] != None):
            if payload['auto_respond'] != None:
                userObj.auto_respond = payload['auto_respond']
            if payload['auto_respond_after'] != None:
                userObj.auto_respond_after = payload['auto_respond_after']
            userProfile.save()
    except DoesNotExist as e:
        log.info("CalltakerProfile does not exist for user_id %r, creating", user_id)
        log.info("psap_id is %r", psap_id)
        psapObj = Psap.objects.get(psap_id=psap_id)
        log.info("got psapObj")
        default_profile_id = psapObj.default_profile_id
        log.info("got psapObj default_profile_id is %r", default_profile_id)
        log.info("got psapObj got defaultProfile")
        userProfile = CalltakerProfile()
        userProfile.psap_id = userObj.psap_id
        if default_profile_id != None:
            log.info("got psapObj got defaultProfile process")
            defaultProfile = CalltakerProfile.objects.get(profile_id=default_profile_id)
            userProfile.incoming_ring = defaultProfile.incoming_ring
            userProfile.ringing_server_volume = defaultProfile.ringing_server_volume
            userProfile.incoming_ring_level = defaultProfile.incoming_ring_level
            userProfile.ring_delay = defaultProfile.ring_delay
            userProfile.auto_respond = defaultProfile.auto_respond
            userProfile.auto_respond_after = defaultProfile.auto_respond_after

        log.info("got psapObj got defaultProfile 1")
        if payload['auto_respond'] != None:
            userObj.auto_respond = payload['auto_respond']

        if payload['auto_respond_after'] != None:
            userObj.auto_respond_after = payload['auto_respond_after']

        log.info("got psapObj got defaultProfile 2")
        userProfile.save()
        log.info("got psapObj got defaultProfile 3")

    if ('queues' in payload) and (payload['queues'] != None):
        log.info("got queues")
        queues = payload['queues']

        for queue_id in queues:
            # make sure the queue still exists
            Queue.objects.get(queue_id=queue_id)
            try:
                QueueMember.objects.get(queue_id=queue_id, user_id=user_id)
            except:
                queueMember = QueueMember(user_id=user_id, queue_id= queue_id, psap_id=psap_id)
                queueMember.save()

    if create_kamailio_user:
        from .schema_sqlalchemy import add_kamailio_user
        sip_reg_domain = f"reg.{domain_name}"
        add_kamailio_user(username, sip_reg_domain)
    log.info("got queues done user_id is %r", user_id)
    return {
        'user_id' : user_id
    }

def update_calltaker_status(status, username=None, user_id=None):
    try:
        log.info("inside update_calltaker_status status %r, username %r, user_id %r", status, username, user_id)
        if username != None:
            calltaker_obj = User.objects.get(username=username)
        elif user_id != None:
            calltaker_obj = User.objects.get(user_id=user_id)
        else:
            log.error("error calling update_calltaker_status no username or user_id")
            return
        calltaker_obj.status = status
        calltaker_obj.save()
    except Exception as e:
        stacktrace = traceback.format_exc()
        log.error("error in update_calltaker_status %s", e.message)
        log.error(stacktrace)


def inactivate_calltaker(user_id):
    userObj = User.objects.get(user_id=user_id)
    userObj.is_active = False
    userObj.save()


def get_available_calltakers(psap_id):
    calltakers = []
    user_ids = []
    for userObj in User.objects(psap_id=psap_id, is_active=True, status='available'):
        calltakers.append(str(userObj.username))
        user_ids.append(str(userObj.user_id))
    log.info("get_all_calltakers psap_id %r, calltakers %r, user_ids %r", psap_id, calltakers, user_ids)
    return calltakers, user_ids

# make all calltakers offline
def reset_calltakers_status(psap_id):
    log.info("reset_calltakers_status for psap_id %r", psap_id)
    for userObj in User.objects(psap_id=psap_id):
        userObj.status = "offline"
        userObj.is_available = False
        userObj.save()

def get_user_id(username, psap_id):
    userObj = User.objects(psap_id=psap_id, username=username)
    return str(userObj.user_id)

