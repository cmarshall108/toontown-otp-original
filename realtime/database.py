"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import os
import ujson

from panda3d.core import NetDatagram, UniqueIdAllocator
from panda3d.direct import DCPacker
from realtime import io, types
from direct.directnotify.DirectNotifyGlobal import directNotify

class JsonFile(object):
    notify = directNotify.newCategory('JsonFile')

    def __init__(self, filepath, mode='r+'):
        self._filepath = filepath
        self._mode = mode
        self._io = open(self._filepath, self._mode)
        self._data = {}

    @property
    def filepath(self):
        return self._filepath

    @property
    def mode(self):
        return self._mode

    @property
    def io(self):
        return self._io

    @property
    def data(self):
        return self._data

    def setup(self):
        self.__load()

    def __getitem__(self, key):
        return self._data.get(key)

    def __setitem__(self, key, value):
        self._data[key] = value
        self.__save()

    def setdefault(self, key, value):
        result = self._data.get(key)

        if not result:
            result = self._data.setdefault(key, value)
            self.__save()

        return result

    def __save(self):
        self._io.write(str(ujson.dumps(self._data, indent=2)))
        self.__load()

    def __load(self):
        try:
            self._data = ujson.load(self._io)
        except:
            self.notify.debug('Failed to load json data from file: %s!' % (
                self._filepath))

class JsonFileManager(object):
    notify = directNotify.newCategory('JsonFileManager')

    def __init__(self, backend):
        self.backend = backend

        self._files = []

    @property
    def files(self):
        return self._files

    def add_file(self, file):
        if file in self._files:
            return

        self._files.append(file)

    def remove_file(self, file):
        if file not in self._files:
            return

        self._files.remove(file)

    def setup(self, filepath):
        file = JsonFile(filepath, 'w+' if not os.path.exists(
            filepath) else 'r+')

        file.setup()
        self.add_file(file)
        return file

class DatabaseBackend(object):
    notify = directNotify.newCategory('DatabaseBackend')

    def __init__(self):
        self._min_id = 0
        self._max_id = 0
        self._allocator = None

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

    def setup(self):
        self._allocator = UniqueIdAllocator(self._min_id, self._max_id)

class JsonDatabase(DatabaseBackend):
    notify = directNotify.newCategory('JsonDatabase')

    def __init__(self):
        DatabaseBackend.__init__(self)

        self._min_id = config.GetInt('database-min-channels', 100000000)
        self._max_id = config.GetInt('database-max-channels', 399999999)

        self.directory = config.GetString('database-directory', 'databases/json')
        self.extension = config.GetString('database-extension', '.json')

        self.tracker_filename = config.GetString('database-tracker', 'next')

        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

        self.file_manager = JsonFileManager(self)

        self.tracker = self.file_manager.setup(self.get_filename(
            self.tracker_filename))

        self._min_id = self.tracker.setdefault('next', self._min_id)

    def get_filename(self, filename):
        return '%s%s' % (os.path.join(self.directory, str(filename)), self.extension)

class DatabaseServer(io.NetworkConnector):
    notify = directNotify.newCategory('DatabaseServer')

    def __init__(self, dc_loader, address, port, channel):
        io.NetworkConnector.__init__(self, dc_loader, address, port, channel)

        self._backend = JsonDatabase()

    @property
    def backend(self):
        return self._backend

    def setup(self):
        io.NetworkConnector.setup(self)

        self._backend.setup()

    def handle_datagram(self, channel, sender, message_type, di):
        pass
