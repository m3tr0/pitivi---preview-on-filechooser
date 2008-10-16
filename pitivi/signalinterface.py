# PiTiVi , Non-linear video editor
#
#       signalinterface.py
#
# Copyright (c) 2008, Edward Hervey <bilboed@bilboed.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

# FIXME/IDEA : Add a decorator to easily add signals (ex: @signal(name="mysignal"))
# FIXME/IDEA : Add a function to quickly define signals (a-la pygobject gsignals)
# FIXME/IDEA : Use Weak dictionnaries for tracking connected callbacks/objects
# FIXME/IDEA : Make specific exceptions !
# FIXME : How to handle classes which are already using gobject (i.e. gst.Pipeline)

"""
Interfaces for event-based programming
"""

from random import randint

class Signallable:
    """
    Signallable interface
    """

    class SignalGroup:
        # internal
        def __init__(self, signallable):
            self.siglist = signallable.get_signals()
            # self.ids is a dictionnary of
            # key: signal name (string)
            # value: list of:
            #    (callback (callable),
            #     args (list),
            #     kwargs (dictionnary))
            self.ids = {}
            # self.handlers is a dictionnary of callback ids per
            # signals.
            self.handlers = {}
            for signame in self.siglist.keys():
                self.handlers[signame] = []

        def connect(self, signame, cb, args, kwargs):
            """ connect """
            # get a unique id
            if not signame in self.handlers.keys():
                raise Exception("Signal %s does not exist" % signame)
            if not callable(cb):
                raise Exception("Provided callable '%r' is not callable" % cb)

            uuid = randint(0, 2**64)
            while uuid in self.ids:
                uuid = randint(0, 2**64)

            self.ids[uuid] = (cb, args, kwargs)
            self.handlers[signame].append(uuid)
            return uuid

        def disconnect(self, sigid):
            """ disconnect """
            if not sigid in self.ids:
                raise Exception("unknown signal id")
            del self.ids[sigid]
            for lists in self.handlers.itervalues():
                if sigid in lists:
                    lists.remove(sigid)

        def emit(self, signame, *args, **kwargs):
            """ emit """
            # emits the signal,
            # will concatenate the given args/kwargs with
            # the ones supplied in .connect()
            res = None
            for sigid in self.handlers[signame]:
                # cb: callable
                cb, orar, kwar = self.ids[sigid]
                ar = args[:] + orar
                kw = kwargs.copy()
                kw.update(kwar)
                res = cb(*ar, **kw)
            return res


    # key : name (string)
    # value : signature (list of any strings)
    __signals__ = { }

    def emit(self, signame, *args, **kwargs):
        """
        Emit the given signal.

        The provided kwargs should contain *at-least* the arguments declared
        in the signal declaration.

        The object emitting the signal will be provided as the first
        argument of the callback

        Returns the first non-None return value given by the callbacks if they
        provide any non-None return value.
        """
        if not hasattr(self, "_signal_group"):
            # if there's no SignalGroup, that means nothing is
            # connected
            return None
        return self._signal_group.emit(signame, self,
                                       *args, **kwargs)

    def connect(self, signame, cb, *args, **kwargs):
        """
        Connect a callback (with optional arguments) to the given
        signal.

        * signame : the name of the signal
        * cb : the callback (needs to be a callable)
        * args/kwargs : (optional) arguments
        """
        if not hasattr(self, "_signal_group"):
            self._signal_group = self.SignalGroup(self)

        return self._signal_group.connect(signame,
                                           cb, args, kwargs)

    def disconnect(self, sigid):
        """
        Disconnect signal using give signal id
        """
        if not hasattr(self, "_signal_group"):
            raise Exception("This class doesn't have any signals !")

        self._signal_group.disconnect(sigid)


    @classmethod
    def get_signals(cls):
        """ Get the full list of signals implemented by this class """
        sigs = {}
        for cla in cls.mro():
            if "__signals__" in cla.__dict__:
                sigs.update(cla.__signals__)
            if cla == Signallable:
                break
        return sigs