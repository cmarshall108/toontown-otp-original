import random

from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.distributed.ClockDelta import *


ChangeDirectionDebounce = 1.0
ChangeDirectionTime = 1.0

class DistributedMMPianoAI(DistributedObjectAI):

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)

        self.rpm = ChangeDirectionTime
        self.direction = 1
        self.offset = ChangeDirectionDebounce
        self.timestamp = 0

    def generate(self):
        DistributedObjectAI.generate(self)

        self.d_setSpeed(self.rpm, self.offset)

    def requestSpeedUp(self):
        avatar = self.air.doId2do.get(self.air.getAvatarIdFromSender())

        if not avatar:
            return

        self.rpm += (ChangeDirectionTime * self.direction)
        self.rpm = max(0.0, min(self.rpm, 360.0))
        self.d_setSpeed(self.rpm, self.offset)
        self.d_playSpeedUp(avatar.doId)

    def requestChangeDirection(self):
        avatar = self.air.doId2do.get(self.air.getAvatarIdFromSender())

        if not avatar:
            return

        self.direction = -self.direction
        self.rpm = self.rpm * -self.direction
        self.d_setSpeed(self.rpm, self.offset)
        self.d_playChangeDirection(avatar.doId)

    def d_setSpeed(self, rpm, offset):
        self.sendUpdate('setSpeed', [rpm, offset, globalClockDelta.getRealNetworkTime(bits=16)])

    def d_playSpeedUp(self, avatarId):
        self.sendUpdate('playSpeedUp', [avatarId])

    def d_playChangeDirection(self, avatarId):
        self.sendUpdate('playChangeDirection', [avatarId])
