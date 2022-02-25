#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import dbus
import re
import time
from collections import OrderedDict

sys_bus = dbus.SystemBus()


def connect_a_phone():
    adapter_object = sys_bus.get_object("org.bluez", "/org/bluez/hci0")
    adapter_properties = dbus.Interface(
        adapter_object, "org.freedesktop.DBus.Properties"
    )
    powered = adapter_properties.Get("org.bluez.Adapter1", "Powered")
    if not powered:
        adapter_properties.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))

    bluez_objects = sys_bus.get_object("org.bluez", "/")
    objects = dbus.Interface(bluez_objects, "org.freedesktop.DBus.ObjectManager")
    phones = [
        path
        for path, interfaces in objects.GetManagedObjects().items()
        if "org.bluez.Device1" in interfaces
        and "phone" in interfaces["org.bluez.Device1"]["Icon"].lower()
    ]

    device_object = sys_bus.get_object("org.bluez", phones[0])
    device_interface = dbus.Interface(device_object, "org.bluez.Device1")
    device_properties = dbus.Interface(device_object, "org.freedesktop.DBus.Properties")
    print("connecting", device_properties.Get("org.bluez.Device1", "Name"))
    device_interface.Connect()
    # the connect call doesn't block, so wait for it
    time.sleep(4)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        help="""action to do, fuzzy matches (default toggle)
"play" play the track
"pause" pause the track
"stop" stop the track
"snext" skip ahead
"sprevious" skip back
"next" next track
"previous" previous track
"toggle" play/pause
"status" show playing track
    """,
    )
    return parser.parse_args()


def get_players():
    """returns a list of interfaces that provide the player interface"""
    player_re = re.compile(r"^.+/player\d+")
    bluez_objects = sys_bus.get_object("org.bluez", "/")
    objects = dbus.Interface(bluez_objects, "org.freedesktop.DBus.ObjectManager")

    return [
        object
        for object in objects.GetManagedObjects().keys()
        if player_re.match(object)
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


def fuzzy_match(entries, keyword, default):
    def score(a, b):
        s = 0
        for ai, bi in zip(a, b):
            if ai == bi:
                s += 1
            else:
                break
        return s

    best = default
    best_score = 0
    for entry in entries:
        if entry == keyword:
            return keyword
        s = score(entry, keyword)
        if s > best_score:
            best = entry
            best_score = s
    return best


def manage_player(args):
    player_path = get_players()[0]
    player_object = sys_bus.get_object("org.bluez", player_path)
    player_interface = dbus.Interface(player_object, "org.bluez.MediaPlayer1")
    player_properties = dbus.Interface(player_object, "org.freedesktop.DBus.Properties")
    player_status = player_properties.Get("org.bluez.MediaPlayer1", "Status")
    try:
        track = player_properties.Get("org.bluez.MediaPlayer1", "Track")
    except dbus.exceptions.DBusException:
        track = {
            "Title": "",
            "Album": "",
            "Artist": "",
            "Duration": -1,
            "TrackNumber": -1,
            "NumberOfTracks": -1,
        }
    title = track.get("Title", "").strip()
    album = track.get("Album", "").strip()
    artist = track.get("Artist", "").strip()
    current_track = track.get("TrackNumber", -1)
    tracks = track.get("NumberOfTracks", -1)
    artist = track.get("Artist", "").strip()
    duration = int(track.get("Duration", -1))
    position = player_properties.Get("org.bluez.MediaPlayer1", "Position")
    try:
        name = player_properties.Get("org.bluez.MediaPlayer1", "Name")
    except dbus.DBusException:
        name = ""

    min_progress = position // 60000
    sec_progress = (position - min_progress * 60000) // 1000
    min_total = duration // 60000
    sec_total = (duration - min_total * 60000) // 1000
    if duration != -1:
        duration_str = f"{min_progress}:{sec_progress:02d}/{min_total}:{sec_total:02d}"
    else:
        duration_str = ""

    if tracks > 0 and current_track > 0:
        track_str = f"track = {current_track}/{tracks},"
    else:
        track_str = ""

    album_sep = "on" if not "Overcast" in name else "-"
    if title:
        if album:
            if artist:
                desc = f'{artist} - "{title}" {album_sep} {album}'
            else:
                desc = f'"{title}" {album_sep} {album}'
        elif artist:
            desc = f'{artist} {album_sep} {album}'
        else:
            desc = f'"{title}"'
    elif album:
        if artist:
            desc = f"{artist} {album_sep} {album}"
        else:
            desc = f"{album}"
    elif artist:
        desc = "{artist}"
    else:
        desc = ""


    full_status = f'{name}: {desc} {track_str} {duration_str}'.strip()

    ACTIONS = OrderedDict(
        [
            ("toggle", lambda: play_pause(player_interface, player_status)),
            ("play", lambda: player_interface.Play()),
            ("status", lambda: status(full_status, player_status)),
            ("pause", lambda: player_interface.Pause()),
            ("stop", lambda: player_interface.Pause()),
            ("next", lambda: player_interface.FastForward()),
            ("previous", lambda: player_interface.Rewind()),
            ("snext", lambda: player_interface.Next()),
            ("sprevious", lambda: player_interface.Previous()),
        ]
    )

    ACTIONS[fuzzy_match(ACTIONS.keys(), args.action, default="toggle")]()


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
