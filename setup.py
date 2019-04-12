import sys

from setuptools import setup, find_packages
from setuptools.command.test import test


def run_tests(*args):
    from django_comments_tree.tests import run_tests
    errors = run_tests()
    if errors:
        sys.exit(1)
    else:
        sys.exit(0)


test.run_tests = run_tests


setup(
    name="django-comments-tree",
    version="0.1.0",
    packages=find_packages(),
    scripts=[],
    include_package_data=True,
    license="MIT",
    description=("Django Comments Framework extension app with django-treebeard "
                 "support, follow up notifications and email "
                 "confirmations."),
    long_description=("A reusable Django app that uses django-treebeards to create a threaded"
                      "comments Framework, following up "
                      "notifications and comments that only hits the "
                      "database after users confirm them by email."),
    author="Ed Henderson",
    author_email="ed@sharpertool.com",
    maintainer="Ed Henderson",
    maintainer_email="ed@sharpertool.com",
    keywords="django comments treebeard threaded",
    url="http://pypi.python.org/pypi/django-comments-tree",
    project_urls={

    },
    install_requires=[
        'Django>=2.0',
        'django-treebeard>=4.1.0',
        'django-contrib-comments>=1.8',
        'djangorestframework>=3.6',
        'docutils',
        'six',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Framework :: Django',
        'Natural Language :: English',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
    ],
    test_suite="dummy",
    zip_safe=True
)
