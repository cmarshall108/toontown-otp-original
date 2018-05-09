from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.task.TaskManagerGlobal import *
import FishingCodes, random

class DistributedFishingSpotAI(DistributedObjectAI):

	def __init__(self, air):
		DistributedObjectAI.__init__(self, air)
		self.posHpr = [0, 0, 0, 0, 0, 0]
		self.avIds = [None, None, None, None, None, None]
		self.isOccupied = False
		self.isReeling = False
		self.fishCaught = False
		self.chanceForTrue = 80
		self.currentChance = 0
		self.isDeciding = False

	def generate(self):
		DistributedObjectAI.generate(self)

	def announceGenerate(self):
		DistributedObjectAI.announceGenerate(self)

	def setPosHpr(self, x, y, z, h, p, r):
		self.posHpr = [x, y, z, h, p, r]

	def getPosHpr(self):
		return self.posHpr

	def requestEnter(self):
		if self.isOccupied == False:
			self.b_setOccupied(self.air.getAvatarIdFromSender(), True)

		self.d_setMovie(FishingCodes.EnterMovie, code=0, item=0, speed=1)

	def requestExit(self):
		if self.isOccupied == True:
			self.b_setOccupied(0, False)

		self.d_setMovie(FishingCodes.ExitMovie, code=0, item=0, speed=1)

	def setOccupied(self, avId, isOccupied):
		self.isOccupied = isOccupied
		self.avId = avId

	def d_setOccupied(self, avId):
		self.sendUpdate('setOccupied', [
			avId])

	def b_setOccupied(self, avId, isOccupied):
		self.setOccupied(avId, isOccupied)
		self.d_setOccupied(avId)

	def doCast(self):
		self.d_setMovie(FishingCodes.CastMovie, code=0, item=0, speed=FishingCodes.CastTime)

	def doAutoReel(self):
		pass

	def doReel(self, speed, netTime, netDistance):
		reelSpeed = netTime / netTime * speed / 3.5

		if self.isReeling == False:
			self.d_setMovie(FishingCodes.BeginReelMovie, code=0, item=0, speed=reelSpeed)
			self.isReeling = True
		else:
			self.d_setMovie(FishingCodes.ContinueReelMovie, code=0, item=0, speed=reelSpeed)
			if self.isDeciding != True:
				if self.fishCaught != True:
					self._maybeCatchFish()

		return

	def d_setMovie(self, mode, code, item, speed):
		self.sendUpdate('setMovie', [
			mode, 
			code, 
			item, 
			speed])

	def _maybeCatchFish(self):
		if self.isDeciding == True:
			# The ai is already deciding if the player caught a fish.
			return

		taskMgr.doMethodLater(FishingCodes.NibbleTime, self._fishNibble, 'fish_nibble')

	def _fishNibble(self, task):
		nibbleWaitTime = random.randint(FishingCodes.NibbleMinWait, FishingCodes.NibbleMaxWait)
		taskMgr.doMethodLater(nibbleWaitTime, self._startCheckForQuery, 'check_for_fish_query')
		# Set the movie state.
		self.d_setMovie(FishingCodes.NibbleMovie, code=0, item=0, speed=1)

	def _startCheckForQuery(self, task):
		if self.isDeciding == False and self.fishCaught == False:
			self.isDeciding = True
			self.fishCaught = True
		else:
			return task.done

		self._checkForFishQuery()
		return task.done

	def _checkForFishQuery(self):
		fishId = random.randint(0, 10)

		if self.isDeciding == True and self.fishCaught == True:
			self._caughtFish(item=fishId, speed=1)
			self.isDeciding = False
			self.fishCaught = False
		else:
			self.fishCaught = False
			self.isDeciding = False

	def _caughtFish(self, item, speed):
		self.d_setMovie(FishingCodes.PullInMovie, code=FishingCodes.FishItem, item=item, speed=speed)
		return None

	def d_fishReleaseQuery(self, fish):
		self.sendUpdate('fishReleaseQuery', [
			fish])

	def fishRelease(self, fish):
		pass