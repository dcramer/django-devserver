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
        
    def handle_session_save(self, *args, **kwargs):
        self._save(*args, **kwargs)
        self.logger.info('Session %s has been saved.', self.session.session_key)