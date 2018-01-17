# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import glob
import os

from django.core.validators import MaxLengthValidator
from django.core.validators import MinLengthValidator
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.core.validators import URLValidator
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

# States
PENDING  = 'PND'
RUNNING  = 'RUN'
COMPLETE = 'CPT'
FAILED   = 'FLD'

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
        
#-------------------------------------------------------------------------------
# Constituent
#-------------------------------------------------------------------------------
class Constituent(models.Model):

    destination = models.FileField(
            help_text = 'The file path for this constituent\'s disk file.')

    request = models.ForeignKey('Request')
    started = models.BooleanField(default = False)
    
    url = models.URLField(
            help_text = 'The URL of this constituent\'s file',
            validators = [URLValidator()])

    #--------------------------------------------------------------------
    # available
    #--------------------------------------------------------------------
    def available(self):

        return self.destination and os.path.exists(self.destination.name)
    
    #--------------------------------------------------------------------
    # describeStatus
    #--------------------------------------------------------------------
    def describeStatus(self, msg = None):
        
        print 'Request:  ' + str(self.request)
        print 'Started:  ' + str(self.started)
        
        if msg:
            print 'Message:  ' + str(msg)
        
    #---------------------------------------------------------------------------
    # getName
    #---------------------------------------------------------------------------
    def getName(self):

        if self.request:
            return self.request.name
            
        baseName = os.path.basename(self.predFile)
        name, ext = os.path.splitext(baseName)
        return name

    #---------------------------------------------------------------------------
    # state
    #
    # PENDING:  started == False
    # RUNNING:  started == True and ConstituentProcesses exist
    # COMPLETE: available() == True
    # FAILED:   started == True and no ConstituentProcesses and 
    #           available() == False
    #
    # Requests and Constituents all use this 'started' flag because the presence
    # or absence a Request's or Constituent's files does not necessarily mean
    # they never existed.  For example, a Constituent that is unavailable() and
    # has no ConstituentProcesses could be either PENDING or FAILED.  Once we
    # know it has been started, we know it is FAILED.
    #---------------------------------------------------------------------------
    def state(self):
        
        if not self.started:
            return PENDING
        
        if self.available():
            return COMPLETE
            
        numProcs = ConstituentProcess.objects.filter(constituent = self).count()
        
        if not numProcs:
            
            msg = 'Failed because it has started and is unavailable, ' + \
                  'but has no processes.'
                  
            self.describeStatus(msg)
            return FAILED
            
        return RUNNING
                
#-------------------------------------------------------------------------------
# ConstituentProcess
#-------------------------------------------------------------------------------
class ConstituentProcess(BaseProcess):

    constituent = models.OneToOneField('Constituent')

    #---
    # This causes ConstituentProcesses, children of RequestProcess, to be
    # deleted when the parent is deleted.
    #---
    parent = models.ForeignKey('RequestProcess')
        
    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        verbose_name        = 'Constituent Process'
        verbose_name_plural = 'Constituent Processes'

#-------------------------------------------------------------------------------
# EndPoint
#-------------------------------------------------------------------------------
class EndPoint(models.Model):

    protocol = models.ForeignKey('Protocol')
                
    name = models.CharField(
        max_length = 80, 
        help_text = 'The name of the end point',
        validators = [MinLengthValidator(4), MaxLengthValidator(80)])
                                 
    serviceId = models.CharField(
        max_length = 80, 
        null = True,     
        blank = True,    
        help_text = 'Indicates a named subset of the data provided by this end point',
        validators = [MaxLengthValidator(80)])
    
    url = models.URLField(
        help_text = 'The base URL of this end point',
        validators = [URLValidator()])
                                
    version = models.CharField(
        max_length = 10, 
        null = True,     
        blank = True,    
        default = '1.0.0', 
        help_text = 'The version of the end point\'s API to use',
        validators = [MaxLengthValidator(10)])
                                 
    enabled  = models.BooleanField(default = True)
        
    #---------------------------------------------------------------------------
    # __unicode__
    #---------------------------------------------------------------------------
    def __unicode__(self): 
        return self.name
        
    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        ordering            = ['name']
        unique_together     = ('name', 'url')
        verbose_name        = "End Point"
        verbose_name_plural = "End Points"       

#-------------------------------------------------------------------------------
# Protocol
#-------------------------------------------------------------------------------
class Protocol(models.Model):
    
    name      = models.CharField(max_length = 10, primary_key = True)
    module    = models.CharField(max_length = 80)
    className = models.CharField(max_length = 20)
    
    #---------------------------------------------------------------------------
    # __unicode__
    #---------------------------------------------------------------------------
    def __unicode__(self): 
        return self.name

