# mech-royale

Bot for the **Builders – Mech Royale** track of the Builders Buildathon: it pilots one mech in a
16-mech battle royale over the `mechfight/1` JSON-lines protocol (stdin/stdout).

## Layout

| File | Purpose |
| --- | --- |
| `Dockerfile` | Image the scorer builds (linux/amd64) and runs in the match sandbox. |
| `bot.py` | The bot logic (`Bot.act` is called once per observation). |
| `mechfight.py` | Protocol wrapper (stdin/stdout loop, types, debug drawing). |

## Local testing (uv)

The organizer's kit (`check/`, `arena/`, `protocol.md`) sits in the parent folder `../`.

```sh
uv run python ../check/check.py -- python -u bot.py
docker build -t mech-royale .
python ../check/check.py --map-dir /arena -- docker run --rm -i --network none --cpus 1 --memory 512m --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "<abs path to kit>/arena:/arena:ro" mech-royale
```

## Third-party code

- `mechfight.py` and the starting version of `bot.py` come from the event's official
  `mechfight-kit` (Python wrapper and example bot).
- No other libraries: Python 3.13 standard library only.

## License

MIT – see `LICENSE`.
