from pandac.PandaModules import *
from direct.directnotify import DirectNotifyGlobal
from direct.distributed.ConnectionRepository import ConnectionRepository
from src.util.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from game.DistributedToonAI import DistributedToonAI
from src.util.MsgTypes import *
from src.util.types import *
import string, types, ast

class OTPInternalRepository(ConnectionRepository):
    notify = DirectNotifyGlobal.directNotify.newCategory("OTPInternalRepository")

    def __init__(self, baseChannel, serverId=None, dcFileNames = None, dcSuffix = 'AI', connectMethod = None, threadedNet = None):
        if connectMethod is None:
            connectMethod = self.CM_HTTP
        ConnectionRepository.__init__(self, connectMethod, config, hasOwnerView = False)
        self.setClientDatagram(False)
        self.dcSuffix = dcSuffix
        if hasattr(self, 'setVerbose'):
            if self.config.GetBool('verbose-internalrepository'):
                self.setVerbose(1)

        # The State Server we are configured to use for creating objects.
        #If this is None, generating objects is not possible.
        self.serverId = self.config.GetInt('air-stateserver', 0) or None
        if serverId is not None:
            self.serverId = serverId

        maxChannels = self.config.GetInt('air-channel-allocation', 1000000)
        self.channelAllocator = UniqueIdAllocator(baseChannel, baseChannel+maxChannels-1)
        self._registeredChannels = set()
        self.contextAllocator = UniqueIdAllocator(0, 100)
        self.ourChannel = self.allocateChannel()
        self.eventLogId = self.config.GetString('eventlog-id', 'AIR:%d' % self.ourChannel)
        self.eventSocket = None
        eventLogHost = self.config.GetString('eventlog-host', '')
        if eventLogHost:
            if ':' in eventLogHost:
                host, port = eventLogHost.split(':', 1)
                self.setEventLogHost(host, int(port))
            else:
                self.setEventLogHost(eventLogHost)

        self.readDCFile(dcFileNames)

    def uniqueName(self, name=''):
        return name

    def allocateChannel(self):
        """
        Allocate an unused channel out of this AIR's configured channel space.

        This is also used to allocate IDs for DistributedObjects, since those
        occupy a channel.
        """

        return self.channelAllocator.allocate()

    def deallocateChannel(self, channel):
        """
        Return the previously-allocated channel back to the allocation pool.
        """

        self.channelAllocator.free(channel)

    def registerForChannel(self, channel):
        """
        Register for messages on a specific Message Director channel.

        If the channel is already open by this AIR, nothing will happen.
        """

        if channel in self._registeredChannels:
            return
        self._registeredChannels.add(channel)

        dg = PyDatagram()
        dg.addServerHeader(channel, self.ourChannel, CONTROL_SET_CHANNEL)
        self.send(dg)

    def unregisterForChannel(self, channel):
        """
        Unregister a channel subscription on the Message Director. The Message
        Director will cease to relay messages to this AIR sent on the channel.
        """

        if channel not in self._registeredChannels:
            return
        self._registeredChannels.remove(channel)

        dg = PyDatagram()
        dg.addServerHeader(channel, self.ourChannel, CONTROL_REMOVE_CHANNEL)
        self.send(dg)

    def addPostRemove(self, dg):
        """
        Register a datagram with the Message Director that gets sent out if the
        connection is ever lost.

        This is useful for registering cleanup messages: If the Panda3D process
        ever crashes unexpectedly, the Message Director will detect the socket
        close and automatically process any post-remove datagrams.
        """

        dg2 = PyDatagram()
        dg2.addServerControlHeader(CONTROL_ADD_POST_REMOVE)
        dg2.addString(dg.getMessage())
        self.send(dg2)

    def clearPostRemove(self):
        """
        Clear all datagrams registered with addPostRemove.

        This is useful if the Panda3D process is performing a clean exit. It may
        clear the "emergency clean-up" post-remove messages and perform a normal
        exit-time clean-up instead, depending on the specific design of the game.
        """

        dg = PyDatagram()
        dg.addServerControlHeader(CONTROL_CLEAR_POST_REMOVE)
        self.send(dg)

    def handleDatagram(self, di):
        msgType = self.getMsgType()

        if msgType == STATESERVER_OBJECT_QUERY_FIELDS:
            self.handleRecieveFieldUpdate(di)
        elif msgType == CLIENT_GET_AVATAR_DETAILS_RESP:
            self.handleAvatarGenerate(di)

    def handleAvatarGenerate(self, di):
        target = di.getUint64()
        avatarId = di.getUint32()
        fields = ast.literal_eval(di.getString())
        dclass = self.dclassesByName['DistributedToonAI']

        if int(fields['setAvatarId']) != avatarId:
            return # We've got a hacker, or a mistake!

        datagram = PyDatagram()
        datagram.addServerHeader(CLIENT_AGENT_CHANNEL, self.ourChannel, CONTROL_MESSAGE)
        datagram.addUint16(CLIENT_SET_AVATAR)
        datagram.addChannel(target)
        datagram.addUint16(CLIENT_GET_AVATAR_DETAILS_RESP)
        datagram.addUint32(int(fields['setAvatarId']))
        datagram.addUint8(0) # Return code.

        avDg = PyDatagram()

        DistributedToon = DistributedToonAI(self)
        DistributedToon.generate()
        DistributedToon.announceGenerate()

        DistributedToon.setName(fields['setName'])
        field = dclass.getFieldByName('setName')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setDNAString(fields['setDNAString'])
        field = dclass.getFieldByName('setDNAString')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setMaxBankMoney(fields['setMaxBankMoney'])
        field = dclass.getFieldByName('setMaxBankMoney')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setBankMoney(fields['setBankMoney'])
        field = dclass.getFieldByName('setBankMoney')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setMaxMoney(fields['setMaxMoney'])
        field = dclass.getFieldByName('setMaxMoney')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setMoney(fields['setMoney'])
        field = dclass.getFieldByName('setMoney')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setMaxHp(fields['setMaxHp'])
        field = dclass.getFieldByName('setMaxHp')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setHp(fields['setHp'])
        field = dclass.getFieldByName('setHp')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setExperience(fields['setExperience'])
        field = dclass.getFieldByName('setExperience')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setMaxCarry(fields['setMaxCarry'])
        field = dclass.getFieldByName('setMaxCarry')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setTrackAccess(fields['setTrackAccess'])
        field = dclass.getFieldByName('setTrackAccess')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setTrackProgress(fields['setTrackProgress'])
        field = dclass.getFieldByName('setTrackProgress')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setInventory(fields['setInventory'])
        field = dclass.getFieldByName('setInventory')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setFriendsList(fields['setFriendsList'])
        field = dclass.getFieldByName('setFriendsList')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setDefaultShard(fields['setDefaultShard'])
        field = dclass.getFieldByName('setDefaultShard')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setDefaultZone(fields['setDefaultZone'])
        field = dclass.getFieldByName('setDefaultZone')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setShtickerBook(fields['setShtickerBook'])
        field = dclass.getFieldByName('setShtickerBook')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setZonesVisited(fields['setZonesVisited'])
        field = dclass.getFieldByName('setZonesVisited')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setHoodsVisited(fields['setHoodsVisited'])
        field = dclass.getFieldByName('setHoodsVisited')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setInterface(fields['setInterface'])
        field = dclass.getFieldByName('setInterface')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setAccountName(fields['setAccountName'])
        field = dclass.getFieldByName('setAccountName')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setLastHood(fields['setLastHood'])
        field = dclass.getFieldByName('setLastHood')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setTutorialAck(fields['setTutorialAck'])
        field = dclass.getFieldByName('setTutorialAck')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setMaxClothes(fields['setMaxClothes'])
        field = dclass.getFieldByName('setMaxClothes')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setClothesTopsList(fields['setClothesTopsList'])
        field = dclass.getFieldByName('setClothesTopsList')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setClothesBottomsList(fields['setClothesBottomsList'])
        field = dclass.getFieldByName('setClothesBottomsList')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setEmoteAccess(fields['setEmoteAccess'])
        field = dclass.getFieldByName('setEmoteAccess')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setTeleportAccess(fields['setTeleportAccess'])
        field = dclass.getFieldByName('setTeleportAccess')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setCogStatus(fields['setCogStatus'])
        field = dclass.getFieldByName('setCogStatus')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setCogCount(fields['setCogCount'])
        field = dclass.getFieldByName('setCogCount')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setCogRadar(fields['setCogRadar'])
        field = dclass.getFieldByName('setCogRadar')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setBuildingRadar(fields['setBuildingRadar'])
        field = dclass.getFieldByName('setBuildingRadar')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setFishes(fields['setFishes'])
        field = dclass.getFieldByName('setFishes')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setHouseId(fields['setHouseId'])
        field = dclass.getFieldByName('setHouseId')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setQuests(fields['setQuests'])
        field = dclass.getFieldByName('setQuests')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setQuestHistory(fields['setQuestHistory'])
        field = dclass.getFieldByName('setQuestHistory')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setRewardHistory(fields['setRewardHistory'])
        field = dclass.getFieldByName('setRewardHistory')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setQuestCarryLimit(fields['setQuestCarryLimit'])
        field = dclass.getFieldByName('setQuestCarryLimit')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setCheesyEffect(fields['setCheesyEffect'])
        field = dclass.getFieldByName('setCheesyEffect')
        dclass.packRequiredField(avDg, DistributedToon, field)
        DistributedToon.setPosIndex(fields['setPosIndex'])
        field = dclass.getFieldByName('setPosIndex')
        dclass.packRequiredField(avDg, DistributedToon, field)
        avDi = PyDatagramIterator(avDg)
        requiredFields = avDi.getRemainingBytes()

        # Store the toon...
        DistributedToon.doId = int(fields['setAvatarId'])
        DistributedToon.generate()
        DistributedToon.announceGenerate()

        # TODO: FIX ME!
        try:
            self.addDOToTables(DistributedToon, location=(200000000, 2000))
        except:
            pass

        dg = PyDatagram()
        dg.addServerHeader(STATE_SERVER_CHANNEl, self.ourChannel, CONTROL_MESSAGE)
        dg.addUint16(CLIENT_SET_AVATAR_RESP)
        dg.addChannel(target)
        dg.addUint32(DistributedToon.doId)
        dg.addUint32(200000000)
        dg.addUint16(2000)
        dg.addUint16(dclass.getNumber())
        dg.appendData(requiredFields)
        self.send(dg)

        datagram.appendData(requiredFields)
        self.send(datagram)

    def handleRecieveFieldUpdate(self, di):
        doId = di.getUint32()
        dclass = di.getUint16()
        fieldId = di.getUint16()

        # Repack the approiate values.
        datagram = PyDatagram()
        datagram.appendData(di.getRemainingBytes())

        # Security check.
        if doId not in self.doId2do:
            return # Invalid update from a doId!

        dclass = self.dclassesByName[self.doId2do[doId].__class__.__name__]
        
        """
        # This fixes the dclass field count index issue.
        nextFieldNum = -1
        self.fields = {}

        for i in range(0, dclass.getNumInheritedFields()):
            if dclass.getFieldByIndex(i) != None:
                nextFieldNum += 1
                fieldTarget = dclass.getFieldByIndex(i)
                self.fields[fieldTarget.getNumber()] = nextFieldNum
            else:
                if dclass.getInheritedField(i) != None:
                    nextFieldNum += 1
                    fieldTarget = dclass.getInheritedField(i)
                    self.fields[fieldTarget.getNumber()] = nextFieldNum
        """

        # Find the field by the index we've recieved.
        print 'done field'
        field = dclass.getInheritedField(fieldId)

        do = dclass.getClassDef()(self)
        do.dclass = dclass
        do.doId = doId

        do.generate()
        print field.getName()
        try:
            dclass.directUpdate(do, field.getName(), datagram)
        except:
            return

    def handleObjEntry(self, di, other):
        doId = di.getUint32()
        parentId = di.getUint32()
        zoneId = di.getUint32()
        classId = di.getUint16()

        if classId not in self.dclassesByNumber:
            self.notify.warning('Received entry for unknown dclass=%d! (Object %d)' % (classId, doId))
            return

        if doId in self.doId2do:
            return # We already know about this object; ignore the entry.

        dclass = self.dclassesByNumber[classId]

        do = dclass.getClassDef()(self)
        do.dclass = dclass
        do.doId = doId
        # The DO came in off the server, so we do not unregister the channel when
        # it dies:
        do.doNotDeallocateChannel = True
        self.addDOToTables(do, location=(parentId, zoneId))

        # Now for generation:
        do.generate()
        if other:
            do.updateAllRequiredOtherFields(dclass, di)
        else:
            do.updateAllRequiredFields(dclass, di)

    def handleObjExit(self, di):
        doId = di.getUint32()

        if doId not in self.doId2do:
            self.notify.warning('Received AI exit for unknown object %d' % (doId))
            return

        do = self.doId2do[doId]
        do.sendDeleteEvent()
        self.removeDOFromTables(do)
        do.delete()

    def sendUpdate(self, do, fieldName, args):
        """
        Send a field update for the given object.
        You should use do.sendUpdate(...) instead. This is not meant to be
        called directly unless you really know what you are doing.
        """

        self.sendUpdateToChannel(do, do.doId, fieldName, args)

    def sendUpdateToChannel(self, do, channelId, fieldName, args):
        """
        Send an object field update to a specific channel.
        This is useful for directing the update to a specific client or node,
        rather than at the State Server managing the object.
        You should use do.sendUpdateToChannel(...) instead. This is not meant
        to be called directly unless you really know what you are doing.
        """

        dclass = do.dclass
        field = dclass.getFieldByName(fieldName)

        # This fixes the dclass field count index issue.
        nextFieldNum = -1
        self.fields = {}

        nextFieldNum = -1
        self.fields = {}

        for i in range(0, dclass.getNumInheritedFields()):
            if dclass.getInheritedField(i) != None:
                nextFieldNum += 1
                fieldTarget = dclass.getInheritedField(i)
                self.fields[fieldTarget.getNumber()] = nextFieldNum

        fieldPacker = DCPacker()
        fieldPacker.rawPackUint16(self.fields[field.getNumber()])
        fieldPacker.beginPack(field)
        field.packArgs(fieldPacker, args)
        fieldPacker.endPack()

        datagram = PyDatagram()
        datagram.addServerHeader(STATE_SERVER_CHANNEl, self.ourChannel, CONTROL_MESSAGE)
        datagram.addUint16(STATESERVER_OBJECT_UPDATE_FIELD)
        datagram.addChannel(channelId)
        datagram.addUint32(do.doId)
        datagram.appendData(fieldPacker.getString())
        self.send(datagram)

    def sendSetLocation(self, do, parentId, zoneId):
        dg = PyDatagram()
        dg.addServerHeader(do.doId, self.ourChannel, STATESERVER_OBJECT_SET_LOCATION)
        dg.addUint32(parentId)
        dg.addUint32(zoneId)
        self.send(dg)

    def generateWithRequired(self, do, parentId, zoneId, optionalFields=[]): # TODO: optionalFields
        """
        Generate an object onto the State Server, choosing an ID from the pool.

        You should probably use do.generateWithRequired(...) instead.
        """
        self.generateWithRequiredAndId(do, parentId, zoneId, optionalFields)

    def generateWithRequiredAndId(self, do, parentId, zoneId, optionalFields=[]):
        """
        Generate an object onto the State Server, specifying its ID and location.

        You should probably use do.generateWithRequiredAndId(...) instead.
        """

        do.preAllocateDoId()
        # Generate the do.
        do.generate()
        do.announceGenerate()
        
        self.addDOToTables(do, location=(parentId, zoneId))
        #do.sendGenerateWithRequired(self, parentId, zoneId, optionalFields)
        
        # Send generate to the state server.
        dclass = self.dclassesByName[do.__class__.__name__]
        dg = PyDatagram()
        dg.addServerHeader(STATE_SERVER_CHANNEl, self.ourChannel, CONTROL_MESSAGE)
        dg.addUint16(STATESERVER_OBJECT_GENERATE_WITH_REQUIRED_OTHER)
        dg.addUint32(do.doId)
        dg.addUint32(parentId)
        dg.addUint32(zoneId)
        dg.addUint32(dclass.getNumber())

        for i in range(0, dclass.getNumInheritedFields()):
            field = dclass.getInheritedField(i)

            if field.isRequired():
                dclass.packRequiredField(dg, do, field)

        self.send(dg)

    def requestDelete(self, do):
        """
        Request the deletion of an object that already exists on the State Server.

        You should probably use do.requestDelete() instead.
        """

        dg = PyDatagram()
        dg.addServerHeader(do.doId, self.ourChannel, STATESERVER_OBJECT_DELETE_RAM)
        dg.addUint32(do.doId)
        self.send(dg)

    def connect(self, host, port=7101):
        """
        Connect to a Message Director. The airConnected message is sent upon
        success.

        N.B. This overrides the base class's connect(). You cannot use the
        ConnectionRepository connect() parameters.
        """

        url = URLSpec()
        url.setServer(host)
        url.setPort(port)

        self.notify.info('Now connecting to %s:%s...' % (host, port))
        ConnectionRepository.connect(self, [url],
                                     successCallback=self.__connected,
                                     failureCallback=self.__connectFailed,
                                     failureArgs=[host, port])

    def __connected(self):
        self.notify.info('Connected successfully.')

        # Listen to our channel...
        self.registerForChannel(self.ourChannel)

        messenger.send('airConnected')
        self.handleConnected()

    def __connectFailed(self, code, explanation, host, port):
        self.notify.warning('Failed to connect! (code=%s; %r)' % (code, explanation))

        # Try again...
        retryInterval = config.GetFloat('air-reconnect-delay', 5.0)
        taskMgr.doMethodLater(retryInterval, self.connect, 'Reconnect delay', extraArgs=[host, port])

    def handleConnected(self):
        """
        Subclasses should override this if they wish to handle the connection
        event.
        """

    def lostConnection(self):
        # This should be overridden by a subclass if unexpectedly losing connection
        # is okay.
        self.notify.error('Lost connection to gameserver!')

    def setEventLogHost(self, host, port=7197):
        """
        Set the target host for Event Logger messaging. This should be pointed
        at the UDP IP:port that hosts the cluster's running Event Logger.

        Providing a value of None or an empty string for 'host' will disable
        event logging.
        """

        if not host:
            self.eventSocket = None
            return

        address = SocketAddress()
        if not address.setHost(host, port):
            self.notify.warning('Invalid Event Log host specified: %s:%s' % (host, port))
            self.eventSocket = None
        else:
            self.eventSocket = SocketUDPOutgoing()
            self.eventSocket.InitToAddress(address)

    def writeServerEvent(self, logtype, *args):
        """
        Write an event to the central Event Logger, if one is configured.

        The purpose of the Event Logger is to keep a game-wide record of all
        interesting in-game events that take place. Therefore, this function
        should be used whenever such an interesting in-game event occurs.
        """

        if self.eventSocket is None:
            return # No event logger configured!

        dg = PyDatagram()
        dg.addString(self.eventLogId)
        dg.addString(logtype)
        for arg in args:
            dg.addString(str(arg))
        self.eventSocket.Send(dg.getMessage())

    def claimOwnership(self, districtId):
        dg = PyDatagram()
        dg.addServerHeader(districtId, self.ourChannel, STATESERVER_OBJECT_SET_AI)
        dg.addChannel(self.ourChannel)
        self.send(dg)
