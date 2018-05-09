from direct.distributed.PyDatagram import PyDatagram
from OTPInternalRepository import OTPInternalRepository
from pandac.PandaModules import *
from src.util.OtpDoGlobals import *
from src.util.types import *
from game.TimeManagerAI import TimeManagerAI
from game import TTHoodAI
from game import BRHoodAI
from game import DDHoodAI
from game import MMHoodAI
from game import DGHoodAI
from game import DLHoodAI
from game.EstateManagerAI import EstateManagerAI

class AIRepository(OTPInternalRepository):

    def __init__(self, baseChannel, stateServerChannel, districtName):
        OTPInternalRepository.__init__(self, baseChannel, stateServerChannel, dcSuffix='AI')
        self.districtName = districtName
        self.notify.setInfo(True)
        self.GameGlobalsId = OTP_DO_ID_TOONTOWN
        self.districtPopulation = 0
        self.districtId = self.ourChannel
        self.hoods = []
        self.zoneAllocator = UniqueIdAllocator(61000, 1 << 20)
        # now connect to message director.
        self.connect(host='127.0.0.1')

    def getGameDoId(self):
        return self.GameGlobalsId

    def getAvatarIdFromSender(self):
        return self.getMsgSender() & 0xFFFFFFFF

    def getAccountIdFromSender(self):
        return (self.getMsgSender() >> 32) & 0xFFFFFFFF

    def allocateZone(self):
        return self.zoneAllocator.allocate()

    def handleConnected(self):
    	OTPInternalRepository.handleConnected(self)
    	self.notify.info('Successfully connected to otp server!')
        self.sendDistrictOnline()
    	self.createAIGlobals()
        self.createZones()

    def sendDistrictOnline(self):
    	datagram = PyDatagram()
        datagram.addServerHeader(STATE_SERVER_CHANNEl, self.ourChannel, CONTROL_MESSAGE)
        datagram.addUint16(STATESERVER_OBJECT_QUERY_MANAGING_AI)
        datagram.addUint32(self.ourChannel)
        datagram.addString(self.districtName)
        datagram.addUint32(self.districtPopulation)
        self.send(datagram)

    def createAIGlobals(self):
        self.timeManager = TimeManagerAI(self)
        #self.timeManager.generateWithRequired(3)

        self.estateMgr = EstateManagerAI(self)
        self.estateMgr.generateWithRequired(3)

    def createZones(self):
        self.hoods.append(DDHoodAI.DDHoodAI(self))
        self.hoods.append(TTHoodAI.TTHoodAI(self))
        self.hoods.append(BRHoodAI.BRHoodAI(self))
        self.hoods.append(MMHoodAI.MMHoodAI(self))
        self.hoods.append(DGHoodAI.DGHoodAI(self))
        self.hoods.append(DLHoodAI.DLHoodAI(self))
        for hood in self.hoods:
            hood.generateObjectsInZone()