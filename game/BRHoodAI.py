from game.HoodAI import HoodAI
from game.DistributedPlutoAI import DistributedPlutoAI

class BRHoodAI(HoodAI):

	def __init__(self, air, zoneId=3000):
		HoodAI.__init__(self, air, zoneId)

	def generateObjectsInZone(self):
		HoodAI.generateObjectsInZone(self)

		if base.config.GetBool('want-classic-chars'):
			self.createClassicChars()

	def createClassicChars(self):
		self.DistributedPluto = DistributedPlutoAI(self.air)
		self.DistributedPluto.setWalk('0', '0')
		self.DistributedPluto.generateWithRequired(self.zoneId)