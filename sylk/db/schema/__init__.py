import logging
from ...config import MONGODB_DB, MONGODB_HOST, MONGODB_PASSWORD, MONGODB_USERNAME, MONGODB_REPLICASET, \
    CREATE_DB
from .utils import getIsoMaxFormat, getIsoFormat
from mongoengine import connect
from pymongo import ReadPreference

from .texting import ConferenceMessage, Greeting
from .conference import Call, Agency, Conference, ConferenceParticipant, ConferenceEvent
from .geo import GeoRouting
from .location import Location, AliServer
from .oauth import Client, Grant, Token
from .psap import Psap
from .queue import Queue, QueueMember
from .report import CallReport, AbandonedCallReport, AbandonedCallReportDetails, CompletedCallReportDetails
from .routing import VoicePrompt, IVR, IncomingLink, OutgoingLink, DialPlan, CallTransferLine
from .speed_dial import SpeedDialGroup, SpeedDial
from .texting import ConferenceMessage, Greeting
from .user import UserRole, UserPermission, UserGroup, User, CalltakerStation, CalltakerProfile, CalltakerActivity
from .admin_line import AdminLineGroup, AdminLine

log = logging.getLogger("emergent-ng911")


'''
client = connect(username="ws", password="Ecomm@911",
                 host='mongodb://localhost:33903/psap?replicaSet=rs-psap')
'''
#client = connect(host='mongodb://localhost:27107/ng911')
if len(MONGODB_REPLICASET) > 0:
    log.info("connect to mongodb user %r, db %s, connections %r", MONGODB_USERNAME, MONGODB_DB, MONGODB_HOST)
    connect(MONGODB_DB, username=MONGODB_USERNAME, password=MONGODB_PASSWORD, host=MONGODB_HOST,
            replicaSet=MONGODB_REPLICASET, read_preference=ReadPreference.SECONDARY_PREFERRED)
else:
#    log.info("connect to mongodb db name %r, connections %r", MONGODB_DB, MONGODB_HOST)
#    connect(MONGODB_DB, host=MONGODB_HOST, username=MONGODB_USERNAME, password=MONGODB_PASSWORD)
    log.info("connect to mongodb")
    #connect("ng911", host="localhost")
    connect(MONGODB_DB, username=MONGODB_USERNAME, password=MONGODB_PASSWORD, host=MONGODB_HOST)


#connect('ng911')
#db = client.ng911
#db.authenticate("ws", "Ecomm@911")

__all__ = [
    'getIsoMaxFormat', 'getIsoFormat',
    'ConferenceMessage', 'Greeting',
    'Call', 'Agency', 'Conference', 'ConferenceParticipant', 'ConferenceEvent',
    'GeoRouting',
    'Location', 'AliServer',
    'Client', 'Grant', 'Token',
    'Psap',
    'Queue', 'QueueMember',
    'CallReport', 'AbandonedCallReport', 'AbandonedCallReportDetails', 'CompletedCallReportDetails',
    'VoicePrompt', 'IVR', 'IncomingLink', 'OutgoingLink', 'DialPlan', 'CallTransferLine',
    'SpeedDialGroup', 'SpeedDial',
    'ConferenceMessage', 'Greeting',
    'UserRole', 'UserGroup', 'User', 'UserPermission',
    'CalltakerStation', 'CalltakerProfile', 'CalltakerActivity',
    'AdminLineGroup', 'AdminLine'
]

