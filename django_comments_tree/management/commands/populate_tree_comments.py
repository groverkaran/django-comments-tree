import sys

from django.db import connections
from django.db.utils import ConnectionDoesNotExist, IntegrityError
from django.core.management.base import BaseCommand

from django_comments_tree.models import TreeComment


__all__ = ['Command']


class Command(BaseCommand):
    help = "Load the treecomment table with valid data from django_comments_tree."

    def add_arguments(self, parser):
        parser.add_argument('using', nargs='*', type=str)

    def populate_db(self, cursor):
        """
        ToDo: More work will be needed to make this transition work
        :param cursor:
        :return:
        """
        # for comment in Comment.objects.all():
        #     sql = ("INSERT INTO %(table)s "
        #            "       ('comment_ptr_id', 'thread_id', 'parent_id',"
        #            "        'level', 'order', 'followup') "
        #            "VALUES (%(id)d, %(id)d, %(id)d, 0, 1, 0)")
        #     cursor.execute(sql % {'table': TreeComment._meta.db_table,
        #                           'id': comment.id})

    def handle(self, *args, **options):
        total = 0
        using = options['using'] or ['default']
        for db_conn in using:
            try:
                self.populate_db(connections[db_conn].cursor())
                total += TreeComment.objects.using(db_conn).count()
            except ConnectionDoesNotExist:
                print("DB connection '%s' does not exist." % db_conn)
                continue
            except IntegrityError:
                if db_conn != 'default':
                    print("Table '%s' (in '%s' DB connection) must be empty."
                          % (TreeComment._meta.db_table, db_conn))
                else:
                    print("Table '%s' must be empty."
                          % TreeComment._meta.db_table)
                sys.exit(1)
        print("Added %d TreeComment object(s)." % total)
