from devserver.modules import DevServerModule
from debug_toolbar_mongo import operation_tracker

class MongoDBSummaryModule(DevServerModule):
    """
    Outputs a summary NoSQL queries.
    """

    logger_name = 'mongodb'

    def __init__(self, *args, **kwargs):
        super(MongoDBSummaryModule, self).__init__(*args, **kwargs)
        operation_tracker.install_tracker()

    def process_init(self, request):
        operation_tracker.reset()

    def process_complete(self, request):
        attrs = ('queries', 'inserts', 'updates', 'removes')
        stats = dict(
            (attr, {
                'count': len(ops),
                'time': sum(op['time'] for op in ops)
            }) for attr, ops in (
                (attr, getattr(operation_tracker, attr)) for attr in attrs
            )
        )

        if any(stat['count'] for stat in stats.values()):
            total_time = sum(stat['time'] for stat in stats.values())
            self.logger.info(', '.join(
                '%(count)d %(name)s (%(time).2fms)' % dict(
                    count=stats[attr]['count'], name=attr, time=stats[attr]['time'],
                ) for attr in attrs
            ), duration=total_time)

