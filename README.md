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
| `tools/diag.py` | Per-match diagnostics on the simulator (cause/time of death, stuck time, time per mode). |
| `tools/arena.py`, `tools/league.py`, `tools/league_merge.py` | 16-bot free-for-all simulator: every mech runs a bot instance with protocol-level vision/sound. `league.py` fields several bot versions in the same matches (paired comparison) next to naive hunters and the kit example. |
| `tools/practice.py` | Practice-style matches on the league engine (crates, NPC drones, cubes, upgrades, drops) against a 15-bot house squad modelled on the track page: shared vision, no infighting, weakest first (one hunter early, one more per house bot killed, all after `--late` 180 s); idle members shoot inside `--sight` 250 m. Default `--noise 2.5` is calibrated on two real scores: kit example ~0.9 (real 1.15), v0.5 ~5.0 (real 4.75); `patient` comes out -0.7 (real -0.5). |
| `tools/trace.py` | Step-by-step trace of one simulated match (who hurts us, mode, position, goal). |
| `tools/early.py` | Profile of the first minute of many matches (arming time, damage by attacker tier). |

## Strategy (v0.5)

- Map model: building prisms rasterized to a 2 m grid + terrain, used for line of sight and wall avoidance.
- Loadout: laser + lightning (gun as fallback); mortar is never picked up (laser cook-off risk).
- Arm up first: while gun-only and not under fire, go for visible laser/lightning pickups.
- Combat: leading gun aim, laser charge-and-release on target, lightning inside its cone, focus one target.
- Survival: face attackers (rear hits x1.5), turn toward hidden attackers, break line of sight when
  outnumbered, outranged, under heavy fire or hurt, and regenerate in cover.
- Zone: travel early enough to be inside the next circle before it shrinks.
- Finish-off: low-HP targets (<30%) are chased and prioritised; a kill's dropped cubes are collected at once.
- Incoming fire: sidestep charging-laser lines, dodge bullets about to hit and run from mortar landing points.
- Memory: crates and weapon pickups seen earlier are remembered so the bot can return to them.
- Navigation: a 4 m walkability grid (mech radius included) plus incremental A* routes around buildings;
  a no-progress watchdog replans (or jets over the obstacle) when the bot jitters in a pocket.
- Loot run: boost towards far weapons/cubes when nobody is close; with no cover and only the gun, go
  arm up (or charge a laser sniper) instead of trading shots at range.
- Quiet movement (`sneak`, on by default): while enemies are known or heard and nobody is shooting at us,
  walk at <= 4.6 m/s. Below 5 m/s a mech makes no step sound, so sound-following opponents cannot locate us.
- Time guard: every decision stops optional work after ~15-30 ms (hard limit is 50 ms on 1 CPU).

## Experiment log (what the simulators said)

Practice-style sim = 1 bot vs 15 hunting house-style bots, calibrated so the kit example scores ~1.2
(real 1.15) and earlier versions land near their real scores (3.71 / 4.44 / 4.75 real vs 4.1 / 4.9 / 5.5 sim).
League = 16 bots in a free-for-all, which is what the qualifying round and final look like.

| Switch (`bot.flags`, env `MR_FLAGS`) | Practice sim | League | Decision |
| --- | --- | --- | --- |
| `sneak` | 5.25 vs 5.40 (neutral) | +0.2 .. +0.65 | **on** |
| `patient` (hold fire at range, hide) | sim 3.19 vs 5.40, but **real 4.04 vs 4.54** (submitted probe 42d652b) | +0.36 +- 0.22 (168 matches, with economy) | undecided: the real practice cost is small; choose at the deadline from the practice-board cutoff |
| `jink` (faster strafe flips) | not run | +0.17 (noise) | off |
| `early` (reach next circle sooner) | not run | -0.14 (noise) | off |
| `laser_tight` | not run | -0.25 (noise), accuracy unchanged | off |
| A* navigation vs v0.3 | +0.4 (noise) | -0.14 +- 0.26 | kept (fixes a real stuck-in-pocket bug) |
| `farm` (explore the safe circle for crates before 150 s) | `tools/practice.py`: +0.17 +- 0.28 (288 matches); **real 4.88 vs 4.75** | not run | **on** |
| `gunlaser` (keep the arm gun, add a laser, skip lightning) | `tools/practice.py`: +1.12 +- 0.41; +1.51 / +0.90 / +1.58 under three opponent models; **real 4.69 vs 4.88** | not run | off: the sim misjudges weapon choice |

