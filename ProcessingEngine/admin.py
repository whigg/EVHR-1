# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

# Register your models here.
from ProcessingEngine.models import Constituent
from ProcessingEngine.models import ConstituentProcess
from ProcessingEngine.models import EndPoint
from ProcessingEngine.models import Request
from ProcessingEngine.models import Protocol
from ProcessingEngine.models import RequestProcess

#------------------------------------------------------------------------
# ConstituentAdmin
#------------------------------------------------------------------------
class ConstituentAdmin(admin.ModelAdmin):
    
    list_display = ('id', 'request', 'getRequestID', 'state')
    
    def getRequestID(self, obj):
        return obj.request.id
    
#------------------------------------------------------------------------
# RequestAdmin
#------------------------------------------------------------------------
class RequestAdmin(admin.ModelAdmin):
    
    list_display = ('name', 'endPoint', 'state', 'id')
    
admin.site.register(Constituent, ConstituentAdmin)
admin.site.register(ConstituentProcess)
admin.site.register(EndPoint)
admin.site.register(Request, RequestAdmin)
admin.site.register(Protocol)
admin.site.register(RequestProcess)
