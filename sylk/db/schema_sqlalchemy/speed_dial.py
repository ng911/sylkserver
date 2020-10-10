from .psap import Psap
from .user import User

from .db import Base

from sqlalchemy import Column, String, ForeignKey, Boolean, PickleType
from sqlalchemy.orm import relationship

#  speed_dial_id = ObjectIdField(required=True, default=bson.ObjectId, unique=True)
#     psap_id = ObjectIdField()
#     role_id = ObjectIdField()
#     user_group_id = ObjectIdField()
#     user_id = ObjectIdField()
#     dest = StringField(required=True)
#     name = StringField(required=True)
#     group_id = ObjectIdField()
#     group = LazyReferenceField(document_type=SpeedDialGroup)
#     show_as_button = BooleanField()
#     icon = StringField()
#     files = ListField(StringField())

class SpeedDialGroup(Base):
    group_id = Column(String, primary_key=True, nullable=False)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    role_id = Column(String)
    user_id = Column(String, ForeignKey(User.user_id))
    group_name = Column(String, nullable=False)


class SpeedDial(Base):
    speed_dial_id = Column(String, primary_key=True)
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    role_id = Column(String)
    user_group_id = Column(String)
    user_id = Column(String, ForeignKey(User.user_id))
    dest = Column(String, nullable=False)
    name = Column(String, nullable=False)
    group_id = Column(String)
    group = relationship('SpeedDialGroup', backref="speeddial")
    show_as_button = Column(Boolean)
    icon = Column(String)
    files = Column(PickleType)