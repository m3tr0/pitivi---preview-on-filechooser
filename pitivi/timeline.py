# PiTiVi , Non-linear video editor
#
#       pitivi/timeline.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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

import gobject
import gst

MEDIA_TYPE_NONE = 0
MEDIA_TYPE_AUDIO = 1
MEDIA_TYPE_VIDEO = 2

## * Object Hierarchy

##   Object
##    |
##    +---- Source
##    |	   |
##    |	   +---- FileSource
##    |	   |
##    |	   +---- LiveSource
##    |	   |
##    |	   +---- Composition
##    |		   |
##    |		   +---- Group
##    |
##    +---- Effect
## 	   |
## 	   +---- Simple Effect (1->1)
## 	   |
## 	   +---- Transition
## 	   |
## 	   +---- Complex Effect (N->1)

class Timeline(gobject.GObject):
    """
    Fully fledged timeline
    """

    # TODO make the compositions more versatile
    # for the time being we hardcode an audio and a video composition
    
    def __init__(self, project):
        gobject.GObject.__init__(self)
        self.project = project
        self.timeline = gst.element_factory_make("gnltimeline", "timeline-" + project.name)
        self._fill_contents()
        self.project.settings.connect_after("settings-changed", self._settings_changed_cb)

    def _fill_contents(self):
        # TODO create the initial timeline according to the project settings
        self.audiocomp = TimelineComposition(media_type = MEDIA_TYPE_AUDIO, name="audiocomp")
        self.videocomp = TimelineComposition(media_type = MEDIA_TYPE_VIDEO, name="videocomp")
        self.videocomp.link_object(self.audiocomp)
        self.timeline.add_many(self.audiocomp.gnlobject,
                               self.videocomp.gnlobject)

    def _settings_changed_cb(self, settings):
        # reset the timeline !
        pstate = self.timeline.get_state()
        self.timeline.set_state(gst.STATE_READY)
        self.timeline.set_state(pstate)

gobject.type_register(Timeline)

class TimelineObject(gobject.GObject):
    """
    Base class for all timeline objects

    * Properties
      _ Start/Stop Time
      _ Media Type
      _ Gnonlin Object
      _ Linked Object
	_ Can be None
	_ Must have same duration
      _ Brother object
        _ This is the same object but with the other media_type

    * signals
      _ 'start-stop-changed' : start position, stop position
      _ 'linked-changed' : new linked object
    """

    __gsignals__ = {
        "start-stop-changed" : ( gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE,
                                 (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, )),
        "linked-changed" : ( gobject.SIGNAL_RUN_LAST,
                             gobject.TYPE_NONE,
                             (gobject.TYPE_PYOBJECT, ))
        }
    
##     start = -1  # start time
##     stop = -1   # stop time
##     linked = None       # linked object
##     brother = None      # brother object, the other-media equivalent of this object
##     factory = None      # the Factory with more details about this object
##     gnlobject = None    # The corresponding GnlObject
##     media_type = MEDIA_TYPE_NONE        # The Media Type of this object

    def __init__(self, factory=None, start=-1, stop=-1,
                 media_type=MEDIA_TYPE_NONE, name=""):
        gobject.GObject.__init__(self)
        self.start = -1
        self.stop = -1
        self.linked = None
        self.brother = None
        self.name = name
        # Set factory and media_type and then create the gnlobject
        self.factory = factory
        self.media_type = media_type
        self._make_gnl_object()
        self.gnlobject.connect("notify::start", self._start_stop_changed_cb)
        self.gnlobject.connect("notify::stop", self._start_stop_changed_cb)
        self._set_start_stop_time(start, stop)

    def _make_gnl_object(self):
        """ create the gnl_object """
        pass

    def _unlink_object(self):
        # really unlink the objects
        if self.linked:
            self.linked = None
            self.emit("linked-changed", None)

    def _link_object(self, object):
        # really do the link
        self.linked = object
        self.emit("linked-changed", self.linked)

    def link_object(self, object):
        """
        link another object to this one.
        If there already is a linked object ,it will unlink it
        """
        if self.linked and not self.linked == object:
            self.unlink_object()
        self._link_object(object)
        pass

    def unlink_object(self):
        """
        unlink from the current linked object
        """
        self.linked._unlink_object()
        self._unlink_object()

    def relink_brother(self):
        """
        links the object back to it's brother
        """
        # if already linked, unlink from previous
        if self.linked:
            self.unlink_object()

        # link to brother
        if self.brother:
            self.link_object(self.brother)

    def get_brother(self, autolink=True):
        """
        returns the brother element if it's possible,
        if autolink, then automatically link it to this element
        """
        if not self.brother:
            self.brother = self._make_brother()
            if not self.brother:
                return None
        if autolink and not self.linked == self.brother:
            self.relink_brother()
        return self.brother

    def _make_brother(self):
        """
        Make the exact same object for the other media_type
        implemented in subclasses
        """
        return None
    
    def _set_start_stop_time(self, start=-1, stop=-1):
        # really modify the start/stop time
        print self.gnlobject, "set_start_stop_time", start, stop
        if not stop == -1 and not self.stop == stop:
            self.stop = stop
            self.gnlobject.set_property("stop", long(stop))
        if not start == -1 and not self.start == start:
            self.start = start
            self.gnlobject.set_property("start", long(start))
            
    def set_start_stop_time(self, start=-1, stop=-1):
        """ sets the start and/or stop time """
        self._set_start_stop_time(start, stop)
        if self.linked:
            self.linked._set_start_stop_time(start, stop)

    def _start_stop_changed_cb(self, gnlobject, property):
        """ start/stop time has changed """
        start = -1
        stop = -1
        if property.name == "start":
            start = gnlobject.get_property("start")
            if start == self.start:
                start = -1
            else:
                self.start = long(start)
        elif property.name == "stop":
            stop = gnlobject.get_property("stop")
            if stop == self.stop:
                stop = -1
            else:
                self.stop = long(stop)
        #if not start == -1 or not stop == -1:
        self.emit("start-stop-changed", self.start, self.stop)
            

