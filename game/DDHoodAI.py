from direct.directnotify.DirectNotifyGlobal import directNotify
from game.HoodAI import HoodAI
from game import ToontownGlobals
from game.DistributedDonaldAI import DistributedDonaldAI
from game.DistributedBoatAI import DistributedBoatAI

class DDHoodAI(HoodAI):
	notify = directNotify.newCategory('DDHoodAI')

	def __init__(self, air):
		HoodAI.__init__(self, air, ToontownGlobals.DonaldsDock)

	def createObjects(self):
		if simbase.config.GetBool('want-boat', False):
			self.createBoat()

		HoodAI.createObjects(self)

	def createBoat(self):
		self.boat = DistributedBoatAI(self.air)
		self.boat.generateWithRequired(self.zoneId)
