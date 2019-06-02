.. _ref-templatetags:

.. index::
   pair: Filters; Templatetags

=========================
Filters and template tags
=========================

Django-comments-tree provides 5 template tags and 3 filters. Load the module to make use of them in your templates::

    {% load comments_tree %}

.. contents:: Table of Contents
   :depth: 1
   :local:
    

.. index::
   single: render_treecomment_tree
   pair: tag; render_treecomment_tree

.. templatetag:: render_treecomment_tree

.. _render-treecomment-tree:
                 
Tag ``render_treecomment_tree``
==============================

Tag syntax:

   .. code-block:: html+django

       {% render_treecomment_tree [for <object>] [with var_name_1=<obj_1> var_name_2=<obj_2>]
                                 [allow_flagging] [allow_feedback] [show_feedback]
                                 [using <template>] %}


Renders the threaded structure of comments posted to the given object using the first template found from the list:

 * ``django_comments_tree/<app>/<model>/comment_tree.html``
 * ``django_comments_tree/<app>/comment_tree.html``
 * ``django_comments_tree/comment_tree.html`` (provided with the app)

It expects either an object specified with the ``for <object>`` argument, or a variable named ``comments``, which might be present in the context or received as ``comments=<comments-object>``. When the ``for <object>`` argument is specified, it retrieves all the comments posted to the given object, ordered by the ``submit_date`` within the thread, as stated by the setting :setting:`COMMENTS_TREE_LIST_ORDER`.

It supports 4 optional arguments:

 * ``allow_flagging``, enables the comment removal suggestion flag. Clicking on the removal suggestion flag redirects to the login view whenever the user is not authenticated.
 * ``allow_feedback``, enables the like and dislike flags. Clicking on any of them redirects to the login view whenever the user is not authenticated.
 * ``show_feedback``, shows two list of users, of those who like the comment and of those who don't like it. By overriding ``includes/django_comments_tree/user_feedback.html`` you could show the lists only to authenticated users.
 * ``using <template_path>``, makes the templatetag use a different template, instead of the default one, ``django_comments_tree/comment_tree.html``

Example usage
-------------

In the usual scenario the tag is used in the object detail template, i.e.: ``blog/article_detail.html``, to include all comments posted to the article, in a tree structure:

   .. code-block:: html+django

       {% render_treecomment_tree for article allow_flagging allow_feedback show_feedback  %}


   
       
.. index::
   single: get_treecomment_tree
   pair: tag; get_treecomment_tree

.. templatetag:: get_treecomment_tree

Tag ``get_treecomment_tree``
===========================

Tag syntax:

   .. code-block:: html+django

       {% get_treecomment_tree for [object] as [varname] [with_feedback] %}


Returns a dictionary to the template context under the name given in ``[varname]`` with the comments posted to the given ``[object]``. The dictionary has the form:

   .. code-block:: python

       {
           'comment': treecomment_object,
           'children': [ list_of_child_xtdcomment_dicts ]
       }

The comments will be ordered by the ``submit_date`` within the thread, as stated by the setting :setting:`COMMENTS_TREE_LIST_ORDER`.

When the optional argument ``with_feedback`` is specified the returned dictionary will contain two additional attributes with the list of users who liked the comment and the list of users who disliked it:

   .. code-block:: python

       {
           'treecomment': treecomment_object,
           'children': [ list_of_child_xtdcomment_dicts ],
           'likedit': [user_a, user_b, ...],
           'dislikedit': [user_n, user_m, ...]
       }

       
Example usage
-------------

Get an ordered dictionary with the comments posted to a given blog story and store the dictionary in a template context variabled called ``comment_tree``:

   .. code-block:: html+django

       {% get_treecomment_tree for story as comments_tree with_feedback %}


.. index::
   single: render_last_treecomments
   pair: tag; render_last_treecomments

.. _render-last-treecomments:

Tag ``render_last_treecomments``
===============================

Tag syntax::

    {% render_last_treecomments [N] for [app].[model] [[app].[model] ...] %}

Renders the list of the last N comments for the given pairs ``<app>.<model>`` using the following search list for templates:

 * ``django_comments_tree/<app>/<model>/comment.html``
 * ``django_comments_tree/<app>/comment.html``
 * ``django_comments_tree/comment.html``

