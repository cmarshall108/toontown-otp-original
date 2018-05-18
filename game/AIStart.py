import __builtin__

from pandac.PandaModules import *

if __debug__:
    loadPrcFileData('', 'window-type none')
    loadPrcFile('config/general.prc')
    loadPrcFile('config/server.prc')

from direct.directbase.DirectStart import *

__builtin__.simbase = base

from realtime import types
from game.AIRepository import AIRepository

def main():
    simbase.air = AIRepository(baseChannel=200000000, serverId=types.STATESERVER_CHANNEL,
        districtName='Loopy Valley', dcFileNames=['config/dclass/toon.dc'])

    simbase.air.connect(host='127.0.0.1', port=7100)

if __name__ == '__main__':
    main()
    simbase.run()
