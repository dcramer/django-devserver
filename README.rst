-----
About
-----

A drop in replacement for Django's built-in runserver command. Features include:

* An extendable interface for handling things such as real-time logging.
* Integration with the werkzeug interactive debugger.
* Threaded (default) and multi-process development servers.
* Ability to specify a WSGI application as your target environment.

------------
Installation
------------

To install the latest stable version::

	pip install git+git://github.com/dcramer/django-devserver#egg=django-devserver


django-devserver has some optional dependancies, which we highly recommend installing.

* ``pip install sqlparse`` -- pretty SQL formatting
* ``pip install werkzeug`` -- interactive debugger
* ``pip install guppy`` -- tracks memory usage (required for MemoryUseModule)
* ``pip install line_profiler`` -- does line-by-line profiling (required for LineProfilerModule)

You will need to include ``devserver`` in your ``INSTALLED_APPS``::

	INSTALLED_APPS = (
	    ...
	    'devserver',            
	)

-----
Usage
-----

Once installed, using the new runserver replacement is easy. You must specify verbosity of 0 to disable real-time log output::

	python manage.py runserver

Note: This will force ``settings.DEBUG`` to ``True``.

By default, ``devserver`` would bind itself to 127.0.0.1:8000. To change this default, ``DEVSERVER_DEFAULT_ADDR`` and ``DEVSERVER_DEFAULT_PORT`` settings are available. 

Additional CLI Options
~~~~~~~~~~~~~~~~~~~~~~

--werkzeug
  Tells Django to use the Werkzeug interactive debugger, instead of it's own.

--forked
  Use a forking (multi-process) web server instead of threaded.

--dozer
  Enable the dozer memory debugging middleware (at /_dozer)

--wsgi-app
  Load the specified WSGI app as the server endpoint.

Please see ``python manage.py runserver --help`` for more information additional options.

Note: You may also use devserver's middleware outside of the management command::

	MIDDLEWARE_CLASSES = (
	    'devserver.middleware.DevServerMiddleware',
	)

-------------
Configuration
-------------

The following options may be configured via your ``settings.py``:

DEVSERVER_ARGS = []
  Additional command line arguments to pass to the ``runserver`` command (as defaults).

DEVSERVER_DEFAULT_ADDR = '127.0.0.1'
  The default address to bind to.

DEVSERVER_DEFAULT_PORT = '8000'
  The default port to bind to.

DEVSERVER_WSGI_MIDDLEWARE
  A list of additional WSGI middleware to apply to the ``runserver`` command.

DEVSERVER_MODULES = []
  A list of devserver modules to load.

DEVSERVER_IGNORED_PREFIXES = ['/media', '/uploads']
  A list of prefixes to surpress and skip process on. By default, ``ADMIN_MEDIA_PREFIX``, ``MEDIA_URL`` and ``STATIC_URL`` (for Django >= 1.3) will be ignored (assuming ``MEDIA_URL`` and ``STATIC_URL`` is relative)::


-------
Modules
-------

django-devserver includes several modules by default, but is also extendable by 3rd party modules. This is done via the ``DEVSERVER_MODULES`` setting::

	DEVSERVER_MODULES = (
	    'devserver.modules.sql.SQLRealTimeModule',
	    'devserver.modules.sql.SQLSummaryModule',
	    'devserver.modules.profile.ProfileSummaryModule',
	
	    # Modules not enabled by default
	    'devserver.modules.ajax.AjaxDumpModule',
	    'devserver.modules.profile.MemoryUseModule',
	    'devserver.modules.cache.CacheSummaryModule',
	    'devserver.modules.profile.LineProfilerModule',
	)

devserver.modules.sql.SQLRealTimeModule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Outputs queries as they happen to the terminal, including time taken.
  
Disable SQL query truncation (used in SQLRealTimeModule) with the ``DEVSERVER_TRUNCATE_SQL`` setting::
  
	DEVSERVER_TRUNCATE_SQL = False

devserver.modules.sql.SQLSummaryModule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Outputs a summary of your SQL usage.

devserver.modules.profile.ProfileSummaryModule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Outputs a summary of the request performance.

devserver.modules.profile.MemoryUseModule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Outputs a notice when memory use is increased (at the end of a request cycle).

devserver.modules.profile.LineProfilerModule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Profiles view methods on a line by line basis. There are 2 ways to profile your view functions, by setting setting.DEVSERVER_AUTO_PROFILE = True or by decorating the view functions you want profiled with devserver.modules.profile.devserver_profile. The decoration takes an optional argument ``follow`` which is a sequence of functions that are called by your view function that you would also like profiled.

An example of a decorated function::
  
	@devserver_profile(follow=[foo, bar])
	def home(request):
	    result['foo'] = foo()
	    result['bar'] = bar()

When using the decorator, we recommend that rather than import the decoration directly from devserver that you have code somewhere in your project like::

	try:
	    if 'devserver' not in settings.INSTALLED_APPS:
	        raise ImportError
	    from devserver.modules.profile import devserver_profile
	except ImportError:
	    class devserver_profile(object):
	        def __init__(self, *args, **kwargs):
	            pass
	        def __call__(self, func):
	            def nothing(*args, **kwargs):
	                return func(*args, **kwargs)
	            return wraps(func)(nothing)

By importing the decoration using this method, devserver_profile will be a pass through decoration if you aren't using devserver (eg in production)


devserver.modules.cache.CacheSummaryModule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Outputs a summary of your cache calls at the end of the request.

devserver.modules.ajax.AjaxDumpModule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Outputs the content of any AJAX responses
  
Change the maximum response length to dump with the ``DEVSERVER_AJAX_CONTENT_LENGTH`` setting::

	DEVSERVER_AJAX_CONTENT_LENGTH = 300

devserver.modules.request.SessionInfoModule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Outputs information about the current session and user.

----------------
Building Modules
----------------

Building modules in devserver is quite simple. In fact, it resembles the middleware API almost identically.

Let's take a sample module, which simple tells us when a request has started, and when it has finished::

	from devserver.modules import DevServerModule
	
	class UselessModule(DevServerModule):
	    logger_name = 'useless'
	    
	    def process_request(self, request):
	        self.logger.info('Request started')
	    
	    def process_response(self, request, response):
	        self.logger.info('Request ended')

There are additional arguments which may be sent to logger methods, such as ``duration``::

	# duration is in milliseconds
	self.logger.info('message', duration=13.134)
