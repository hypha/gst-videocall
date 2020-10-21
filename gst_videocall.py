
#!/usr/bin/env python

import sys, os
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gst, GObject, Gtk
import platform

def pipeline_from_list(elements):
    """
    Parse a list of element definitions, defined as dictionaries,
    into a pipeline
    """
    pipe = Gst.Pipeline()
    prv = None
    for element in elements:
        gst_el = Gst.ElementFactory.make(element['el_name'])
        if gst_el is not None:
            for i in set(element.keys()) - set(['el_name']):
                gst_el.set_property(i, element[i])
            pipe.add(gst_el)
            if prv is not None:
               prv.link(gst_el)
            prv = gst_el
        else:
            raise Exception(f"Attempt to make element {element} returned None")
    return pipe

class Sending_Pipeline:
    """ Class for the sending GStreamer pipeline """


    def __init__(self):
        # Elements is a list of dictionaries, in which the
        # name key defines the element and the rest are properties
        elements = []

        # Source is OS-dependent
        if platform.system() == "Linux":
            elements.append({
                              "el_name": "v4l2src",
                              "name": "source"
                           })
            elements.append({
                "el_name": "videoconvert",
                "name": "converter"
            })

        elif platform.system() == "Darwin":
            elements.append({
                             "el_name":"avfvideosrc",
                             "name": "source"
                             })
            elements.append({
                             "el_name": "capsfilter",
                             "name": "source-caps",
                             "caps": Gst.Caps.from_string("video/x-raw")
                             })
        elif platform.system() == "Windows":
            print("This tool does not support Windows [yet]")
            sys.exit(1)

        # Time overlay
        elements.append({
                         "el_name": "timeoverlay",
                         "name": "timeoverlay",
                         "halignment": "right",
                         "valignment": "bottom",
                         "text": "Stream time:",
                         "shaded-background": "true",
                         "font-desc":"Courier, 24"
                         })

        # Monitor branch & sink
        elements.append({
                         "el_name": "tee",
                         "name": "monitor"
                         })

        # Output sink
        elements.append({
                         "el_name": "autovideosink",
                         "name": "video-out"
                        })
        self.player = pipeline_from_list(elements)


    def set_state(self, state):
        self.player.set_state(state)

    def get_bus(self):
        return self.player.get_bus()


class GTK_Main:
    """ The main Gtk application window """
    def __init__(self):
        window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        window.set_title("GST Videocall application")
        window.set_default_size(500, 400)
        window.connect("destroy", Gtk.main_quit, "WM destroy")
        vbox = Gtk.VBox()
        window.add(vbox)
        self.movie_window = Gtk.DrawingArea()
        vbox.add(self.movie_window)
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, False, 0)
        hbox.set_border_width(10)
        hbox.pack_start(Gtk.Label(), False, False, 0)
        self.button = Gtk.Button("Start")
        self.button.connect("clicked", self.start_stop)
        hbox.pack_start(self.button, False, False, 0)
        self.button2 = Gtk.Button("Quit")
        self.button2.connect("clicked", self.exit)
        hbox.pack_start(self.button2, False, False, 0)
        self.button3 = Gtk.Button("Silence!")
        self.button3.connect("clicked", self.silence)
        hbox.pack_start(self.button3, False, False, 0)
        hbox.add(Gtk.Label())
        window.show_all()

        self.sending = Sending_Pipeline()
        bus = self.sending.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)

    def start_stop(self, w):
        if self.button.get_label() == "Start":
            self.button.set_label("Stop")
            self.sending.player.set_state(Gst.State.PLAYING)
        else:
            self.sending.player.set_state(Gst.State.NULL)
            self.button.set_label("Start")

    def silence(self, w):
        timeoverlay = self.sending.player.get_child_by_name('timeoverlay')
        timeoverlay.set_property('silent',
                not (timeoverlay.get_property('silent'))
                )

    def exit(self, widget, data=None):
        Gtk.main_quit()

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.sending.set_state(Gst.State.NULL)
            self.button.set_label("Start")
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)
            self.sending.set_state(Gst.State.NULL)
            self.button.set_label("Start")

    def on_sync_message(self, bus, message):
        struct = message.get_structure()
        if not struct:
            return
        message_name = struct.get_name()
        if message_name == "prepare-xwindow-id":
            # Assign the viewport
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_xwindow_id(self.movie_window.window.xid)


if __name__ == '__main__':
    Gst.init(None)
    GTK_Main()
    Gtk.main()






