# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import errno
import os

from django.db import models

#-------------------------------------------------------------------------------
# BaseProcess
#-------------------------------------------------------------------------------
class BaseProcess(models.Model):

    pid = models.IntegerField(null = True)

    #---------------------------------------------------------------------------
    # pidRunning
    #---------------------------------------------------------------------------
    def pidRunning(self):
        
        try:
            os.kill(self.pid, 0)
            
        except OSError as err:
            
            if err.errno == errno.ESRCH:
                
                # ESRCH == No such process
                return False
            
            elif err.errno == errno.EPERM:
            
                # EPERM clearly means there's a process to deny access to
                return True
            
            else:            
                #---
                # According to "man 2 kill" possible error values are
                # (EINVAL, EPERM, ESRCH)
                #---
                raise

        return True

    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        abstract = True
        
#------------------------------------------------------------------------
# JobDaemonProcess
#------------------------------------------------------------------------
class JobDaemonProcess(BaseProcess):

    #--------------------------------------------------------------------
    # Meta
    #--------------------------------------------------------------------
    class Meta:
        verbose_name        = 'Job Daemon Process'
        verbose_name_plural = 'Job Daemon Processes'

