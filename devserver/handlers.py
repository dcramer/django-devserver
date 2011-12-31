from django.core.handlers.wsgi import WSGIHandler

from devserver.middleware import DevServerMiddleware


class DevServerHandler(WSGIHandler):
    def load_middleware(self):
        super(DevServerHandler, self).load_middleware()

        i = DevServerMiddleware()

        # TODO: verify this order is fine
        self._request_middleware.append(i.process_request)
        self._view_middleware.append(i.process_view)
        self._response_middleware.append(i.process_response)
        self._exception_middleware.append(i.process_exception)
