from django.core.management.commands.runserver import BaseRunserverCommand
from django.core.servers.basehttp import AdminMediaHandler, WSGIServerException, \
                                         WSGIServer

import os
import sys
import django
import SocketServer
from optparse import make_option

from devserver.handlers import DevServerHandler
from devserver.utils.http import SlimWSGIRequestHandler

def null_technical_500_response(request, exc_type, exc_value, tb):
    raise exc_type, exc_value, tb

def run(addr, port, wsgi_handler, ipv6=False, mixin=None):
    if mixin:
        class new(mixin, WSGIServer):
            def __init__(self, *args, **kwargs):
                WSGIServer.__init__(self, *args, **kwargs)
    else:
        new = WSGIServer
    server_address = (addr, port)
    httpd = new(server_address, SlimWSGIRequestHandler, ipv6=ipv6)
    httpd.set_app(wsgi_handler)
    httpd.serve_forever()

class Command(BaseRunserverCommand):
    option_list = BaseRunserverCommand.option_list + (
        make_option('--werkzeug', action='store_true', dest='use_werkzeug', default=False,
            help='Tells Django to use the Werkzeug interactive debugger.'),
        make_option('--adminmedia', dest='admin_media_path', default='',
            help='Specifies the directory from which to serve admin media.'),
        make_option('--forked', action='store_true', dest='use_forked', default=False,
            help='Use forking instead of threading for multiple web requests.'),
    )
    help = "Starts a lightweight Web server for development which outputs additional debug information."

    def get_handler(self, *args, **options):
        """
        Returns the default WSGI handler for the runner.
        """
        handler = super(Command, self).get_handler(*args, **options)
        from django.conf import settings
        admin_media_path = options.get('admin_media_path', '')
        use_static_handler = options.get('use_static_handler', True)
        insecure_serving = options.get('insecure_serving', False)
        if int(options['verbosity']) >= 1:
            handler = DevServerHandler(handler)
        if (settings.DEBUG and use_static_handler or
                (use_static_handler and insecure_serving)):
            try:
                from django.contrib.staticfiles.handlers import StaticFilesHandler
                handler = StaticFilesHandler(handler)
            except ImportError:
                pass
        handler = AdminMediaHandler(handler, admin_media_path)
        return handler

    def inner_run(self, *args, **options):
        # Flag the server as active
        from devserver import settings
        import devserver
        settings.DEVSERVER_ACTIVE = True
        settings.DEBUG = True

        from django.conf import settings
        from django.utils import translation

        use_reloader = options.get('use_reloader', True)
        shutdown_message = options.get('shutdown_message', '')
        use_werkzeug = options.get('use_werkzeug', False)
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'

        if use_werkzeug:
            try:
                from werkzeug import run_simple, DebuggedApplication
            except ImportError, e:
                use_werkzeug = False
            else:
                use_werkzeug = True
                from django.views import debug
                debug.technical_500_response = null_technical_500_response

        self.stdout.write("Validating models...\n\n")
        self.validate(display_num_errors=True)
        self.stdout.write((
            "Django version %(version)s, using settings %(settings)r\n"
            "Running django-devserver %(devserver_version)s\n"
            "Development server is running at http://%(addr)s:%(port)s/\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "version": self.get_version(),
            "devserver_version": devserver.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "addr": self._raw_ipv6 and '[%s]' % self.addr or self.addr,
            "port": self.port,
            "quit_command": quit_command,
        })
        # django.core.management.base forces the locale to en-us. We should
        # set it up correctly for the first request (particularly important
        # in the "--noreload" case).
        translation.activate(settings.LANGUAGE_CODE)

        if options['use_forked']:
            mixin = SocketServer.ForkingMixIn
        else:
            mixin = SocketServer.ThreadingMixIn

        try:
            handler = self.get_handler(*args, **options)
            if use_werkzeug:
                run_simple(self.addr, int(self.port), DebuggedApplication(handler, True),
                    use_reloader=use_reloader, use_debugger=True)
            else:
                run(self.addr, int(self.port), handler, ipv6=self.use_ipv6, mixin=mixin)
        except WSGIServerException, e:
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                13: "You don't have permission to access that port.",
                98: "That port is already in use.",
                99: "That IP address can't be assigned-to.",
            }
            try:
                error_text = ERRORS[e.args[0].args[0]]
            except (AttributeError, KeyError):
                error_text = str(e)
            sys.stderr.write(self.style.ERROR("Error: %s" % error_text) + '\n')
            # Need to use an OS exit because sys.exit doesn't work in a thread
            os._exit(1)
        except KeyboardInterrupt:
            if shutdown_message:
                self.stdout.write("%s\n" % shutdown_message)
            sys.exit(0)
