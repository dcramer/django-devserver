from devserver.models import MODULES


class DevServerMiddleware(object):
    def should_process(self, request):
        from django.conf import settings

        if getattr(settings, 'STATIC_URL', None) and request.build_absolute_uri().startswith(request.build_absolute_uri(settings.STATIC_URL)):
            return False

        if settings.MEDIA_URL and request.build_absolute_uri().startswith(request.build_absolute_uri(settings.MEDIA_URL)):
            return False

        if getattr(settings, 'ADMIN_MEDIA_PREFIX', None) and request.path.startswith(settings.ADMIN_MEDIA_PREFIX):
            return False

        if request.path == '/favicon.ico':
            return False

        for path in getattr(settings, 'DEVSERVER_IGNORED_PREFIXES', []):
            if request.path.startswith(path):
                return False

        return True

    def process_request(self, request):
        # Set a sentinel value which process_response can use to abort when
        # another middleware app short-circuits processing:
        request._devserver_active = True

        self.process_init(request)

        if self.should_process(request):
            for mod in MODULES:
                mod.process_request(request)

    def process_response(self, request, response):
        # If this isn't set, it usually means that another middleware layer
        # has returned an HttpResponse and the following middleware won't see
        # the request. This happens most commonly with redirections - see
        # https://github.com/dcramer/django-devserver/issues/28 for details:
        if not getattr(request, "_devserver_active", False):
            return response

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
        #return view_func(request, *view_args, **view_kwargs)

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
