from direct.distributed.DistributedObjectAI import DistributedObjectAI

class EstateManagerAI(DistributedObjectAI):

	def __init__(self, air):
		DistributedObjectAI.__init__(self, air)

	def generate(self):
		DistributedObjectAI.generate(self)

	def avatarEnter(self):
		DistributedObjectAI.avatarEnter(self)
    
	def getEstateZone(self, avatarId, name):
		self.sendUpdateToAvatarId(avatarId, 'setEstateZone', [
            avatarId, self.air.allocateZone()])

	def avatarExit(self):
		DistributedObjectAI.avatarExit(self)