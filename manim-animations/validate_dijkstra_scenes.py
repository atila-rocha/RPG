"""
Testes de estado da animação de Dijkstra — sem Manim.

Roda o gravador (`dijkstra_record.py`) sobre o `algs4-py` e verifica:

a) golden: resultado final do tinyEWD (distTo, edgeTo, SPT, custo, ordem);
b) invariantes: relaxação, monotonicidade, heap e SPT em todo passo;
c) determinismo: duas gravações produzem a mesma sequência;
d) linha a linha: cobertura das linhas e views de código;
e) abas: a aba ativa segue o módulo/linha executada e realmente troca;
f) layout: pesos do grafo sem colisão entre si nem com os nós.

Uso:  python validate_dijkstra_scenes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import dijkstra_record as rec  # noqa: E402

VERDE = "\033[92m"
VERMELHO = "\033[91m"
RESET = "\033[0m"
TOL = 1e-9


class Falha(AssertionError):
    pass


def verificar(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise Falha(mensagem)


def assinatura(passos: list[rec.Step]) -> list[tuple]:
    return [
        (
            p.modulo,
            p.linha,
            p.acao,
            p.destaque,
            tuple(round(float(d), 6) for d in p.estado.get("distTo", [])),
            tuple(tuple(e) if e else None for e in p.estado.get("edgeTo", [])),
            tuple(p.estado.get("pq_ordem", [])),
            tuple(p.estado.get("marcados", [])),
        )
        for p in passos
    ]


# ---------------------------------------------------------------------------
# a) Golden
# ---------------------------------------------------------------------------

DIST_FINAL = [0.0, 1.05, 0.26, 0.99, 0.38, 0.73, 1.51, 0.60]
EDGE_TO_FINAL = [
    None,
    (5, 1, 0.32),
    (0, 2, 0.26),
    (7, 3, 0.39),
    (0, 4, 0.38),
    (4, 5, 0.35),
    (3, 6, 0.52),
    (2, 7, 0.34),
]
SPT_FINAL = [
    (0, 2, 0.26),
    (0, 4, 0.38),
    (2, 7, 0.34),
    (3, 6, 0.52),
    (4, 5, 0.35),
    (5, 1, 0.32),
    (7, 3, 0.39),
]
ORDEM_EXTRACAO = [0, 2, 4, 7, 5, 3, 1, 6]
CUSTO_FINAL = 2.56


def testar_golden() -> None:
    verificar(rec.V_CANONICO == 8, f"V do tinyEWD = {rec.V_CANONICO}, esperado 8")
    verificar(len(rec.ARESTAS_CANONICAS) == 15, f"E = {len(rec.ARESTAS_CANONICAS)}, esperado 15")
    verificar(rec.ORIGEM == 0, f"origem = {rec.ORIGEM}, esperado 0")

    passos = rec.coletar_detalhado()
    final = passos[-1].estado

    for v, (obtido, esperado) in enumerate(zip(final["distTo"], DIST_FINAL)):
        verificar(abs(obtido - esperado) < TOL, f"distTo[{v}] = {obtido}, esperado {esperado}")
    verificar(len(final["distTo"]) == 8, f"distTo final tem {len(final['distTo'])} posições")

    verificar(final["edgeTo"] == EDGE_TO_FINAL, f"edgeTo final divergiu: {final['edgeTo']}")
    verificar(
        sorted(final["spt"]) == SPT_FINAL,
        f"SPT final divergiu: {sorted(final['spt'])}",
    )
    verificar(abs(final["custo"] - CUSTO_FINAL) < TOL, f"custo final = {final['custo']}")
    verificar(
        sorted(final["marcados"]) == list(range(8)),
        f"marcados finais = {final['marcados']}",
    )
    verificar(final["ipq"] == {}, f"IPQ final não está vazia: {final['ipq']}")
    verificar(final["pq_ordem"] == [], f"heap final não está vazio: {final['pq_ordem']}")

    ordem = [p.destaque[1] for p in passos if p.destaque[3] == "extraido"]
    verificar(ordem == ORDEM_EXTRACAO, f"ordem de extração divergiu: {ordem}")

    verificar(passos[0].linha == 38, f"primeiro passo na linha {passos[0].linha}, esperado 38")
    verificar(passos[0].modulo == "algs4.dijkstra_sp", f"primeiro módulo = {passos[0].modulo}")
    verificar(passos[-1].destaque[0] == "fim", "último passo não marca o fim")
    verificar("concluído" in passos[-1].acao, f"ação final inesperada: {passos[-1].acao}")


# ---------------------------------------------------------------------------
# b) Invariantes
# ---------------------------------------------------------------------------


def testar_invariantes() -> None:
    passos = rec.coletar_detalhado()

    anterior_marcados: set[int] = set()
    anterior_dist: list[float] | None = None

    for i, passo in enumerate(passos):
        est = passo.estado
        dist = est.get("distTo") or []
        edge_to = est.get("edgeTo") or []
        marcados = set(est.get("marcados", []))

        verificar(passo.acao.strip() != "", f"[{i}] ação vazia")
        verificar(passo.pausa > 0, f"[{i}] pausa inválida: {passo.pausa}")
        verificar("= ?" not in passo.acao, f"[{i}] ação com valor não resolvido: {passo.acao}")

        if dist:
            verificar(len(dist) == rec.V_CANONICO, f"[{i}] distTo com {len(dist)} posições")
        if edge_to:
            verificar(len(edge_to) == rec.V_CANONICO, f"[{i}] edgeTo com {len(edge_to)} posições")

        # Extração é monotônica: nenhum vértice sai de marcados.
        verificar(
            anterior_marcados <= marcados,
            f"[{i}] marcados andaram para trás: {anterior_marcados} -> {marcados}",
        )
        anterior_marcados = marcados

        # Distâncias nunca aumentam (pesos não negativos).
        if anterior_dist and dist:
            for v, (a, b) in enumerate(zip(anterior_dist, dist)):
                verificar(b <= a + TOL, f"[{i}] distTo[{v}] aumentou: {a} -> {b}")
            anterior_dist = list(dist)
        elif dist:
            anterior_dist = list(dist)

        # SPT = edgeTo apenas dos finalizados; custo = soma dos pesos.
        spt = [edge_to[v] for v in sorted(marcados) if v < len(edge_to) and edge_to[v] is not None]
        verificar(
            sorted(est.get("spt", [])) == sorted(spt),
            f"[{i}] SPT não é o edgeTo dos finalizados",
        )
        verificar(
            abs(sum(e[2] for e in spt) - float(est.get("custo", 0))) < TOL,
            f"[{i}] custo {est.get('custo')} != soma da SPT",
        )

        # Todo finalizado (menos a origem) tem predecessor.
        for v in marcados:
            if v != rec.ORIGEM:
                verificar(
                    v < len(edge_to) and edge_to[v] is not None,
                    f"[{i}] vértice {v} finalizado sem edgeTo",
                )

        # IPQ lógica: um item por vértice, chave igual a distTo.
        ipq = est.get("ipq") or {}
        chaves = est.get("ipq_keys") or {}
        for v, chave in ipq.items():
            verificar(v not in marcados, f"[{i}] vértice {v} na IPQ e finalizado")
            verificar(
                abs(chave - dist[v]) < TOL,
                f"[{i}] IPQ[{v}] = {chave} != distTo[{v}] = {dist[v]}",
            )
        for v in ipq:
            if v in chaves:
                verificar(
                    abs(chaves[v] - dist[v]) < TOL,
                    f"[{i}] keys[{v}] = {chaves[v]} != distTo[{v}] = {dist[v]}",
                )

        # A ordem física do heap só contém vértices não finalizados (tinyEWD
        # não produz duplicatas; a checagem é a do estado real).
        ordem = list(est.get("pq_ordem", []))
        for v in ordem:
            verificar(0 <= v < rec.V_CANONICO, f"[{i}] índice inválido no heap: {v}")
            verificar(v not in marcados, f"[{i}] finalizado {v} ainda em pq_ordem")

        # Propriedade do heap (pai <= filho), exceto durante swim/sink, quando
        # uma troca intermediária pode deixar o vetor momentaneamente fora.
        if passo.modulo != "algs4.index_min_pq" and len(ordem) == len(set(ordem)):
            for k in range(1, len(ordem)):
                pai, filho = ordem[(k - 1) // 2], ordem[k]
                verificar(
                    chaves.get(pai, dist[pai]) <= chaves.get(filho, dist[filho]) + TOL,
                    f"[{i}] heap violado: pai {pai} > filho {filho} ({ordem})",
                )

        # Toda aresta em edgeTo realiza a distância do destino:
        # distTo[v] == distTo[u] + w. (Não se exige isso para TODAS as
        # arestas: durante a execução há arestas ainda não relaxadas, e é
        # justamente por isso que o algoritmo continua.)
        if dist and edge_to:
            for v, e in enumerate(edge_to):
                if e is None or v >= len(dist):
                    continue
                u, _w, peso = e
                if dist[u] < 999999.0:
                    verificar(
                        abs(dist[v] - (dist[u] + peso)) < TOL,
                        f"[{i}] edgeTo[{v}] = {u}->{v} não realiza distTo: "
                        f"{dist[v]} != {dist[u]} + {peso}",
                    )

        # Dijkstra: todo finalizado tem distância <= qualquer não finalizado.
        nao_finalizados = [v for v in range(rec.V_CANONICO) if v not in marcados]
        if marcados and nao_finalizados and dist:
            maior_final = max((dist[v] for v in marcados), default=0.0)
            menor_aberto = min(dist[v] for v in nao_finalizados)
            verificar(
                maior_final <= menor_aberto + TOL,
                f"[{i}] extração fora de ordem: final {maior_final} > aberto {menor_aberto}",
            )


# ---------------------------------------------------------------------------
# c) Determinismo
# ---------------------------------------------------------------------------


def testar_determinismo() -> None:
    verificar(
        assinatura(rec.coletar_detalhado()) == assinatura(rec.coletar_detalhado()),
        "duas gravações produziram sequências diferentes",
    )


# ---------------------------------------------------------------------------
# d) Linha a linha e views de código
# ---------------------------------------------------------------------------

LINHAS_DIJKSTRA = {
    38, 39, 40, 41, 42, 43, 44, 45, 46,
    48, 49, 50, 51, 52, 53, 54, 55, 57,
}
LINHAS_IPQ = {4, 5, 6, 9, 10, 11, 12, 13, 21, 46, 47, 48, 49, 51, 52, 55, 60, 61, 62, 64, 66, 67, 69, 70, 71, 72, 74, 75, 77, 78}
LINHAS_ARESTA = {19, 20}

NOMES_VIEWS = {
    ("algs4.dijkstra_sp", "DijkstraSP.__init__"),
    ("algs4.dijkstra_sp", "DijkstraSP.relax"),
    ("algs4.index_min_pq", "IndexMinPQ.__init__"),
    ("algs4.index_min_pq", "IndexMinPQ.insert"),
    ("algs4.index_min_pq", "IndexMinPQ.change"),
    ("algs4.index_min_pq", "IndexMinPQ.contains"),
    ("algs4.index_min_pq", "IndexMinPQ.del_min"),
    ("algs4.index_min_pq", "IndexMinPQ.is_empty"),
    ("algs4.index_min_pq", "IndexMinPQ.swim"),
    ("algs4.index_min_pq", "IndexMinPQ.sink"),
    ("algs4.directed_edge", "DirectedEdge.To"),
}


def testar_detalhado() -> None:
    passos = rec.coletar_detalhado()
    verificar(len(passos) > 100, f"poucos passos: {len(passos)}")

    vistos: set[tuple[str, int]] = set()
    for i, passo in enumerate(passos[:-1]):
        view = rec.funcao_da_linha(passo.linha, passo.modulo)
        verificar(
            view.modulo == passo.modulo,
            f"[{i}] view {view.nome} de {view.modulo} não bate com {passo.modulo}",
        )
        # A linha destacada tem de existir dentro do bloco de código exibido;
        # senão o indicador do painel sai do código (clamp em `_posicionar`).
        verificar(
            view.inicio <= passo.linha <= view.fim,
            f"[{i}] linha {passo.linha} fora da view {view.nome} "
            f"({view.inicio}-{view.fim})",
        )
        if passo.modulo == "algs4.dijkstra_sp":
            verificar(
                passo.linha in LINHAS_DIJKSTRA,
                f"[{i}] linha {passo.linha} fora do DijkstraSP",
            )
        elif passo.modulo == "algs4.index_min_pq":
            verificar(
                passo.linha in LINHAS_IPQ,
                f"[{i}] linha {passo.linha} fora da IndexMinPQ",
            )
        elif passo.modulo == "algs4.directed_edge":
            verificar(
                passo.linha in LINHAS_ARESTA,
                f"[{i}] linha {passo.linha} fora de DirectedEdge",
            )
        else:
            raise Falha(f"[{i}] módulo inesperado no trace: {passo.modulo}")
        vistos.add((passo.modulo, passo.linha))

        if i > 0:
            ant = passos[i - 1]
            chave_atual = (passo.modulo, passo.linha, passo.estado)
            chave_ant = (ant.modulo, ant.linha, ant.estado)
            verificar(
                chave_atual != chave_ant,
                f"[{i}] passo duplicado consecutivo: {passo.modulo}:{passo.linha}",
            )

    # Linha 48 é o `def relax` (não gera evento de linha na chamada) e a 55 é
    # o `pq.change`, ramo que não executa no tinyEWD porque o `contains` do
    # algs4 sempre devolve False. A view de `relax` mostra a 48; o painel
    # continua fiel ao caminho real (insert na 57).
    for linha in LINHAS_DIJKSTRA - {48, 55}:
        verificar(
            ("algs4.dijkstra_sp", linha) in vistos,
            f"linha {linha} do DijkstraSP nunca foi destacada",
        )

    # Views de código: derivadas do ast real, sem inventar funções.
    funcoes = rec.funcoes_codigo()
    chaves = {(f.modulo, f.nome) for f in funcoes}
    verificar(chaves == NOMES_VIEWS, f"views {sorted(chaves)} != esperado")
    verificar(len(chaves) == len(funcoes), "view repetida no painel")

    for f in funcoes:
        arquivo = rec.arquivo_modulo(f.modulo)
        linhas = arquivo.read_text(encoding="utf-8").splitlines()
        verificar(
            f.texto == "\n".join(linhas[f.inicio - 1 : f.fim]),
            f"{f.modulo}.{f.nome}: texto não bate com o fonte",
        )


# ---------------------------------------------------------------------------
# e) Abas
# ---------------------------------------------------------------------------

ABA_ESPERADA = {
    38: "et",
    39: "dt",
    40: "dt",
    41: "dt",
    42: "dt",
    43: "heap",
    44: "heap",
    45: "heap",
    46: "heap",
    48: "dt",
    49: "dt",
    50: "dt",
    51: "dt",
    52: "dt",
    53: "et",
    54: "heap",
    55: "heap",
    57: "heap",
}


def _alvo(passo: rec.Step, ativa: str | None) -> str:
    """Cópia da regra de `EstruturaPanel._alvo` (sem importar Manim)."""
    if passo.modulo == "algs4.index_min_pq":
        return "heap"
    if passo.modulo == "algs4.directed_edge":
        return "dt"
    if passo.modulo == "algs4.dijkstra_sp":
        return ABA_ESPERADA.get(passo.linha, ativa or "heap")
    return ativa or "heap"


def testar_abas() -> None:
    from dijkstra_common import EstruturaPanel  # importa Manim apenas aqui

    passos = rec.coletar_detalhado()
    ativa = None
    alvos: list[str] = []
    for passo in passos:
        ativa = _alvo(passo, ativa)
        alvos.append(ativa)

    # A regra do teste e a regra da cena precisam ser a mesma.
    painel = EstruturaPanel(np_array_centro(), 6.70, 2.90)
    for passo, esperado in zip(passos, alvos):
        verificar(
            painel._alvo(passo) == esperado,
            f"cena e validador discordam em {passo.modulo}:{passo.linha}",
        )

    trocas = sum(1 for a, b in zip(alvos, alvos[1:]) if a != b)
    verificar(trocas >= 6, f"poucas trocas de aba: {trocas}")

    # As três abas são realmente usadas.
    verificar(set(alvos) == {"heap", "dt", "et"}, f"abas usadas: {set(alvos)}")

    # Sequência didática: começa em edgeTo, passa por distTo e depois heap.
    verificar(alvos[0] == "et", f"primeira aba = {alvos[0]}, esperado et")
    verificar("dt" in alvos[:15], "distTo não aparece na inicialização")
    verificar(alvos[15] == "heap" or "heap" in alvos[10:25], "heap não aparece na IPQ")


def np_array_centro():
    import numpy as np

    return np.array([-3.35, -2.30, 0])


# ---------------------------------------------------------------------------
# f) Layout do grafo
# ---------------------------------------------------------------------------


def testar_layout() -> None:
    from dijkstra_common import DirectedGraphView

    grafo = DirectedGraphView()
    pesos = list(grafo.pesos.items())

    # Nenhum peso em cima de um nó.
    for (u, v), txt in pesos:
        for vertice, pt in grafo.coords.items():
            dist = ((txt.get_center()[0] - pt[0]) ** 2 + (txt.get_center()[1] - pt[1]) ** 2) ** 0.5
            verificar(dist > 0.34, f"peso {u}->{v} encosta no nó {vertice}")

    # Pesos não se sobrepõem.
    for i in range(len(pesos)):
        for j in range(i + 1, len(pesos)):
            (a, b), ta = pesos[i]
            (c, d), tb = pesos[j]
            dx = abs(ta.get_center()[0] - tb.get_center()[0])
            dy = abs(ta.get_center()[1] - tb.get_center()[1])
            verificar(
                dx > 0.20 or dy > 0.14,
                f"pesos {a}->{b} e {c}->{d} se sobrepõem",
            )

    # Arestas recíprocas deslocadas: as setas não ficam na mesma reta.
    p45 = grafo.setas[(4, 5)].get_center()
    p54 = grafo.setas[(5, 4)].get_center()
    verificar(
        abs(p45[0] - p54[0]) + abs(p45[1] - p54[1]) > 0.05,
        "setas 4->5 e 5->4 estão sobrepostas",
    )
    p57 = grafo.setas[(5, 7)].get_center()
    p75 = grafo.setas[(7, 5)].get_center()
    verificar(
        abs(p57[0] - p75[0]) + abs(p57[1] - p75[1]) > 0.05,
        "setas 5->7 e 7->5 estão sobrepostas",
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    testes = [
        ("golden", testar_golden),
        ("invariantes", testar_invariantes),
        ("determinismo", testar_determinismo),
        ("linha a linha", testar_detalhado),
        ("abas", testar_abas),
        ("layout", testar_layout),
    ]
    falhas = 0
    for nome, fn in testes:
        try:
            fn()
        except Falha as exc:
            falhas += 1
            print(f"{VERMELHO}FALHOU{RESET} {nome}: {exc}")
        else:
            print(f"{VERDE}ok{RESET}     {nome}")

    if falhas:
        print(f"\n{falhas} teste(s) falharam.")
        return 1
    print("\nTodos os testes de estado passaram (sem Manim).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
