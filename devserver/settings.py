from django.conf import settings

DEVSERVER_MODULES = getattr(settings, 'DEVSERVER_MODULES', (
    'devserver.modules.sql.SQLRealTimeModule',
    'devserver.modules.sql.SQLSummaryModule',
    'devserver.modules.profile.ProfileSummaryModule',
    # 'devserver.modules.request.SessionInfoModule',
    # 'devserver.modules.profile.MemoryUseModule',
    # 'devserver.modules.profile.LeftOversModule',
    # 'devserver.modules.cache.CacheSummaryModule',
))

DEVSERVER_TRUNCATE_SQL = getattr(settings, 'DEVSERVER_TRUNCATE_SQL', True)

# This variable gets set to True when we're running the devserver
DEVSERVER_ACTIVE = False

DEVSERVER_AJAX_CONTENT_LENGTH = getattr(settings, 'DEVSERVER_AJAX_CONTENT_LENGTH', 300)