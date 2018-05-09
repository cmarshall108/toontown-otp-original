from game.HoodAI import HoodAI
from game.DistributedGoofyAI import DistributedGoofyAI
from game.DistributedDGFlowerAI import DistributedDGFlowerAI

class DGHoodAI(HoodAI):

	def __init__(self, air, zoneId=5000):
		HoodAI.__init__(self, air, zoneId)

	def generateObjectsInZone(self):
		HoodAI.generateObjectsInZone(self)

		if base.config.GetBool('want-classic-chars'):
			self.createClassicChars()

		self.createDGFlower()

	def createClassicChars(self):
		self.DistributedGoofy = DistributedGoofyAI(self.air)
		self.DistributedGoofy.setWalk('0', '0')
		self.DistributedGoofy.generateWithRequired(self.zoneId)

	def createDGFlower(self):
		self.DistributedDGFlower = DistributedDGFlowerAI(self.air, height=10)
		self.DistributedDGFlower.generateWithRequired(self.zoneId)