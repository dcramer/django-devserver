from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import StoppableWSGIServer, AdminMediaHandler, WSGIServerException
from django.test.testcases import TestServerThread

from devserver.utils.http import SlimWSGIRequestHandler

import SocketServer

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