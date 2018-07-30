
from django.conf.urls import url

import api.views

urlpatterns = [

    url(r'^download/$',           api.views.download),
    url(r'^getErrors/$',          api.views.getErrors),
    url(r'^orderComposite/$',     api.views.orderMosaic),
    url(r'^percentageComplete/$', api.views.percentageComplete),
    url(r'^ready/$',              api.views.ready),
    url(r'^status/$',             api.views.status),

    url(r'^simulateOrderComposite/$',     api.views.simulateOrderMosaic),
    url(r'^simulatePercentageComplete/$', api.views.simulatePercentageComplete),
]