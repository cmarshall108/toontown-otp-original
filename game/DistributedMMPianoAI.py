from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.distributed.ClockDelta import *
import random

class DistributedMMPianoAI(DistributedObjectAI):
    MM_PIANO_STARTING_SPEED = 3.0
    MM_PIANO_MAX_SPEED = 9.5

    MM_PIANO_STARTING_DIRECTION = 360
    MM_PIANO_MAX_DIRECTION = -360

    rotationDirections = [
        MM_PIANO_STARTING_DIRECTION,
        MM_PIANO_MAX_DIRECTION
    ]

    def __init__(self, air):
        DistributedObjectAI.__init__(self, air)
        self.currentSpeed = self.MM_PIANO_STARTING_SPEED
        self.currentRotation = self.MM_PIANO_STARTING_DIRECTION
    
    def generate(self):
        DistributedObjectAI.generate(self)

    def announceGenerate(self):
        DistributedObjectAI.announceGenerate(self)

        # Set the default speed on generate.
        self.d_setSpeed(self.currentSpeed, self.currentRotation, globalClockDelta.getRealNetworkTime())
    
    def avatarEnter(self):
        DistributedObjectAI.avatarEnter(self)

    def requestSpeedUp(self):
        if self.currentSpeed < self.MM_PIANO_MAX_SPEED:
            self.currentSpeed += 1.0
        else:
            self.currentSpeed = self.MM_PIANO_MAX_SPEED

        self.d_setSpeed(self.currentSpeed, self.currentRotation, globalClockDelta.getRealNetworkTime())
        self.d_playSpeedUp(self.air.getAvatarIdFromSender())

    def requestChangeDirection(self):
        #if self.currentRotation == self.MM_PIANO_MAX_DIRECTION:
        #    self.currentRotation = self.MM_PIANO_STARTING_DIRECTION
        #else:
        #    self.currentRotation = self.MM_PIANO_MAX_DIRECTION

        self.d_setSpeed(self.MM_PIANO_MAX_DIRECTION, self.MM_PIANO_MAX_DIRECTION, globalClockDelta.getRealNetworkTime())
        self.d_playChangeDirection(self.air.getAvatarIdFromSender())

    def d_setSpeed(self, rpm, offset, timestamp):
        self.sendUpdate('setSpeed', [
            rpm, 
            offset, 
            timestamp])

    def d_playSpeedUp(self, avatarId):
        self.sendUpdate('playSpeedUp', [
            avatarId])

    def d_playChangeDirection(self, avatarId):
        self.sendUpdate('playChangeDirection', [
            avatarId])

	def avatarExit(self):
		DistributedObjectAI.avatarExit(self)