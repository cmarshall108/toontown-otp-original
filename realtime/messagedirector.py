"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

from panda3d.core import DatagramIterator
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify

class Participant(io.NetworkHandler):
    notify = directNotify.newCategory('Participant')

    def __init__(self, *args, **kwargs):
        io.NetworkHandler.__init__(self, *args, **kwargs)

    def handle_datagram(self, di):
        if di.get_uint8() == 1:
            self.handle_control_message(di)

    def handle_control_message(self, di):
        channel = di.get_uint64()

        if channel == types.CONTROL_MESSAGE:
            message_type = di.get_uint16()
            sender = di.get_uint64()

            if message_type == types.CONTROL_SET_CHANNEL:
                self.network.interface.add_channel(self, sender)
            elif message_type == types.CONTROL_REMOVE_CHANNEL:
                self.network.interface.remove_channel(self)
            elif message_type == types.CONTROL_ADD_POST_REMOVE:
                if not di.get_remaining_size():
                    return

                self.network.interface.add_post_remove(sender, io.NetworkDatagram(
                    di.get_remaining_bytes()))
            elif message_type == types.CONTROL_CLEAR_POST_REMOVE:
                self.network.interface.remove_post_remove(self)
        else:
            self.network.handle_route_message(channel, di.get_uint64(), di)

    def handle_post_removes(self):
        for datagram in self.network.interface.get_post_removes(self):
            self.handle_datagram(DatagramIterator(datagram))

        self.network.interface.remove_post_remove(self)

    def handle_disconnected(self):
        self.handle_post_removes()
        self.network.interface.remove_channel(self)
        io.NetworkHandler.handle_disconnected(self)

class ParticipantInterface(object):
    notify = directNotify.newCategory('ParticipantInterface')

    def __init__(self):
        self._participants = {}
        self._post_removes = {}

    @property
    def participants(self):
        return self._participants

    @property
    def post_removes(self):
        return self._post_removes

    def has_channel(self, channel):
        return channel in self._participants

    def add_channel(self, participant, channel):
        if self.has_channel(channel):
            return

        participant.channel = channel
        self._participants[participant.channel] = participant

    def remove_channel(self, participant):
        if not self.has_channel(participant.channel):
            return

        del self._participants[participant.channel]
        participant.channel = None

    def get_participant(self, channel):
        return self._participants.get(channel)

    def has_post_remove(self, channel):
        return channel in self._post_removes

    def add_post_remove(self, channel, datagram):
        post_removes = self._post_removes.setdefault(channel, [])
        post_removes.append(datagram)

    def remove_post_remove(self, participant):
        if not self.has_post_remove(participant.channel):
            return

        del self._post_removes[participant.channel]

    def get_post_removes(self, participant):
        if not self.has_post_remove(participant.channel):
            return []

        return self._post_removes.pop(participant.channel)

class MessageDirector(io.NetworkListener):
    notify = directNotify.newCategory('MessageDirector')

    def __init__(self, address, port):
        io.NetworkListener.__init__(self, address, port, Participant)

        self._interface = ParticipantInterface()

    @property
    def interface(self):
        return self._interface

    def handle_route_message(self, channel, sender, di):
        if not self._interface.has_channel(channel):
            self.notify.warning('Cannot route message to channel: %d, channel is not a participant!' % (
                channel))

            return

        if not self._interface.has_channel(sender):
            self.notify.warning('Cannot route message to channel: %d, sender %d is not a participant!' % (
                channel, sender))

            return

        participant = self._interface.get_participant(channel)

        if not participant:
            return

        datagram = io.NetworkDatagram()
        datagram.add_header(channel, sender, di.get_uint16())
        datagram.append_data(di.get_remaining_bytes())
        participant.handle_send_datagram(datagram)
