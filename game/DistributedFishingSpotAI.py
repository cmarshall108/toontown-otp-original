import random

from direct.distributed.DistributedObjectAI import DistributedObjectAI
from game import FishingCodes

class DistributedFishingSpotAI(DistributedObjectAI):

	def __init__(self, air):
		DistributedObjectAI.__init__(self, air)

		self.posHpr = [0, 0, 0, 0, 0, 0]
		self.avatarId = 0

	def announceGenerate(self):
		DistributedObjectAI.announceGenerate(self)

	def generate(self):
		DistributedObjectAI.generate(self)

	def setPosHpr(self, x, y, z, h, p, r):
		self.posHpr = [x, y, z, h, p, r]

	def getPosHpr(self):
		return self.posHpr

	def requestEnter(self):
		avatar = self.air.doId2do.get(self.air.getAvatarIdFromSender())

		if not avatar:
			return

		if self.avatarId:
			return

		self.b_setOccupied(avatar.doId)
		self.d_setMovie(FishingCodes.EnterMovie, 0, 0, 0)

	def requestExit(self):
		avatar = self.air.doId2do.get(self.air.getAvatarIdFromSender())

		if not avatar:
			return

		if not self.avatarId:
			return

		self.b_setOccupied(0)
		self.d_setMovie(FishingCodes.ExitMovie, 0, 0, 0)

	def setOccupied(self, avatarId):
		self.avatarId = avatarId

	def d_setOccupied(self, avatarId):
		self.sendUpdate('setOccupied', [avatarId])

	def b_setOccupied(self, avatarId):
		self.setOccupied(avatarId)
		self.d_setOccupied(avatarId)

	def getOccupied(self):
		return self.avatarId

	def d_setMovie(self, mode, code, item, speed):
		self.sendUpdate('setMovie', [mode, code, item, speed])
