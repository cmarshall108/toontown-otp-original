from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.task.TaskManagerGlobal import *
from direct.distributed.ClockDelta import *
from panda3d.core import *

class DistributedToonInteriorAI(DistributedObjectAI):

    def __init__(self, air, zoneId=0, blockNumber=0):
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
        self.sendUpdate('setState', [
            state,
            timestamp])

    def b_setState(self, state, timestamp):
        self.setState(state, timestamp)
        self.d_setState(state, timestamp)

    def getState(self):
        return self.state

    def getToonData(self):
        return self.toonData