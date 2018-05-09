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
from direct.task.TaskManagerGlobal import taskMgr

__builtin__.config = get_config_showbase()
__builtin__.taskMgr = taskMgr

from realtime import clientagent, messagedirector, stateserver, database

def main():
    message_director = messagedirector.MessageDirector('0.0.0.0', 7100)
    message_director.setup()

    client_agent = clientagent.ClientAgent('0.0.0.0', 6667, '127.0.0.1', 7100, 1000)
    client_agent.setup()

    state_server = stateserver.StateServer('127.0.0.1', 7100, 1001)
    state_server.setup()

    database_server = database.DatabaseServer('127.0.0.1', 7100, 1002)
    database_server.setup()

if __name__ == '__main__':
    main()
    taskMgr.run()
