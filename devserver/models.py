import django
from django.core import exceptions
from django.core.exceptions import ImproperlyConfigured

from devserver.logger import GenericLogger
import logging


MODULES = []


def check_installed_apps_configuration():
    """
    Check the app is put in correct order in INSTALLED_APPS

    django.contrib.staticfiles runserver command is likely to
    override devserver management command if put in wrong order.

    Django had reversed order of management commands collection prior to 1.7
    https://code.djangoproject.com/ticket/16599
    """
    from django.conf import settings
    try:
        staticfiles_index = settings.INSTALLED_APPS.index('django.contrib.staticfiles')
        devserver_index = settings.INSTALLED_APPS.index('devserver')
    except ValueError:
        pass
    else:
        latest_app_overrides = django.VERSION < (1, 7)
        if devserver_index < staticfiles_index and latest_app_overrides:
            logging.error(
                'Put "devserver" below "django.contrib.staticfiles" in INSTALLED_APPS to make it work')
        elif devserver_index > staticfiles_index and not latest_app_overrides:
            logging.error(
                'Put "devserver" above "django.contrib.staticfiles" in INSTALLED_APPS to make it work')


def load_modules():
    global MODULES

    MODULES = []

    from devserver import settings

    for path in settings.DEVSERVER_MODULES:
        try:
            name, class_name = path.rsplit('.', 1)
        except ValueError:
            raise exceptions.ImproperlyConfigured("%s isn\'t a devserver module" % path)

        try:
            module = __import__(name, {}, {}, [''])
        except ImportError as e:
            raise exceptions.ImproperlyConfigured("Error importing devserver module %s: %s" % (name, e))

        try:
            cls = getattr(module, class_name)
        except AttributeError:
            raise exceptions.ImproperlyConfigured("Error importing devserver module %s does not define a %s class" % (name, class_name))

        try:
            instance = cls(GenericLogger(cls))
        except:
            raise  # Bubble up problem loading panel

        MODULES.append(instance)

if not MODULES:
    check_installed_apps_configuration()
    load_modules()