#-------------------------------------------------------------------------------
# Request
#-------------------------------------------------------------------------------
class Request(models.Model):

    name                = models.CharField(max_length = 80)
    endPoint            = models.ForeignKey('EndPoint')
    started             = models.BooleanField(default = False)
    aggregationComplete = models.BooleanField(default = False)

    destination = models.FileField(
        help_text = 'The file path for this request\'s disk files.')

    startDate = models.DateField(
        null = True, 
        blank = True,
        help_text = 'Earliest date to retrieve')
                                 
    endDate = models.DateField(
        null = True, 
        blank = True,
        help_text = 'Latest date to retrieve')

    #--------------------------------------------------------------------
    # describeStatus
    #--------------------------------------------------------------------
    def describeStatus(self, msg = None):
        
        print 'Name:     ' + self.name
        print 'Started:  ' + str(self.started)
        print 'Agg cmpt: ' + str(self.aggregationComplete)

        if msg:
            print 'Message:  ' + str(msg)
        
    #---------------------------------------------------------------------------
    # save
    #---------------------------------------------------------------------------
    def save(self, *args, **kwargs):

        # Things to validate for new sites.
        if self.id:
            
            # Validate dates.
            if self.startDate and self.endDate and self.startDate > self.endDate:

                raise RuntimeError('Start date, ' + str(startDate) + \
                                   ' must be less than end date, ' + \
                                   str(endDate) + '.')
        
        # Invoke the base class save().
        super(Request, self).save(*args, **kwargs)

    #---------------------------------------------------------------------------
    # state
    #
    # PENDING:  started == False
    # RUNNING:  started == True and not COMPLETE and not FAILED
    # COMPLETE: all constituents are complete
    # FAILED:   at least one constituent failed
    #
    # This is confusing.  For clarity, some tests will be redundant, explicitly
    # restated instead of forcing you to remember the implicit state throughout
    # this method.
    #---------------------------------------------------------------------------
    def state(self):
        
        # If the aggregation is complete, it's complete.
        if self.aggregationComplete:
            return COMPLETE

        # It is incomplete and not started; therefore, pending.
        if not self.started:
            return PENDING

        # It is started, so it must have a RequestProcess.
        hasReqProc = RequestProcess.objects.filter(request = self).count() > 0

        if not hasReqProc:
            
            msg = 'Failed because it is started and incomplete, ' + \
                  'but has no processes.'
                  
            self.describeStatus(msg)                  
            return FAILED
        
        # Check the constituents.
        constituents = Constituent.objects.filter(request = self)

        # If there are none, it must be running.
        if constituents.count() == 0:
            return RUNNING
        
        # Ask each constituent its state.
        numComplete = 0
        oneFailed   = False
        onePending  = False
        oneRunning  = False 

        for constituent in constituents:
            
            cState = constituent.state()
            
            if cState == FAILED:

                oneFailed = True
                break
                
            elif cState == COMPLETE:
                
                numComplete += 1
                
            elif cState == PENDING:
                
                onePending = True
                
            elif cState == RUNNING:
                
                oneRunning = True
            
        # One FAILED
        if oneFailed:
            return FAILED
            
        # None FAILED and at least one RUNNING
        if oneRunning:                
            return RUNNING
            
        # None FAILED, none RUNNING and at least one PENDING
        if onePending:
            return PENDING

        #---
        # Now we know:
        #   - it has been started 
        #   - it is incomplete
        #   - it has a request process
        #   - no constituent are pending, running or failed
        #
        # All the constituents should be complete.  If not, there's a problem.
        # Otherwise, it must be in the aggregation phase.
        #---
        if numComplete != constituent.count():

            msg = 'Failed because given the other elements of its state, ' + \
                  'all its constituents should be complete.  They are not.'
                  
            self.describeStatus(msg)
            return FAILED
            
        return RUNNING
        
    #---------------------------------------------------------------------------
    # __unicode__
    #---------------------------------------------------------------------------
    def __unicode__(self): 
        return self.name
        
    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        ordering = ['name']
    
#-------------------------------------------------------------------------------
# RequestProcess
#-------------------------------------------------------------------------------
class RequestProcess(BaseProcess):

    request = models.OneToOneField('Request')

    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        verbose_name        = "Request Process"
        verbose_name_plural = "Request Processes"

#-------------------------------------------------------------------------------
# pre_delete
#
# This is called before a Request is deleted.  This 'signal' method deletes the
# predictor from the site directory.
#-------------------------------------------------------------------------------
@receiver(pre_delete)
def preDeletePredictor(sender, instance, using, **kwargs):

    if sender == Request:

        # Do not remove the entire subdirectory, else you lose Landsat state.
        if instance.destination and os.path.isdir(instance.destination.name):

            globFiles = []
            
            fileExts  = ['*.csv', '*.gfs', '*.gml', '*.gz', '*.nc', '*.tif', 
                         '*.xml', '*.xsd', '*.xyz']
            
            for fileExt in fileExts:
                
                globStmt = os.path.join(instance.destination.name, fileExt)
                globFiles += glob.glob(globStmt)

            for f in globFiles:
                os.remove(f)
        
    elif sender == Constituent:

        if instance.destination and os.path.exists(instance.destination.name):
            os.remove(instance.destination.name)


