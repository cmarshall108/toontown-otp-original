from direct.directnotify.DirectNotifyGlobal import directNotify
from game.HoodAI import HoodAI
from game import ToontownGlobals
from game import DoorTypes
from game.DistributedMinnieAI import DistributedMinnieAI
from game.DistributedMMPianoAI import DistributedMMPianoAI

class MMHoodAI(HoodAI):
	notify = directNotify.newCategory('MMHoodAI')

	def __init__(self, air):
		HoodAI.__init__(self, air, ToontownGlobals.MinniesMelodyland)

	def createObjects(self):
		HoodAI.createObjects(self)

		if simbase.config.GetBool('want-piano', False):
			self.createPiano()

	def createClassicChars(self):
		self.classicChar = DistributedMinnieAI(self.air)
		self.classicChar.generateWithRequired(self.zoneId)

	def createPiano(self):
		self.piano = DistributedMMPianoAI(self.air)
		self.piano.generateWithRequired(self.zoneId)
