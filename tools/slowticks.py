"""Find the slowest decisions of our bot in league matches and what it was doing at the time.

    uv run python tools/slowticks.py --matches 6 [--botfile bot.py] [--flags patient,sneak]
"""
import argparse
import collections
import cProfile
import io
import os
import pstats
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arena  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--matches", type=int, default=4)
ap.add_argument("--start", type=int, default=9000)
ap.add_argument("--kit", default="..")
ap.add_argument("--botfile", default=os.path.join(os.path.dirname(HERE), "bot.py"))
ap.add_argument("--flags", default="")
ap.add_argument("--threshold", type=float, default=10.0)
ap.add_argument("--profile", action="store_true")
args = ap.parse_args()

cfg = arena.load_cfg(args.kit)
fac = arena.make_factory("bot:%s?%s" % (args.botfile, args.flags), args.kit)
hunt = arena.make_factory("hunter", args.kit)
exm = arena.make_factory("example", args.kit)
mod = next(iter(arena._MODS.values()))
world = mod._shared[0]
slow = []
by_mode = collections.Counter()
tot_by_mode = collections.Counter()
prof = cProfile.Profile() if args.profile else None
for k in range(args.matches):
    entries = [("ours", fac)] * 8 + [("hunter", hunt)] * 4 + [("example", exm)] * 4
    sim = arena.League(cfg, world, args.start + k, entries, econ=True)
    for i, b in enumerate(sim.bots):
        if sim.mechs[i].label != "ours":
            continue
        orig = b.act

        def timed(o, orig=orig, b=b, k=k):
            t0 = time.perf_counter()
            if prof:
                prof.enable()
            r = orig(o)
            if prof:
                prof.disable()
            dt = (time.perf_counter() - t0) * 1000
            m = getattr(b, "mode", "?")
            tot_by_mode[m] += 1
            if dt >= args.threshold:
                by_mode[m] += 1
                slow.append((dt, k, o["t"], m, b.search is not None, len(o["mechs"]), len(o["crates"])))
            return r
        b.act = timed
    sim.run()
slow.sort(reverse=True)
n = sum(tot_by_mode.values())
print("decisions %d; >= %.0f ms: %d (%.2f%%)" % (n, args.threshold, len(slow), 100.0 * len(slow) / max(1, n)))
print("slow by mode:", dict(by_mode), " | decisions by mode:", dict(tot_by_mode))
for row in slow[:12]:
    print("  %.1f ms  match %d t=%.1f mode=%s astar_running=%s visible=%d crates=%d" % row)
if prof:
    st = io.StringIO()
    pstats.Stats(prof, stream=st).sort_stats("cumulative").print_stats(14)
    print(st.getvalue()[:3500])
