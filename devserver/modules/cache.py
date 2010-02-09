from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.core.cache import cache

from devserver.modules import DevServerModule

class CacheSummaryModule(DevServerModule):
    """
    Outputs a summary of cache events once a response is ready.
    """

    logger_name = 'cache'

    attrs_to_track = ['set', 'get', 'delete', 'add', 'get_many']
    
    def process_init(self):
        from devserver.utils.stats import track

        # save our current attributes
        self.old = dict((k, getattr(cache, k)) for k in self.attrs_to_track)

        for k in self.attrs_to_track:
            setattr(cache, k, track(getattr(cache, k), 'cache'))

    def process_complete(self):
        from devserver.utils.stats import stats

        self.logger.info('%(calls)s calls; %(hits)s hits; %(misses)s misses' % dict(
            calls = stats.get_total_calls('cache'),
            hits = stats.get_total_hits('cache'),
            misses = stats.get_total_misses_for_function('cache', cache.get) + stats.get_total_misses_for_function('cache', cache.get_many),
            gets = stats.get_total_calls_for_function('cache', cache.get),
            sets = stats.get_total_calls_for_function('cache', cache.set),
            get_many = stats.get_total_calls_for_function('cache', cache.get_many),
            deletes = stats.get_total_calls_for_function('cache', cache.delete),
            #cache_calls_list = [(c['time'], c['func'].__name__, c['args'], c['kwargs'], simplejson.dumps(c['stack'])) for c in stats.get_calls('cache')],
        ), duration=stats.get_total_time('cache'))

        # set our attributes back to their defaults
        for k, v in self.old.iteritems():
            setattr(cache, k, v)
        