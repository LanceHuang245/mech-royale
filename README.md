# mech-royale

Bot for the **Builders – Mech Royale** track of the Builders Buildathon: it pilots one mech in a
16-mech battle royale over the `mechfight/1` JSON-lines protocol (stdin/stdout).

## Layout

| File | Purpose |
| --- | --- |
| `Dockerfile` | Image the scorer builds (linux/amd64) and runs in the match sandbox. |
| `bot.py` | The bot logic (`Bot.act` is called once per observation). |
| `mechfight.py` | Protocol wrapper (stdin/stdout loop, types, debug drawing). |
| `tools/sim.py` | Rough local simulator (our bot vs 15 hunting stand-in bots) for smoke tests. Not the real game. |
| `tools/diag.py` | Per-match diagnostics on the simulator (damage in/out, accuracy, time per mode). |

## Strategy (v0.2)

- Map model: building prisms rasterized to a 2 m grid + terrain, used for line of sight and wall avoidance.
- Loadout: laser + lightning (gun as fallback); mortar is never picked up (laser cook-off risk).
- Arm up first: while gun-only and not under fire, go for visible laser/lightning pickups.
- Combat: leading gun aim, laser charge-and-release on target, lightning inside its cone, focus one target.
- Survival: face attackers (rear hits x1.5), turn toward hidden attackers, break line of sight when
  outnumbered, outranged, under heavy fire or hurt, and regenerate in cover.
- Zone: travel early enough to be inside the next circle before it shrinks.

## Local testing (uv)

The organizer's kit (`check/`, `arena/`, `protocol.md`) sits in the parent folder `../`.

```sh
uv run python ../check/check.py -- python -u bot.py
uv run python tools/sim.py --matches 16 --noise 4 --lasers 3      # local smoke test
uv run python tools/sim.py --matches 16 --bot example --noise 4 --lasers 3
docker build -t mech-royale .
python ../check/check.py --map-dir /arena -- docker run --rm -i --network none --cpus 1 --memory 512m --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "<abs path to kit>/arena:/arena:ro" mech-royale
```

## Third-party code

- `mechfight.py` and the starting version of `bot.py` come from the event's official
  `mechfight-kit` (Python wrapper and example bot).
- No other libraries: Python 3.13 standard library only.

## License

MIT – see `LICENSE`.
