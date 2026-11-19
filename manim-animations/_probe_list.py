import sys
sys.path.insert(0, r"C:\Users\atila\Documents\RPG\algs4-py")
from algs4.flow_network import FlowNetwork
class CountingNet(FlowNetwork):
    ins = 0
    def adj(self, v):
        for e in self._adj[v]:
            CountingNet.ins += 1
            yield e
g = CountingNet(r"C:\Users\atila\Documents\RPG\dataset\tinyFN.txt")
from algs4.ford_fulkerson import FordFulkerson
paths=[]
orig=FordFulkerson.has_augmenting_path
def wrapped(self, gg, s, t):
    ok=orig(self,gg,s,t)
    if ok:
        p=[]; v=t
        while v!=s:
            e=self.edgeTo[v]; p.append((e.from_(),e.to())); v=e.other(v)
        paths.append(p[::-1])
    else: paths.append(None)
    return ok
FordFulkerson.has_augmenting_path=wrapped
CountingNet.ins=0
mf=FordFulkerson(g,0,g.V-1)
print("value",mf.value,"ins",CountingNet.ins)
for p in paths: print(None if p is None else " -> ".join([str(p[0][0])]+[str(x[1]) for x in p]))
