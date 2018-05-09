from game.HoodAI import HoodAI
from game.DistributedDonaldAI import DistributedDonaldAI

class DLHoodAI(HoodAI):

	def __init__(self, air, zoneId=9000):
		HoodAI.__init__(self, air, zoneId)

	def generateObjectsInZone(self):
		HoodAI.generateObjectsInZone(self)

		if base.config.GetBool('want-classic-chars'):
			self.createClassicChars()

	def createClassicChars(self):
		self.DistributedDonald = DistributedDonaldAI(self.air)
		self.DistributedDonald.setWalk('0', '0')
		self.DistributedDonald.generateWithRequired(self.zoneId)