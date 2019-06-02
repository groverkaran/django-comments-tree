.. django-comments-tree documentation master file, created by
   sphinx-quickstart on Mon Dec 19 19:20:12 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=====================
django-comments-tree
=====================

.. module:: django_comments_tree
   :synopsis: django-comments-extended.

.. highlightlang:: html+django

A Django pluggable application that adds comments to your project. It extends the once official `Django Comments Framework <https://pypi.python.org/pypi/django-contrib-comments>`_ with the following features:

.. index::
   single: Features

#. Comments model based on `django-treebeard <https://pypi.python.org/pypi/django-treebeard>`_ to provide a robust and fast threaded and nested comment structure.
#. Efficiently associate a comment tree with any model through a link table which avoids populating each comment with extra link data.
#. Customizable maximum thread level, either for all models or on a per app.model basis.
#. Optional notifications on follow-up comments via email.
#. Mute links to allow cancellation of follow-up notifications.
#. Comment confirmation via email when users are not authenticated.
#. Comments hit the database only after they have been confirmed.
#. Registered users can like/dislike comments and can suggest comments removal.
#. Template tags to list/render the last N comments posted to any given list of app.model pairs.
#. Emails sent through threads (can be disable to allow other solutions, like a Celery app).
#. Fully functional JavaScript plugin using ReactJS, jQuery, Bootstrap, Remarkable and MD5.

.. image:: images/cover.png
    
Contents
========
   
.. toctree::
   :maxdepth: 1

   quickstart
   tutorial
   example
   logic
   webapi
   javascript
   templatetags
   migrating
   extending
   i18n
   settings
   templates
