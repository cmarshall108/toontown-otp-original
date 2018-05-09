from direct.distributed.DistributedObjectAI import DistributedObjectAI
from game.DistributedCCharBaseAI import DistributedCCharBaseAI

class DistributedPlutoAI(DistributedCCharBaseAI):

	def __init__(self, air):
		DistributedCCharBaseAI.__init__(self, air)

	def generate(self):
		DistributedCCharBaseAI.generate(self)

	def avatarEnter(self):
		pass

	def avatarExit(self):
		pass