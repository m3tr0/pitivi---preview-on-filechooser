# PiTiVi , Non-linear video editor
#
#       pitivi/check.py
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

import gtk
import gst
import sys
import instance

def initial_checks():
    """
    do some basic check
    If there is a problem, will display the error and exit.
    """
    res = _checks()
    if not res:
        return
    message, detail = res
    # TODO check if we're running graphically
    dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR,
                               buttons=gtk.BUTTONS_OK)
    dialog.set_markup("<b>"+message+"</b>")
    dialog.format_secondary_text(detail)
    dialog.run()

    sys.exit()
    
def _checks():
    reg = gst.registry_get_default()
    if instance.PiTiVi:
        return ("PiTiVi is already running",
                "An instance of PiTiVi is already running in this script")
    if not reg.find_plugin("gnonlin"):
        return ("Could not find the GNonLin plugins!",
                "Make sure the plugins were installed and are available in the GStreamer plugins path")
    if not reg.find_plugin("autodetect"):
        return ("Could not find the autodetect plugins!",
                "Make sure you have installed gst-plugins-good and is available in the GStreamer plugin path")
    return None