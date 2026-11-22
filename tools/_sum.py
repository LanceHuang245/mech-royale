import sys, json, glob, statistics as st
name = sys.argv[1]
p = []
for f in glob.glob("/tmp/%s.*.log" % name) + glob.glob("C:/Users/Lance/AppData/Local/Temp/%s.*.log" % name):
    for l in open(f):
        if l.startswith("{"):
            p.append(json.loads(l)["points"])
print("%s n=%d mean=%.2f se=%.2f zeros=%d" % (name, len(p), st.mean(p), st.stdev(p) / len(p) ** .5, sum(1 for x in p if x == 0)))
