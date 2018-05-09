from direct.distributed.DistributedSmoothNodeAI import DistributedSmoothNodeAI
from direct.task.TaskManagerGlobal import *
from direct.task.Task import Task

class DistributedToonAI(DistributedSmoothNodeAI):

	def __init__(self, air):
		DistributedSmoothNodeAI.__init__(self, air)

	def generate(self):
		DistributedSmoothNodeAI.generate(self)

	def announceGenerate(self):
		DistributedSmoothNodeAI.announceGenerate(self)

	def setParent(self, parent):
		self.sendUpdate('setParent', [
			parent])

	def clearSmoothing(self, bogus):
		self.sendUpdate('clearSmoothing', [
			bogus])

	def setSmPosHpr(self, x, y, z, h, p, r, t):
		self.sendUpdate('setSmPosHpr', [
			x,
			y,
			z,
			h,
			p,
			r,
			t])

	def setSmStop(self, timestamp):
		self.sendUpdate('setSmStop', [
			timestamp])

	def setAnimState(self, an1, an2, timestamp):
		pass

	def setSmXY(self, x, y, timestamp):
		self.sendUpdate('setSmXY', [
			x,
			y,
			timestamp])

	def setSmPos(self, x, y, z, timestamp):
		self.sendUpdate('setSmPos', [
			x,
			y,
			z,
			timestamp])

	def setSmStop(self, timestamp):
		self.sendUpdate('setSmStop', [
			timestamp])

	def setSmH(self, h, timestamp):
		self.sendUpdate('setSmH', [
			h, 
			timestamp])

	def setSmXYH(self, x, y, h, timestamp):
		self.sendUpdate('setSmXYH', [
			x,
			y,
			h,
			timestamp])

	def suggestResync(self, avatarId):
		self.sendUpdate('suggestResync', [
			avatarId])

	def setNearbyAvatarQT(self, qtList):
		self.sendUpdate('setNearbyAvatarQT', [
			qtList])

	def setQT(self, qtSequence):
		self.sendUpdate('setQT', [
			qtSequence])

	def setQTQuest(self, qtSequence):
		self.sendUpdate('setQTQuest', [
			qtSequence])

	def setEmoteState(self, emote1, emote2, timestamp):
		self.sendUpdate('setEmoteState', [
			emote1,
			emote2,
			timestamp])

	def teleportQuery(self, requesterId):
		self.sendUpdate('teleportQuery', [
			requesterId])

	def teleportResponse(self, avId, available, shardId, hoodId, zoneId):
		self.sendUpdate('teleportResponse', [
			avId,
			available,
			shardId,
			hoodId,
			zoneId])

	def setWhisperQTFrom(self, fromId, qtSequence):
		self.sendUpdate('setWhisperQTFrom', [
			fromId,
			qtSequence])

	def setAvatarId(self, avatarId):
		self.avatarId = avatarId

	def getAvatarId(self):
		return self.avatarId

	def setName(self, name):
		self.name = name

	def getName(self):
		return self.name

	def setDNAString(self, dnaString):
		self.dnaString = dnaString

	def getDNAString(self):
		return self.dnaString.decode('base64')

	def setMaxBankMoney(self, maxBankMoney):
		self.maxBankMoney = maxBankMoney

	def getMaxBankMoney(self):
		return self.maxBankMoney

	def setBankMoney(self, bankMoney):
		self.bankMoney = bankMoney

	def getBankMoney(self):
		return self.bankMoney

	def setMaxMoney(self, maxMoney):
		self.maxMoney = maxMoney

	def getMaxMoney(self):
		return self.maxMoney

	def setMoney(self, money):
		self.money = money

	def getMoney(self):
		return self.money

	def setMaxHp(self, maxHp):
		self.maxHp = maxHp

	def getMaxHp(self):
		return self.maxHp

	def setHp(self, hp):
		self.hp = hp

	def getHp(self):
		return self.hp

	def setExperience(self, experience):
		self.experience = experience

	def getExperience(self):
		return self.experience

	def setMaxCarry(self, maxCarry):
		self.maxCarry = maxCarry

	def getMaxCarry(self):
		return self.maxCarry

	def setTrackAccess(self, trackAccess):
		self.trackAccess = trackAccess

	def getTrackAccess(self):
		return self.trackAccess

	def setTrackProgress(self, trackProgress):
		self.trackProgress = trackProgress

	def getTrackProgress(self):
		return self.trackProgress

	def setInventory(self, inventory):
		self.inventory = inventory

	def getInventory(self):
		return self.inventory

	def setFriendsList(self, frieldsList):
		self.frieldsList = frieldsList

	def getFriendsList(self):
		return self.frieldsList

	def setDefaultShard(self, defaultShard):
		self.defaultShard = defaultShard

	def getDefaultShard(self):
		return self.defaultShard

	def setDefaultZone(self, defaultZone):
		self.defaultZone = defaultZone

	def getDefaultZone(self):
		return self.defaultZone

	def setShtickerBook(self, shtickerBook):
		self.shtickerBook = shtickerBook

	def getShtickerBook(self):
		return self.shtickerBook

	def setZonesVisited(self, zonesVisited):
		self.zonesVisited = zonesVisited

	def getZonesVisited(self):
		return self.zonesVisited

	def setHoodsVisited(self, hoodsVisited):
		self.hoodsVisited = hoodsVisited

	def getHoodsVisited(self):
		return self.hoodsVisited

	def setInterface(self, interface):
		self.interface = interface

	def getInterface(self):
		return self.interface

	def setAccountName(self, accountName):
		self.accountName = accountName

	def getAccountName(self):
		return self.accountName

	def setLastHood(self, lastHood):
		self.lastHood = lastHood

	def getLastHood(self):
		return self.lastHood

	def setTutorialAck(self, tutorialAck):
		self.tutorialAck = tutorialAck

	def getTutorialAck(self):
		return self.tutorialAck

	def setMaxClothes(self, maxClothes):
		self.maxClothes = maxClothes

	def getMaxClothes(self):
		return self.maxClothes

	def setClothesTopsList(self, clothesTopsList):
		self.clothesTopsList = clothesTopsList

	def getClothesTopsList(self):
		return self.clothesTopsList

	def setClothesBottomsList(self, clothesBottomsList):
		self.clothesBottomsList = clothesBottomsList

	def getClothesBottomsList(self):
		return self.clothesBottomsList

	def setEmoteAccess(self, emoteAccess):
		self.emoteAccess = emoteAccess

	def getEmoteAccess(self):
		return self.emoteAccess

	def setTeleportAccess(self, teleportAccess):
		self.teleportAccess = teleportAccess

	def getTeleportAccess(self):
		return self.teleportAccess

	def setCogStatus(self, cogStatus):
		self.cogStatus = cogStatus

	def getCogStatus(self):
		return self.cogStatus

	def setCogCount(self, cogCount):
		self.cogCount = cogCount

	def getCogCount(self):
		return self.cogCount

	def setCogRadar(self, cogRadar):
		self.cogRadar = cogRadar

	def getCogRadar(self):
		return self.cogRadar

	def setBuildingRadar(self, buildingRadar):
		self.buildingRadar = buildingRadar

	def getBuildingRadar(self):
		return self.buildingRadar

	def setFishes(self, fishes):
		self.fishes = fishes

	def getFishes(self):
		return self.fishes

	def setHouseId(self, houseId):
		self.houseId = houseId

	def getHouseId(self):
		return self.houseId

	def setQuests(self, quests):
		self.quests = quests

	def getQuests(self):
		return self.quests

	def setQuestHistory(self, questHistory):
		self.questHistory = questHistory

	def getQuestHistory(self):
		return self.questHistory

	def setRewardHistory(self, rewardHistory):
		self.rewardHistory = rewardHistory

	def getRewardHistory(self):
		return self.rewardHistory

	def setQuestCarryLimit(self, questCarryLimit):
		self.questCarryLimit = questCarryLimit

	def getQuestCarryLimit(self):
		return self.questCarryLimit

	def setCheesyEffect(self, cheesyEffect):
		self.cheesyEffect = cheesyEffect

	def getCheesyEffect(self):
		return self.cheesyEffect

	def setPosIndex(self, posIndex):
		self.posIndex = posIndex

	def getPosIndex(self):
		return self.posIndex