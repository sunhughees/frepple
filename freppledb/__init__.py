#
# Copyright (C) 2020 by frePPLe bv
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

VERSION = "6.10.0"
__version__ = VERSION


def runCommand(taskname, *args, **kwargs):
    """
    Auxilary method to run a django command. It is intended to be used
    as a target for the multiprocessing module.

    The code is put here, such that a child process loads only
    a minimum of other python modules.
    """
    # Initialize django
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freppledb.settings")
    import django

    django.setup()

    # Be sure to use the correct database
    from django.db import DEFAULT_DB_ALIAS, connections
    from freppledb.common.middleware import _thread_locals

    database = kwargs.get("database", DEFAULT_DB_ALIAS)
    setattr(_thread_locals, "database", database)
    if "FREPPLE_TEST" in os.environ:
        from django.conf import settings

        for db in settings.DATABASES:
            connections[db].close()
            settings.DATABASES[db]["NAME"] = settings.DATABASES[db]["TEST"]["NAME"]

    # Run the command
    try:
        from django.core import management

        management.call_command(taskname, *args, **kwargs)
    except Exception as e:
        taskid = kwargs.get("task", None)
        if taskid:
            from datetime import datetime
            from freppledb.execute.models import Task

            task = Task.objects.all().using(database).get(pk=taskid)
            task.status = "Failed"
            now = datetime.now()
            if not task.started:
                task.started = now
            task.finished = now
            task.message = str(e)
            task.processid = None
            task.save(using=database)
