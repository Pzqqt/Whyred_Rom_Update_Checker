#!/usr/bin/env python3
# encoding: utf-8

import os
from collections import OrderedDict
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import SQLITE_FILE

_Base = declarative_base()
_Engine = create_engine(
    "sqlite:///%s" % os.path.join(os.path.dirname(os.path.abspath(__file__)), SQLITE_FILE)
)
_DBSession = sessionmaker(bind=_Engine)

@contextmanager
def create_dbsession(**kw):
    session = _DBSession(**kw)
    try:
        yield session
    finally:
        session.close()

# 多线程模式下各个线程会同时对数据库进行读写
# 但是一个线程只对数据库中的一条数据进行读写, 与其他线程并不相互冲突
# 所以不需要加锁

class Saved(_Base):
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
        """ 返回Saved对象存储的键值字典 """
        return OrderedDict([
            (k, getattr(self, k))
            for k in (
                "ID FULL_NAME LATEST_VERSION BUILD_TYPE BUILD_VERSION "
                "BUILD_DATE BUILD_CHANGELOG FILE_MD5 FILE_SHA1 FILE_SHA256 "
                "DOWNLOAD_LINK FILE_SIZE"
            ).split()
        ])

    @classmethod
    def get_saved_info(cls, name):
        """
        根据name查询并返回数据库中已存储的数据
        如果数据不存在, 则返回None
        :param name: CheckUpdate子类的类名
        :return: Saved对象或None
        """
        with create_dbsession() as session:
            return session.query(cls).filter(cls.ID == name).one()

_Base.metadata.create_all(_Engine)
