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
log = logging.getLogger("emergent-ng911")


class CallReport(Document):
    report_id = ObjectIdField(required=True, default=bson.ObjectId)
    type = StringField(required=True, choices=('completed', 'abandoned'), default='completed')
    psap_id = ObjectIdField(required=True)
    report_name = StringField()
    start_time = ComplexDateTimeField()
    end_time = ComplexDateTimeField()
    pdf_file = StringField()
    csv_file = StringField()
    meta = {
        'indexes': [
            'report_id',
            'psap_id',
            'type',
            'report_name',
            'start_time',
            'end_time'
        ]
    }


class CompletedCallReportDetails(Document):
    report_id = ObjectIdField(required=True)
    psap_id = ObjectIdField(required=True)
    orig_type = StringField()
    start_time = StringField()
    caller_ani = StringField()
    name_calltaker = StringField()
    response_time = FloatField()
    avg_response_time= FloatField()
    duration = IntField()
    avg_duration = FloatField()
    meta = {
        'indexes': [
            'report_id',
            'psap_id'
        ]
    }

class AbandonedCallReportDetails(Document):
    report_id = ObjectIdField(required=True)
    psap_id = ObjectIdField(required=True)
    orig_type = StringField()
    start_time = StringField()
    caller_ani = StringField()
    meta = {
        'indexes': [
            'report_id',
            'psap_id'
        ]
    }



class AbandonedCallReport(Document):
    psap_id = ObjectIdField(required=True)
    report_name = StringField()


