#!/usr/bin/python

#============================ adjust path =====================================

import sys
import os
from builtins import input
if __name__ == "__main__":
    here = sys.path[0]
    sys.path.insert(0, os.path.join(here, '..', '..','libs'))
    sys.path.insert(0, os.path.join(here, '..', '..','external_libs'))

#============================ verify installation =============================

from SmartMeshSDK.utils import SmsdkInstallVerifier
(goodToGo,reason) = SmsdkInstallVerifier.verifyComponents(
    [
        SmsdkInstallVerifier.PYTHON,
        SmsdkInstallVerifier.PYSERIAL,
    ]
)
if not goodToGo:
    print ("Your installation does not allow this application to run:\n")
    print (reason)
    input("Press any button to exit")
    sys.exit(1)

#============================ imports =========================================

import requests
import json

from   SmartMeshSDK                         import sdk_version
from   SmartMeshSDK.utils                   import AppUtils, \
                                                   FormatUtils
from   SmartMeshSDK.IpMgrConnectorSerial    import IpMgrConnectorSerial
from   SmartMeshSDK.IpMgrConnectorMux       import IpMgrSubscribe
from   SmartMeshSDK.protocols.oap           import OAPDispatcher,    \
                                                   OAPNotif

#============================ logging =========================================

# local
import logging
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log = logging.getLogger('App')
log.setLevel(logging.ERROR)
log.addHandler(NullHandler())

# global
AppUtils.configureLogging()

#============================ defines =========================================

DEFAULT_SERIALPORT = 'COM7'
SERVER_HOST        = 'clouddata.dustcloud.org'
SERVER_PORT        = '80'

#============================ helper functions ================================

# called when the manager generates a data notification
def handle_data(notifName, notifParams):
    
    # have the OAP dispatcher parse the packet.
    # It will call handle_oap_data() is this data is a valid OAP data.
    oapdispatcher.dispatch_pkt(notifName, notifParams)

# called when the OAP dispatcher can successfully parse received data as OAP
def handle_oap_data(mac,notif):
    
    if isinstance(notif,OAPNotif.OAPTempSample):
        
        mac         = FormatUtils.formatMacString(mac)
        temperature = float(notif.samples[0])/100
        
        try:
            r = requests.post(
                "http://{0}:{1}/api/v1/oap".format(SERVER_HOST,SERVER_PORT),
                data = json.dumps({
                    'mac':          mac,
                    'temperature':  temperature,
                }),
                headers = {
                    'Content-type': 'application/json',
                }
            )
        except Exception as err:
            print (err)
        else:
            print ('sent mac={0} temperature={1:.2f}C'.format(mac,temperature))

#============================ main ============================================

# print banner
print ('PublishToWeb - (c) Dust Networks')
print ('SmartMesh SDK {0}'.format('.'.join([str(b) for b in sdk_version.VERSION])))

# set up the OAP dispatcher (which parses OAP packets)
oapdispatcher = OAPDispatcher.OAPDispatcher()
oapdispatcher.register_notif_handler(handle_oap_data)

# ask user for serial port number
serialport = input('\nSmartMesh IP manager\'s API serial port (leave blank for '+DEFAULT_SERIALPORT+'): ')
if not serialport.strip():
    serialport = DEFAULT_SERIALPORT

# connect to manager
connector = IpMgrConnectorSerial.IpMgrConnectorSerial()
try:
    connector.connect({
        'port': serialport,
    })
except Exception as err:
    print ('failed to connect to manager at {0}, error ({1})\n{2}'.format(
        serialport,
        type(err),
        err
    ))
    input('Aborting. Press Enter to close.')
    sys.exit(1)
else:
    print ('Connected to {0}.\n'.format(serialport))

# subscribe to data notifications 
subscriber = IpMgrSubscribe.IpMgrSubscribe(connector)
subscriber.start()
subscriber.subscribe(
    notifTypes =    [
                        IpMgrSubscribe.IpMgrSubscribe.NOTIFDATA,
                    ],
    fun =           handle_data,
    isRlbl =        False,
)
