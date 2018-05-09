from game.HoodAI import HoodAI
from game.DistributedMinnieAI import DistributedMinnieAI
from game.DistributedMMPianoAI import DistributedMMPianoAI

class MMHoodAI(HoodAI):

	def __init__(self, air, zoneId=4000):
		HoodAI.__init__(self, air, zoneId)

	def generateObjectsInZone(self):
		HoodAI.generateObjectsInZone(self)

		if base.config.GetBool('want-classic-chars'):
			self.createClassicChars()

		self.createMMPiano()

	def createClassicChars(self):
		self.DistributedMinnie = DistributedMinnieAI(self.air)
		self.DistributedMinnie.setWalk('0', '0')
		self.DistributedMinnie.generateWithRequired(self.zoneId)

	def createMMPiano(self):
		self.DistributedMMPiano = DistributedMMPianoAI(self.air)
		self.DistributedMMPiano.generateWithRequired(self.zoneId)