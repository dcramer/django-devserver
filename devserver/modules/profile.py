from devserver.modules import DevServerModule
from devserver.utils.time import ms_from_timedelta

from datetime import datetime

class ProfileSummaryModule(DevServerModule):
    """
    Outputs a summary of cache events once a response is ready.
    """

    logger_name = 'profile'
    
    def process_init(self, request):
        self.start = datetime.now()

    def process_complete(self, request):
        duration = datetime.now() - self.start
        
        self.logger.info('Total time to render was %.2fs', ms_from_timedelta(duration) / 1000)