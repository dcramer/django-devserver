from datetime import datetime

from django.conf import settings
from django.core.servers.basehttp import WSGIRequestHandler

try:
    from django.db import connections
except ImportError:
    # Django version < 1.2
    from django.db import connection
    connections = {'default': connection}

from devserver.utils.time import ms_from_timedelta


class SlimWSGIRequestHandler(WSGIRequestHandler):
    """
    Hides all requests that originate from either ``STATIC_URL`` or ``MEDIA_URL``
    as well as any request originating with a prefix included in
    ``DEVSERVER_IGNORED_PREFIXES``.
    """
    def handle(self, *args, **kwargs):
        self._start_request = datetime.now()
        return WSGIRequestHandler.handle(self, *args, **kwargs)

    def get_environ(self):
        env = super(SlimWSGIRequestHandler, self).get_environ()
        env['REMOTE_PORT'] = self.client_address[-1]
        return env

    def log_message(self, format, *args):
        duration = datetime.now() - self._start_request

        env = self.get_environ()

        for url in (getattr(settings, 'STATIC_URL', None), settings.MEDIA_URL):
            if not url:
                continue
            if self.path.startswith(url):
                return
            elif url.startswith('http:'):
                if ('http://%s%s' % (env['HTTP_HOST'], self.path)).startswith(url):
                    return

        for path in getattr(settings, 'DEVSERVER_IGNORED_PREFIXES', []):
            if self.path.startswith(path):
                return

        format += " (time: %.2fs; sql: %dms (%dq))"
        queries = [
            q for alias in connections
            for q in connections[alias].queries
        ]
        args = list(args) + [
            ms_from_timedelta(duration) / 1000,
            sum(float(c.get('time', 0)) for c in queries) * 1000,
            len(queries),
        ]
        return WSGIRequestHandler.log_message(self, format, *args)
