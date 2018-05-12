"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import os
import ujson
import yaml

from panda3d.core import NetDatagram, UniqueIdAllocator
from panda3d.direct import DCPacker
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify

class DatabaseError(RuntimeError):
    """
    An database specific runtime error
    """

class DatabaseFile(object):

    def __init__(self, filename):
        self._filename = filename
        self._data = {}

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, filename):
        self._filename = filename

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    def setup(self):
        if not os.path.exists(self._filename):
            self.save()

        self.load()

    def has_value(self, key):
        return key in self._data

    def set_value(self, key, value):
        self._data[key] = value
        self.save()

    def get_value(self, key):
        return self._data.get(key)

    def set_default_value(self, key, value):
        if self.has_value(key):
            return self.get_value(key)

        self.set_value(key, value)
        return value

    def close(self):
        self.save()

        self._filename = None
        self._data = None

    def shutdown(self):
        self.close()

class DatabaseJSONFile(DatabaseFile):

    def save(self):
        io = open(self._filename, 'w')
        ujson.dump(self._data, io, indent=2)
        io.close()

    def load(self):
        io = open(self._filename, 'r')
        self._data = ujson.load(io)
        io.close()

class DatabaseYAMLFile(DatabaseFile):

    def save(self):
        io = open(self._filename, 'w')
        output = yaml.dump(self._data, Dumper=yaml.Dumper, default_flow_style=False)
        io.write(output)
        io.close()

    def load(self):
        io = open(self._filename, 'r')
        self._data = yaml.load(io, Loader=yaml.Loader)
        io.close()

class DatabaseManager(object):

    def __init__(self, file_handler):
        self._files = {}
        self._file_handler = file_handler

        self._min_id = config.GetInt('database-min-channels', 100000000)
        self._max_id = config.GetInt('database-max-channels', 399999999)

        self._directory = config.GetString('database-directory', 'databases/json')
        self._extension = config.GetString('database-extension', '.json')

        if not os.path.exists(self._directory):
            os.makedirs(self._directory)

        self._tracker = None
        self._tracker_filename = config.GetString('database-tracker', 'next')

        self._allocator = None

    @property
    def files(self):
        return self._files

    @property
    def file_handler(self):
        return self._file_handler

    @file_handler.setter
    def file_handler(self, file_handler):
        self._file_handler = file_handler

    @property
    def min_id(self):
        return self._min_id

    @min_id.setter
    def min_id(self, min_id):
        self._min_id = min_id

    @property
    def max_id(self):
        return self._max_id

    @max_id.setter
    def max_id(self, max_id):
        self._max_id = max_id

    @property
    def directory(self):
        return self._directory

    @property
    def extension(self):
        return self._extension

    @property
    def tracker(self):
        return self._tracker

    @tracker.setter
    def tracker(self, tracker):
        self._tracker = tracker

    @property
    def tracker_filename(self):
        return self._tracker_filename

    @property
    def allocator(self):
        return self._allocator

    @allocator.setter
    def allocator(self, allocator):
        self._allocator = allocator

    def setup(self):
        self._tracker = self.open_file(self.get_filename(self._tracker_filename))
        self._min_id = self._tracker.set_default_value('next', self._min_id)
        self._allocator = UniqueIdAllocator(self._min_id, self._max_id)

    def has_file(self, filename):
        return filename in self._files

    def add_file(self, file):
        if self.has_file(file.filename):
            return

        self._files[file.filename] = file
        file.setup()

    def remove_file(self, file):
        if not self.has_file(file.filename):
            return

        file.shutdown()
        del self._files[file.filename]

    def get_file(self, filename):
        return self._files.get(filename)

    def get_filename(self, filename):
        return '%s%s' % (os.path.join(self._directory, filename), self._extension)

    def open_file(self, filename):
        file = self._file_handler(filename)
        self.add_file(file)
        return file

    def close_file(self, file):
        if not isinstance(file, self._file_handler):
            raise DatabaseError('Cannot close file of invalid type: %r, expected: %r!' % (
                file, self._file_handler))

        self.remove_file(file)

    def shutdown(self):
        for file in self._files:
            self.remove_file(file)

class DatabaseJSONBackend(DatabaseManager):

    def __init__(self):
        DatabaseManager.__init__(self, DatabaseJSONFile)

class DatabaseYAMLBackend(DatabaseManager):

    def __init__(self):
        DatabaseManager.__init__(self, DatabaseYAMLFile)

class DatabaseServer(io.NetworkConnector):
    notify = directNotify.newCategory('DatabaseServer')

    def __init__(self, dc_loader, address, port, channel):
        io.NetworkConnector.__init__(self, dc_loader, address, port, channel)

        self._backend = DatabaseYAMLBackend()

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, backend):
        self._backend = backend

    def setup(self):
        self._backend.setup()

        io.NetworkConnector.setup(self)

    def handle_datagram(self, channel, sender, message_type, di):
        pass

    def shutdown(self):
        self._backend.shutdown()

        io.NetworkConnector.shutdown(self)
