#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import dbus
import re
import time

sys_bus = dbus.SystemBus()

def connect_a_phone():
    adapter_object = sys_bus.get_object("org.bluez", "/org/bluez/hci0")
    adapter_properties = dbus.Interface(adapter_object, "org.freedesktop.DBus.Properties")
    powered = adapter_properties.Get("org.bluez.Adapter1", "Powered")
    if not powered:
        adapter_properties.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))

    bluez_objects = sys_bus.get_object("org.bluez", "/")
    objects = dbus.Interface(bluez_objects, "org.freedesktop.DBus.ObjectManager")
    phones = [
        path
        for path, interfaces in objects.GetManagedObjects().items()
        if "org.bluez.Device1" in interfaces and
           "phone" in interfaces["org.bluez.Device1"]["Icon"].lower()
    ]


    device_object = sys_bus.get_object("org.bluez", phones[0])
    device_interface = dbus.Interface(device_object, "org.bluez.Device1")
    device_properties = dbus.Interface(device_object, "org.freedesktop.DBus.Properties")
    print("connecting", device_properties.Get("org.bluez.Device1","Name"))
    device_interface.Connect()
    #the connect call doesn't block, so wait for it
    time.sleep(4)



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["play", "pause", "stop", "next", "previous", "playpause", "status"], help="action to do")
    return parser.parse_args()

def get_players():
    """returns a list of interfaces that provide the player interface"""
    player_re = re.compile(r"^.+/player\d+")
    bluez_objects = sys_bus.get_object("org.bluez", "/")
    objects = dbus.Interface(bluez_objects, "org.freedesktop.DBus.ObjectManager")

    return [
        object for object 
        in objects.GetManagedObjects().keys() 
        if  player_re.match(object)
    ]

def play_pause(device, player_status):
    if player_status == "playing":
        device.Pause()
    elif player_status == "paused":
        device.Play()

def status(name, status):
    if status == "playing":
        print(status, name)
    elif status == "paused":
        print(status)

def manage_player(args):
    player_path = get_players()[0]
    player_object = sys_bus.get_object("org.bluez", player_path)
    player_interface = dbus.Interface(player_object, "org.bluez.MediaPlayer1")
    player_properties = dbus.Interface(player_object, "org.freedesktop.DBus.Properties")
    player_status = player_properties.Get("org.bluez.MediaPlayer1","Status")
    track = player_properties.Get("org.bluez.MediaPlayer1", "Track")
    title = track.get('Title', "")
    album = track.get('Album', "")
    artist = track.get('Artist', "")
    try:
        name = player_properties.Get("org.bluez.MediaPlayer1","Name")
    except dbus.DBusException:
        name = ""

    if name == "Overcast":
        full_status = f"{name}: {artist} {title} {album}"
    else:
        full_status = f"{name}: {album} {title}"

    ACTIONS = {
     "playpause": lambda : play_pause(player_interface, full_status),
     "play": lambda : player_interface.Play(),
     "pause": lambda : player_interface.Pause(),
     "stop": lambda : player_interface.Pause(),
     "next": lambda : player_interface.Next(),
     "previous": lambda : player_interface.Previous(),
     "status": lambda: status(full_status, player_status)
    }

    ACTIONS[args.action]()

def main():
    args = parse_args()
    try:
        manage_player(args)
    except IndexError:
        try:
            connect_a_phone()
            manage_player(args)
        except IndexError:
            print("could not connect a phone")



if __name__ == "__main__":
    main()
