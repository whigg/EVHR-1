# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from ProcessingEngine.admin import RequestAdmin

# Register your models here.
from GeoProcessingEngine.models import GeoEndPoint
from GeoProcessingEngine.models import GeoRequest
from GeoProcessingEngine.models import LandsatMetadata
from GeoProcessingEngine.models import GeoProtocol

admin.site.register(GeoEndPoint)
admin.site.register(GeoRequest, RequestAdmin)
admin.site.register(LandsatMetadata)
admin.site.register(GeoProtocol)
