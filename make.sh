#!/bin/bash

flake8 django_comments_tree
if [ $? -ne 0 ]
then
    echo "Flake 8 failed"
    exit 1
fi

tox -epy37-django210,py37-django220,py38-django210,py38-django220
if [ $? -ne 0 ]
then
    echo "Tox tests failed. Please review"
    exit 2
fi

version=$(sed 's/__version__ = "\(.*\)"/\1/' django_comments_tree/version.py)
git tag --force $version && git push && git push --tags --force

python setup.py sdist
twine upload dist/* && rm dist/*
