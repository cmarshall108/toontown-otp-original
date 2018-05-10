from panda3d.core import *
from direct.distributed.PyDatagram import PyDatagram
from OTPInternalRepository import OTPInternalRepository
from direct.directnotify import DirectNotifyGlobal
from game.OtpDoGlobals import *
from realtime.types import *
from game.TimeManagerAI import TimeManagerAI

class AIRepository(OTPInternalRepository):
    notify = DirectNotifyGlobal.directNotify.newCategory('AIRepository')
    notify.setInfo(True)

    GameGlobalsId = OTP_DO_ID_TOONTOWN

    def __init__(self, baseChannel, serverId, districtName, dcFileNames):
        OTPInternalRepository.__init__(self, baseChannel, serverId, dcFileNames=dcFileNames, dcSuffix='AI')

        self.districtName = districtName
        self.districtPopulation = 0
        self.districtId = self.ourChannel

        self.hoods = []
        self.zoneAllocator = UniqueIdAllocator(61000, 1 << 20)

    def getGameDoId(self):
        return self.GameGlobalsId

    def getAvatarIdFromSender(self):
        return self.getMsgSender() & 0xFFFFFFFF

    def getAccountIdFromSender(self):
        return (self.getMsgSender() >> 32) & 0xFFFFFFFF

    def allocateZone(self):
        return self.zoneAllocator.allocate()

    def deallocateZone(self, zoneId):
        self.zoneAllocator.free(zoneId)

    def handleConnected(self):
    	OTPInternalRepository.handleConnected(self)

        # register the AI on the state server...
        dg = PyDatagram()
        dg.addServerHeader(self.serverId, self.ourChannel, STATESERVER_ADD_SHARD)
        dg.addString(self.districtName)
        dg.addUint32(self.districtPopulation)
        self.send(dg)

        # create the AI globals...
    	self.createGlobals()
        self.createZones()

    def createGlobals(self):
        self.timeManager = TimeManagerAI(self)
        self.timeManager.generateWithRequired(3)

    def createZones(self):
        pass
