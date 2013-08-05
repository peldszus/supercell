# vim: set fileencoding=utf-8 :
#
# Copyright (c) 2013 Daniel Truemper <truemped at googlemail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
'''A :class:`Service` is the main element of a `supercell` application. It will
instanciate the :class:`supercell.api.Environment` and parse the configuration
files as well as the command line. In the final step the
:class:`tornado.web.Application` is created and bound to a socket.
'''
from __future__ import absolute_import, division, print_function, with_statement

import logging
import os

import tornado.options
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.options import define

from supercell.api.environment import Environment
from supercell.api.logging import SupercellLoggingHandler


define('logfile', default='root.log', help='Filename to store the logs')


define('loglevel', default='INFO', help='Log level')


define('port', default=8080, help='Port to listen on')


define('address', default='127.0.0.1', help='Address to bind on')


define('socketfd', default=None, help='Filedescriptor used from circus')


class Service(object):
    '''Main service implementation managing the
    :class:`tornado.web.Application` and taking care of configuration.'''

    def main(self):
        '''Main method starting a **supercell** process.

        This will first instantiate the :class:`tornado.web.Application` and
        then bind it to the socket. There are two possibilities to bind to a
        socket: either by binding to a certain port and address as defined by
        the configuration (the *port* and *address* configuration settings) or
        by the *socketfd* command line parameter.

        The latter is mainly used in combination with Circus
        (http://circus.readthedocs.org/). There you would bind the socket from
        circus and start the worker processes by binding to the file
        descriptor.
        '''
        app = self.get_app()

        server = HTTPServer(app)

        if self.config.socketfd:
            import socket
            sock = socket.fromfd(int(self.config.socketfd), socket.AF_INET,
                                 socket.SOCK_STREAM)
            server.add_socket(sock)
        else:
            server.bind(self.config.port, address=self.config.address)
            server.start(1)

        self.slog.info('Starting supercell')
        IOLoop.instance().start()

    def get_app(self):
        '''Create the :class:`tornado.web.Appliaction` instance and return it.

        In this method the :func:`Service.bootstrap()` is called, then
        :func:`Service.run()` will initialize the app.'''

        # initialize the environment
        self.environment

        # bootstrap the service
        self.bootstrap()

        # perform all the configuration parsing
        self.config

        # add handlers, health checks, managed objects to the environment
        self.run()

        # do not allow any changes on the environment anymore.
        self.environment._finalize()

        return self.environment.get_application(self.config)

    @property
    def slog(self):
        '''Initialize the logging and return the logger.'''
        if not hasattr(self, '_slog'):
            self.initialize_logging()
            self._slog = logging.getLogger('supercell')
        return self._slog

    @property
    def environment(self):
        '''The default environment instance.'''
        if not hasattr(self, '_environment'):
            self._environment = Environment()
        return self._environment

    @property
    def config(self):
        '''Assemble the configration files and command line arguments in order
        to finalize the service's configuration. All configuration values
        can be overwritten by the command line.'''
        if not hasattr(self, '_config'):
            # parse config files and command line arguments
            self.parse_config_files()
            self.parse_command_line()
            from tornado.options import options
            self._config = options
        return self._config

    def parse_config_files(self):
        '''Parse the config files and return the `config` object, i.e. the
        `tornado.options.options` instance. For each entry in the
        `Environment.config_file_paths()` it will check for a general
        *config.py* and then for a file named as defined by
        `Environment.config_name`.

        So if the config file paths are set to `['/etc/myservice',
        './etc/']` the following files are parsed::

            /etc/myservice/config.cfg
            /etc/myservice/user_hostname.cfg
            ./etc/config.cfg
            ./etc/user_hostname.cfg
        '''
        filename = self.environment.config_name
        for path in self.environment.config_file_paths:
            cfg = os.path.join(path, 'config.cfg')
            if os.path.exists(cfg):
                tornado.options.parse_config_file(cfg)

            cfg = os.path.join(path, filename)
            if os.path.exists(cfg):
                tornado.options.parse_config_file(cfg)

    def parse_command_line(self):
        '''Parse the command line arguments to set different configuration
        values.'''
        tornado.options.parse_command_line()

    def initialize_logging(self):
        '''Initialize the python logging system.

        It is difficult to check whether the logging system is already
        initialized, so we are currently only checking if a
        :class:`TimedRotatingFileHandler` has already been added to the `root`
        logger. This should only be necessary when running unittests though.'''
        root = logging.getLogger()

        hdlrs = [h for h in root.handlers
                 if isinstance(h, SupercellLoggingHandler)]
        if len(hdlrs) == 0:
            root.setLevel(self.config.loglevel)
            root.addHandler(SupercellLoggingHandler(self.config.logfile))

    def bootstrap(self):
        '''Implement this method in order to manipulate the configuration
        paths, e.g..'''
        pass

    def run(self):
        '''Implement this method in order to add handlers and managed objects
        to the environment, before the app is started.'''
        pass
