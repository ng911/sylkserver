from sqlalchemy.orm import sessionmaker, relationship, backref
from .db import engine, getUniqueId
from .psap import Psap
from .user import User
from .kamailio import add_psap_domain, add_kamailio_user


def create_sample_entries():
    Session = sessionmaker(bind=engine)
    session = Session()
    if session.query(Psap).first() == None:
        psap_id_la = getUniqueId()
        psap_la = Psap(psap_id=psap_id_la, psap_name="los angeles", domain_name="psap.la.emergent911.com")
        psap_id_sf = getUniqueId()
        psap_sf = Psap(psap_id=psap_id_sf, psap_name="san francisco", domain_name="psap.sf.emergent911.com")
        session.add(psap_la)
        session.add(psap_sf)

        user_tarun_la = User(username="tarun", psap_id=psap_id_la, fullname="tarun mehta", password_hash=User.generate_password_hash("tarun2020"))
        user_mike_la = User(username="mike", psap_id=psap_id_la, fullname="mike tedder", password_hash=User.generate_password_hash("mike2020"))
        user_raushan_la = User(username="raushan", psap_id=psap_id_la, fullname="raushan raja", password_hash=User.generate_password_hash("raushan2020"))
        session.add(user_tarun_la)
        session.add(user_mike_la)
        session.add(user_raushan_la)
        user_tarun_sf = User(username="tarun", psap_id=psap_id_sf, fullname="tarun mehta", password_hash=User.generate_password_hash("tarun2020"))
        user_mike_sf = User(username="mike", psap_id=psap_id_sf, fullname="mike tedder", password_hash=User.generate_password_hash("mike2020"))
        user_raushan_sf = User(username="raushan", psap_id=psap_id_sf, fullname="raushan raja", password_hash=User.generate_password_hash("raushan2020"))
        session.add(user_tarun_sf)
        session.add(user_mike_sf)
        session.add(user_raushan_sf)

        session.commit()


Psap.__table__.create(bind=engine, checkfirst=True)
User.__table__.create(bind=engine, checkfirst=True)

from ...config import PSQL_IS_TEST_ENV

if PSQL_IS_TEST_ENV:
    create_sample_entries()

__all__ = [
    'Psap', 'User',
    'add_psap_domain', 'add_kamailio_user'
]


