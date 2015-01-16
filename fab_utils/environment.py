# -*- coding: utf-8 -*-

from fabric.api import env, abort
from fabric.tasks import Task


class Environment(Task):

    def run(self, *args):
        env.shell = "/bin/bash -l -i -c"
        env.name = self.name
        env.roledefs = self.roledefs

        diff = set(args) - set(env.roledefs.keys())

        if len(args) == 0:
            env.roles = self.roledefs.keys()
        elif len(diff) == 0:
            env.roles = list(args)
        else:
            abort("The following specified roles do not exist:\n    %s" % ', '.join(diff))
