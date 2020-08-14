import datetime, logging, traceback
from collections import namedtuple

import arrow
import bson
import bcrypt
import six
from pymongo import ReadPreference
from mongoengine import *
from mongoengine import signals

# from werkzeug.security import generate_password_hash, check_password_hash
from ..config import MONGODB_DB, MONGODB_HOST, MONGODB_PASSWORD, MONGODB_USERNAME, MONGODB_REPLICASET, \
    CREATE_DB
log = logging.getLogger("emergent-ng911")




def create_calltaker(username, password, fullname, queue_id, psap_id):
    utcnow = datetime.datetime.utcnow()
    user = User()
    user.username = username
    user.fullname = fullname
    user.password_hash = User.generate_password_hash(password)
    user.created_at = utcnow
    user.psap_id = psap_id
    user.roles=['calltaker']
    user.save()

    queueMember = QueueMember()
    queueMember.psap_id = psap_id
    queueMember.queue_id = queue_id
    queueMember.user_id = user.user_id
    queueMember.save()


def add_speed_dial(name, group, number, psap_id):
    speedDialObj =  SpeedDial()
    speedDialObj.psap_id = psap_id
    speedDialObj.name = name
    if group != "":
        speedDialObj.group = group
    speedDialObj.dest = number
    speedDialObj.save()


def add_call_transfer_line(type, name, star_code, psap_id):
    lineObj = CallTransferLine()
    lineObj.psap_id = psap_id
    lineObj.type = type
    lineObj.name = name
    lineObj.star_code = star_code
    lineObj.save()


def create_test_data(ip_address="192.168.1.3", asterisk_ip_address="192.168.1.3", asterisk_port=5090):
    #ip_address = "192.168.1.3"
    #asterisk_ip_address = ip_address
    #asterisk_port = "5090"
    '''
    psap1_obj = Psap()
    psap1_obj.name = "Royal Thai EMS"
    psap1_obj.domain = "royalthai-ems-nga911.psapcloud.com"
    psap1_obj.save()
    royal_ems_psap_id = str(psap1_obj.psap_id)
    print("created Royal Thai EMS psap %r", royal_ems_psap_id)

    psap2_obj = Psap()
    psap2_obj.name = "Royal Thai Police"
    psap2_obj.domain = "royalthai-police-nga911.psapcloud.com"
    psap2_obj.save()
    royal_police_psap_id = str(psap2_obj.psap_id)
    print("created Royal Thai police psap %r", royal_police_psap_id)

    psap3_obj = Psap()
    psap3_obj.name = "Royal Thai Fire"
    psap3_obj.domain = "royalthai-fire-nga911.psapcloud.com"
    psap3_obj.save()
    royal_fire_psap_id = str(psap3_obj.psap_id)
    print("created Royal Thai fire psap %r", royal_fire_psap_id)

    psap4_obj = Psap()
    psap4_obj.name = "Bangkok EMS"
    psap4_obj.domain = "bangkok-ems-nga911.psapcloud.com"
    psap4_obj.save()
    bangkok_ems_psap_id = str(psap4_obj.psap_id)
    print("created Bangkok EMS psap %r", bangkok_ems_psap_id)

    psap5_obj = Psap()
    psap5_obj.name = "Bangkok Police"
    psap5_obj.domain = "bangkok-police-nga911.psapcloud.com"
    psap5_obj.save()
    bangkok_police_psap_id = str(psap5_obj.psap_id)
    print("created Bangkok police psap %r", bangkok_police_psap_id)

    psap6_obj = Psap()
    psap6_obj.name = "Bangkok Fire"
    psap6_obj.domain = "bangkok-fire-nga911.psapcloud.com"
    psap6_obj.save()
    bangkok_fire_psap_id = str(psap6_obj.psap_id)
    print("created Bangkok fire psap %r", bangkok_fire_psap_id)
    '''
    royal_ems_psap_id = "5f34e216db4262909b028e1f"
    royal_police_psap_id = "5f34e218db4262909b028e21"
    royal_fire_psap_id = "5f34e219db4262909b028e23"

    bangkok_ems_psap_id = "5f34e21adb4262909b028e25"
    bangkok_police_psap_id = "5f34e21bdb4262909b028e27"
    bangkok_fire_psap_id = "5f34e21cdb4262909b028e29"

    # create call takers and add to queue
    User.add_user_psap("tarun-rt-ems", "tarun2020", royal_ems_psap_id)
    User.add_user_psap("don-rt-ems", "don2020", royal_ems_psap_id)
    User.add_user_psap("mark-rt-ems", "mark2020", royal_ems_psap_id)
    User.add_user_psap("candace-rt-ems", "candace2020", royal_ems_psap_id)
    print ("Add users for rt ems")

    User.add_user_psap("tarun-rt-police", "tarun2020", royal_police_psap_id)
    User.add_user_psap("don-rt-police", "don2020", royal_police_psap_id)
    User.add_user_psap("mark-rt-police", "mark2020", royal_police_psap_id)
    User.add_user_psap("candace-rt-police", "candace2020", royal_police_psap_id)
    print ("Add users for rt police")

    User.add_user_psap("tarun-rt-fire", "tarun2020", royal_fire_psap_id)
    User.add_user_psap("don-rt-fire", "don2020", royal_fire_psap_id)
    User.add_user_psap("mark-rt-fire", "mark2020", royal_fire_psap_id)
    User.add_user_psap("candace-rt-fire", "candace2020", royal_fire_psap_id)
    print ("Add users for rt fire")

    # create call takers and add to queue
    User.add_user_psap("tarun-bk-ems", "tarun2020", bangkok_ems_psap_id)
    User.add_user_psap("don-bk-ems", "don2020", bangkok_ems_psap_id)
    User.add_user_psap("mark-bk-ems", "mark2020", bangkok_ems_psap_id)
    User.add_user_psap("candace-bk-ems", "candace2020", bangkok_ems_psap_id)
    print ("Add users for bk ems")

    User.add_user_psap("tarun-bk-police", "tarun2020", bangkok_police_psap_id)
    User.add_user_psap("don-bk-police", "don2020", bangkok_police_psap_id)
    User.add_user_psap("mark-bk-police", "mark2020", bangkok_police_psap_id)
    User.add_user_psap("candace-bk-police", "candace2020", bangkok_police_psap_id)
    print ("Add users for bk police")

    User.add_user_psap("tarun-bk-fire", "tarun2020", bangkok_fire_psap_id)
    User.add_user_psap("don-bk-fire", "don2020", bangkok_fire_psap_id)
    User.add_user_psap("mark-bk-fire", "mark2020", bangkok_fire_psap_id)
    User.add_user_psap("candace-bk-fire", "candace2020", bangkok_fire_psap_id)
    print ("Add users for bk fire")


def remove_room(room_number):
    if room_number is not None:
        print ("deleting room number %r", room_number)
        Call.objects(room_number=room_number).delete()
        ConferenceEvent.objects(room_number=room_number).delete()
        ConferenceParticipant.objects(room_number=room_number).delete()
        Location.objects.get(room_number=room_number).delete()
        Conference.objects.get(room_number=room_number).delete()

def remove_call(room_number=None, status=None):
    if status is not None:
        for confDbObj in Conference.objects(room_number=room_number):
            room_number = confDbObj.room_number
            remove_room(room_number)
        return
    if room_number is not None:
        remove_room(room_number)



if CREATE_DB:
    if (Psap.objects().count() == 0):
        create_test_data()



