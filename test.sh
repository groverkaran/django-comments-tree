#!/bin/bash

flake8 django_comments_tree
if [ $? -ne 0 ]
then
    echo "Flake 8 failed"
    exit 1
fi

tox -epy37-django210,py37-django220
if [ $? -ne 0 ]
then
    echo "tox failed"
    #exit 2
fi
