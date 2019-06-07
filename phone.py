#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import dbus
import re

sys_bus = dbus.SystemBus()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["play", "pause", "next", "previous", "playpause", "status"], help="action to do")
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

def main():
    args = parse_args()
    player_path = get_players()[0]
    player_object = sys_bus.get_object("org.bluez", player_path)
    player_interface = dbus.Interface(player_object, "org.bluez.MediaPlayer1")
    player_properties = dbus.Interface(player_object, "org.freedesktop.DBus.Properties")
    player_status = player_properties.Get("org.bluez.MediaPlayer1","Status")
    name = player_properties.Get("org.bluez.MediaPlayer1","Name")

    ACTIONS = {
     "playpause": lambda : play_pause(player_interface, player_status),
     "play": lambda : player_interface.Play(),
     "pause": lambda : player_interface.Pause(),
     "next": lambda : player_interface.Next(),
     "previous": lambda : player_interface.Previous(),
     "status": lambda: status(name, player_status)
    }

    ACTIONS[args.action]()

if __name__ == "__main__":
    main()
