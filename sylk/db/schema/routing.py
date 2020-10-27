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


class VoicePrompt(Document):
    psap_id = ObjectIdField(required=True)
    description = StringField()
    file_name = FileField()


class IVR(Document):
    ivr_id = ObjectIdField(required=True,unique=True)
    psap_id = ObjectIdField()
    ivr_name = StringField()
    use_key = IntField()
    on_key = StringField(choices=('Prompt Only', 'Prompt with Key Press'))
    play_prompt = ReferenceField(VoicePrompt)
    ivr_type = StringField(choices=('Prompt Only', 'Prompt with Key Press'))
    on_ivr_completion = StringField(choices=('Hangup', 'Go to ACD'))


class IncomingLink(Document):
    link_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
    psap_id = ObjectIdField(required=True)
    name = StringField()
    orig_type = StringField(required=True, choices=('sos_wireless', 'sos_wireline', 'admin', 'sos_text', 'calltaker_gateway'))
    max_channels = IntField(min_value=0)
    ip_address = StringField()
    regex = BooleanField(default=False) # called_number is matched with python regex
    port = IntField(min_value=0)
    called_no = StringField()
    ringback = BooleanField(default=False)
    queue_id = ObjectIdField()
    ali_format = StringField()
    use_called_number_for_ani = BooleanField(default=False, required=False)
    strip_ani_prefix = IntField(default=0, required=False)
    strip_ani_suffix = IntField(default=0, required=False)
    strip_from_prefix = IntField(default=0, required=False)
    strip_from_suffix = IntField(default=0, required=False)
    meta = {
        'indexes': [
            'psap_id',
            'link_id'
        ]
    }

    def is_origination_calltaker(self):
        return self.orig_type == 'calltaker_gateway'

    def is_origination_admin(self):
        return self.orig_type == 'admin'

    def is_origination_sos(self):
        return self.is_origination_sos_wireless() or self.is_origination_sos_wireline() or self.is_origination_sos_text()

    def is_origination_sos_wireless(self):
        return self.orig_type == 'sos_wireless'

    def is_origination_sos_wireline(self):
        return self.orig_type == 'sos_wireline'

    def is_origination_sos_text(self):
        return self.orig_type == 'sos_text'

def add_calltaker_gateway(ip_addr, psap_id):
    IncomingLink(psap_id=psap_id, name="calltaker gateway", orig_type='calltaker_gateway', ip_address=ip_addr).save()


class OutgoingLink(Document):
    link_id = ObjectIdField(required=True)
    ip_address = StringField(required=True)
    port = IntField(min_value=0)
    from_value = StringField()
    meta = {
        'indexes': [
            'ip_address',
            'link_id'
        ]
    }


# add this later
class DialPlan(Document):
    pass

class CallTransferLine(Document):
    line_id = ObjectIdField(required=True, default=bson.ObjectId)
    psap_id = ObjectIdField(required=True)
    role_id = ObjectIdField()
    type = StringField(required=False, choices=('wireless', 'wireline', 'all'))
    name = StringField(required=True)
    star_code = StringField(required=False)
    target = StringField(required=False)
    flash_transfer = BooleanField(required=False, default=False)

    meta = {
        'indexes': [
            'psap_id',
            'line_id',
            'type'
        ]
    }


