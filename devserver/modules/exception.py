from devserver.modules import DevServerModule

class ExceptionModule(DevServerModule):
    """
    Logs view exceptions.
    """

    logger_name = 'exception'

    def process_exception(self, request, exception):
        self.logger.error(exception)
