
from django.conf.urls import url

import api.views

urlpatterns = [

    url(r'^download/$',           api.views.download),
    url(r'^orderMosaic/$',        api.views.orderMosaic),
    url(r'^percentageComplete/$', api.views.percentageComplete),
    url(r'^ready/$',              api.views.ready),
    url(r'^status/$',             api.views.status),

    url(r'^simulateOrderMosaic/$',       api.views.simulateOrderMosaic),
    url(r'^simulateercentageComplete/$', api.views.simulatePercentageComplete),
]