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
    
    request     = models.ForeignKey('ProcessingEngine.Request', 
                                    on_delete = models.CASCADE)

    inputFile   = models.TextField(primary_key = True)
    command     = models.TextField(blank = True, null = True)
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

#-------------------------------------------------------------------------------
# EvhrScene
#
# An EvhrScene represents a single input scene file path.  EVHR requests can
# optionally include a list of input scenes.  EvhrScene represents one of them.
#-------------------------------------------------------------------------------
class EvhrScene(models.Model):

    request = models.ForeignKey('ProcessingEngine.Request', 
                                on_delete = models.CASCADE)

    sceneFile = models.FileField()

