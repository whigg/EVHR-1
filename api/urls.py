
from django.conf.urls import url

import api.views

urlpatterns = [

    url(r'^getOutput/$',   api.views.download),
    url(r'^orderMosaic/$', api.views.orderMosaic),
    url(r'^status/$',      api.views.status),
]
