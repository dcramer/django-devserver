from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import os
import sys

import django
from django.core.servers.basehttp import run, AdminMediaHandler, WSGIServerException
from devserver.handlers import DevServerHandler

def null_technical_500_response(request, exc_type, exc_value, tb):
    raise exc_type, exc_value, tb

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noreload', action='store_false', dest='use_reloader', default=True,
            help='Tells Django to NOT use the auto-reloader.'),
        make_option('--nowerkzeug', action='store_false', dest='use_werkzeug', default=True,
            help='Tells Django to NOT use the Werkzeug interactive debugger.'),
        make_option('--adminmedia', dest='admin_media_path', default='',
            help='Specifies the directory from which to serve admin media.'),
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
        use_werkzeug = options.get('use_werkzeug', '')
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
            settings.DEVSERVER_ACTIVE = True
            settings.DEBUG = True

            from django.conf import settings
            from django.utils import translation

            print "Validating models..."
            self.validate(display_num_errors=True)
            print "\nDjango version %s, using settings %r" % (django.get_version(), settings.SETTINGS_MODULE)
            print "Development server is running at http://%s:%s/" % (addr, port)
            print "Quit the server with %s." % quit_command

            # django.core.management.base forces the locale to en-us. We should
            # set it up correctly for the first request (particularly important
            # in the "--noreload" case).
            translation.activate(settings.LANGUAGE_CODE)

            try:
                handler = AdminMediaHandler(DevServerHandler(), admin_media_path)
                if use_werkzeug:
                    run_simple(addr, int(port), DebuggedApplication(handler, True),
                        use_reloader=use_reloader, use_debugger=True)
                else:
                    run(addr, int(port), handler)
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
