# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.validators import DecimalValidator
from django.db import models

from ProcessingEngine.models import EndPoint
from ProcessingEngine.models import Protocol
from ProcessingEngine.models import Request

#-------------------------------------------------------------------------------
# GeoEndPoint
#-------------------------------------------------------------------------------
class GeoEndPoint(EndPoint):

    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        verbose_name        = 'Geo End Point'
        verbose_name_plural = 'Geo End Points'

#-------------------------------------------------------------------------------
# GeoRequest
#
# A request has a bounding box, represented by ulx, uly, lrx, lry and epsg. 
# Ideally, the box would be represented using a geospatial object.  That
# requires Geodjango.  Instead, store corner points as ordinates.
#-------------------------------------------------------------------------------
class GeoRequest(Request):

    ulx = models.DecimalField(
        decimal_places = 8,
        max_digits = 20,
        help_text = 'Upper-left X ordinate for the request',
        validators = [DecimalValidator(12, 8)])

    uly = models.DecimalField(
        decimal_places = 8,
        max_digits = 20,
        help_text = 'Upper-left Y ordinate for the request',
        validators = [DecimalValidator(12, 8)])

    lrx = models.DecimalField(
        decimal_places = 8,
        max_digits = 20,
        help_text = 'Lower-right X ordinate for the request',
        validators = [DecimalValidator(12, 8)])

    lry = models.DecimalField(
        decimal_places = 8,
        max_digits = 20,
        help_text = 'Lower-right Y ordinate for the request',
        validators = [DecimalValidator(12, 8)])

    srs = models.CharField(
        max_length = 1000,
        help_text = 'The OGC well-known text definition of the spatial reference system describing ulx, uly, lrx and lry.')

    outSRS = models.CharField(
        max_length = 1000,
        null = True,
        blank = True,
        help_text = 'The OGC well-known text definition of the spatial reference system describing the output products.')

    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        verbose_name        = 'Geo Request'
        verbose_name_plural = 'Geo Requests'

#-------------------------------------------------------------------------------
# LandsatMetadata
#-------------------------------------------------------------------------------
class LandsatMetadata(models.Model):
    
    acquisitionDate = models.DateField(null = False, blank = False)
    sceneID         = models.CharField(max_length = 21)
    productID       = models.CharField(max_length = 40, primary_key = True)
    path            = models.IntegerField()
    row             = models.IntegerField()

    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:

        verbose_name        = 'Landsat Metadata'
        verbose_name_plural = 'Landsat Metadata'

    #--------------------------------------------------------------------
    # __unicode__
    #--------------------------------------------------------------------
    def __unicode__(self):
        return self.productID

#-------------------------------------------------------------------------------
# GeoProtocol
#-------------------------------------------------------------------------------
class GeoProtocol(Protocol):

    #---------------------------------------------------------------------------
    # Meta
    #---------------------------------------------------------------------------
    class Meta:
        verbose_name        = 'Geo Protocol'
        verbose_name_plural = 'Geo Protocols'


