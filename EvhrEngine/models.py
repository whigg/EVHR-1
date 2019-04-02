# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from ProcessingEngine.models import EndPoint
from ProcessingEngine.models import Protocol

import xml.etree.ElementTree as ET
import os

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
# EvhrNode
#-------------------------------------------------------------------------------
class EvhrNode(models.Model):
    
    group = models.ForeignKey('EvhrNodeGroup')
    name = models.CharField(max_length=20)
    enabled = models.BooleanField(default=True)
    
    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:

        unique_together = (('group', 'name'),)
        verbose_name = 'EVHR Node'
        verbose_name_plural = 'EVHR Nodes'
        
#-------------------------------------------------------------------------------
# EvhrNodeGroup
#-------------------------------------------------------------------------------
class EvhrNodeGroup(models.Model):
    
    name = models.CharField(max_length=20, primary_key=True)
    enabled = models.BooleanField(default=True)
    
    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        verbose_name = 'EVHR Node Group'
        verbose_name_plural = 'EVHR Node Groups'
    
#-------------------------------------------------------------------------------
# EvhrNodePID
#-------------------------------------------------------------------------------
class EvhrNodePID(models.Model):
    
    node = models.ForeignKey('EvhrNode')
    pid = models.IntegerField(null=True)
    
    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:

        unique_together = (('node', 'pid'),)
        verbose_name = 'EVHR Node PID'
        verbose_name_plural = 'EVHR Node PIDs'
    
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

    #---------------------------------------------------------------------------
    # getProdLevelCode
    #---------------------------------------------------------------------------
    def getProdLevelCode(self):

        try:
            extension = os.path.splitext(self.sceneFile.name)[1]
            xmlFileName = self.sceneFile.name.replace(extension, '.xml')
            tree = ET.parse(xmlFileName)
      
            return tree.getroot().find('IMD').find('PRODUCTLEVEL').text
      
        except:
            return ''

    #---------------------------------------------------------------------------
    # save
    #---------------------------------------------------------------------------
    def save(self, *args, **kwargs):
     
        if '1B' in self.getProdLevelCode(): # could be Stereo 1B or LV1B
            
            # Invoke the base class save().
            super(EvhrScene, self).save(*args, **kwargs)

        else:
            print 'Scene was not saved because it is not level 1B.'
