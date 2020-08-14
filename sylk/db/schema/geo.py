import logging
from mongoengine import *
from .routing import IVR

log = logging.getLogger("emergent-ng911")

class GeoRouting(Document):
    georouting_id = ObjectIdField(required=True,unique=True)
    psap_id = ObjectIdField()
    description = StringField()
    file_name = FileField()
    routing = ReferenceField(IVR)

