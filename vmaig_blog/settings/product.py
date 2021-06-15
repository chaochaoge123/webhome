#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/3/30 16:23
# @Author  : qqc
# @File    : product.py
# @Software: PyCharm


from .base import *

DEBUG = False


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': "db3",  # 数据库名
        "HOST": "47.102.138.171",  # 主机IP（本地为127.0.0.1）
        "PORT": 3306,  # 端口号：默认3306
        'USER': os.environ.get('DATABA_USER', ''),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', '')
    },
    'OPTIONS': {
                "init_command": "SET foreign_key_checks = 0;",
        }
}

# cache配置
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'options': {
            'MAX_ENTRIES': 1024,
        }
    },
    #'memcache': {
    #    'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
    #    'LOCATION': '127.0.0.1:11211',
    #    'options': {
    #        'MAX_ENTRIES': 1024,
    #    }
    #},
    #"redis": {
    #    "BACKEND": "django_redis.cache.RedisCache",
    #    "LOCATION": "redis://127.0.0.1:6379/1",
    #    "OPTIONS": {
    #        "CLIENT_CLASS": "django_redis.client.DefaultClient",
    #    }
    #}
}
