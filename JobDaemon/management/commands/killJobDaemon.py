
import os

from django.core.management.base import BaseCommand

from JobDaemon.models import JobDaemonProcess

#------------------------------------------------------------------------
# Command
#
# manage.py killJobDaemon
#------------------------------------------------------------------------
class Command(BaseCommand):
    
    #--------------------------------------------------------------------
    # handle
    #--------------------------------------------------------------------
    def handle(self, **options):
    
        jdPs = JobDaemonProcess.objects.all()
        
        for jdp in jdPs:
            
            pid = jdp.pid
            print 'Killing JobDaemon process ' + str(pid) + ' ...'

            try:
                os.kill(int(pid), 9)
                    
            except OSError: 
                pass
                
            except IOError: # proc has already terminated
                pass

            JobDaemonProcess.objects.filter(pid = pid).delete()
        

