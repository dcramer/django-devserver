from devserver.modules import DevServerModule
from devserver.utils.time import ms_from_timedelta

from datetime import datetime

import gc

class ProfileSummaryModule(DevServerModule):
    """
    Outputs a summary of cache events once a response is ready.
    """

    logger_name = 'profile/summary'
    
    def process_init(self, request):
        self.start = datetime.now()

    def process_complete(self, request):
        duration = datetime.now() - self.start
        
        self.logger.info('Total time to render was %.2fs', ms_from_timedelta(duration) / 1000)

class LeftOversModule(DevServerModule):
    """
    Outputs a summary of events the garbage collector couldn't handle.
    
    """
    # TODO: Not even sure this is correct, but the its a general idea

    logger_name = 'profile/leftovers'
    
    def process_init(self, request):
        gc.enable()
        gc.set_debug(gc.DEBUG_SAVEALL)

    def process_complete(self, request):
        gc.collect()
        self.logger.info('%s objects left in garbage', len(gc.garbage))
    