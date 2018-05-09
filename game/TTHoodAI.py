from game.HoodAI import HoodAI
from game.DistributedMickeyAI import DistributedMickeyAI
from game.DistributedFishingSpotAI import DistributedFishingSpotAI
from game.DistributedDoorAI import DistributedDoorAI
from game.DistributedToonInteriorAI import DistributedToonInteriorAI
from game import DoorTypes

class TTHoodAI(HoodAI):

	def __init__(self, air, zoneId=2000):
		HoodAI.__init__(self, air, zoneId)

	def generateObjectsInZone(self):
		HoodAI.generateObjectsInZone(self)
		
		if base.config.GetBool('want-classic-chars'):
			self.createClassicChars()

		self.createFishingSpots()
		self.createDoors()

	def createClassicChars(self):
		self.DistributedMickey = DistributedMickeyAI(self.air)
		self.DistributedMickey.setWalk('0', '0')
		self.DistributedMickey.generateWithRequired(self.zoneId)

	def createFishingSpots(self):
		self.DistributedFishingSpot_0 = DistributedFishingSpotAI(self.air)
		self.DistributedFishingSpot_0.setPosHpr(-77.5097, 47.3772, -3.2852, 176.818, 0, 0)
		self.DistributedFishingSpot_0.generateWithRequired(self.zoneId)

		self.DistributedFishingSpot_1 = DistributedFishingSpotAI(self.air)
		self.DistributedFishingSpot_1.setPosHpr(-90.7111, 43.1895, -3.30975, -133.237, 0, 0)
		self.DistributedFishingSpot_1.generateWithRequired(self.zoneId)

		self.DistributedFishingSpot_2 = DistributedFishingSpotAI(self.air)
		self.DistributedFishingSpot_2.setPosHpr(-83.6628, -42.4479, -3.95932, -29.2345, 0, 0)
		self.DistributedFishingSpot_2.generateWithRequired(self.zoneId)

	def createDoors(self):
		self.doors = {}
		self.doors[0] = DistributedDoorAI(self.air, zoneId=self.zoneId, blockNumber=20)
		self.doors[0].setDoorType(DoorTypes.EXT_HQ)
		self.doors[0].setSwing(0)
		self.doors[0].generateWithRequired(self.zoneId)

		self.interiorZone = self.air.allocateZone()
		self.interior = DistributedToonInteriorAI(self.air, zoneId=self.interiorZone, blockNumber=20)
		self.interior.generateWithRequired(self.interiorZone)

		self.doors[0].setOtherZoneIdAndDoId(self.interiorZone, doId=self.interior.getDoId())
		self.doors[1] = DistributedDoorAI(self.air, zoneId=self.interiorZone, blockNumber=20)
		self.doors[1].setDoorType(DoorTypes.INT_HQ)
		self.doors[1].setSwing(0)
		self.doors[1].generateWithRequired(self.zoneId)
		self.doors[1].setOtherZoneIdAndDoId(self.zoneId, doId=self.doors[0].getDoId())