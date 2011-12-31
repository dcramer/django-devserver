import SocketServer

from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from django.core.management import call_command
from django.core.servers.basehttp import StoppableWSGIServer, AdminMediaHandler, WSGIServerException
from django.test.testcases import TestServerThread

from devserver.utils.http import SlimWSGIRequestHandler


class ThreadedTestServerThread(TestServerThread):
    def run(self):
        try:
            wsgi_handler = AdminMediaHandler(WSGIHandler())
            server_address = (self.address, self.port)

            class new(SocketServer.ThreadingMixIn, StoppableWSGIServer):
                def __init__(self, *args, **kwargs):
                    StoppableWSGIServer.__init__(self, *args, **kwargs)

            httpd = new(server_address, SlimWSGIRequestHandler)
            httpd.set_app(wsgi_handler)
            self.started.set()
        except WSGIServerException, e:
            self.error = e
            self.started.set()
            return

        # Must do database stuff in this new thread if database in memory.
        if settings.DATABASE_ENGINE == 'sqlite3' \
            and (not settings.TEST_DATABASE_NAME or settings.TEST_DATABASE_NAME == ':memory:'):
            # Import the fixture data into the test database.
            if hasattr(self, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                call_command('loaddata', *self.fixtures, **{'verbosity': 0})

        # Loop until we get a stop event.
        while not self._stopevent.isSet():
            httpd.handle_request()
