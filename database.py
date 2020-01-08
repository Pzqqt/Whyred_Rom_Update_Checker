#!/usr/bin/env python3
# encoding: utf-8

from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from check_init import CheckUpdate
from check_list import CHECK_LIST
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

def write_to_database(check_update_obj):
    """
    将CheckUpdate实例的info_dic数据写入数据库
    :param check_update_obj: CheckUpdate实例
    :return: None
    """
    assert isinstance(check_update_obj, CheckUpdate)
    session = DBSession()
    try:
        if check_update_obj.name in {x.ID for x in session.query(Saved).all()}:
            saved_data = session.query(Saved).filter(Saved.ID == check_update_obj.name).one()
            saved_data.FULL_NAME = check_update_obj.fullname
            for key, value in check_update_obj.info_dic.items():
                setattr(saved_data, key, value)
        else:
            new_data = Saved(
                ID=check_update_obj.name,
                FULL_NAME=check_update_obj.fullname,
                **check_update_obj.info_dic
            )
            session.add(new_data)
        session.commit()
    finally:
        session.close()

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
    except NoResultFound:
        return None
    finally:
        session.close()

def cleanup():
    """
    将数据库中存在于数据库但不存在于CHECK_LIST的项目删除掉
    :return: 被删除的项目名字的集合
    """
    session = DBSession()
    try:
        saved_ids = {x.ID for x in session.query(Saved).all()}
        checklist_ids = {x.__name__ for x in CHECK_LIST}
        drop_ids = saved_ids - checklist_ids
        for id_ in drop_ids:
            session.delete(session.query(Saved).filter(Saved.ID == id_).one())
        session.commit()
        return drop_ids
    finally:
        session.close()

def is_updated(check_update_obj):
    """
    传入CheckUpdate实例, 与数据库中已存储的数据进行比对
    如果有更新, 则返回True, 否则返回False
    :param check_update_obj: CheckUpdate实例
    :return: True或False
    """
    assert isinstance(check_update_obj, CheckUpdate)
    if check_update_obj.info_dic["LATEST_VERSION"] is None:
        return False
    saved_info = get_saved_info(check_update_obj.name)
    if saved_info is None:
        return True
    if check_update_obj.info_dic["LATEST_VERSION"] == saved_info.LATEST_VERSION:
        return False
    return True
