from django.core.management.base import BaseCommand, CommandError
from django.core.servers.basehttp import AdminMediaHandler, WSGIServerException, \
                                         WSGIServer
from django.core.handlers.wsgi import WSGIHandler

import os
import sys
import django
import SocketServer
from optparse import make_option

from devserver.handlers import DevServerHandler
from devserver.utils.http import SlimWSGIRequestHandler

def null_technical_500_response(request, exc_type, exc_value, tb):
    raise exc_type, exc_value, tb

def run(addr, port, wsgi_handler, mixin=None):
    if mixin:
        class new(mixin, WSGIServer):
            def __init__(self, *args, **kwargs):
                WSGIServer.__init__(self, *args, **kwargs)
    else:
        new = WSGIServer
    server_address = (addr, port)
    httpd = new(server_address, SlimWSGIRequestHandler)
    httpd.set_app(wsgi_handler)
    httpd.serve_forever()

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noreload', action='store_false', dest='use_reloader', default=True,
            help='Tells Django to NOT use the auto-reloader.'),
        make_option('--werkzeug', action='store_true', dest='use_werkzeug', default=False,
            help='Tells Django to use the Werkzeug interactive debugger.'),
        make_option('--adminmedia', dest='admin_media_path', default='',
            help='Specifies the directory from which to serve admin media.'),
        make_option('--forked', action='store_true', dest='use_forked', default=False,
            help='Use forking instead of threading for multiple web requests.'),
    )
    help = "Starts a lightweight Web server for development which outputs additional debug information."
    args = '[optional port number, or ipaddr:port]'

    # Validation is called explicitly each time the server is reloaded.
    requires_model_validation = False

    def handle(self, addrport='', *args, **options):
        if args:
            raise CommandError('Usage is runserver %s' % self.args)
        if not addrport:
            addr = ''
            port = '8000'
        else:
            try:
                addr, port = addrport.split(':')
            except ValueError:
                addr, port = '', addrport
        if not addr:
            addr = '127.0.0.1'

        if not port.isdigit():
            raise CommandError("%r is not a valid port number." % port)

        use_reloader = options.get('use_reloader', True)
        admin_media_path = options.get('admin_media_path', '')
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


        def inner_run():
            # Flag the server as active
            from devserver import settings
            import devserver
            settings.DEVSERVER_ACTIVE = True
            settings.DEBUG = True

            from django.conf import settings
            from django.utils import translation

            print "Validating models..."
            self.validate(display_num_errors=True)
            print "\nDjango version %s, using settings %r" % (django.get_version(), settings.SETTINGS_MODULE)
            print "Running django-devserver %s" % (devserver.get_version(),)
            print "%s server is running at http://%s:%s/" % (options['use_forked'] and 'Forked' or 'Threaded', addr, port)
            print "Quit the server with %s." % quit_command

            # django.core.management.base forces the locale to en-us. We should
            # set it up correctly for the first request (particularly important
            # in the "--noreload" case).
            translation.activate(settings.LANGUAGE_CODE)

            if int(options['verbosity']) < 1:
                base_handler = WSGIHandler
            else:
                base_handler = DevServerHandler

            if options['use_forked']:
                mixin = SocketServer.ForkingMixIn
            else:
                mixin = SocketServer.ThreadingMixIn

            try:
                handler = AdminMediaHandler(base_handler(), admin_media_path)
                if use_werkzeug:
                    run_simple(addr, int(port), DebuggedApplication(handler, True),
                        use_reloader=use_reloader, use_debugger=True)
                else:
                    run(addr, int(port), handler, mixin)
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
                    print shutdown_message
                sys.exit(0)

        if use_reloader:
            from django.utils import autoreload
            autoreload.main(inner_run)
        else:
            inner_run()
