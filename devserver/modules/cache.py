from django.core.cache import cache

from devserver.modules import DevServerModule


class CacheSummaryModule(DevServerModule):
    """
    Outputs a summary of cache events once a response is ready.
    """
    real_time = False

    logger_name = 'cache'

    attrs_to_track = ['set', 'get', 'delete', 'add', 'get_many']

    def process_init(self, request):
        from devserver.utils.stats import track

        # save our current attributes
        self.old = dict((k, getattr(cache, k)) for k in self.attrs_to_track)

        for k in self.attrs_to_track:
            setattr(cache, k, track(getattr(cache, k), 'cache', self.logger if self.real_time else None))

    def process_complete(self, request):
        from devserver.utils.stats import stats

        calls = stats.get_total_calls('cache')
        hits = stats.get_total_hits('cache')
        misses = stats.get_total_misses_for_function('cache', cache.get) + stats.get_total_misses_for_function('cache', cache.get_many)

        if calls and (hits or misses):
            ratio = int(hits / float(misses + hits) * 100)
        else:
            ratio = 100

        if not self.real_time:
            self.logger.info('%(calls)s calls made with a %(ratio)d%% hit percentage (%(misses)s misses)' % dict(
                calls=calls,
                ratio=ratio,
                hits=hits,
                misses=misses,
            ), duration=stats.get_total_time('cache'))

        # set our attributes back to their defaults
        for k, v in self.old.iteritems():
            setattr(cache, k, v)


class CacheRealTimeModule(CacheSummaryModule):
    real_time = True
