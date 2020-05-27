#!/usr/bin/env python3
# encoding: utf-8

import threading

THREADING_LOCK = threading.Lock()

class PageCache:

    """ 一个保存了页面源码的类
    键为(<url>, <请求方法>, <url参数>), 值为页面源码
    将PageCache对象嵌入到CheckUpdate.request_url方法中
    可以在请求之前检查是否已经请求过 (将检查三个要素: url, 请求方法, url参数)
    如果否, 则继续请求, 并在请求成功之后将请求方法, url, url参数, 页面源码保存至本对象
    如果是, 则从本对象中取出之前请求得到的源码, 可以避免重复请求

    为什么不使用lru_cache装饰器呢?
    因为被缓存的函数(CheckUpdate.request_url)的参数中可能有字典,
    而字典是不可哈希的, 也就用不了lru_cache了.
    在PageCache中, 字典参数会被适当地处理.
    """

    def __init__(self):
        self.__page_cache = dict()

    @staticmethod
    def __params_change(params):
        if params is None:
            return None
        if isinstance(params, dict):
            return frozenset(params.items())
        raise TypeError("'params' must be a dict or None")

    def read(self, request_method, url, params):
        params = self.__params_change(params)
        return self.__page_cache.get((request_method, url, params))

    def save(self, request_method, url, params, page_source):
        if request_method not in {"get", "post"}:
            raise TypeError("'request_method' must be 'get' or 'post'")
        params = self.__params_change(params)
        self.__page_cache[(request_method, url, params)] = page_source

    def clear(self):
        with THREADING_LOCK:
            self.__page_cache.clear()
