import sys, json
sys.path.insert(0, r"C:\Users\atila\Documents\RPG\algs4-py")
shadow = sys.argv[1]
if shadow != "-":
    sys.path.insert(0, shadow)
sys.path.insert(0, r"C:\Users\atila\Documents\RPG\manim-animations\src")
import flow_record as rec
det = rec.coletar_detalhado("edmonds_karp")
comp = rec.coletar("edmonds_karp")
print("detalhado", len(det), "compacto", len(comp), "inspecoes", det[-1].estado.get("inspecoes"))
for p in comp:
    print(json.dumps([p.acao, str(p.destaque), p.estado.get("valor"), p.estado.get("caminho"), p.estado.get("inspecoes"), p.estado.get("augmentacoes"), p.estado.get("corte")], ensure_ascii=False))
