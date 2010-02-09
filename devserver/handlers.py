from django.core.handlers.wsgi import WSGIHandler
from django.core.management.color import color_style

import datetime
import sys
import logging



class GenericLogger(object):
    def __init__(self, module):
        self.module = module
        self.style = color_style()
    
    def log(self, message, *args, **kwargs):
        id = kwargs.pop('id', None)
        duration = kwargs.pop('duration', None)
        level = kwargs.pop('level', logging.INFO)
        if duration:
            tpl = self.style.SQL_KEYWORD('(%.2fms)' % duration) + ' %(message)s'
        else:
            tpl = '%(message)s'

        if args:
            print message, args
            message = message % args

        if level == logging.ERROR:
            message = self.style.ERROR(message)
        elif level == logging.WARN:
            message = self.style.NOTICE(message)
        else:
            message = self.style.HTTP_INFO(message)

        tpl = self.style.SQL_FIELD('[%s] ' % self.module.logger_name) + tpl

        message = tpl % dict(
            id=id,
            module=self.module.logger_name,
            message=message,
            asctime=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )
        
        sys.stdout.write(message + '\n')

    warn = lambda x, *a, **k: x.log(level=logging.WARN, *a, **k)
    info = lambda x, *a, **k: x.log(level=logging.INFO, *a, **k)
    debug = lambda x, *a, **k: x.log(level=logging.DEBUG, *a, **k)
    error = lambda x, *a, **k: x.log(level=logging.ERROR, *a, **k)
    critical = lambda x, *a, **k: x.log(level=logging.CRITICAL, *a, **k)
    fatal = lambda x, *a, **k: x.log(level=logging.FATAL, *a, **k)

MODULES = []
def load_modules():
    global MODULES
    
    MODULES = []
    
    from django.core import exceptions
    from devserver import settings
    
    for path in settings.DEVSERVER_MODULES:
        try:
            name, class_name = path.rsplit('.', 1)
        except ValueError:
            raise exceptions.ImproperlyConfigured, '%s isn\'t a devserver module' % path

        try:
            module = __import__(name, {}, {}, [''])
        except ImportError, e:
            raise exceptions.ImproperlyConfigured, 'Error importing devserver module %s: "%s"' % (name, e)

        try:
            cls = getattr(module, class_name)
        except AttributeError:
            raise exceptions.ImproperlyConfigured, 'Error importing devserver module "%s" does not define a "%s" class' % (name, class_name)

        try:
            instance = cls(GenericLogger(cls))
        except:
            raise # Bubble up problem loading panel

        MODULES.append(instance)

class DevServerMiddleware(object):
    def process_request(self, request):
        for mod in MODULES:
            mod.process_request(request)
    
    def process_response(self, request, response):
        for mod in MODULES:
            mod.process_response(request, response)
        return response
        
    def process_exception(self, request, exception):
        for mod in MODULES:
            mod.process_exception(request, exception)
        
    def process_view(self, request, view_func, view_args, view_kwargs):
        for mod in MODULES:
            mod.process_view(request, view_func, view_args, view_kwargs)
        return view_func(request, *view_args, **view_kwargs)

    def process_init(self):
        from devserver.utils.stats import stats
        
        stats.reset()
        
        for mod in MODULES:
            mod.process_init()

    def process_complete(self):
        for mod in MODULES:
            mod.process_complete()

class DevServerHandler(WSGIHandler):
    def load_middleware(self):
        super(DevServerHandler, self).load_middleware()

        # TODO: verify this order is fine
        self._request_middleware.append(DevServerMiddleware().process_request)
        self._view_middleware.append(DevServerMiddleware().process_view)
        self._response_middleware.append(DevServerMiddleware().process_response)
        self._exception_middleware.append(DevServerMiddleware().process_exception)

    def __call__(self, *args, **kwargs):
        # XXX: kind of hackish -- we reload module instances at start so the middlework works as normal
        load_modules()
        
        DevServerMiddleware().process_init()

        try:
            response = super(DevServerHandler, self).__call__(*args, **kwargs)
            return response
        finally:
            DevServerMiddleware().process_complete()
