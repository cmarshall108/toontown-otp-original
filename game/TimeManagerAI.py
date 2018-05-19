import time

from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.distributed.ClockDelta import globalClockDelta

class TimeManagerAI(DistributedObjectAI):

	def __init__(self, air):
		DistributedObjectAI.__init__(self, air)

	def requestServerTime(self, context):
		self.sendUpdateToAvatarId(self.air.getAvatarIdFromSender(), 'serverTime', [context,
			globalClockDelta.getRealNetworkTime(bits=16), int(time.time())])
