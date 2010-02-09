from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.core.cache import cache

from devserver.modules import DevServerModule
from devserver.utils.stats import track, get_stats

class CacheSummaryModule(DevServerModule):
    """
    Outputs a summary of cache events once a response is ready.
    """

    logger_name = 'cache'

    attrs_to_track = ['set', 'get', 'delete', 'add', 'get_many']
    old = {}
    
    def process_request(self, request):
        self.old = dict((k, getattr(cache, k)) for k in self.attrs_to_track)

        for k in self.attrs_to_track:
            setattr(cache, k, track(getattr(cache, k), 'cache'))

    def process_response(self, request, response):
        self.logger.info('total time %(time)s - %(calls)s calls; %(hits)s hits; %(misses)s misses' % dict(
            calls = get_stats().get_total_calls('cache'),
            time = get_stats().get_total_time('cache'),
            hits = get_stats().get_total_hits('cache'),
            misses = get_stats().get_total_misses_for_function('cache', cache.get) + get_stats().get_total_misses_for_function('cache', cache.get_many),
            gets = get_stats().get_total_calls_for_function('cache', cache.get),
            sets = get_stats().get_total_calls_for_function('cache', cache.set),
            get_many = get_stats().get_total_calls_for_function('cache', cache.get_many),
            deletes = get_stats().get_total_calls_for_function('cache', cache.delete),
            #cache_calls_list = [(c['time'], c['func'].__name__, c['args'], c['kwargs'], simplejson.dumps(c['stack'])) for c in get_stats().get_calls('cache')],
        ))

        for k, v in self.old.iteritems():
            setattr(cache, k, v)
        