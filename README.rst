A drop in replacement for Django's built-in runserver command. Features an extendable interface for handling things such as real-time logging.

Included modules:

* SQL: Outputs queries as they happen to the terminal, including time taken.

Installation
------------

To install the latest stable version::

	pip install git+git://github.com/dcramer/django-devserver#egg=django-devserver


You will need to include ``devserver`` in your ``INSTALLED_APPS``::

	INSTALLED_APPS = (
	    'devserver',
	    ...
	)

You may also specify additional modules to load via the ``DEVSERVER_MODULES`` setting::

	DEVSERVER_MODULES = (
	    'devserver.modules.sql.SQLModule',
	)

Usage
-----

Once installed, using the new runserver replacement is easy::

	python manage.py rundevserver