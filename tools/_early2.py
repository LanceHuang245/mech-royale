import sys, os, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import practice as P
import arena as A
DEF = os.environ["DEFF"]
cfg = A.load_cfg("..")
ours = A.make_factory("bot:bot.py?" + DEF, "..")
world = None
for seed in range(1, int(sys.argv[1]) + 1):
    if world is None:
        mod = next(iter(A._MODS.values()), None)
        world = mod._shared[0]
    sim = P.Squad(cfg, world, seed, ours, "..", 180.0, 250.0, 2.5, 0.6)
    log = []
    od = sim.damage
    def dm(t, by, amt, ev, od=od, sim=sim, log=log):
        if t is sim.mechs[0] and by is not None and not isinstance(by, A.Prop):
            log.append((round(sim.t, 1), by.id, round(math.dist(by.pos[:2], t.pos[:2])), sim._kind, round(amt)))
        od(t, by, amt, ev)
    sim.damage = dm
    try:
        r = sim.run()[0]["points"]
    except P._Done:
        r = sum(1 for _, i in sim.deaths if i != 0)
    if sim.t < 30:
        wp = [w["kind"] if w else None for w in sim.mechs[0].weapons]
        byw = collections.Counter()
        for tt, i, d, k, a in log: byw[(i, k)] += a
        print(seed, "pts", r, "t", round(sim.t, 1), "first", log[:1], "weapons", wp, "dmg", dict(byw))
