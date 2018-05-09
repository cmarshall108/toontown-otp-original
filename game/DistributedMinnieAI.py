from direct.distributed.DistributedObjectAI import DistributedObjectAI
from game.DistributedCCharBaseAI import DistributedCCharBaseAI

class DistributedMinnieAI(DistributedCCharBaseAI):

	def __init__(self, air):
		DistributedCCharBaseAI.__init__(self, air)

	def generate(self):
		DistributedCCharBaseAI.generate(self)

	def avatarEnter(self):
		DistributedCCharBaseAI.avatarEnter(self)

	def avatarExit(self):
		DistributedCCharBaseAI.avatarExit(self)