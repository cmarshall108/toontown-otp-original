from panda3d.core import *
from direct.distributed.PyDatagram import PyDatagram
from OTPInternalRepository import OTPInternalRepository
from direct.directnotify import DirectNotifyGlobal
from game.OtpDoGlobals import *
from realtime.types import *
from direct.distributed.AIZoneData import AIZoneDataStore
from game.TimeManagerAI import TimeManagerAI
from game.EstateManagerAI import EstateManagerAI
from game.TTHoodAI import TTHoodAI
from game.DDHoodAI import DDHoodAI
from game.DGHoodAI import DGHoodAI
from game.MMHoodAI import MMHoodAI

class AIRepository(OTPInternalRepository):
    notify = DirectNotifyGlobal.directNotify.newCategory('AIRepository')
    notify.setInfo(True)

    GameGlobalsId = OTP_DO_ID_TOONTOWN

    def __init__(self, baseChannel, serverId, districtName, dcFileNames):
        OTPInternalRepository.__init__(self, baseChannel, serverId, dcFileNames=dcFileNames, dcSuffix='AI')

        self.zoneDataStore = AIZoneDataStore()

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

    def getZoneDataStore(self):
        return self.zoneDataStore

    def getAvatarExitEvent(self, avId):
        return 'distObjDelete-%d' % avId

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

        # add a post remove to remove the shard from the state server
        # when we disconnect from the message director...
        dg = PyDatagram()
        dg.addServerHeader(self.serverId, self.ourChannel, STATESERVER_REMOVE_SHARD)
        self.addPostRemove(dg)

        # create the AI globals...
    	self.createGlobals()
        self.createZones()

    def createGlobals(self):
        self.timeManager = TimeManagerAI(self)
        self.timeManager.generateWithRequired(OTP_ZONE_ID_OLD_QUIET_ZONE)

        self.estateManager = EstateManagerAI(self)
        self.estateManager.generateWithRequired(OTP_ZONE_ID_OLD_QUIET_ZONE)

    def createZones(self):
        if simbase.config.GetBool('want-toontown-central', False):
            self.hoods.append(TTHoodAI(self))

        if simbase.config.GetBool('want-donalds-dock', False):
            self.hoods.append(DDHoodAI(self))

        if simbase.config.GetBool('want-daisys-garden', False):
            self.hoods.append(DGHoodAI(self))

        if simbase.config.GetBool('want-minnies-melody-land', False):
            self.hoods.append(MMHoodAI(self))

        for hood in self.hoods:
            hood.createObjects()
