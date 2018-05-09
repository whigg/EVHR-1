
from django.conf.urls import url

import api.views

urlpatterns = [

    url(r'^getOutput/$',          api.views.download),
    url(r'^orderMosaic/$',        api.views.orderMosaic),
    url(r'^percentageComplete/$', api.views.percentageComplete),
    url(r'^status/$',             api.views.status),
    url(r'^apiReady/$',           api.views.apiReady),
]