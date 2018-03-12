# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from EVHR import settings

from ProcessingEngine.management.CommandHelper import CommandHelper
from ProcessingEngine.models import EndPoint

from GeoProcessingEngine.models import GeoRequest
from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

from api import utils

#-------------------------------------------------------------------------------
# download
#
# curl --url "http://localhost:8000/api/download/?request=36"
#-------------------------------------------------------------------------------
@csrf_exempt
def download(request):

    requestId = request.GET.get('request')
    
    try:
        req = GeoRequest.objects.get(id = requestId)

    except GeoRequest.DoesNotExist:

        success = False
        msg = 'Request ' + str(requestId) + ' does not exist.'
        return JsonResponse({'success': success, 'msg': msg})
        
    return downloadHelper(requestId)        

#--------------------------------------------------------------------------------
# downloadHelper
#--------------------------------------------------------------------------------
def downloadHelper(requestId):
    
    msg = None
    success = False
    
    try:
        response = utils.downloadRequest(requestId)
        
        if not response:

            msg = 'There were no constituents to download for request ' + \
                  str(requestId) + '.'
    
        else:
            
            success = True
            msg = 'Your file is: ' + str(response)
            
    except Exception, e:
        msg = e

    return JsonResponse({'success': success, 'msg': str(msg)})
    
#-------------------------------------------------------------------------------
# orderMosaic
#
# http://localhost:8000/api/orderMosaic?ulx=-113.39250146&uly=43.35041085&lrx=-112.80953835&lry=42.93059617&epsg=4326&outEpsg=102039
#
# curl --url "http://localhost:8000/api/orderMosaic/?ulx=-113.39250146&uly=43.35041085&lrx=-112.80953835&lry=42.93059617&epsg=4326&outEpsg=102039"
#-------------------------------------------------------------------------------
@csrf_exempt
def orderMosaic(request):

    geoRequest             = GeoRequest()
    geoRequest.name        = 'API_' + str(uuid.uuid4())
    geoRequest.destination = None #settings.OUTPUT_DIRECTORY
    geoRequest.startDate   = None                      # N/A
    geoRequest.endDate     = None                      # N/A
    geoRequest.started     = False
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
    
    return JsonResponse({'id': geoRequest.id})
    
#-------------------------------------------------------------------------------
# percentageComplete
#
# curl --url "http://localhost:8000/api/percentageComplete/?request=36"
#-------------------------------------------------------------------------------
@csrf_exempt
def percentageComplete(request):

    requestId = request.GET.get('request')
    success = False
    
    try:
        req = GeoRequest.objects.get(id = requestId)
        success = True
        msg = req.percentageComplete()
        
    except GeoRequest.DoesNotExist:

        msg = 'Request ' + str(requestId) + ' does not exist.'

    return JsonResponse({'success': success, 'msg': msg})

#-------------------------------------------------------------------------------
# status
#
# curl --url "http://localhost:8000/api/status/?request=36"
#-------------------------------------------------------------------------------
@csrf_exempt
def status(request):

    requestId = request.GET.get('request')
    success = False
    
    try:
        req = GeoRequest.objects.get(id = requestId)
        success = True
        msg = 'state is ' + str(req.state())
        
    except GeoRequest.DoesNotExist:

        msg = 'Request ' + str(requestId) + ' does not exist.'

    return JsonResponse({'success': success, 'msg': msg})
        
    
        
