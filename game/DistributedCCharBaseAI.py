import random

from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.distributed.ClockDelta import *

class DistributedCCharBaseAI(DistributedObjectAI):

	def __init__(self, air):
		DistributedObjectAI.__init__(self, air)

		self.srcNode = ''
		self.destNode = ''

	def generate(self):
		DistributedObjectAI.generate(self)

	def announceGenerate(self):
		DistributedObjectAI.announceGenerate(self)

	def setWalk(self, srcNode, destNode):
		self.srcNode = srcNode
		self.destNode = destNode

	def getWalk(self):
		return [self.srcNode, self.destNode, globalClockDelta.getRealNetworkTime()]

	def avatarEnter(self):
		chatCatagory = 1 # Avatar entering.
		chatMessage = random.randint(0, 3)

		self.sendUpdate('setChat', [chatCatagory, chatMessage,
			self.air.getAvatarIdFromSender()])

	def avatarExit(self):
		chatCatagory = 2 # Avatar leaving.
		chatMessage = random.randint(0, 3)

		self.sendUpdate('setChat', [chatCatagory, chatMessage,
			self.air.getAvatarIdFromSender()])
