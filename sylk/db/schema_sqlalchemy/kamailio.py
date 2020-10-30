import hashlib
import six
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy import inspect
from sqlalchemy.sql import text
from .db import engine


# from https://stackoverflow.com/questions/5297448/how-to-get-md5-sum-of-a-string-using-python
def get_md5(strVal):
    if six.PY2:
        return hashlib.md5(strVal).hexdigest()
    else:
        return hashlib.md5(strVal.encode('utf-8')).hexdigest()


def get_ha1(username, domain, password):
    return get_md5("%s:%s:%s" % (username, domain, password))


def get_ha1b(username, domain, password):
    return get_md5("%s@%s:%s:%s" % (username, domain, realm, password))


def add_kamailio_user(username, domain, password="emergent"):
    '''
        from
        https://stackoverflow.com/questions/17089103/does-kamailio-provide-api-for-other-program-to-creating-sip-account
        INSERT INTO subscriber (username, domain, password, ha1, ha1b) VALUES
          '101', 'test.com', 'test123',
          MD5('101:test.com:test123'), MD5('101@test.com:test.com:test123')
        );
        The special values here are for ha1 and ha1b columns, which have to be:
        * ha1 = md5(username:realm:password)
        * ha1b = md5(username@domain:realm:password)

    :param username:
    :param domain:
    :param password:
    :return:
    '''
    ha1 = get_ha1(username, domain, password)
    ha1b = get_ha1(username, domain, password)
    with engine.connect() as con:
        data = {"username": username, "domain": domain, "password": password, "ha1" : ha1, "ha1b" :  ha1b}
        statement = text("""
            INSERT INTO subscriber (username, domain, password, ha1, ha1b) VALUES(:username, :domain, :password, :ha1, :ha1b)
        """)
        con.execute(statement, **data)


def add_kamailio_domain(domain):
    with engine.connect() as con:
        data = {"domain": domain}
        statement = text("""
            INSERT INTO domain (domain) VALUES(:domain)
        """)
        con.execute(statement, **data)

