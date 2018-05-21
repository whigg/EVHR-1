# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time # for simulatePercentageComplete
import uuid

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from EVHR import settings

from ProcessingEngine.management.CommandHelper import CommandHelper
from ProcessingEngine.models import EndPoint

from GeoProcessingEngine.models import GeoRequest
from GeoProcessingEngine.management.GeoRetriever import GeoRetriever

from EvhrEngine.models import EvhrScene

from api import utils

#-------------------------------------------------------------------------------
# download
#
# curl --url "http://evhr102/api/download/?id=36"
#-------------------------------------------------------------------------------
@csrf_exempt
def download(request):

    requestId = request.GET('id')
    
    try:
        req = GeoRequest.objects.filter(id = requestId)

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
# curl --url "http://evhr102/api/orderMosaic/?ulx=-148&uly=65&lrx=-147.5&lry=64.5&epsg=4326"
#
# ./manage.py processEvhrRequest --name testFairbanks --epName "EVHR Mosaic" --ulx -148 --uly 65 --lrx -147.5 --lry 64.5 --epsg 4326 --outEpsg 4326 --scenes "/att/pubrepo/NGA/WV01/1B/2008/059/WV01_1020010001076500_X1BS_005733445010_03/WV01_20080228205612_1020010001076500_08FEB28205612-P1BS-005733445010_03_P001.ntf" "/att/pubrepo/NGA/WV01/1B/2008/059/WV01_1020010001076500_X1BS_052804587010_01/WV01_20080228205612_1020010001076500_08FEB28205612-P1BS-052804587010_01_P001.ntf" "/att/pubrepo/NGA/WV01/1B/2008/059/WV01_1020010001076500_X1BS_005733445010_03/WV01_20080228205614_1020010001076500_08FEB28205614-P1BS-005733445010_03_P002.ntf" -n 1
#
# curl --url "http://evhr102/api/orderMosaic/?ulx=-148&uly=65&lrx=-147.5&lry=64.5&epsg=4326&scenes=/att/pubrepo/NGA/WV01/1B/2008/059/WV01_1020010001076500_X1BS_005733445010_03/WV01_20080228205612_1020010001076500_08FEB28205612-P1BS-005733445010_03_P001.ntf,/att/pubrepo/NGA/WV01/1B/2008/059/WV01_1020010001076500_X1BS_052804587010_01/WV01_20080228205612_1020010001076500_08FEB28205612-P1BS-052804587010_01_P001.ntf"
#-------------------------------------------------------------------------------
@csrf_exempt
def orderMosaic(request):

    if request.method != 'POST':

        return JsonResponse({'success': False,
                             'msg': 'Please use a "POST" request.'})

    geoRequest             = GeoRequest()
    geoRequest.name        = 'API_' + str(uuid.uuid4())
    geoRequest.destination = None   # settings.OUTPUT_DIRECTORY
    geoRequest.startDate   = None   # N/A
    geoRequest.endDate     = None   # N/A
    geoRequest.started     = False
    geoRequest.ulx         = request.POST['ulx']
    geoRequest.uly         = request.POST['uly']
    geoRequest.lrx         = request.POST['lrx']
    geoRequest.lry         = request.POST['lry']
    
    ep = EndPoint.objects.filter(name = 'EVHR Mosaic')[0]
    geoRequest.endPoint = ep
    
    geoRequest.srs = GeoRetriever. \
                     constructSrsFromIntCode(request.POST['epsg']). \
                     ExportToWkt()
    
    geoRequest.save()
    
    print 'scenes = ' + str(request.POST['scenes'])
    
    if request.POST.has_key('scenes'):
        
        sceneStr = request.POST['scenes']
        sceneList = sceneStr.split(',')
        
        for scene in sceneList:
            
            evhrScene = EvhrScene()
            evhrScene.request = geoRequest
            evhrScene.sceneFile = scene
            evhrScene.save()
        
    return JsonResponse({'id': geoRequest.id})
    
#-------------------------------------------------------------------------------
# percentageComplete
#
# curl --url "http://evhr102/api/percentageComplete/?id=36"
#-------------------------------------------------------------------------------
@csrf_exempt
def percentageComplete(request):

    requestId = request.GET('id')
    success = False
    
    try:
        req = GeoRequest.objects.get(id = requestId)
        success = True
        msg = req.percentageComplete()
        
    except GeoRequest.DoesNotExist:

        msg = 'Request ' + str(requestId) + ' does not exist.'

    return JsonResponse({'success': success, 'msg': msg})

#-------------------------------------------------------------------------------
# ready
#
# curl --url "http://evhr102/api/ready/"
#-------------------------------------------------------------------------------
@csrf_exempt
def ready(request):

    success = True
    msg = 'EVHR is ready.'
    return JsonResponse({'success': success, 'msg': msg})
        
#-------------------------------------------------------------------------------
# simulateOrderMosaic
#
# curl --url "http://evhr102/api/simulateOrderMosaic/?ulx=-148&uly=65&lrx=-147.5&lry=64.5&epsg=4326"
#-------------------------------------------------------------------------------
@csrf_exempt
def simulateOrderMosaic(request):

    ulx  = request.GET('ulx')
    uly  = request.GET('uly')
    lrx  = request.GET('lrx')
    lry  = request.GET('lry')
    epsg = request.GET('epsg')

    return JsonResponse({'ulx'  : ulx,
                         'uly'  : uly,
                         'lrx'  : lrx,
                         'lry'  : lry,
                         'epsg' : epsg,
                         'id'   : 'simID'})

#-------------------------------------------------------------------------------
# simulatePercentageComplete
#
# curl --url "http://evhr102/api/simulatePercentageComplete/?id=36"
#-------------------------------------------------------------------------------
@csrf_exempt
def simulatePercentageComplete(request):

    msg = 50.0 if int(time.time()) % 2 == 0 else 100.0
    return JsonResponse({'success': True, 'msg': msg})

#-------------------------------------------------------------------------------
# status
#
# curl --url "http://evhr102/api/status/?id=36"
#-------------------------------------------------------------------------------
@csrf_exempt
def status(request):

    requestId = request.GET('id')
    success = False
    
    try:
        req = GeoRequest.objects.get(id = requestId)
        success = True
        msg = 'state is ' + str(req.state())
        
    except GeoRequest.DoesNotExist:

        msg = 'Request ' + str(requestId) + ' does not exist.'

    return JsonResponse({'success': success, 'msg': msg})
        
    
        
