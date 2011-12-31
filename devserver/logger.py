import logging
import sys
import re
import datetime

from django.utils.encoding import smart_str
from django.core.management.color import color_style
from django.utils import termcolors


_bash_colors = re.compile(r'\x1b\[[^m]*m')


def strip_bash_colors(string):
    return _bash_colors.sub('', string)


class GenericLogger(object):
    def __init__(self, module):
        self.module = module
        self.style = color_style()

    def log(self, message, *args, **kwargs):
        id = kwargs.pop('id', None)
        duration = kwargs.pop('duration', None)
        level = kwargs.pop('level', logging.INFO)

        tpl_bits = []
        if id:
            tpl_bits.append(self.style.SQL_FIELD('[%s/%s]' % (self.module.logger_name, id)))
        else:
            tpl_bits.append(self.style.SQL_FIELD('[%s]' % self.module.logger_name))
        if duration:
            tpl_bits.append(self.style.SQL_KEYWORD('(%dms)' % duration))

        if args:
            message = message % args

        message = smart_str(message)

        if level == logging.ERROR:
            message = self.style.ERROR(message)
        elif level == logging.WARN:
            message = self.style.NOTICE(message)
        else:
            try:
                HTTP_INFO = self.style.HTTP_INFO
            except:
                HTTP_INFO = termcolors.make_style(fg='red')
            message = HTTP_INFO(message)

        tpl = ' '.join(tpl_bits) % dict(
            id=id,
            module=self.module.logger_name,
            asctime=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )

        indent = ' ' * (len(strip_bash_colors(tpl)) + 1)

        new_message = []
        first = True
        for line in message.split('\n'):
            if first:
                new_message.append(line)
            else:
                new_message.append('%s%s' % (indent, line))
            first = False

        message = '%s %s' % (tpl, '\n'.join(new_message))

        sys.stdout.write('    ' + message + '\n')

    warn = lambda x, *a, **k: x.log(level=logging.WARN, *a, **k)
    info = lambda x, *a, **k: x.log(level=logging.INFO, *a, **k)
    debug = lambda x, *a, **k: x.log(level=logging.DEBUG, *a, **k)
    error = lambda x, *a, **k: x.log(level=logging.ERROR, *a, **k)
    critical = lambda x, *a, **k: x.log(level=logging.CRITICAL, *a, **k)
    fatal = lambda x, *a, **k: x.log(level=logging.FATAL, *a, **k)
