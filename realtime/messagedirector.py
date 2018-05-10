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

    def __init__(self, *args, **kwargs):
        io.NetworkHandler.__init__(self, *args, **kwargs)

    def handle_datagram(self, di):
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
                self.network.interface.add_channel(self, sender)
            elif message_type == types.CONTROL_REMOVE_CHANNEL:
                self.network.interface.remove_channel(self, sender)
            elif message_type == types.CONTROL_ADD_POST_REMOVE:
                pass
            elif message_type == types.CONTROL_CLEAR_POST_REMOVE:
                pass
        else:
            try:
                sender = di.get_uint64()
            except:
                return self.handle_disconnect()

            self.network.handle_route_message(self, channel, sender, di)

class ParticipantInterface(object):
    notify = directNotify.newCategory('ParticipantInterface')

    def __init__(self):
        self._participants = {}

    @property
    def participants(self):
        return self._participants

    def has_channel(self, channel):
        return channel in self._participants

    def add_channel(self, participant, channel):
        if self.has_channel(channel):
            return

        participant.channel = channel
        self._participants[participant.channel] = participant

    def remove_channel(self, participant, channel):
        if not self.has_channel(participant.channel):
            return

        del self._participants[participant.channel]
        participant.channel = None

class MessageDirector(io.NetworkListener):
    notify = directNotify.newCategory('MessageDirector')

    def __init__(self, address, port):
        io.NetworkListener.__init__(self, address, port, Participant)

        self._interface = ParticipantInterface()

    @property
    def interface(self):
        return self._interface

    def handle_route_message(self, participant, channel, sender, di):
        if not self._interface.has_channel(channel):
            self.notify.warning('Cannot route message to channel: %d, channel is not a participant!' % (
                channel))

            return

        if not self._interface.has_channel(sender):
            self.notify.warning('Cannot route message to channel: %d, sender %d is not a participant!' % (
                channel, sender))

            return

        datagram = NetDatagram()
        datagram.add_uint64(channel)
        datagram.add_uint64(sender)
        datagram.add_uint16(di.get_uint16())
        datagram.append_data(di.get_remaining_bytes())
        self._interface.participants[channel].handle_send_datagram(datagram)
