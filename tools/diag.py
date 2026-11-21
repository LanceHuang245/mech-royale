"""Per-match diagnostics on the local sim: damage in/out, accuracy, time per mode."""
import sys, json, gzip, math, collections, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import sim, bot as B
cfg = json.loads(gzip.open(os.path.join(sys.argv[1], 'check', 'stream.jsonl.gz'), 'rt').readline())['config']
sim.NOISE_MULT, sim.LASER_BOTS = float(sys.argv[3]), int(sys.argv[4])
w = B.World(os.path.join(sys.argv[1], 'arena'))
tot = collections.Counter()
for seed in range(1, 1 + int(sys.argv[2])):
    s = sim.Sim(cfg, w, seed, B.Bot)
    st = collections.Counter()
    ob, od, oa = s.shoot_bullet, s.damage, s.bot.act
    def sb(m, stt, ob=ob, s=s, st=st):
        if m is s.me: st['shots'] += 1
        ob(m, stt)
    def dm(t, by, amt, ev, od=od, s=s, st=st):
        if by is s.me: st['hits'] += 1; st['out'] += amt
        if t is s.me: st['in'] += amt
        od(t, by, amt, ev)
    def act(o, oa=oa, s=s, st=st):
        a = oa(o); st['m_' + s.bot.mode] += 1; return a
    s.shoot_bullet, s.damage, s.bot.act = sb, dm, act
    r = s.run()
    tot.update(st); tot['pts'] += r['points']
    print(seed, r['points'], r['t'], r['weapons'], {k: round(v) for k, v in st.items()})
print({k: round(v) for k, v in tot.items()})
