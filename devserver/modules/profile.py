from devserver.modules import DevServerModule
from devserver.utils.time import ms_from_timedelta

from datetime import datetime

import functools
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

try:
    from line_profiler import LineProfiler
except ImportError:
    class LineProfilerModule(DevServerModule):
        
        def __new__(cls, *args, **kwargs):
            warnings.warn('LineProfilerModule requires line_profiler to be installed.')
            return super(LineProfilerModule, cls).__new__(cls)

        class devserver_profile(object):
            def __init__(self, follow=[]):
                pass
            def __call__(self, func):
                return func
else:
    class LineProfilerModule(DevServerModule):
        """
        Outputs a Line by Line profile of any @profile'd functions that were run
        """
        logger_name = 'profile'

        def process_init(self, request):
            request.devserver_profiler = LineProfiler()
            request.devserver_profiler_run = False

        def process_complete(self, request):
            from cStringIO import StringIO
            out = StringIO()
            if hasattr(request,'devserver_profiler_run') and request.devserver_profiler_run:
                request.devserver_profiler.print_stats(stream=out)
                self.logger.info(out.getvalue())

    class devserver_profile(object):
        def __init__(self, follow=[]):
            self.follow = follow
            
        def __call__(self, func):
            def profiled_func(request, *args, **kwargs):
                try:
                    request.devserver_profiler.add_function(func)
                    request.devserver_profiler_run = True
                    for f in self.follow:
                        request.devserver_profiler.add_function(f)
                    request.devserver_profiler.enable_by_count()
                    retval = func(request, *args, **kwargs)
                finally:
                    request.devserver_profiler.disable_by_count()
                return retval
            return functools.wraps(func)(profiled_func)
    
        