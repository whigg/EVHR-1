
from django.conf import settings

#-------------------------------------------------------------------------------
# class CorsMiddleware
#-------------------------------------------------------------------------------
class CorsMiddleware(object):

    #---------------------------------------------------------------------------
    # __init__
    #---------------------------------------------------------------------------
    def __init__(self, get_response):
        self.get_response = get_response
                        
    #---------------------------------------------------------------------------
    # __call__
    #---------------------------------------------------------------------------
    def __call__(self, request):
        
        origin = request.META.get('HTTP_ORIGIN')
        response = self.get_response(request)
        
        # if origin in settings.CORS_ORIGIN_WHITELIST:
        #     response["Access-Control-Allow-Origin"] = origin

        response["Access-Control-Allow-Origin"] = '*'
                                                   
        return response