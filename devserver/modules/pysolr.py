# encoding: utf-8
"""
Profile pysolr queries

Usage:
1. Add ``'devserver.modules.pysolr.PySolrModule',`` to DEVSERVER_MODULES
2. Optionally, set ``DEVSERVER_LOG_PYSOLR_DETAILS = True`` to see individual queries and times
"""
from __future__ import absolute_import

from collections import deque
from functools import wraps
from timeit import default_timer

try:
    import pysolr
except ImportError:
    import warnings

    class PySolrModule(DevServerModule):
        def __new__(cls, *args, **kwargs):
            warnings.warn('PySolrModule requires pysolr to be installed')
            return super(PySolrModule, cls).__new__(cls)

from django.conf import settings
from devserver.modules import DevServerModule


class PySolrModule(DevServerModule):
    """Profile Solr queries made using pysolr"""
    logger_name = 'solr'

    def process_init(self, request):
        self.queries = deque()

        self.real_send_request = pysolr.Solr._send_request

        def monkey_send(obj, method, path, *args, **kwargs):
            start_time = default_timer()
            try:
                return self.real_send_request(obj, method, path, *args, **kwargs)
            finally:
                elapsed = default_timer() - start_time
                self.queries.append((elapsed, method, path))

        pysolr.Solr._send_request = wraps(pysolr.Solr._send_request)(monkey_send)

    def process_complete(self, request):
        pysolr.Solr._send_request = self.real_send_request
        del self.real_send_request

        if getattr(settings, 'DEVSERVER_LOG_PYSOLR_DETAILS', False):
            total_time = 0.0
            for elapsed, method, path in self.queries:
                total_time += elapsed
                self.logger.info('%0.2fs %4s %s', elapsed, method, path)
        else:
            total_time = sum(i for i, j, k in self.queries)

        self.logger.info('%d Solr queries in %0.2fs', len(self.queries), total_time)
