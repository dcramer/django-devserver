import urllib
from devserver.modules import DevServerModule

class SessionInfoModule(DevServerModule):
    """
    Displays information about the currently authenticated user and session.
    """

    logger_name = 'session'
    
    def process_request(self, request):
        self.has_session = bool(getattr(request, 'session', False))
        if self.has_session is not None:
            self._save = request.session.save
            self.session = request.session
            request.session.save = self.handle_session_save
    
    def process_response(self, request, response):
        if getattr(self, 'has_session', False):
            if getattr(request, 'user', None) and request.user.is_authenticated():
                user = '%s (id:%s)' % (request.user.username, request.user.pk)
            else:
                user = '(Anonymous)'
            self.logger.info('Session %s authenticated by %s', request.session.session_key, user)
            request.session.save = self._save
            self._save = None
            self.session = None
            self.has_session = False
        
    def handle_session_save(self, *args, **kwargs):
        self._save(*args, **kwargs)
        self.logger.info('Session %s has been saved.', self.session.session_key)

class RequestDumpModule(DevServerModule):
    """
    Dumps the request headers and variables.
    """

    logger_name = 'request'

    def process_request(self, request):
        req = self.logger.style.SQL_KEYWORD('%s %s %s\n' % (request.method, '?'.join((request.META['PATH_INFO'], request.META['QUERY_STRING'])), request.META['SERVER_PROTOCOL']))
        for var, val in request.META.items():
            if var.startswith('HTTP_'):
                var = var[5:].replace('_', '-').title()
                req += '%s: %s\n' % (self.logger.style.SQL_FIELD(var), val)
        if request.META['CONTENT_LENGTH']:
            req += '%s: %s\n' % (self.logger.style.SQL_FIELD('Content-Length'), request.META['CONTENT_LENGTH'])
        if request.POST:
            req += '\n%s\n' % self.logger.style.HTTP_INFO(urllib.urlencode(dict((k, v.encode('utf8')) for k,v in request.POST.items())))
        if request.FILES:
            req += '\n%s\n' % self.logger.style.HTTP_NOT_MODIFIED(urllib.urlencode(request.FILES))
        self.logger.info('Full request:\n%s', req)
