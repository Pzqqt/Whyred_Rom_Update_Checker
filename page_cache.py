#!/usr/bin/env python3
# encoding: utf-8

import threading
from typing import Union, NoReturn

class PageCache:

    """ 一个保存了页面源码的类
    键为(<url>, <url参数>), 值为页面源码
    将PageCache对象嵌入到CheckUpdate.request_url方法中
    可以在请求之前检查是否已经请求过 (将检查两个要素: url, url参数)
    如果否, 则继续请求, 并在请求成功之后将url, url参数, 页面源码保存至本对象
    如果是, 则从本对象中取出之前请求得到的源码, 可以避免重复请求

    为什么不使用lru_cache装饰器呢?
    因为url参数可能是字典,
    而字典是不可哈希的, 也就用不了lru_cache了.
    在PageCache中, 字典参数会被适当地处理.
    """

    def __init__(self):
        self.__page_cache = dict()
        self.threading_lock = threading.RLock()

    @staticmethod
    def __params_change(params: Union[dict, None]) -> Union[frozenset, None]:
        if params is None:
            return None
        if isinstance(params, dict):
            return frozenset(params.items())
        raise TypeError("'params' must be a dict or None")

    def read(self, url: str, params: Union[dict, None]) -> str:
        params = self.__params_change(params)
        with self.threading_lock:
            return self.__page_cache.get((url, params))

    def save(self, url: str, params: Union[dict, None], page_source: str) -> NoReturn:
        params = self.__params_change(params)
        with self.threading_lock:
            self.__page_cache[(url, params)] = page_source

    def clear(self) -> NoReturn:
        with self.threading_lock:
            self.__page_cache.clear()
