
from django.conf.urls import url

import api.views

urlpatterns = [

    url(r'^orderMosaic/$', api.views.orderMosaic),
]
