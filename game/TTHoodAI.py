from direct.directnotify.DirectNotifyGlobal import directNotify
from game.HoodAI import HoodAI
from game import ToontownGlobals
from game import DoorTypes
from game.DistributedMickeyAI import DistributedMickeyAI
from game.DistributedFishingSpotAI import DistributedFishingSpotAI
from game.DistributedDoorAI import DistributedDoorAI
from game.DistributedToonInteriorAI import DistributedToonInteriorAI

class TTHoodAI(HoodAI):
	notify = directNotify.newCategory('TTHoodAI')

	def __init__(self, air):
		HoodAI.__init__(self, air, ToontownGlobals.ToontownCentral)

		self.fishingSpots = {}
		self.doors = {}

	def createObjects(self):
		HoodAI.createObjects(self)

		if simbase.config.GetBool('want-fishing-spots', False):
			self.createFishingSpots()

		if simbase.config.GetBool('want-doors', False):
			self.createDoors()

	def createClassicChars(self):
		self.classicChar = DistributedMickeyAI(self.air)
		self.classicChar.generateWithRequired(self.zoneId)

	def createFishingSpots(self):
		self.fishingSpots[0] = DistributedFishingSpotAI(self.air)
		self.fishingSpots[0].setPosHpr(-77.5097, 47.3772, -3.2852, 176.818, 0, 0)
		self.fishingSpots[0].generateWithRequired(self.zoneId)

		self.fishingSpots[1] = DistributedFishingSpotAI(self.air)
		self.fishingSpots[1].setPosHpr(-90.7111, 43.1895, -3.30975, -133.237, 0, 0)
		self.fishingSpots[1].generateWithRequired(self.zoneId)

		self.fishingSpots[2] = DistributedFishingSpotAI(self.air)
		self.fishingSpots[2].setPosHpr(-83.6628, -42.4479, -3.95932, -29.2345, 0, 0)
		self.fishingSpots[2].generateWithRequired(self.zoneId)

	def createDoors(self):
		self.interiorZone = self.air.allocateZone()
		self.interior = DistributedToonInteriorAI(self.air, zoneId=self.interiorZone, blockNumber=20)
		self.interior.generateWithRequired(self.interiorZone)

		self.doors[0] = DistributedDoorAI(self.air, zoneId=self.zoneId, blockNumber=20)
		self.doors[0].setDoorType(DoorTypes.EXT_HQ)
		self.doors[0].setSwing(0)
		self.doors[0].generateWithRequired(self.zoneId)
		self.doors[0].setOtherZoneIdAndDoId(self.interiorZone, doId=self.interior.getDoId())

		self.doors[1] = DistributedDoorAI(self.air, zoneId=self.interiorZone, blockNumber=20)
		self.doors[1].setDoorType(DoorTypes.INT_HQ)
		self.doors[1].setSwing(0)
		self.doors[1].generateWithRequired(self.zoneId)
		self.doors[1].setOtherZoneIdAndDoId(self.zoneId, doId=self.doors[0].getDoId())
