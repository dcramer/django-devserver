from devserver.modules import DevServerModule

class SessionInfoModule(DevServerModule):
    """
    Displays information about the currently authenticated user and session.
    """

    logger_name = 'session'
    
    def process_response(self, request, response):
        if getattr(request, 'user', None) and request.user.is_authenticated():
            user = '%s (id:%s)' % (request.user.username, request.user.pk)
        else:
            user = '(Anonymous)'
        self.logger.info('Session %s authenticated by %s' % (request.session.session_key, user))