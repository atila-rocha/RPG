import sys
sys.path.insert(0, r"C:\Users\atila\Documents\RPG\algs4-py")
shadow = sys.argv[1]
if shadow != "-":
    sys.path.insert(0, shadow)
sys.path.insert(0, r"C:\Users\atila\Documents\RPG\manim-animations\src")
import flow_record as rec
print("modulo:", rec.arquivo_modulo("algs4.ford_fulkerson"))
det = rec.coletar_detalhado("edmonds_karp")
comp = rec.coletar("edmonds_karp")
print("detalhado:", len(det), "compacto:", len(comp))
print("inspecoes final:", det[-1].estado.get("inspecoes"))
print("valor:", det[-1].estado.get("valor"), "corte:", det[-1].estado.get("corte"))
print("compacto assinatura:")
for p in comp:
    print("  ", p.acao, p.destaque, p.estado.get("valor"), p.estado.get("caminho"), p.estado.get("inspecoes"))
