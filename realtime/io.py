"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

from panda3d.core import QueuedConnectionManager, QueuedConnectionListener, QueuedConnectionReader, \
    ConnectionWriter, PointerToConnection, NetAddress, NetDatagram, DatagramIterator, Filename

from panda3d.direct import DCFile
from realtime import types
from direct.directnotify.DirectNotifyGlobal import directNotify

class NetworkError(RuntimeError):
    """
    A network specific runtime error
    """

class NetworkDCLoader(object):
    notify = directNotify.newCategory('NetworkDCLoader')

    def __init__(self):
        self._dc_file = DCFile()
        self._dc_file.clear()
        self._dc_suffix = ""

        self._dclasses_by_name = {}
        self._dclasses_by_number = {}

        self._hash_value = 0

    @property
    def dc_file(self):
        return self._dc_file

    @property
    def dc_suffix(self):
        return self._dc_suffix

    @property
    def dclasses_by_name(self):
        return self._dclasses_by_name

    @property
    def dclasses_by_number(self):
        return self._dclasses_by_number

    @property
    def hash_value(self):
        return self._hash_value

    def read_dc_files(self, dc_file_names=None):
        dc_imports = {}
        if dc_file_names == None:
            read_result = self._dc_file.read_all()
            if not read_result:
                self.notify.error("Could not read dc file.")
        else:
            for dc_fileName in dc_file_names:
                pathname = Filename(dc_fileName)
                read_result = self._dc_file.read(pathname)
                if not read_result:
                    self.notify.error("Could not read dc file: %s" % (
                        pathname))

        self._hash_value = self._dc_file.get_hash()

        # Now get the class definition for the classes named in the DC
        # file.
        for i in range(self._dc_file.get_num_classes()):
            dclass = self._dc_file.get_class(i)
            number = dclass.get_number()
            class_name = dclass.get_name() + self._dc_suffix

            # Does the class have a definition defined in the newly
            # imported namespace?
            class_def = dc_imports.get(class_name)

            # Also try it without the dc_suffix.
            if class_def == None:
                class_name = dclass.get_name()
                class_def = dc_imports.get(class_name)

            if class_def == None:
                self.notify.debug("No class definition for %s." % (
                    class_name))
            else:
                if inspect.ismodule(class_def):
                    if not hasattr(class_def, class_name):
                        self.notify.error("Module %s does not define class %s." % (
                            class_name, class_name))

                    class_def = getattr(class_def, class_name)

                if not inspect.isclass(class_def):
                    self.notify.error("Symbol %s is not a class name." % (
                        class_name))
                else:
                    dclass.set_class_def(class_def)

            self._dclasses_by_name[class_name] = dclass
            if number >= 0:
                self._dclasses_by_number[number] = dclass

class NetworkManager(object):
    notify = directNotify.newCategory('NetworkManager')

    def get_unique_name(self, name):
        return '%s-%s-%d' % (self.__class__.__name__, name, id(self))

