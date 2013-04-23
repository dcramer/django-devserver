from devserver.modules import DevServerModule
from devserver.utils.time import ms_from_timedelta
from devserver.settings import DEVSERVER_AUTO_PROFILE

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

        def __init__(self, request):
            super(MemoryUseModule, self).__init__(request)
            self.hpy = hpy()
            self.oldh = self.hpy.heap()
            self.logger.info('heap size is %s', filesizeformat(self.oldh.size))

        def process_complete(self, request):
            newh = self.hpy.heap()
            alloch = newh - self.oldh
            dealloch = self.oldh - newh
            self.oldh = newh
            self.logger.info('%s allocated, %s deallocated, heap size is %s', *map(filesizeformat, [alloch.size, dealloch.size, newh.size]))

try:
    from line_profiler import LineProfiler
except ImportError:
    import warnings

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
        Outputs a Line by Line profile of any @devserver_profile'd functions that were run
        """
        logger_name = 'profile'

        def process_view(self, request, view_func, view_args, view_kwargs):
            request.devserver_profiler = LineProfiler()
            request.devserver_profiler_run = False
            if (DEVSERVER_AUTO_PROFILE):
                _unwrap_closure_and_profile(request.devserver_profiler, view_func)
                request.devserver_profiler.enable_by_count()

        def process_complete(self, request):
            if hasattr(request, 'devserver_profiler_run') and (DEVSERVER_AUTO_PROFILE or request.devserver_profiler_run):
                from cStringIO import StringIO
                out = StringIO()
                if (DEVSERVER_AUTO_PROFILE):
                    request.devserver_profiler.disable_by_count()
                request.devserver_profiler.print_stats(stream=out)
                self.logger.info(out.getvalue())

    def _unwrap_closure_and_profile(profiler, func):
        if not hasattr(func, 'func_code'):
            return
        profiler.add_function(func)
        if func.func_closure:
            for cell in func.func_closure:
                if hasattr(cell.cell_contents, 'func_code'):
                    _unwrap_closure_and_profile(profiler, cell.cell_contents)

    class devserver_profile(object):
        def __init__(self, follow=[]):
            self.follow = follow

        def __call__(self, func):
            def profiled_func(*args, **kwargs):
                request = args[0]
                if hasattr(request, 'request'):
                    # We're decorating a Django class-based-view and the first argument is actually self:
                    request = args[1]

                try:
                    request.devserver_profiler.add_function(func)
                    request.devserver_profiler_run = True
                    for f in self.follow:
                        request.devserver_profiler.add_function(f)
                    request.devserver_profiler.enable_by_count()
                    return func(*args, **kwargs)
                finally:
                    request.devserver_profiler.disable_by_count()

            return functools.wraps(func)(profiled_func)
