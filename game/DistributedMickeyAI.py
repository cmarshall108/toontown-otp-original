from direct.distributed.DistributedObjectAI import DistributedObjectAI
from game.DistributedCCharBaseAI import DistributedCCharBaseAI

class DistributedMickeyAI(DistributedCCharBaseAI):

	def __init__(self, air):
		DistributedCCharBaseAI.__init__(self, air)
