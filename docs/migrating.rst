.. _ref-migrating:

================================
Migrating to django-comments-tree
================================

If your project uses django-contrib-comments you can easily plug django-comments-tree to add extra functionalities like comment confirmation by mail, comment threading and follow-up notifications.

This section describes how to make django-comments-tree take over comments support in a project in which django-contrib-comments tables have received data already.


Preparation
===========

First of all, install django-comments-tree:

   .. code-block:: bash

       (venv)$ cd mysite
       (venv)$ pip install django-comments-tree

Then edit the settings module and change your :setting:`INSTALLED_APPS` so that django_comments_tree and django_comments are listed in this order. Also change the :setting:`COMMENTS_APP` and add the ``EMAIL_*`` settings to be able to send mail messages:

   .. code-block:: python

       INSTALLED_APPS = [
           ...
           'django_comments_tree',
           'django_comments',
           ...
       ]
       ...
       COMMENTS_APP = 'django_comments_tree'

       # Either enable sending mail messages to the console:
       EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

       # Or set up the EMAIL_* settings so that Django can send emails:
       EMAIL_HOST = "smtp.mail.com"
       EMAIL_PORT = "587"
       EMAIL_HOST_USER = "alias@mail.com"
       EMAIL_HOST_PASSWORD = "yourpassword"
       EMAIL_USE_TLS = True
       DEFAULT_FROM_EMAIL = "Helpdesk <helpdesk@yourdomain>"


Edit the urls module of the project and mount django_comments_tree's URLs in the path in which you had django_comments' URLs, django_comments_tree's URLs includes django_comments':

   .. code-block:: python

       from django.conf.urls import include, url

       urlpatterns = [
           ...
           url(r'^comments/', include('django_comments_tree.urls')),
           ...
       ]


Now create the tables for django-comments-tree:

   .. code-block:: bash

       (venv)$ python manage.py migrate

       
Populate comment data
=====================

The following step will populate **TreeComment**'s table with data from the **Comment** model. For that purpose you can use the ``populate_xtdcomments`` management command:

   .. code-block:: bash

       (venv)$ python manage.py populate_xtdcomments
       Added 3468 TreeComment object(s).

You can pass as many DB connections as you have defined in :setting:`DATABASES` and the command will run in each of the databases, populating the **TreeComment**'s table with data from the comments table existing in each database.

Now the project is ready to handle comments with django-comments-tree.
