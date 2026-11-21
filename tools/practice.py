"""Practice-style matches on the league engine (crates, NPC drones, cubes, upgrades, supply drops):
our bot vs a 15-bot house squad.

Squad model from the track page: shared vision, no infighting, weakest first. One hunter early, one
more per house bot that dies, all of them after --late seconds; idle members still shoot inside --sight m.

    uv run python tools/practice.py --matches 48 [--flags a,b] [--botfile bot.py] [--bot example]
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arena as A  # noqa: E402

TIERS = [4.0] * 4 + [2.5] * 4 + [1.3] * 4 + [0.7] * 3  # house aim noise per slot 1..15 (easy .. expert)


class _Done(Exception):
    pass


class Squad(A.League):
    def __init__(self, cfg, world, seed, ours, kit, late, sight, noise):
        entries = [("ours", ours)] + [("house", A.make_factory("hunter:%g" % (s * noise), kit)) for s in TIERS]
        self.late, self.sight = late, sight
        super().__init__(cfg, world, seed, entries, econ=True)

    def _active(self, m):
        house = [x for x in self.mechs[1:] if x.alive]
        n = len(house) if self.t >= self.late else 1 + (15 - len(house))
        return m in house[:n]

    def step_zone(self):
        if not self.mechs[0].alive:  # only our placement matters: stop once we are dead
            raise _Done
        super().step_zone()

    def targets(self, m):
        # house bots never fight each other (or farm): their shots only hit us
        if not isinstance(m, A.Prop) and m.id != 0:
            return [self.mechs[0]] if self.mechs[0].alive else []
        return super().targets(m)

    def obs_for(self, me, los_cache):
        o = super().obs_for(me, los_cache)
        if me.id == 0:
            return o
        us = self.mechs[0]
        seen = [m for m in o["mechs"] if m["id"] == 0]
        if self._active(me):
            if not seen and us.alive:  # shared vision: the squad always knows where we are
                seen = [{"id": 0, "kind": "mech", "pos": list(us.pos), "vel": list(us.vel), "aim": list(us.aim),
                         "hp": us.hp, "max_hp": us.max_hp, "cubes": us.cubes,
                         "weapons": [w["kind"] for w in us.weapons if w], "charging": us.charge > 0}]
        else:
            seen = [m for m in seen if math.dist(m["pos"][:2], me.pos[:2]) < self.sight]
            o["sounds"] = []
        o["mechs"] = seen
        return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", type=int, default=24)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--kit", default="..")
    ap.add_argument("--botfile", default=os.path.join(os.path.dirname(HERE), "bot.py"))
    ap.add_argument("--flags", default=os.environ.get("MR_FLAGS", ""))
    ap.add_argument("--bot", choices=["ours", "example"], default="ours")
    ap.add_argument("--late", type=float, default=180.0)
    ap.add_argument("--sight", type=float, default=250.0)
    ap.add_argument("--noise", type=float, default=2.5)  # calibrated: example ~0.9, v0.5 ~5.0 (real 1.15 / 4.75)
    args = ap.parse_args()
    cfg = A.load_cfg(args.kit)
    ours = A.make_factory("example" if args.bot == "example" else "bot:%s?%s" % (args.botfile, args.flags), args.kit)
    world = None
    pts = []
    for k in range(args.matches):
        if world is None:  # the league shares one World between all instances
            mod = next(iter(A._MODS.values()), None)
            world = mod._shared[0] if mod else A.S.B.World(os.path.join(args.kit, "arena"))
        sim = Squad(cfg, world, 1 + args.start + k, ours, args.kit, args.late, args.sight, args.noise)
        try:
            p = sim.run()[0]["points"]
        except _Done:
            p = sum(1 for _, i in sim.deaths if i != 0)  # house bots that died before us
        us = sim.mechs[0]
        pts.append(p)
        print(json.dumps({"points": p, "t": round(sim.t, 1), "cubes": us.cubes, "upg": us.upg}), flush=True)
    print("mean points %.2f over %d" % (sum(pts) / len(pts), len(pts)))


if __name__ == "__main__":
    main()
