"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import __builtin__
import os

from panda3d.core import loadPrcFile

if os.path.exists('config/general.prc'):
    loadPrcFile('config/general.prc')

from panda3d.direct import get_config_showbase
from direct.task.TaskManagerGlobal import taskMgr as task_mgr

__builtin__.config = get_config_showbase()
__builtin__.task_mgr = task_mgr

from realtime import io, types, clientagent, messagedirector, \
    stateserver, database

def main():
    dc_loader = io.NetworkDCLoader()
    dc_loader.read_dc_files(['config/dclass/toon.dc'])

    message_director = messagedirector.MessageDirector('0.0.0.0', 7100)
    message_director.setup()

    client_agent = clientagent.ClientAgent(dc_loader, '0.0.0.0', 6667,
        '127.0.0.1', 7100, types.CLIENTAGENT_CHANNEL)

    client_agent.setup()

    state_server = stateserver.StateServer(dc_loader, '127.0.0.1', 7100,
        types.STATESERVER_CHANNEL)

    state_server.setup()

    database_server = database.DatabaseServer(dc_loader, '127.0.0.1', 7100,
        types.DATABASE_CHANNEL)

    database_server.setup()

if __name__ == '__main__':
    main()
    task_mgr.run()
