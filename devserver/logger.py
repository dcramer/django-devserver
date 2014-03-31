import logging
import re
import datetime

from django.utils.encoding import smart_str
from django.core.management.color import color_style
from django.utils import termcolors


_bash_colors = re.compile(r'\x1b\[[^m]*m')


def strip_bash_colors(string):
    return _bash_colors.sub('', string)


class GenericLogger(logging.LoggerAdapter):

    def __init__(self, logger, extra):
        if extra:
            self.module = extra.get('module', '')

        if self.module:
            self.logger = logging.getLogger(self.module.logger_name)
        else:
            self.logger = logger

        self.extra = extra
        self.style = color_style()

    def process(self, message, kwargs):
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

        return '    %s %s' % (tpl, '\n'.join(new_message)), kwargs
