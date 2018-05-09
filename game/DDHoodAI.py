from game.HoodAI import HoodAI
from game.DistributedDonaldAI import DistributedDonaldAI
from game.DistributedBoatAI import DistributedBoatAI

class DDHoodAI(HoodAI):

	def __init__(self, air, zoneId=1000):
		HoodAI.__init__(self, air, zoneId)

	def generateObjectsInZone(self):
		HoodAI.generateObjectsInZone(self)

		#The boat generates a classicchar.
		#if base.config.GetBool('want-classic-chars', False):
			#self.createClassicChars()

		self.createDistributedBoat()

	def createClassicChars(self):
		self.DistributedDonald = DistributedDonaldAI(self.air)
		self.DistributedDonald.setWalk('0', '0')
		self.DistributedDonald.generateWithRequired(self.zoneId)

	def createDistributedBoat(self):
		self.DistributedBoat = DistributedBoatAI(self.air)
		self.DistributedBoat.generateWithRequired(self.zoneId)