Example usage
-------------

Render the list of the last 5 comments posted, either to the blog.story model or to the blog.quote model. See it in action in the *Multiple Demo Site*, in the *blog homepage*, template ``blog/homepage.html``::

    {% render_last_treecomments 5 for blog.story blog.quote %}


.. index::
   single: get_last_treecomments
   pair: tag; get_last_treecomments

Tag ``get_last_treecomments``
============================

Tag syntax::

    {% get_last_treecomments [N] as [varname] for [app].[model] [[app].[model] ...] %}

Gets the list of the last N comments for the given pairs ``<app>.<model>`` and stores it in the template context whose name is defined by the ``as`` clause.

Example usage
-------------

Get the list of the last 10 comments two models, ``Story`` and ``Quote``, have received and store them in the context variable ``last_10_comment``. You can then loop over the list with a ``for`` tag::

    {% get_last_treecomments 10 as last_10_comments for blog.story blog.quote %}
    {% if last_10_comments %}
      {% for comment in last_10_comments %}
        <p>{{ comment.comment|linebreaks }}</p> ...
      {% endfor %}
    {% else %}
      <p>No comments</p>
    {% endif %}


    
.. index::
   single: get_treecomment_count
   pair: tag; get_treecomment_count

.. templatetag:: get_treecomment_count

Tag ``get_treecomment_count``
============================

Tag syntax::

    {% get_treecomment_count as [varname] for [app].[model] [[app].[model] ...] %}

Gets the comment count for the given pairs ``<app>.<model>`` and populates the template context with a variable containing that value, whose name is defined by the ``as`` clause.


Example usage
-------------

Get the count of comments the model ``Story`` of the app ``blog`` have received, and store it in the context variable ``comment_count``::

    {% get_treecomment_count as comment_count for blog.story %}

Get the count of comments two models, ``Story`` and ``Quote``, have received and store it in the context variable ``comment_count``::

    {% get_treecomment_count as comment_count for blog.story blog.quote %}


.. index::
   single: tree_comment_gravatar

.. templatetag:: tree_comment_gravatar

Filter ``tree_comment_gravatar``
===============================

Filter syntax::

  {{ comment.email|tree_comment_gravatar }}

A simple gravatar filter that inserts the `gravatar <http://www.gravatar.com/>`_ image associated to an email address.

This filter has been named ``tree_comment_gravatar`` as oposed to simply ``gravatar`` to avoid potential name collisions with other gravatar filters the user might have opted to include in the template.


.. index::
   single: tree_comment_gravatar_url

.. templatetag:: tree_comment_gravatar_url

Filter ``tree_comment_gravatar_url``
===================================

Filter syntax::

  {{ comment.email|tree_comment_gravatar_url }}

A simple gravatar filter that inserts the `gravatar URL <http://www.gravatar.com/>`_ associated to an email address.

This filter has been named ``tree_comment_gravatar_url`` as oposed to simply ``gravatar_url`` to avoid potential name collisions with other gravatar filters the user might have opted to include in the template.


.. index::
   single: render_markup_comment, Markdown; reStructuredText
   pair: filter; render_markup_comment

.. templatetag:: render_markup_comment
   
Filter ``render_markup_comment``
================================

Filter syntax:

   .. code-block:: html+django

       {{ comment.comment|render_markup_comment }}


Renders a comment using a markup language specified in the first line of the comment. It uses `django-markup <https://github.com/bartTC/django-markup>`_ to parse the comments with a markup language parser and produce the corresponding output.

Example usage
-------------

A comment posted with a content like:

   .. code-block:: text

       #!markdown
       An [example](http://url.com/ "Title")

Would be rendered as a markdown text, producing the output:

   .. code-block:: html
       
       <p><a href="http://url.com/" title="Title">example</a></p>

Available markup languages are:

 * `Markdown <http://daringfireball.net/projects/markdown/syntax>`_, when starting the comment with ``#!markdown``.
 * `reStructuredText <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_, when starting the comment with ``#!restructuredtext``.
 * Linebreaks, when starting the comment with ``#!linebreaks``.
