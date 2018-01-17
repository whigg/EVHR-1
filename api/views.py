# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from EVHR import settings

from ProcessingEngine.management.CommandHelper import CommandHelper
from ProcessingEngine.models import EndPoint

from GeoProcessingEngine.models import GeoRequest
from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

#-------------------------------------------------------------------------------
# orderMosaic
#
# localhost:8000/api/orderMosaic?ulx=-113.39250146&uly=43.35041085&lrx=-112.80953835&lry=42.93059617&epsg=4326&outEpsg=102039
#-------------------------------------------------------------------------------
@csrf_exempt
def orderMosaic(request):

    geoRequest             = GeoRequest()
    geoRequest.name        = 'API_' + str(uuid.uuid4())
    geoRequest.destination = settings.EVHR_SETTINGS['outputDirectory']
    geoRequest.startDate   = None                      # N/A
    geoRequest.endDate     = None                      # N/A
    geoRequest.started     = True
    geoRequest.ulx         = request.GET.get('ulx')
    geoRequest.uly         = request.GET.get('uly')
    geoRequest.lrx         = request.GET.get('lrx')
    geoRequest.lry         = request.GET.get('lry')
    
    ep = EndPoint.objects.filter(name = 'EVHR Mosaic')[0]
    geoRequest.endPoint = ep
    
    geoRequest.srs = GeoRetriever. \
                     constructSrsFromIntCode(request.GET.get('epsg')). \
                     ExportToWkt()
    
    geoRequest.outSRS = \
        GeoRetriever.constructSrsFromIntCode(request.GET.get('outEpsg')). \
        ExportToWkt()
    
    geoRequest.save()
    
    # CommandHelper.handle(geoRequest)
    
    return geoRequest.id
