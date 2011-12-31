import json

from devserver.modules import DevServerModule
from devserver import settings


class AjaxDumpModule(DevServerModule):
    """
    Dumps the content of all AJAX responses.
    """

    logger_name = 'ajax'

    def process_response(self, request, response):
        if request.is_ajax():
            # Let's do a quick test to see what kind of response we have
            if len(response.content) < settings.DEVSERVER_AJAX_CONTENT_LENGTH:
                content = response.content
                if settings.DEVSERVER_AJAX_PRETTY_PRINT:
                    content = json.dumps(json.loads(content), indent=4)
                self.logger.info(content)
