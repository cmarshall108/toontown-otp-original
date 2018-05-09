
class HoodAI:

	def __init__(self, air, zoneId):
		self.air = air
		self.zoneId = zoneId

	def generateObjectsInZone(self):
		print ('HoodAI: Generated neighborhood with zone: %d' % self.zoneId)