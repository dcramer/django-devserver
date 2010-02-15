from devserver.models import MODULES

class DevServerMiddleware(object):
    def should_process(self, request):
        from django.conf import settings
        
        if settings.MEDIA_URL and request.path.startswith(settings.MEDIA_URL):
            return False
        
        if settings.ADMIN_MEDIA_PREFIX and request.path.startswith(settings.ADMIN_MEDIA_PREFIX):
            return False
        
        if request.path == '/favicon.ico':
            return False
        
        return True
    
    def process_request(self, request):
        self.process_init(request)
        
        if self.should_process(request):
            for mod in MODULES:
                mod.process_request(request)
    
    def process_response(self, request, response):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_response(request, response)
        
        self.process_complete(request)
        
        return response
        
    def process_exception(self, request, exception):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_exception(request, exception)
        
    def process_view(self, request, view_func, view_args, view_kwargs):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_view(request, view_func, view_args, view_kwargs)
        return view_func(request, *view_args, **view_kwargs)

    def process_init(self, request):
        from devserver.utils.stats import stats
        
        stats.reset()
        
        if self.should_process(request):
            for mod in MODULES:
                mod.process_init(request)

    def process_complete(self, request):
        if self.should_process(request):
            for mod in MODULES:
                mod.process_complete(request)