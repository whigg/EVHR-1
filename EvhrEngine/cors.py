
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
        
        response = self.get_response(request)
        
        response["Access-Control-Allow-Origin"] = [
            'cad4nasa-dev.gsfc.nasa.gov',
            'gs618-dslaybl1.ndc.nasa.gov']
                                                   
        return response