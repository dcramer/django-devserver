from django.core.handlers.wsgi import WSGIHandler, set_script_prefix, signals, base, STATUS_CODE_TEXT
from django.core.management.color import color_style
from django.utils import termcolors

import datetime
import sys
import logging

import re

_bash_colors = re.compile(r'\x1b\[[^m]*m')
def strip_bash_colors(string):
    return _bash_colors.sub('', string)

class GenericLogger(object):
    def __init__(self, module):
        self.module = module
        self.style = color_style()
    
    def log(self, message, *args, **kwargs):
        id = kwargs.pop('id', None)
        duration = kwargs.pop('duration', None)
        level = kwargs.pop('level', logging.INFO)
        
        tpl_bits = []
        if id:
            tpl_bits.append(self.style.SQL_FIELD('[%s/%s]' % (self.module.logger_name, id)))
        else:
            tpl_bits.append(self.style.SQL_FIELD('[%s]' % self.module.logger_name))
        if duration:
            tpl_bits.append(self.style.SQL_KEYWORD('(%.2fms)' % duration))

        if args:
            message = message % args

        if level == logging.ERROR:
            message = self.style.ERROR(message)
        elif level == logging.WARN:
            message = self.style.NOTICE(message)
        else:
            try:
                HTTP_INFO = self.style.HTTP_INFO
            except:
                HTTP_INFO = termcolors.make_style(fg='red')
            message = HTTP_INFO(message)

        tpl = ' '.join(tpl_bits) % dict(
            id=id,
            module=self.module.logger_name,
            asctime=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )
        
        indent = ' ' * (len(strip_bash_colors(tpl)) + 1)
        
        new_message = []
        first = True
        for line in message.split('\n'):
            if first:
                new_message.append(line)
            else:
                new_message.append('%s%s' % (indent, line))
            first = False

        message = '%s %s' % (tpl, '\n'.join(new_message))

        sys.stdout.write(message.encode('utf8') + '\n')

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
    def should_process(self, request):
        from django.conf import settings
        
        if settings.MEDIA_URL and request.path.startswith(settings.MEDIA_URL):
            return False
        
        if settings.ADMIN_MEDIA_PREFIX and request.path.startswith(settings.ADMIN_MEDIA_PREFIX):
            return False
        
        if request.path == '/favicon.ico':
            return False
        
        return True
    
    def process_request(self, request):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_request(request)
    
    def process_response(self, request, response):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_response(request, response)
        return response
        
    def process_exception(self, request, exception):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_exception(request, exception)
        
    def process_view(self, request, view_func, view_args, view_kwargs):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_view(request, view_func, view_args, view_kwargs)
        return view_func(request, *view_args, **view_kwargs)

    def process_init(self, request):
        from devserver.utils.stats import stats
        
        stats.reset()
        
        if self.should_process(request):
            for mod in MODULES:
                mod.process_init(request)

    def process_complete(self, request):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_complete(request)

class DevServerHandler(WSGIHandler):
    def load_middleware(self):
        super(DevServerHandler, self).load_middleware()

        # TODO: verify this order is fine
        self._request_middleware.append(DevServerMiddleware().process_request)
        self._view_middleware.append(DevServerMiddleware().process_view)
        self._response_middleware.append(DevServerMiddleware().process_response)
        self._exception_middleware.append(DevServerMiddleware().process_exception)

    def __call__(self, environ, start_response):
        from django.conf import settings

        # XXX: kind of hackish -- we reload module instances at start so the middlework works as normal
        load_modules()

        # Set up middleware if needed. We couldn't do this earlier, because
        # settings weren't available.
        if self._request_middleware is None:
            self.initLock.acquire()
            # Check that middleware is still uninitialised.
            if self._request_middleware is None:
                self.load_middleware()
            self.initLock.release()

        set_script_prefix(base.get_script_name(environ))
        signals.request_started.send(sender=self.__class__)
        try:
            try:
                request = self.request_class(environ)
            except UnicodeDecodeError:
                response = http.HttpResponseBadRequest()
            else:
                DevServerMiddleware().process_init(request)

                response = self.get_response(request)

                # Apply response middleware
                for middleware_method in self._response_middleware:
                    response = middleware_method(request, response)
                response = self.apply_response_fixes(request, response)
        finally:
            signals.request_finished.send(sender=self.__class__)

        try:
            status_text = STATUS_CODE_TEXT[response.status_code]
        except KeyError:
            status_text = 'UNKNOWN STATUS CODE'
        status = '%s %s' % (response.status_code, status_text)
        response_headers = [(str(k), str(v)) for k, v in response.items()]
        for c in response.cookies.values():
            response_headers.append(('Set-Cookie', str(c.output(header=''))))
        start_response(status, response_headers)
        
        try:
            return response
        finally:
            DevServerMiddleware().process_complete(request)