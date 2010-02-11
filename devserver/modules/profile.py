from devserver.modules import DevServerModule
from devserver.utils.time import ms_from_timedelta

from datetime import datetime

import gc

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

class LeftOversModule(DevServerModule):
    """
    Outputs a summary of events the garbage collector couldn't handle.
    """
    # TODO: Not even sure this is correct, but the its a general idea

    logger_name = 'profile'
    
    def process_init(self, request):
        gc.enable()
        gc.set_debug(gc.DEBUG_SAVEALL)

    def process_complete(self, request):
        gc.collect()
        self.logger.info('%s objects left in garbage', len(gc.garbage))

from django.template.defaultfilters import filesizeformat

try:
    from guppy import hpy
except ImportError:
    import warnings

    class MemoryUseModule(DevServerModule):
        def __new__(cls, *args, **kwargs):
            warnings.warn('MemoryUseModule requires guppy to be installed.')
            return super(MemoryUseModule, cls).__new__(cls)
else:
    class MemoryUseModule(DevServerModule):
        """
        Outputs a summary of memory usage of the course of a request.
        """
        logger_name = 'profile'
    
        def process_init(self, request):
            from guppy import hpy
        
            self.usage = 0

            self.heapy = hpy()
            self.heapy.setrelheap()

        def process_complete(self, request):
            h = self.heapy.heap()
        
            if h.domisize > self.usage:
                self.usage = h.domisize
        
            if self.usage:
                self.logger.info('Memory usage was increased by %s', filesizeformat(self.usage))
    
