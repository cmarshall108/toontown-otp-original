from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.distributed.ClockDelta import *
import random

class DistributedCCharBaseAI(DistributedObjectAI):

	def __init__(self, air):
		DistributedObjectAI.__init__(self, air)
		self.timestamp = globalClockDelta.getRealNetworkTime()

	def generate(self):
		DistributedObjectAI.generate(self)

	def announceGenerate(self):
		DistributedObjectAI.announceGenerate(self)

	def setWalk(self, srcNode, destNode):
		self.srcNode = srcNode
		self.destNode = destNode

	def getWalk(self):
		return [self.srcNode, self.destNode, self.timestamp]

	def avatarEnter(self):
		self.setAvatarEnterChat()

	def setAvatarEnterChat(self):
		chatCatagory = 1 # Avatar entering.
		chatMessage = random.randint(0, 3)

		self.sendUpdate('setChat', [
			chatCatagory, 
			chatMessage, 
			self.air.getAvatarIdFromSender()])

	def avatarExit(self):
		self.setAvatarExitChat()

	def setAvatarExitChat(self):
		chatCatagory = 2 # Avatar leaving.
		chatMessage = random.randint(0, 3)

		self.sendUpdate('setChat', [
			chatCatagory, 
			chatMessage, 
			self.air.getAvatarIdFromSender()])