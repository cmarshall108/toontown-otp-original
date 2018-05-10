"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

from panda3d.core import NetDatagram
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify

class Participant(io.NetworkHandler):
    notify = directNotify.newCategory('Participant')

    def handle_datagram(self, di, datagram):
        try:
            code = di.get_uint8()
        except:
            return self.handle_disconnect()

        if code == 1:
            self.handle_control_message(di)

    def handle_control_message(self, di):
        try:
            channel = di.get_uint64()
        except:
            return self.handle_disconnect()

        if channel == types.CONTROL_MESSAGE:
            try:
                message_type = di.get_uint16()
                sender = di.get_uint64()
            except:
                return self.handle_disconnect()

            if message_type == types.CONTROL_SET_CHANNEL:
                self.network.interface.register_channel(self, sender)
            elif message_type == types.CONTROL_REMOVE_CHANNEL:
                self.network.interface.unregister_channel(self, sender)
        else:
            try:
                sender = di.get_uint64()
            except:
                return self.handle_disconnect()

            self.network.handle_route_message(self, channel, sender, di)

class ParticipantInterface(object):
    notify = directNotify.newCategory('ParticipantInterface')

    def __init__(self):
        self.participants = {}

    def is_registered(self, channel):
        return channel in self.participants

    def register_channel(self, participant, channel):
        if self.is_registered(channel):
            return

        participant.channel = channel
        self.participants[participant.channel] = participant

    def unregister_channel(self, participant, channel):
        if not self.is_registered(participant.channel):
            return

        del self.participants[participant.channel]
        participant.channel = None

class MessageDirector(io.NetworkListener):
    notify = directNotify.newCategory('MessageDirector')

    def __init__(self, address, port):
        io.NetworkListener.__init__(self, address, port, Participant)

        self.interface = ParticipantInterface()

    def handle_route_message(self, participant, channel, sender, di):
        if not self.interface.is_registered(channel):
            self.notify.warning('Cannot route message to channel: %d, channel is not a participant!' % (
                channel))

            return

        if not self.interface.is_registered(sender):
            self.notify.warning('Cannot route message to channel: %d, sender %d is not a participant!' % (
                channel, sender))

            return

        datagram = NetDatagram()
        datagram.add_uint64(sender)
        datagram.add_uint16(di.get_uint16())
        datagram.append_data(di.get_remaining_bytes())
        self.interface.participants[channel].handle_send_datagram(datagram)
