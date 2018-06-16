from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.directnotify.DirectNotifyGlobal import directNotify

class DistributedHQInteriorAI(DistributedObjectAI):
    notify = directNotify.newCategory('DistributedHQInteriorAI')

    def __init__(self, air, interiorZone, blockNumber):
        DistributedObjectAI.__init__(self, air)

        self.interiorZone = interiorZone
        self.blockNumber = blockNumber
        self.leaderBoard = ''

    def getZoneIdAndBlock(self):
        return [self.interiorZone, self.blockNumber]

    def setLeaderBoard(self, leaderBoard):
        self.leaderBoard = leaderBoard

    def d_setLeaderBoard(self, leaderBoard):
        self.sendUpdate('setLeaderBoard', [leaderBoard])

    def b_setLeaderBoard(self, leaderBoard):
        self.setLeaderBoard(leaderBoard)
        self.d_setLeaderBoard(leaderBoard)

    def getLeaderBoard(self):
        return self.leaderBoard
