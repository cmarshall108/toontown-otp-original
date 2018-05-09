from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.task.TaskManagerGlobal import *
from direct.distributed.ClockDelta import *
from panda3d.core import *

class DistributedDoorAI(DistributedObjectAI):

    def __init__(self, air, zoneId=0, blockNumber=0):
        DistributedObjectAI.__init__(self, air)
        self.zoneId = zoneId
        self.blockNumber = blockNumber
        self.doorSwing = 0
        self.doorType = 0
        self.doorIndex = 0
        self.state = ['off', 0]
        self.exitDoorState = ['off', 0]
        self.denyAvatarIds = []
        self.waitDoorOpening = 3.0
        self.waitDoorClosing = 3.0

    def generate(self):
        DistributedObjectAI.generate(self)

    def announceGenerate(self):
        DistributedObjectAI.announceGenerate(self)

    def getZoneIdAndBlock(self):
        return [self.zoneId, self.blockNumber]

    def setSwing(self, doorSwing):
        self.doorSwing = doorSwing

    def getSwing(self):
        return self.doorSwing

    def setDoorType(self, doorType):
        self.doorType = doorType

    def getDoorType(self):
        return self.doorType

    def setDoorIndex(self, doorIndex):
        self.doorIndex = doorIndex

    def getDoorIndex(self):
        return self.doorIndex

    def setOtherZoneIdAndDoId(self, zoneId, doId):
        self.sendUpdate('setOtherZoneIdAndDoId', [
            zoneId,
            doId])

    def _getSender(self):
        avatarId = self.air.getAvatarIdFromSender()
        if not avatarId:
            return None

        return avatarId

    def requestEnter(self):
        avatarId = self._getSender()

        if avatarId in self.denyAvatarIds:
            self.d_rejectEnter(avatarId, reason='You are not allowed to enter the building!')
            return

        self._startAvatarEntering(avatarId)

    def requestExit(self):
        avatarId = self._getSender()

        if avatarId in self.denyAvatarIds:
            self.d_rejectEnter(avatarId, reason='You are not allowed to exit the building!')
            return

        self._startAvatarExiting(avatarId)

    def _startAvatarEntering(self, avatarId):
        self.b_setState(state='opening', timestamp=globalClockDelta.getRealNetworkTime(bits=32))
        self.b_setState(state='open', timestamp=globalClockDelta.getRealNetworkTime(bits=32))
        self.d_toonEnter(avatarId)

    def _startAvatarExiting(self, avatarId):
        pass

    def d_rejectEnter(self, avatarId, reason):
        self.sendUpdateToAvatarId(avatarId, 'rejectEnter', [
            reason])

    def d_toonEnter(self, avatarId):
        self.sendUpdateToAvatarId(avatarId, 'toonEnter', [
            avatarId])

    def d_toonExit(self, avatarId):
        self.sendUpdate('toonExit', [
            avatarId])

    def d_suitEnter(self, avatarId):
        self.sendUpdate('toonExit', [
            avatarId])

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

    def setExitDoorState(self, state, timestamp):
        self.exitDoorState = [state, timestamp]

    def getExitDoorState(self):
        return self.exitDoorState