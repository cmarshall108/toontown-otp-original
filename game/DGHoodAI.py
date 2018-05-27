from direct.directnotify.DirectNotifyGlobal import directNotify
from game.HoodAI import HoodAI
from game import ToontownGlobals
from game.DistributedGoofyAI import DistributedGoofyAI
from game.DistributedDGFlowerAI import DistributedDGFlowerAI

class DGHoodAI(HoodAI):
	notify = directNotify.newCategory('DGHoodAI')

	def __init__(self, air):
		HoodAI.__init__(self, air, ToontownGlobals.DaisyGardens)

	def createObjects(self):
		HoodAI.createObjects(self)

		if simbase.config.GetBool('want-flower', False):
			self.createFlower()

	def createClassicChars(self):
		self.classicChar = DistributedGoofyAI(self.air)
		self.classicChar.generateWithRequired(self.zoneId)

	def createFlower(self):
		self.flower = DistributedDGFlowerAI(self.air)
		self.flower.generateWithRequired(self.zoneId)
