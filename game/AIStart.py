from pandac.PandaModules import *
loadPrcFile('config/general.prc')
 
from direct.directbase.DirectStart import *
from game.AIRepository import AIRepository
import __builtin__
__builtin__.AIServer = AIRepository(baseChannel=200000000, stateServerChannel=1003, districtName='Loopy Valley')

try:
	run()
except:
	base.run()