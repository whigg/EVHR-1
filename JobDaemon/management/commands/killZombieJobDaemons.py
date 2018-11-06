
import os

from django.core.management.base import BaseCommand

from ProcessingEngine.models import ConstituentProcess
from ProcessingEngine.models import RequestProcess
from JobDaemon.models import JobDaemonProcess

#------------------------------------------------------------------------
# Command
#
# manage.py killZombieJobDaemons
#------------------------------------------------------------------------
class Command(BaseCommand):
    
    #--------------------------------------------------------------------
    # handle
    #--------------------------------------------------------------------
    def handle(self, **options):
        
        killZombieJobDaemons()

#--------------------------------------------------------------------
# killZombieJobDaemons
#--------------------------------------------------------------------
def killZombieJobDaemons():
    
    # Get all the process IDs.
    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
    
    for pid in pids:
        
        try:
            
            # Does it have 'jobDaemon' in the command line?
            cmdLine = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()
            
            if cmdLine.find('jobDaemon') != -1:
                
                #---
                # If this PID is unrepresented in ConstituentProcess
                # or JobDaemonProcess, delete it.
                #---
                if JobDaemonProcess.objects.filter(pid = pid).exists():
                    continue
                
                if RequestProcess.objects.filter(pid = pid).exists():
                    continue
                
                if ConstituentProcess.objects.filter(pid = pid).exists():
                    continue
                
                # Delete the PID.
                print 'Killing JobDaemon process ' + str(pid) + '...'
                os.kill(int(pid), 9)
        
        except OSError: # probably don't have permission to kill
            
            print 'Unable to kill ' + str(pid)
            continue
        
        except IOError: # proc has already terminated
            continue


