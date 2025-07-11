#!/usr/bin/env python3
# encoding: utf-8

from __future__ import annotations
import os
import threading
from collections import OrderedDict

from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from config import SQLITE_FILE


if not os.path.isabs(SQLITE_FILE):
    SQLITE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), SQLITE_FILE)

_Base = declarative_base()
_Engine = create_engine("sqlite:///%s" % SQLITE_FILE)
_DatabaseSession = sessionmaker(bind=_Engine)
_DatabaseSession.threading_lock = threading.RLock()

# noinspection PyPep8Naming
def DatabaseSession(**kwargs) -> Session:
    with _DatabaseSession.threading_lock:
        return _DatabaseSession(**kwargs)

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

    def get_kv(self) -> OrderedDict:
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
    def get_saved_info(cls, name: str) -> Saved:
        """
        根据name查询并返回数据库中已存储的数据
        如果数据不存在, 则抛出`sqlalchemy.orm.exc.NoResultFound`异常
        :param name: CheckUpdate子类的类名
        :return: Saved对象
        """
        with DatabaseSession() as session:
            return session.query(cls).filter_by(ID=name).one()

_Base.metadata.create_all(_Engine)