Tried in `tools/practice.py` (288 paired matches, se ~0.27) and removed: gun-only bots backing off laser snipers
instead of charging (+0.00), longer loot runs while unarmed (+0.01), stronger low-HP focus (-0.17), lightning
chain targeting (-0.09), dodging to the goal side (-0.02), wider cover search (24 dirs, 6 threats: -0.64).
Dodging itself is worth about +0.4 (turning it off: -0.42). Also dropped: gun + lightning (-1.83), closing to
28 m whenever lightning is held (+0.44, noise), a 2x wider gun aim window (+0.14, noise).

Practice upper bounds (`tools/practice.py`, capability granted to our bot only, 192 matches each): damage taken
-30% +2.58, damage dealt +30% +2.08, max HP +30% +1.18, 360 deg vision +1.05, start with 10 cubes +0.95, spawn
with laser + lightning +0.83, 1.5x hit boxes +0.56. Unlike the free-for-all, damage dealt is worth a lot in
practice: every house bot killed is a placement point.

### Upper bounds ("oracle" switches in the league, paired, 120 matches each)

A capability is granted for free to 4 of the 16 mechs (flags `o_acc`, `o_dmgin`, `o_dmgout`, `o_hp`, `o_vis`), so the
gain shows how much engineering that capability could ever be worth in a free-for-all.

| Granted capability | Gain over the base bot (points per match) |
| --- | --- |
| Damage taken -30% | **+1.65** (se 0.29) |
| Max HP +30% | **+1.36** (se 0.28) |
| 360 deg vision to 300 m, hearing x1.5 | +0.90 (se 0.29) |
| Damage dealt +30% | +0.63 (se 0.34) |
| Hit boxes 1.5x wider (gun hit rate ~44% -> ~65%) | +0.28 (se 0.27) |

Cube economy (league with crates, NPC drones, supply drops, upgrade offers; hit boxes grow 5% per cube):
starting with 5 cubes +1.02, with 10 cubes +1.67 (se 0.29); the normal bot ends a match with ~6 cubes on average.

The real practice score of a submission is deterministic (resubmitting identical code gave the identical score),
and the hide-and-wait probe scored 4.04 against a simulator prediction of ~3.3, i.e. the real house bots hunt a
passive bot less aggressively than the practice sim models.

Survivability dominates; aiming improvements are worth almost nothing. The only large legitimate source of
effective HP is the cube economy (cubes: +4% HP and damage each up to 10, plus upgrade offers), which these
simulators do not model yet.

## Local testing (uv)

The organizer's kit (`check/`, `arena/`, `protocol.md`) sits in the parent folder `../`.

```sh
uv run python ../check/check.py -- python -u bot.py
uv run python tools/sim.py --matches 16                  # local smoke test (defaults are calibrated:
uv run python tools/sim.py --matches 16 --bot example    #  kit example ~1.2, v0.2 bot ~4.1; real 1.15 / 3.71)
uv run python tools/sim.py --matches 16 --botfile other_bot.py   # A/B another version of the bot
uv run python tools/league.py --matches 12 --entry new=bot:bot.py?sneak=8 --entry old=bot:other_bot.py=8   # paired league A/B
docker build -t mech-royale .
python ../check/check.py --map-dir /arena -- docker run --rm -i --network none --cpus 1 --memory 512m --read-only --tmpfs /tmp:rw,size=64m --user 65534:65534 -v "<abs path to kit>/arena:/arena:ro" mech-royale
```

## Third-party code

- `mechfight.py` and the starting version of `bot.py` come from the event's official
  `mechfight-kit` (Python wrapper and example bot).
- No other libraries: Python 3.13 standard library only.

## License

MIT – see `LICENSE`.