class NetworkConnector(NetworkManager):
    notify = directNotify.newCategory('NetworkConnector')

    def __init__(self, dc_loader, address, port, channel, timeout=5000):
        NetworkManager.__init__(self)

        self.dc_loader = dc_loader
        self.__address = address
        self.__port = port
        self.channel = channel
        self.__timeout = timeout

        self.__manager = QueuedConnectionManager()
        self.__reader = QueuedConnectionReader(self.__manager, 0)
        self.__writer = ConnectionWriter(self.__manager, 0)

        self.__socket = None

        self.__read_task = None
        self.__disconnect_task = None

    def setup(self):
        if not self.__socket:
            self.__socket = self.__manager.openTCPClientConnection(self.__address,
                self.__port, self.__timeout)

            if not self.__socket:
                raise NetworkError('Failed to connect TCP socket on address: <%s:%d>!' % (
                    self.__address, self.__port))

            self.__reader.add_connection(self.__socket)
            self.register_for_channel(self.channel)

        self.__read_task = taskMgr.add(self.__read_incoming, self.get_unique_name('read-incoming'))
        self.__disconnect_task = taskMgr.add(self.__listen_disconnect, self.get_unique_name('listen-disconnect'))

    def register_for_channel(self, channel):
        """
        Registers our connections channel with the MessageDirector
        """

        datagram = NetDatagram()
        datagram.add_uint8(1)
        datagram.add_uint64(types.CONTROL_MESSAGE)
        datagram.add_uint16(types.CONTROL_SET_CHANNEL)
        datagram.add_uint64(channel)

        self.handle_send_connection_datagram(datagram)

    def unregister_for_channel(self, channel):
        """
        Unregisters our connections channel from the MessageDirector
        """

        datagram = NetDatagram()
        datagram.add_uint8(1)
        datagram.add_uint64(types.CONTROL_MESSAGE)
        datagram.add_uint16(types.CONTROL_REMOVE_CHANNEL)
        datagram.add_uint64(channel)

        self.handle_send_connection_datagram(datagram)

    def __read_incoming(self, task):
        """
        Polls for incoming data
        """

        if self.__reader.data_available():
            datagram = NetDatagram()

            if self.__reader.get_data(datagram):
                self.__handle_data(datagram)

        return task.cont

    def __listen_disconnect(self, task):
        """
        Watches our connected socket object and determines if the stream has ended..
        """

        if not self.__reader.is_connection_ok(self.__socket):
            self.handle_disconnected()

        return task.cont

    def __handle_data(self, datagram):
        """
        Handles incoming data from the connector
        """

        if not datagram.get_length():
            return

        di = DatagramIterator(datagram)

        try:
            sender = di.get_uint64()
            message_type = di.get_uint16()
        except:
            return

        self.handle_datagram(sender, message_type, di)

    def handle_send_connection_datagram(self, datagram):
        """
        Sends a datagram to our connection
        """

        if not datagram.get_length():
            return

        self.__writer.send(datagram, self.__socket)

    def handle_datagram(self, sender, message_type, di):
        """
        Handles a datagram that was pulled from the queue
        """

    def handle_disconnect(self):
        """
        Disconnects our client socket instance
        """

        self.__manager.close_connection(self.__socket)

    def handle_disconnected(self):
        """
        Handles disconnection when the socket connection closes
        """

        self.unregister_for_channel(self.channel)
        self.__reader.remove_connection(self.__socket)

    def shutdown(self):
        if self.__read_task:
            taskMgr.remove(self.__read_task)

        if self.__disconnect_task:
            taskMgr.remove(self.__disconnect_task)

        self.__read_task = None
        self.__disconnect_task = None

class NetworkHandler(NetworkManager):
    notify = directNotify.newCategory('NetworkHandler')

    def __init__(self, network, rendezvous, address, connection, channel=None):
        self.network = network
        self.rendezvous = rendezvous
        self.address = address
        self.connection = connection
        self.channel = channel

        self.__data = []

        self.__update_task = None

    def setup(self):
        if not self.__update_task:
            self.__update_task = taskMgr.add(self.__update, self.get_unique_name('update-handler'))

    def register_for_channel(self, channel):
        """
        Registers our connections channel with the MessageDirector
        """

        datagram = NetDatagram()
        datagram.add_uint8(1)
        datagram.add_uint64(types.CONTROL_MESSAGE)
        datagram.add_uint16(types.CONTROL_SET_CHANNEL)
        datagram.add_uint64(channel)

        self.network.handle_send_connection_datagram(datagram)

    def unregister_for_channel(self, channel):
        """
        Unregisters our connections channel from the MessageDirector
        """

        datagram = NetDatagram()
        datagram.add_uint8(1)
        datagram.add_uint64(types.CONTROL_MESSAGE)
        datagram.add_uint16(types.CONTROL_REMOVE_CHANNEL)
        datagram.add_uint64(channel)

        self.network.handle_send_connection_datagram(datagram)

    def __update(self, task):
        """
        Pops a datagram from the queue and handles it
        """

        if not len(self.__data):
            return task.cont

        datagram = self.__data.pop()
        di = DatagramIterator(datagram)

        if not di.get_remaining_size():
            return task.cont

        self.handle_datagram(di, datagram)
        return task.cont

    def is_queued(self, datagram):
        """
        Returns true if the datagram is queued else False
        """

        return datagram in self.__data

    def queue(self, datagram):
        """
        Places a new datagram in the data queue
        """

        if self.is_queued(datagram) or not datagram.get_length():
            return

        self.__data.append(datagram)

    def dequeue(self, datagram):
        """
        Removes a datagram from the data queue
        """

        if not self.is_queued(datagram):
            return

        self.__data.remove(datagram)

    def handle_send_datagram(self, datagram):
        """
        Sends a datagram to our connection
        """

        self.network.handle_send_datagram(datagram, self.connection)

    def handle_datagram(self, di, datagram):
        """
        Handles a datagram that was pulled from the queue
        """

    def handle_disconnect(self):
        """
        Disconnects our client socket instance
        """

        self.network.handle_disconnected(self.connection)

    def handle_disconnected(self):
        """
        Handles disconnection when the socket connection closes
        """

    def shutdown(self):
        if self.__update_task:
            taskMgr.remove(self.__update_task)

