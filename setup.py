import os
from setuptools import setup, find_packages

setup(name='django-devserver',
    version=".".join(map(str, __import__("devserver").__version__)),
    description='Drop-in replacement for Django\'s runserver',
    author='David Cramer',
    author_email='dcramer@gmail.com',
    url='http://github.com/dcramer/django-devserver',
    packages=find_packages(),
    classifiers=[
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Operating System :: OS Independent",
        "Topic :: Software Development"
    ],
)
