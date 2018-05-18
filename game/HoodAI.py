from direct.directnotify.DirectNotifyGlobal import directNotify

class HoodAI:
	notify = directNotify.newCategory('HoodAI')

	def __init__(self, air, zoneId):
		self.air = air
		self.zoneId = zoneId

	def createObjects(self):
		self.notify.info('Created objects for hood %s in zone %d.' % (
			self.__class__.__name__, self.zoneId))
