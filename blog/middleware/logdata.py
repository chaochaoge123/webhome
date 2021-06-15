#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2021/3/31 16:46
# @Author  : qqc
# @File    : logdata.py
# @Software: PyCharm

import json
import logging
from django.utils.deprecation import MiddlewareMixin
import time


class LoggingMiddleware(MiddlewareMixin):

    def process_request(self, request):
        pass