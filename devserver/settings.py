from django.conf import settings

DEVSERVER_MODULES = getattr(settings, 'DEVSERVER_MODULES', (
    'devserver.modules.sql.SQLRealTimeModule',
    'devserver.modules.profile.ProfileSummaryModule',
    'devserver.modules.sql.SQLSummaryModule',
    # 'devserver.modules.profile.MemoryUseModule',
    # 'devserver.modules.profile.LeftOversModule',
    # 'devserver.modules.cache.CacheSummaryModule',
))

DEVSERVER_TRUNCATE_SQL = getattr(settings, 'DEVSERVER_TRUNCATE_SQL', True)

# This variable gets set to True when we're running the devserver
DEVSERVER_ACTIVE = False