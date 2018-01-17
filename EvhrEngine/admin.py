# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

# Register your models here.
from EvhrEngine.models import EvhrEndPoint
from EvhrEngine.models import EvhrProtocol

admin.site.register(EvhrEndPoint)
admin.site.register(EvhrProtocol)
