import sys
sys.path.insert(0, r"C:\Users\atila\Documents\RPG\algs4-py")
sys.path.insert(0, r"C:\Users\atila\Documents\RPG\manim-animations\src")
import flow_record as rec
for nome in ("edmonds_karp", "ford_fulkerson_dfs"):
    d = rec.coletar_detalhado(nome)
    c = rec.coletar(nome)
    print(nome, "detalhado", len(d), "compacto", len(c), "inspecoes", d[-1].estado["inspecoes"])
