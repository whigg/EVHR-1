# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from ProcessingEngine.models import EndPoint
from ProcessingEngine.models import Protocol

#-------------------------------------------------------------------------------
# EvhrEndPoint
#-------------------------------------------------------------------------------
class EvhrEndPoint(EndPoint):

    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        verbose_name        = 'EVHR End Point'
        verbose_name_plural = 'EVHR End Points'

#-------------------------------------------------------------------------------
# EvhrError
#-------------------------------------------------------------------------------
class EvhrError(models.Model):
    
    constituent = models.ForeignKey('Constituent')
    inputFile   = models.FileField()
    command     = models.TextField()
    errorOutput = models.TextField()
    
    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        verbose_name        = 'EVHR Error'
        verbose_name_plural = 'EVHR Errors'
    
#-------------------------------------------------------------------------------
# EvhrProtocol
#-------------------------------------------------------------------------------
class EvhrProtocol(Protocol):

    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        verbose_name        = 'EVHR Protocol'
        verbose_name_plural = 'EVHR Protocols'


