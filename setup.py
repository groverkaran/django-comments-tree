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
    version="0.1.0a3",
    packages=find_packages(),
    scripts=[],
    include_package_data=True,
    license="MIT",
    description=("Django Comments Framework extension app with django-treebeard "
                 "support, follow up notifications and email "
                 "confirmations, as well as real-time comments using Firebase "
                 "for notifications."),
    long_description=("A reusable Django app that uses django-treebeard "
                      "to create a threaded"
                      "comments Framework, following up "
                      "notifications and comments that only hits the "
                      "database after users confirm them by email."
                      "Real-time comment updates are also available using "
                      "Django channels as a notification mechanism of comment updates. "
                      "Clients can connect to channels for updates, and then query "
                      "the backend for the actual changes, so that all data is "
                      "located in the backend database."
                      ),
    author="Ed Henderson",
    author_email="ed@sharpertool.com",
    maintainer="Ed Henderson",
    maintainer_email="ed@sharpertool.com",
    keywords="django comments treebeard threaded django-channels websockets",
    url="https://github.com/sharpertool/django-comments-tree",
    project_urls={
        'Original Package': 'https://github.com/danirus/django-comments-xtd',
    },
    python_requires='>=3.5',
    install_requires=[
        'Django>=2.0',
        'django-treebeard>=4.1.0',
        'django-contrib-comments>=1.8',
        'djangorestframework>=3.6',
        'django-markupfield>=1.5.1',
        'markdown>=3.1.1',
        'docutils',
        'six',
    ],
    extras_requires=[
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Framework :: Django',
        'Natural Language :: English',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
    ],
    test_suite="dummy",
    zip_safe=True
)
