from datetime import datetime

from django.conf import settings
from werkzeug.serving import WSGIRequestHandler

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
        return super(SlimWSGIRequestHandler, self).handle(*args, **kwargs)

    def log(self, type, message, *args):
        if type != 'info':
            return super(SlimWSGIRequestHandler, self).log(type, message,
                                                           *args)

        duration = datetime.now() - self._start_request

        env = self.make_environ()

        for url in (getattr(settings, 'STATIC_URL', None), settings.MEDIA_URL):
            if not url:
                continue
            if self.path.startswith(url):
                return
            elif url.startswith('http:'):
                if (('http://%s%s' % (env['HTTP_HOST'], self.path))
                        .startswith(url)):
                    return

        for path in getattr(settings, 'DEVSERVER_IGNORED_PREFIXES', []):
            if self.path.startswith(path):
                return

        format = ' (time: %.2fs; sql: %dms (%dq))'
        queries = [
            q for alias in connections
            for q in connections[alias].queries
        ]
        message += format % (
            ms_from_timedelta(duration) / 1000,
            sum(float(c.get('time', 0)) for c in queries) * 1000,
            len(queries),
        )
        return super(SlimWSGIRequestHandler, self).log(type, message, *args)
