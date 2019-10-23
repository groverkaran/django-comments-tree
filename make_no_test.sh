#!/bin/bash

version=$(sed 's/__version__ = "\(.*\)"/\1/' django_comments_tree/version.py)
git tag --force $version && git push && git push --tags --force

python setup.py sdist
twine upload dist/* && rm dist/*
