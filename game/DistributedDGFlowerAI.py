from direct.distributed.DistributedObjectAI import DistributedObjectAI

class DistributedDGFlowerAI(DistributedObjectAI):

	def __init__(self, air, height=10):
		DistributedObjectAI.__init__(self, air)
		self.height = height

	def generate(self):
		DistributedObjectAI.generate(self)
		self.b_setHeight(self.height)

	def announceGenerate(self):
		DistributedObjectAI.announceGenerate(self)

	def avatarEnter(self):
		pass

	def avatarExit(self):
		pass

	def setHeight(self, height):
		self.height = height

	def d_setHeight(self, height):
		self.sendUpdate('setHeight', [height])

	def b_setHeight(self, height):
		self.setHeight(height)
		self.d_setHeight(height)
