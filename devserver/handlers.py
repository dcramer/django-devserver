from django.core.handlers.wsgi import WSGIHandler

import datetime
import sys
import logging

class GenericLogger(object):
    def __init__(self, module):
        self.module = module
    
    def log(self, message, *args, **kwargs):
        id = kwargs.pop('id', None)
        if id:
            tpl = '[%(asctime)s] [%(module)s/%(id)s] %(message)s'
        else:
            tpl = '[%(asctime)s] [%(module)s] %(message)s'

        if args:
            message = message % args

        print tpl % dict(
            id=id,
            module=self.module.logger_name,
            message=message,
            asctime=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )

    warn = lambda x, *a, **k: x.log(*a, **k)
    info = lambda x, *a, **k: x.log(*a, **k)
    debug = lambda x, *a, **k: x.log(*a, **k)
    error = lambda x, *a, **k: x.log(*a, **k)
    critical = lambda x, *a, **k: x.log(*a, **k)
    fatal = lambda x, *a, **k: x.log(*a, **k)

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
load_modules()

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
