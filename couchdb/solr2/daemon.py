# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import os

__all__ = ['daemonize']

# File mode creation mask of the daemon
umask = 0

# Default working directory for the daemon
workdir = "/"

# Default maximum for the number of available file descriptors
maxfd = 1024

if (hasattr(os, "devnull")):
   redirect_to = os.devnull
else:
   redirect_to = "/dev/null"


def daemonize(pid_file):
    """Daemonize the current process.

    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/278731
    """
    try:
        pid = os.fork()
    except OSError, e:
        raise Exception, "%s [%d]" % (e.strerror, e.errno)

    if (pid == 0): # First child
        os.setsid()
        try:
            pid = os.fork() # Fork to prevent zombies
        except OSError, e:
            raise Exception, "%s [%d]" % (e.strerror, e.errno)

        if (pid == 0): # Second child
            os.chdir(workdir)
            os.umask(umask)
        else:
            os._exit(0)
    else:
        os._exit(0)
    if (os.sysconf_names.has_key("SC_OPEN_MAX")):
        maxfd = os.sysconf("SC_OPEN_MAX")
    else:
        maxfd = maxfd
    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError: # Ignore if fd wasn't opened before
            pass
    os.open(redirect_to, os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)

    fp = file(pid_file, 'w')
    fp.write(str(os.getpid()))
    fp.close()
    return 0