gobject.type_register(TimelineObject)
        
class TimelineSource(TimelineObject):
    """
    Base class for all sources (O input)
    """

    def __init__(self, **kw):
        TimelineObject.__init__(self, **kw)

    def _make_gnl_object(self):
        if self.media_type == MEDIA_TYPE_AUDIO:
            mybin = self.factory.make_audio_bin()
            self.name = mybin.get_name()
        elif self.media_type == MEDIA_TYPE_VIDEO:
            mybin = self.factory.make_video_bin()
            self.name = mybin.get_name()
        else:
            raise NameError, "media type is NONE !"
        self.gnlobject = gst.element_factory_make("gnlsource", "source-" + self.name)
        self.gnlobject.set_property("element", mybin)
        self.gnlobject.set_property("start", long(0))
        self.gnlobject.set_property("stop", long(self.factory.length))
        
gobject.type_register(TimelineSource)

class TimelineFileSource(TimelineSource):
    """
    Seekable sources (mostly files)
    """
    __gsignals__ = {
        "media-start-stop-changed" : ( gobject.SIGNAL_RUN_LAST,
                                       gobject.TYPE_NONE,
                                       (gobject.TYPE_UINT64, gobject.TYPE_UINT64))
        }

    media_start = -1
    media_stop = -1
    
    def __init__(self, media_start=-1, media_stop=-1, **kw):
        TimelineSource.__init__(self, **kw)
        self.gnlobject.connect("notify::media-start", self._media_start_stop_changed_cb)
        self.gnlobject.connect("notify::media-stop", self._media_start_stop_changed_cb)
        if media_start == -1:
            media_start = 0
        if media_stop == -1:
            media_stop = self.factory.length
        self.set_media_start_stop_time(media_start, media_stop)
        
    def _make_brother(self):
        """ make the brother element """
        print self.gnlobject, "making filesource brother"
        # find out if the factory provides the other element type
        if self.media_type == MEDIA_TYPE_NONE:
            return None
        if self.media_type == MEDIA_TYPE_VIDEO:
            if not self.factory.is_audio:
                return None
            brother = TimelineFileSource(media_start=self.media_start, media_stop=self.media_stop,
                                         factory=self.factory, start=self.start, stop=self.stop,
                                         media_type=MEDIA_TYPE_AUDIO, name=self.name)
        elif self.media_type == MEDIA_TYPE_AUDIO:
            if not self.factory.is_video:
                return None
            brother = TimelineFileSource(media_start=self.media_start, media_stop=self.media_stop,
                                         factory=self.factory, start=self.start, stop=self.stop,
                                         media_type=MEDIA_TYPE_VIDEO, name=self.name)
        else:
            brother = None
        return brother

    def _set_media_start_stop_time(self, start=-1, stop=-1):
        if not stop == -1 and not self.media_stop == stop:
            self.media_stop = stop
            self.gnlobject.set_property("media_stop", long(stop))
        if not start == -1 and not self.media_start == start:
            self.media_start = start
            self.gnlobject.set_property("media_start", long(start))

    def set_media_start_stop_time(self, start=-1, stop=-1):
        """ sets the media start/stop time """
        self._set_media_start_stop_time(start, stop)
        if self.linked and isinstance(self.linked, TimelineFileSource):
            self.linked._set_media_start_stop_time(start, stop)

    def _media_start_stop_changed_cb(self, gnlobject, property):
        mstart = None
        mstop = None
        if property.name == "media-start":
            mstart = gnlobject.get_property("media-start")
            if mstart == self.media_start:
                mstart = None
            else:
                self.media_start = mstart
        elif property.name == "media-stop":
            mstop = gnlobject.get_property("media-stop")
            if mstop == self.media_stop:
                mstop = None
            else:
                self.media_stop = mstop
        if mstart or mstop:
            self.emit("media-start-stop-changed",
                      self.media_start, self.media_stop)

