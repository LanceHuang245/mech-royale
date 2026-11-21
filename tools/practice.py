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

wrap = A.wrap

TIERS = [4.0] * 4 + [2.5] * 4 + [1.3] * 4 + [0.7] * 3  # house aim noise per slot 1..15 (easy .. expert)


class _Done(Exception):
    pass


class Squad(A.League):
    def __init__(self, cfg, world, seed, ours, kit, late, sight, noise, pref=1.0):
        entries = [("ours", ours)] + [("house", A.make_factory("hunter:%g" % (s * noise), kit)) for s in TIERS]
        self.late, self.sight = late, sight
        super().__init__(cfg, world, seed, entries, econ=True)
        for b in self.bots[1:]:
            b.pref_mul = pref
        if "o_arm" in getattr(self.bots[0], "flags", ()):  # oracle: spawn with the target loadout
            self.mechs[0].weapons = [A.S.weapon("laser", cfg), A.S.weapon("lightning", cfg)]

    def _active(self, m):
        house = [x for x in self.mechs[1:] if x.alive]
        n = len(house) if self.t >= self.late else 1 + (15 - len(house))
        return m in house[:n]

    def step_zone(self):
        if not self.mechs[0].alive:  # only our placement matters: stop once we are dead
            raise _Done
        super().step_zone()

    def damage(self, t, by, amt, ev):
        # weapon damage upgrades (the league engine only applies plating / armor / nanites); gun_rate as +15% dps
        u = getattr(by, "upg", None)
        if u and not isinstance(by, A.Prop):
            k = self._kind
            if k == "laser":
                amt *= 1.18 ** u.get("laser_damage", 0)
            elif k == "gun":
                amt *= 1.15 ** (u.get("gun_damage", 0) + u.get("gun_rate", 0))
            elif k == "lightning":
                amt *= 1.10 ** u.get("lightning_efficiency", 0)
        super().damage(t, by, amt, ev)

    def targets(self, m):
        # house bots never fight each other (or farm): their shots only hit us
        if not isinstance(m, A.Prop) and m.id != 0:
            return [self.mechs[0]] if self.mechs[0].alive else []
        return super().targets(m)

    def obs_for(self, me, los_cache):
        if me.id == 0:
            return super().obs_for(me, los_cache)
        # house bots only use: us, nearby weapons, the zone and their own state (a lean obs is ~5x faster)
        us, t = self.mechs[0], self.t
        d = math.dist(us.pos[:2], me.pos[:2])
        if self._active(me):  # shared vision: the squad always knows where we are
            knows = us.alive
        else:  # idle: own vision (200 m, 120 deg wedge or 45 m near range, line of sight) plus 5 s memory, inside sight
            if us.alive and d <= min(200.0, self.sight) and (
                    d <= 45 or abs(wrap(math.atan2(us.pos[1] - me.pos[1], us.pos[0] - me.pos[0]) - me.aim[0])) <= math.radians(60)) \
                    and self._los_cached(me, us, los_cache):
                me.seen[0] = t
            knows = us.alive and t - me.seen.get(0, -99) <= 5 and d < self.sight
        mechs = [{"id": 0, "kind": "mech", "pos": list(us.pos), "vel": list(us.vel), "aim": list(us.aim)}] if knows else []
        c, r, _ = self.zone_now()
        ss, _, _ = self.zone_info()
        self.evs[me.id] = []
        return {"t": t, "tick": int(round(t * 20)), "mechs": mechs, "sounds": [],
                "pickups": [p for p in self.pickups if math.dist(p["pos"][:2], me.pos[:2]) < 90],
                "self": {"pos": me.pos, "aim": me.aim, "weapons": me.weapons, "energy": me.energy,
                         "in_zone": math.dist(me.pos[:2], c) <= r},
                "zone": {"center": c, "radius": r, "next_center": self.z_next[0], "next_radius": self.z_next[1],
                         "shrink_start": ss}}


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
    ap.add_argument("--pref", type=float, default=0.6, help="house bots' preferred fighting distance multiplier (0.6 fits gunlaser real -0.19)")
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
        sim = Squad(cfg, world, 1 + args.start + k, ours, args.kit, args.late, args.sight, args.noise, args.pref)
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
