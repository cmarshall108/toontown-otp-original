from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.task.TaskManagerGlobal import *
from direct.distributed.ClockDelta import *
from panda3d.core import *

class DistributedToonInteriorAI(DistributedObjectAI):

    def __init__(self, air, zoneId, blockNumber):
        DistributedObjectAI.__init__(self, air)

        self.zoneId = zoneId
        self.blockNumber = blockNumber

        self.state = ['toon', 0]
        self.toonData = ''

    def getZoneIdAndBlock(self):
        return [self.zoneId, self.blockNumber]

    def setState(self, state, timestamp):
        self.state = [state, timestamp]

    def d_setState(self, state, timestamp):
        self.sendUpdate('setState', [state, timestamp])

    def b_setState(self, state, timestamp):
        self.setState(state, timestamp)
        self.d_setState(state, timestamp)

    def getState(self):
        return self.state

    def setToonData(self, toonData):
        self.toonData = toonData

    def d_setToonData(self, toonData):
        self.sendUpdate('setToonData', [toonData])

    def b_setToonData(self, toonData):
        self.setToonData(toonData)
        self.d_setToonData(toonData)

    def getToonData(self):
        return self.toonData