gobject.type_register(TimelineFileSource)

class TimelineLiveSource(TimelineSource):
    """
    Non-seekable sources (like cameras)
    """

    def __init__(self, **kw):
        TimelineSource.__init__(self, **kw)

gobject.type_register(TimelineLiveSource)

class TimelineComposition(TimelineSource):
    """
    Combines sources and effects
    _ Sets the priority of the GnlObject(s) contained within
    _ Effects have always got priorities higher than the sources
    _ Can contain global effects that have the highest priority
      _ Those global effect spread the whole duration of the composition
    _ Simple effects can overlap each other
    _ Complex Effect(s) have a lower priority than Simple Effect(s)
      _ For sanity reasons, Complex Effect(s) can't overlap each other
    _ Transitions have the lowest effect priority
    _ Source(s) contained in it follow each other if possible
    _ Source can overlap each other
      _ Knows the "visibility" of the sources contained within

    _ Provides a "condensed list" of the objects contained within
      _ Allows to quickly show a top-level view of the composition
    
    * Sandwich view example (top: high priority):
	     [ Global Simple Effect(s) (RGB, YUV, Speed,...)	]
	     [ Simple Effect(s), can be several layers		]
	     [ Complex Effect(s), non-overlapping		]
	     [ Transition(s), non-overlapping			]
	     [ Layers of sources				]

    * Properties:
      _ Global Simple Effect(s) (Optionnal)
      _ Simple Effect(s)
      _ Complex Effect(s)
      _ Transition(s)
      _ Condensed list

    * Signals:
      _ 'condensed-list-changed' : condensed list
    
    """

    __gsignals__ = {
        'condensed-list-changed' : ( gobject.SIGNAL_RUN_LAST,
                                     gobject.TYPE_NONE,
                                     (gobject.TYPE_PYOBJECT, ))
        }

    global_effects = [] # list of effects starting from highest priority
    simple_effects = [[]] # list of layers of simple effects (order: priority, then time)
    complex_effects = [] # complex effect sorted by time
    transitions = [] # transitions sorted by time
    # list of layers of simple effects (order: priority, then time)
    # each layer contains (min priority, max priority, list objects)
    #sources = [(2048, 2060, [])] 
    condensed = [] # list of sources/transitions seen from a top-level view

    def __init__(self, **kw):
        self.sources = [(2048, 2060, [])]
        TimelineSource.__init__(self, **kw)

    def _make_gnl_object(self):
        self.gnlobject = gst.element_factory_make("gnlcomposition", "composition-" + self.name)
        # connect to start/stop notify time

    # global effects
    
    def add_global_effect(self, global_effect, order, auto_linked=True):
        """
        add a global effect
        order :
           n : put at the given position (0: first)
           -1 : put at the end (lowest priority)
        auto_linked : if True will add the brother (if any) of the given effect
                to the linked composition with the same order
        """
        pass

    def remove_global_effect(self, global_effect, remove_linked=True):
        """
        remove a global effect
        If remove_linked is True and the effect has a linked effect, will remove
        it from the linked composition
        """
        pass

    # simple effects
    
    def add_simple_effect(self, simple_effect, order, auto_linked=True):
        """
        add a simple effect

        order works if there's overlapping:
           n : put at the given position (0: first)
           -1 : put underneath all other simple effects
        auto_linked : if True will add the brother (if any) of the given effect
                to the linked composition with the same order
        """
        pass

    def remove_simple_effect(self, simple_effect, remove_linked=True):
        """
        removes a simple effect
        If remove_linked is True and the effect has a linked effect, will remove
        it from the linked composition
        """
        pass

    # complex effect

    def add_complex_effect(self, complex_effect, auto_linked=True):
        """
        adds a complex effect
        auto_linked : if True will add the brother (if any) of the given effect
                to the linked composition with the same order
        """
        # if it overlaps with existing complex effect, raise exception
        pass

    def remove_complex_effect(self, complex_effect, remove_linked=True):
        """
        removes a complex effect
        If remove_linked is True and the effect has a linked effect, will remove
        it from the linked composition
        """
        pass

    def _make_condensed_list(self):
        """ makes a condensed list """
        def condensed_sum(list1, list2):
            """ returns a condensed list of the two given lists """
            print self.gnlobject, "condensed_sum"
            print self.gnlobject, "comparing", list1, "with", list2
            if not list1:
                return list2[:]
            if not list2:
                return list1[:]
            
            res = list1[:]

            # find the objects in list2 that go under list1 and insert them at
            # the good position in res
            for obj in list2:
                # go through res to see if it can go somewhere
                for pos in range(len(res)):
                    if obj.start <= res[pos].start:
                        res.insert(pos, obj)
                        break
                if pos == len(res) and obj.start > res[-1].start:
                    res.append(obj)
            print self.gnlobject, "returning", res
            return res
                
            
        lists = [x[2] for x in self.sources]
        lists.insert(0, self.transitions)
        return reduce(condensed_sum, lists)

    def _update_condensed_list(self):
        """ updates the condensed list """
        print self.gnlobject, "_update_condensed_list"
        # build a condensed list
        clist = self._make_condensed_list()
        if self.condensed:
            # compare it to the self.condensed
            list_changed = False
            print "comparing:"
            for i in self.condensed:
                print i.gnlobject, i.start, i.stop
            print "with"
            for i in clist:
                print i.gnlobject, i.start, i.stop
            if not len(clist) == len(self.condensed):
                list_changed = True
            else:
                for a, b in zip(clist, self.condensed):
                    if not a == b:
                        list_changed = True
                        break
        else:
            list_changed = True
        # if it's different or new, set it to self.condensed and emit the signal
        if list_changed:
            self.condensed = clist
            self.emit("condensed-list-changed", self.condensed)

    # Transitions

    def add_transition(self, transition, source1, source2, auto_linked=True):
        """
        adds a transition between source1 and source2
        auto_linked : if True will add the brother (if any) of the given transition
                to the linked composition with the same parameters
        """
        # if it overlaps with existing transition, raise exception
        pass

    def move_transition(self, transition, source1, source2):
        """ move a transition between source1 and source2 """
        # if it overlays with existing transition, raise exception
        pass

    def remove_transition(self, transition, reorder_sources=True, remove_linked=True):
        """
        removes a transition,
        If reorder sources is True it puts the sources
        between which the transition was back one after the other
        If remove_linked is True and the transition has a linked effect, will remove
        it from the linked composition
        """
        pass

    # Sources

    def _get_source_position(self, source):
        position = 0
        foundit = False
        for slist in self.sources:
            if source in slist[2]:
                foundit = True
                break
            position = position + 1
        if foundit:
            return position + 1
        return 0

    def _have_got_this_source(self, source):
        for slist in self.sources:
            if source in slist[2]:
                return True
        return False

    def add_source(self, source, position, auto_linked=True):
        """
        add a source (with correct start/stop time already set)
        position : the vertical position
          _ 0 : insert above all other layers
          _ n : insert at the given position (1: top row)
          _ -1 : insert at the bottom, under all sources
        auto_linked : if True will add the brother (if any) of the given source
                to the linked composition with the same parameters
        """
        print self.gnlobject, "add_source", self.sources
        def my_add_sorted(sources, object):
            slist = sources[2]
            i = 0
            for item in slist:
                if item.start > object.start:
                    break
                i = i + 1
            object.gnlobject.set_property("priority", sources[0])
            slist.insert(i, object)
        # TODO : add functionnality to add above/under
        # For the time being it's hardcoded to a single layer
        position = 1

        # add it to the correct self.sources[position]
        my_add_sorted(self.sources[position-1], source)
        
        # add it to self.gnlobject
        print "adding", source.gnlobject, "to composition", self.gnlobject
        self.gnlobject.add(source.gnlobject)

        # update the condensed list
        self._update_condensed_list()

        # if auto_linked and self.linked, add brother to self.linked with same parameters
        if auto_linked and self.linked:
            if source.get_brother():
                self.linked.add_source(source.brother, position, auto_linked=False)
        print self.gnlobject, "added source", source.gnlobject
        print self.sources

    def insert_source_after(self, source, existingsource, push_following=True, auto_linked=True):
        """
        inserts a source after the existingsource, pushing the following ones
        if existingsource is None, it puts the source at the beginning
        """
        if existingsource:
            print self.gnlobject, "insert_source", source.gnlobject, "after", existingsource.gnlobject
        else:
            print self.gnlobject, "insert_source", source.gnlobject, "at the beginning"
            
        # find the time where it's going to be added
        if not existingsource or not self._have_got_this_source(existingsource):
            start = 0
            position = 1
            existorder = 0
        else:
            start = existingsource.stop
            position = self._get_source_position(existingsource)
            existorder = self.sources[position - 1][2].index(existingsource) + 1

        print "start=%d, position=%d, existorder=%d, sourcelength=%d" % (start, position, existorder, source.factory.length)
        for i in self.sources[position -1][2]:
            print i.gnlobject, i.start, i.stop
        # set the correct start/stop time
        stop = start + source.factory.length
        source.set_start_stop_time(start, stop)
        
        # pushing following
        if push_following and not position in [-1, 0]:
            print self.gnlobject, "pushing following", existorder, len(self.sources[position - 1][2])
            for i in range(existorder, len(self.sources[position - 1][2])):
                mvsrc = self.sources[position - 1][2][i]
                print "run", i, "start", mvsrc.start, "stop", mvsrc.stop
                # increment self.sources[position - 1][i] by source.factory.length
                mvsrc.set_start_stop_time(mvsrc.start + source.factory.length,
                                          mvsrc.stop + source.factory.length)
        
        self.add_source(source, position, auto_linked=auto_linked)

    def append_source(self, source, position=1, auto_linked=True):
        """
        puts a source after all the others
        """
        print self.gnlobject, "append_source", source.gnlobject
        # find the source with the highest stop time on the first layer
        if self.sources[position - 1]:
            existingsource = self.sources[position - 1][2][-1]
        else:
            existingsource = None

        self.insert_source_after(source, existingsource, push_following=False,
                                 auto_linked=auto_linked)

    def prepend_source(self, source, push_following=True, auto_linked=True):
        """
        adds a source to the beginning of the sources
        """
        print self.gnlobject, "prepend_source", source.gnlobject
        self.insert_source_after(source, None, push_following, auto_linked)

    def move_source(self, source, newpos):
        """
        moves the source to the new position
        """
        self._update_condensed_list()
        pass

    def remove_source(self, source, remove_linked=True, collapse_neighbours=False):
        """
        removes a source
        If remove_linked is True and the source has a linked source, will remove
        it from the linked composition
        """
        self._update_condensed_list()
        # if self.linked and remove_linked, self.linked.remove_source()
        pass

