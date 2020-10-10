from .db import Base
from .psap import Psap
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from .user import User

class ConferenceMessage(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    room_number = Column(String, nullable=False)
    sender_uri = Column(String)
    message = Column(String)
    message_id = Column(String)
    message_time = Column(DateTime, default=datetime.utcnow())
    content_type = Column(String)


class Greeting(Base):
    psap_id = Column(String, ForeignKey(Psap.psap_id), nullable=False)
    greeting_id = Column(String, primary_key=True, nullable=False)
    user_id = Column(String, ForeignKey(User.user_id))
    desc = Column(String, nullable=False)
    group = Column(String)