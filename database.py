#!/usr/bin/env python3
# encoding: utf-8

from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, exc

from config import SQLITE_FILE

Base = declarative_base()
Engine = create_engine("sqlite:///%s" % SQLITE_FILE)
DBSession = sessionmaker(bind=Engine)
Base.metadata.create_all(Engine)

class Saved(Base):

    __tablename__ = "saved"
    ID = Column(String, primary_key=True, nullable=False)
    FULL_NAME = Column(String, nullable=False)
    LATEST_VERSION = Column(String)
    BUILD_TYPE = Column(String)
    BUILD_VERSION = Column(String)
    BUILD_DATE = Column(String)
    BUILD_CHANGELOG = Column(String)
    FILE_MD5 = Column(String)
    FILE_SHA1 = Column(String)
    FILE_SHA256 = Column(String)
    DOWNLOAD_LINK = Column(String)
    FILE_SIZE = Column(String)

    def get_kv(self):
        dic = self.__dict__.copy()
        dic.pop("_sa_instance_state")
        return dic

def get_saved_info(name):
    """
    根据name查询并返回数据库中已存储的数据
    如果数据不存在, 则返回None
    :param name: CheckUpdate子类的类名
    :return: Saved对象或None
    """
    session = DBSession()
    try:
        return session.query(Saved).filter(Saved.ID == name).one()
    except exc.NoResultFound:
        return None
    finally:
        session.close()
