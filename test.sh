#!/bin/bash

flake8 django_comments_tree
if [ $? -ne 0 ]
then
    echo "Flake 8 failed"
    exit 1
fi

tox
if [ $? -ne 0 ]
then
    echo "tox failed"
    #exit 2
fi
