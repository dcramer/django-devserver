"""
Based on initial work from django-debug-toolbar
"""

from datetime import datetime
import sys
import traceback

import django
from django.db import connection
from django.db.backends import util
from django.views.debug import linebreak_iter
from django.template import Node
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.encoding import force_unicode
from django.utils.hashcompat import sha_constructor
from django.utils.translation import ugettext_lazy as _

from devserver.modules import DevServerModule
#from devserver.utils.stack import tidy_stacktrace, get_template_info
from devserver import settings

# # TODO:This should be set in the toolbar loader as a default and panels should
# # get a copy of the toolbar object with access to its config dictionary
# SQL_WARNING_THRESHOLD = getattr(settings, 'DEVSERVER_CONFIG', {}) \
#                             .get('SQL_WARNING_THRESHOLD', 500)

class DatabaseStatTracker(util.CursorDebugWrapper):
    """
    Replacement for CursorDebugWrapper which outputs information as it happens.
    """
    def execute(self, sql, params=()):
        hash = sha_constructor(sql + str(params)).hexdigest()
        
        start = datetime.now()
        try:
            return self.cursor.execute(sql, params)
        finally:
            stop = datetime.now()
            duration = ms_from_timedelta(stop - start)
            # stacktrace = tidy_stacktrace(traceback.extract_stack())
            # template_info = None
            # # TODO: can probably move this into utils
            # cur_frame = sys._getframe().f_back
            # try:
            #     while cur_frame is not None:
            #         if cur_frame.f_code.co_name == 'render':
            #             node = cur_frame.f_locals['self']
            #             if isinstance(node, Node):
            #                 template_info = get_template_info(node.source)
            #                 break
            #         cur_frame = cur_frame.f_back
            # except:
            #     pass
            # del cur_frame
            
            self.logger.debug(sql, duration=duration, id=hash, *params)
            
            # 
            # # We keep `sql` to maintain backwards compatibility
            # self.db.queries.append({
            #     'sql': self.db.ops.last_executed_query(self.cursor, sql, params),
            #     'duration': duration,
            #     'raw_sql': sql,
            #     'params': _params,
            #     'stacktrace': stacktrace,
            #     'start_time': start,
            #     'stop_time': stop,
            #     'is_slow': (duration > SQL_WARNING_THRESHOLD),
            #     'is_select': sql.lower().strip().startswith('select'),
            #     'template_info': template_info,
            # })

def ms_from_timedelta(td):
    """
    Given a timedelta object, returns a float representing milliseconds
    """
    return (td.seconds * 1000) + (td.microseconds / 1000.0)


def reformat_sql(sql):
    stack = sqlparse.engine.FilterStack()
    stack.preprocess.append(BoldKeywordFilter()) # add our custom filter
    stack.postprocess.append(sqlparse.filters.SerializerUnicode()) # tokens -> strings
    return ''.join(stack.run(sql))

class SQLRealTimeModule(DevServerModule):
    """
    Outputs SQL queries as they happen.
    """
    
    logger_name = 'sql'
    
    def process_init(self):
        self.old_cursor = util.CursorDebugWrapper
        util.CursorDebugWrapper = DatabaseStatTracker
        DatabaseStatTracker.logger = self.logger
    
    def process_complete(self):
        util.CursorDebugWrapper = self.old_cursor