gobject.type_register(TimelineComposition)

class TimelineEffect(TimelineObject):
    """
    Base class for effects (1->n input(s))
    """

    def __init__(self, nbinputs=1, **kw):
        self.nbinputs = nbinputs
        TimelineObject.__init__(self, **kw)

    def _make_gnl_obejct(self):
        self.gnlobject = gst.element_factory_make("gnloperation", "operation-" + self.name)
        self._set_up_gnl_operation()

    def _set_up_gnl_operation(self):
        """ fill up the gnloperation for the first go """

gobject.type_register(TimelineEffect)

class TimelineSimpleEffect(TimelineEffect):
    """
    Simple effects (1 input)
    """

    def __init__(self, factory, **kw):
        self.factory = factory
        TimelineEffect.__init__(self, **kw)

    def _set_up_gnl_operation(self):
        # fill up the gnloperation for the first go
        pass

gobject.type_register(TimelineSimpleEffect)

class TimelineTransition(TimelineEffect):
    """
    Transition Effect
    """
    source1 = None
    source2 = None

    def __init__(self, factory, source1=None, source2=None, **kw):
        self.factory = factory
        TimelineEffect.__init__(self, nbinputs=2, **kw)
        self.source1 = source1
        self.source2 = source2

    def set_sources(self, source1, source2):
        """ changes the sources in between which the transition lies """
        self.source1 = source1
        self.source2 = source2

    def _set_up_gnl_operation(self):
        # fill up the gnloperation for the first go
        pass

gobject.type_register(TimelineTransition)

class TimelineComplexEffect(TimelineEffect):
    """
    Complex Effect
    """

    def __init__(self, factory, **kw):
        self.factory = factory
        # Find out the number of inputs
        nbinputs = 2
        TimelineEffect.__init__(self, nbinputs=nbinputs, **kw)

    def _set_up_gnl_operation(self):
        # fill up the gnloperation for the first go
        pass

gobject.type_register(TimelineComplexEffect)