class NetworkListener(NetworkManager):
    notify = directNotify.newCategory('NetworkListener')

    def __init__(self, address, port, handler, backlog=10000):
        NetworkManager.__init__(self)

        self.__address = address
        self.__port = port
        self.__handler = handler
        self.__backlog = backlog

        self.__manager = QueuedConnectionManager()
        self.__listener = QueuedConnectionListener(self.__manager, 0)
        self.__reader = QueuedConnectionReader(self.__manager, 0)
        self.__writer = ConnectionWriter(self.__manager, 0)

        self.__socket = None
        self.__handlers = {}

        self.__listen_task = None
        self.__read_task = None
        self.__disconnect_task = None

    def setup(self):
        if not self.__socket:
            self.__socket = self.__manager.openTCPServerRendezvous(self.__address,
                self.__port, self.__backlog)

            if not self.__socket:
                raise NetworkError('Failed to bind TCP socket on address: <%s:%d>!' % (
                    self.__address, self.__port))

            self.__listener.add_connection(self.__socket)

        self.__listen_task = taskMgr.add(self.__listen_incoming, self.get_unique_name('listen-incoming'))
        self.__read_task = taskMgr.add(self.__read_incoming, self.get_unique_name('read-incoming'))
        self.__disconnect_task = taskMgr.add(self.__listen_disconnect, self.get_unique_name('listen-disconnect'))

    def __listen_incoming(self, task):
        """
        Polls for incoming connections
        """

        if self.__listener.new_connection_available():
            rendezvous = PointerToConnection()
            address = NetAddress()
            connection = PointerToConnection()

            if self.__listener.get_new_connection(rendezvous, address, connection):
                self.__handle_connection(rendezvous, address, connection.p())

        return task.cont

    def __read_incoming(self, task):
        """
        Polls for incoming data
        """

        if self.__reader.data_available():
            datagram = NetDatagram()

            if self.__reader.get_data(datagram):
                self.__handle_data(datagram, datagram.get_connection())

        return task.cont

    def __listen_disconnect(self, task):
        """
        Watches all connected socket objects and determines if the stream has ended...
        """

        for handler in self.__handlers.values():
            if not self.__reader.is_connection_ok(handler.connection):
                self.handle_disconnected(handler.connection)

        return task.cont

    def __has_handler(self, connection):
        """
        Returns True if the handler is queued else False
        """

        return connection in self.__handlers

    def __add_handler(self, handler):
        """
        Adds a handler to the handlers dictionary
        """

        if self.__has_handler(handler.connection):
            return

        handler.setup()
        self.__handlers[handler.connection] = handler
        self.__reader.add_connection(handler.connection)

    def __remove_handler(self, handler):
        """
        Removes a handler from the handlers dictionary
        """

        if not self.__has_handler(handler.connection):
            return

        del self.__handlers[handler.connection]
        self.__reader.remove_connection(handler.connection)
        handler.shutdown()

    def __handle_connection(self, rendezvous, address, connection):
        """
        Handles an incoming connection from the connection listener
        """

        handler = self.__handler(self, rendezvous, address, connection)
        self.__add_handler(handler)

    def __handle_data(self, datagram, connection):
        """
        Handles new data incoming from the connection reader
        """

        if not self.__has_handler(connection):
            return

        self.__handlers[connection].queue(datagram)

    def get_handler_from_channel(self, channel):
        """
        Returns a handler instance if one is associated with that channel
        """

        for connection, handler in self.__handlers.items():
            if handler.channel == channel:
                return handler

        return None

    def handle_send_datagram(self, datagram, connection):
        """
        Sends a datagram to a specific connection
        """

        if not datagram.get_length() or not self.__has_handler(connection):
            return

        self.__writer.send(datagram, connection)

    def handle_disconnected(self, connection):
        """
        Handles disconnection of a client socket instance
        """

        handler = self.__handlers.get(connection)

        if not handler:
            return

        handler.handle_disconnected()
        self.__reader.remove_connection(connection)
        self.__remove_handler(self.__handlers[connection])

    def shutdown(self):
        if self.__listen_task:
            taskMgr.remove(self.__listen_task)

        if self.__read_task:
            taskMgr.remove(self.__read_task)

        if self.__disconnect_task:
            taskMgr.remove(self.__disconnect_task)

        self.__listen_task = None
        self.__read_task = None
        self.__disconnect_task = None

        self.__listener.remove_connection(self.__socket)
