---
name: Car Cyberdeck
url: github.com/jvitorcosta/car-cyberdeck
status: public, open source (MIT), releases v1.0.0, v1.1.0 and v2.0.0
started: 2026-10-04
---

Facts (from the repo README and CHANGELOG at v2.0.0, 2026-10-29): two cheap 2.8" ESP32 touchscreens and a Garmin watch app for the car, all on the phone's WiFi hotspot, no server. Black deck (Freenove FNK0104B, ESP32-S3), in a Game Boy Advance shell (Vitor's photo): Spotify now playing as a Gen-3 (FireRed/Emerald) Pokémon battle with album art, a random Pokémon walking the HP bar as the song plays, synced lyrics (LRCLIB) in the dialogue box incl. Japanese/Chinese text, a genre badge from the iTunes catalogue, and a colour picked from each song for the lights; phone remote page with a QR code; updates over WiFi. Yellow deck (ESP32-2432S028R "Cheap Yellow Display", optional): drives the car's two Bluetooth LED controllers (inside and outside lights) with a terminal-style dashboard (clock, weather, trip timer), colours and presets, the black deck's lyrics and music mode; controlled by touch, Siri Shortcuts, an Xbox controller or the watch. Honda City watch app (Garmin Forerunner 255, Connect IQ): each light zone's colour and level, the presets, music mode, a glance card. Retired or not built: the companion screen with the sing-along avatar was retired on 2026-10-28; the Bluetooth OBD link is only a planned hook for the trip meter. Reliability (README and CHANGELOG): updates over WiFi into a two-slot layout with rollback if new firmware crashes early, watchdogs and back-offs on dropped links, signed requests for the light controls. C++17 / Arduino / PlatformIO, host-side unit tests, CI, tagged releases. Built with heavy use of Claude Code.

Variants:
- Built Car Cyberdeck, open-source firmware for two ESP32 touchscreens and a Garmin watch app: one deck shows Spotify as a Pokémon battle with synced lyrics, the other drives the car's LED lights by touch, Siri, an Xbox pad or the watch, all over the phone hotspot, with CI and tagged releases.

Tags: [side-project] [embedded] [outlier]
