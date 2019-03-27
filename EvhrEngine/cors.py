
#-------------------------------------------------------------------------------
# class CorsMiddleware
#-------------------------------------------------------------------------------
class CorsMiddleware(object):

    #---------------------------------------------------------------------------
    # process_response
    #---------------------------------------------------------------------------
    def process_response(self, req, resp):
        
        response["Access-Control-Allow-Origin"] = [
            'cad4nasa-dev.gsfc.nasa.gov',
            'gs618-dslaybl1.ndc.nasa.gov']
                                                   
        return response