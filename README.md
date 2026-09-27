# The Green Thumb

The Garden's directory: every device, app, site, service and project with its web address, IP, SSH command and Tailscale name — plus a **password locker** encrypted on your own device (AES-GCM, key from your passphrase via PBKDF2). The server only ever stores scrambled text; passwords show as `••••••` until you tap 👁 View. Printed as a flip-through phone book (one page per device) in a green organic-hemp pack.

Part of the Garden's papers, all read through **[The Corner Chronicle](https://github.com/real-CAK3D/NewsStand)** — one home-screen app that mounts every paper under one private (Tailscale-only) HTTPS address: [The Double Wide](https://github.com/real-CAK3D/TheDoubleWide) (daily), [The Re-Up](https://github.com/real-CAK3D/TheRe-Up) (want ads), [The Sunday Smoke](https://github.com/real-CAK3D/TheSundaySmoke) (Sundays), [Roach Clips](https://github.com/real-CAK3D/RoachClips) (Tuesdays) and [The Green Thumb](https://github.com/real-CAK3D/TheGreenThumb) (the directory). The papers are written by [Hermes](https://github.com/NousResearch/hermes-agent) agents running on a small Oracle VM called The Garden.

## Files

| File | What it does |
|---|---|
| `build_green_thumb.py` | Copies the directory from the Obsidian vault (agents keep it current, never with passwords) and prints the phone book. |
| `site/js/gt.js` | Search (turns to the page), the locker (unlock / view / copy / edit / import a password-manager CSV — read and encrypted in the browser). |
| `serve.py` | Stores the encrypted locker and your own listings. |
| `gardenweb.py` | The small shared web-server kit every Garden paper carries its own copy of. |

## Running

Refreshes hourly; served at `/green-thumb/` under the Newsstand. The locker needs HTTPS (Web Crypto). Each project is Linux-first (`%-d` date formatting) and expects a Hermes install on the same machine.
