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
'''Base mechanics for content type providers and a default provider for the
JSON (`application/json`) content type.
'''
from __future__ import absolute_import, division, print_function, with_statement

from collections import defaultdict
import json

from supercell._compat import with_metaclass, ifilter
from supercell.api import ContentType
from supercell.utils import parse_accept_header


__all__ = ['NoProviderFound', 'ProviderBase', 'JsonProvider']


class NoProviderFound(Exception):
    '''Raised if no matching provider for the client's `Accept` header was
    found.'''
    pass


class ProviderMeta(type):
    '''Meta class for all content type providers.

    This will simply register a provider with the respective content type
    information and make them available in a list of content types and their
    mappers.
    '''

    KNOWN_CONTENT_TYPES = defaultdict(list)

    def __new__(cls, name, bases, dct):
        provider_class = type.__new__(cls, name, bases, dct)

        ct = provider_class.CONTENT_TYPE
        if ct:
            ProviderMeta.KNOWN_CONTENT_TYPES[ct.content_type].append(
                    (ct, provider_class))
            if name == 'ProviderBase':
                provider_class.map_provider = ProviderMeta.map_provider

        return provider_class

    @staticmethod
    def map_provider(accept_header, handler):
        '''Map a given content type to the correct provider implementation.

        If no provider matches, raise a `NoProviderFound` exception.

        .. note::

            TODO this algorithm can certainly be simplified via sorting and
            searching...

        :param accept_header: HTTP Accept header value
        :type accept_header: str
        :param handler: supercell request handler
        '''
        accept = parse_accept_header(accept_header)
        if len(accept_header) == 0:
            raise NoProviderFound()

        for (ctype, params, q) in accept:
            if ctype not in handler._PROD_CONTENT_TYPES:
                raise NoProviderFound()

            c = ContentType(ctype, vendor=params.get('vendor', None),
                            version=params.get('version', None))
            if c not in handler._PROD_CONTENT_TYPES[ctype]:
                raise NoProviderFound()

            known_types = [t for t in ProviderMeta.KNOWN_CONTENT_TYPES[ctype]
                           if t[0] == c]

            if len(known_types) == 1:
                return known_types[0][1]

        raise NoProviderFound()


class ProviderBase(with_metaclass(ProviderMeta, object)):
    '''Base class for content type providers.'''

    CONTENT_TYPE = None
    '''The target content type for the provider.'''

    def provide(self, model):
        '''This method should return the correct representation as a simple
        string (i.e. byte buffer) that will be used as return value.

        :param model: the model to convert to a certain content type
        :type model: supercell.schematics.Model
        '''
        raise NotImplemented()


class JsonProvider(ProviderBase):
    '''Default `application/json` provider.'''

    CONTENT_TYPE = ContentType('application/json', None, None)

    def provide(self, model):
        '''Simply return the json via `json.dumps`.

        .. seealso:: :py:mod:`supercell.api.provider.ProviderBase.provide`
        '''
        return json.dumps(model.serialize())
