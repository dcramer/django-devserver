import socket
import SocketServer
import threading

from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler
from django.core.management import call_command
from django.core.servers.basehttp import WSGIServer

from devserver.utils.http import SlimWSGIRequestHandler

try:
    from django.core.servers.basehttp import (WSGIServerException as
                                              wsgi_server_exc_cls)
except ImportError:  # Django 1.6
    wsgi_server_exc_cls = socket.error


class StoppableWSGIServer(WSGIServer):
    """WSGIServer with short timeout, so that server thread can stop this server."""

    def server_bind(self):
        """Sets timeout to 1 second."""
        WSGIServer.server_bind(self)
        self.socket.settimeout(1)

    def get_request(self):
        """Checks for timeout when getting request."""
        try:
            sock, address = self.socket.accept()
            sock.settimeout(None)
            return (sock, address)
        except socket.timeout:
            raise


class ThreadedTestServerThread(threading.Thread):
    """Thread for running a http server while tests are running."""

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self._stopevent = threading.Event()
        self.started = threading.Event()
        self.error = None
        super(ThreadedTestServerThread, self).__init__()

    def _should_loaddata(self):
        # Must do database stuff in this new thread if database in memory.
        if not hasattr(self, 'fixtures'):
            return False
        if settings.DATABASE_ENGINE != 'sqlite3':
            return False
        if settings.TEST_DATABASE_NAME and settings.TEST_DATABASE_NAME != ':memory:':
            return False
        return True

    def run(self):
        """Sets up test server and database and loops over handling http requests."""
        # AdminMediaHandler was removed in Django 1.5; use it only when available.
        handler = WSGIHandler()
        try:
            from django.core.servers.basehttp import AdminMediaHandler
            handler = AdminMediaHandler(handler)
        except ImportError:
            pass

        try:
            server_address = (self.address, self.port)

            class new(SocketServer.ThreadingMixIn, StoppableWSGIServer):
                def __init__(self, *args, **kwargs):
                    StoppableWSGIServer.__init__(self, *args, **kwargs)

            httpd = new(server_address, SlimWSGIRequestHandler)
            httpd.set_app(handler)
            self.started.set()
        except wsgi_server_exc_cls, e:
            self.error = e
            self.started.set()
            return

        if self._should_loaddata():
            # We have to use this slightly awkward syntax due to the fact
            # that we're using *args and **kwargs together.
            call_command('loaddata', *self.fixtures, **{'verbosity': 0})

        # Loop until we get a stop event.
        while not self._stopevent.isSet():
            httpd.handle_request()

    def join(self, timeout=None):
        """Stop the thread and wait for it to finish."""
        self._stopevent.set()
        threading.Thread.join(self, timeout)
