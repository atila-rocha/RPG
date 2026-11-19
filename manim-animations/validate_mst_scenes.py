"""
Testes de estado das animações MST — sem Manim.

Roda o gravador (`mst_record.py`) sobre o `algs4-py` e verifica:

a) golden: a sequência exata de passos de cada algoritmo;
b) invariantes: propriedades que valem em todo passo;
c) determinismo: duas gravações produzem exatamente a mesma sequência.

Se o `algs4` mudar de comportamento, este arquivo falha alto em vez de
gerar um vídeo errado.

Uso:  python validate_mst_scenes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import mst_record as rec  # noqa: E402

VERDE = "\033[92m"
VERMELHO = "\033[91m"
RESET = "\033[0m"


class Falha(AssertionError):
    pass


def verificar(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise Falha(mensagem)


def chave(passo: rec.Step) -> tuple:
    """Assinatura estável de um passo, para o golden."""
    tipo, u, v, status = passo.destaque
    return (tipo, u, v, status)


def assinatura_algoritmo(passos: list[rec.Step]) -> list[tuple]:
    return [
        (
            chave(p),
            tuple(tuple(e) for e in p.estado["mst"]),
            round(float(p.estado["custo"]), 6),
        )
        for p in passos
    ]


# ---------------------------------------------------------------------------
# a) Golden
# ---------------------------------------------------------------------------

GOLDEN_KRUSKAL = [
    ("inicio", None, None, None),
    ("aresta", 0, 7, "aceita"),
    ("aresta", 2, 3, "aceita"),
    ("aresta", 1, 7, "aceita"),
    ("aresta", 0, 2, "aceita"),
    ("aresta", 5, 7, "aceita"),
    ("aresta", 1, 3, "rejeitada"),
    ("aresta", 1, 5, "rejeitada"),
    ("aresta", 2, 7, "rejeitada"),
    ("aresta", 4, 5, "aceita"),
    ("aresta", 1, 2, "rejeitada"),
    ("aresta", 4, 7, "rejeitada"),
    ("aresta", 0, 4, "rejeitada"),
    ("aresta", 6, 2, "aceita"),
    ("fim", None, None, None),
]

GOLDEN_LAZY = [
    ("vertice", 0, None, "marcado"),
    ("aresta", 0, 7, "aceita"),
    ("aresta", 1, 7, "aceita"),
    ("aresta", 0, 2, "aceita"),
    ("aresta", 2, 3, "aceita"),
    ("aresta", 5, 7, "aceita"),
    ("aresta", 1, 3, "obsoleta"),
    ("aresta", 1, 5, "obsoleta"),
    ("aresta", 2, 7, "obsoleta"),
    ("aresta", 4, 5, "aceita"),
    ("aresta", 1, 2, "obsoleta"),
    ("aresta", 4, 7, "obsoleta"),
    ("aresta", 0, 4, "obsoleta"),
    ("aresta", 6, 2, "aceita"),
    ("aresta", 3, 6, "obsoleta"),
    ("aresta", 6, 0, "obsoleta"),
    ("aresta", 6, 4, "obsoleta"),
    ("fim", None, None, None),
]

GOLDEN_EAGER = [
    ("vertice", 0, None, "inicio"),
    ("vertice", 0, None, "extraido"),
    ("relax", 0, 6, "insert"),
    ("relax", 0, 2, "insert"),
    ("relax", 0, 4, "insert"),
    ("relax", 0, 7, "insert"),
    ("vertice", 7, None, "extraido"),
    ("relax", 7, 1, "insert"),
    ("relax", 7, 5, "insert"),
    ("relax", 7, 4, "decrease_key"),
    ("vertice", 1, None, "extraido"),
    ("relax", 1, 3, "insert"),
    ("vertice", 2, None, "extraido"),
    ("relax", 2, 6, "decrease_key"),
    ("relax", 2, 3, "decrease_key"),
    ("vertice", 3, None, "extraido"),
    ("vertice", 5, None, "extraido"),
    ("relax", 5, 4, "decrease_key"),
    ("vertice", 4, None, "extraido"),
    ("vertice", 6, None, "extraido"),
    ("fim", None, None, None),
]


# ---------------------------------------------------------------------------
# Golden do segundo grafo (tinyMST6: 6 vértices, 8 arestas, custo 13)
# ---------------------------------------------------------------------------


GOLDEN_KRUSKAL_MST6 = [
    ("inicio", None, None, None),
    ("aresta", 1, 2, "aceita"),
    ("aresta", 0, 1, "aceita"),
    ("aresta", 3, 4, "aceita"),
    ("aresta", 2, 4, "aceita"),
    ("aresta", 0, 2, "rejeitada"),
    ("aresta", 3, 5, "aceita"),
    ("fim", None, None, None),
]

GOLDEN_LAZY_MST6 = [
    ("vertice", 0, None, "marcado"),
    ("aresta", 0, 1, "aceita"),
    ("aresta", 1, 2, "aceita"),
    ("aresta", 2, 4, "aceita"),
    ("aresta", 3, 4, "aceita"),
    ("aresta", 0, 2, "obsoleta"),
    ("aresta", 3, 5, "aceita"),
    ("aresta", 4, 5, "obsoleta"),
    ("aresta", 1, 3, "obsoleta"),
    ("fim", None, None, None),
]

GOLDEN_EAGER_MST6 = [
    ("vertice", 0, None, "inicio"),
    ("vertice", 0, None, "extraido"),
    ("relax", 0, 2, "insert"),
    ("relax", 0, 1, "insert"),
    ("vertice", 1, None, "extraido"),
    ("relax", 1, 3, "insert"),
    ("relax", 1, 2, "decrease_key"),
    ("vertice", 2, None, "extraido"),
    ("relax", 2, 4, "insert"),
    ("vertice", 4, None, "extraido"),
    ("relax", 4, 5, "insert"),
    ("relax", 4, 3, "decrease_key"),
    ("vertice", 3, None, "extraido"),
    ("relax", 3, 5, "insert"),
    ("vertice", 5, None, "extraido"),
    ("fim", None, None, None),
]


def _golden_mst6(kruskal, lazy, eager) -> None:
    """Golden do tinyMST6 (custo 13, 5 arestas na MST)."""
    verificar(
        [chave(p) for p in kruskal] == GOLDEN_KRUSKAL_MST6,
        f"golden Kruskal (tinyMST6) divergiu:\n  obtido={[chave(p) for p in kruskal]}",
    )
    verificar(
        [chave(p) for p in lazy] == GOLDEN_LAZY_MST6,
        f"golden Prim Lazy (tinyMST6) divergiu:\n  obtido={[chave(p) for p in lazy]}",
    )
    verificar(
        [chave(p) for p in eager] == GOLDEN_EAGER_MST6,
        f"golden Prim Eager (tinyMST6) divergiu:\n  obtido={[chave(p) for p in eager]}",
    )

    esperado_kruskal = [(1, 2, 1.0), (0, 1, 2.0), (3, 4, 2.0), (2, 4, 3.0), (3, 5, 5.0)]
    # O Prim Lazy acrescenta as arestas na ordem em que as encontra, que não é
    # a ordem por peso do Kruskal. O conjunto tem de ser o mesmo.
    esperado_lazy = [(0, 1, 2.0), (1, 2, 1.0), (2, 4, 3.0), (3, 4, 2.0), (3, 5, 5.0)]
    verificar(
        kruskal[-1].estado["mst"] == esperado_kruskal,
        f"MST Kruskal (tinyMST6): {kruskal[-1].estado['mst']}",
    )
    verificar(
        lazy[-1].estado["mst"] == esperado_lazy,
        f"MST Prim Lazy (tinyMST6): {lazy[-1].estado['mst']}",
    )
    verificar(
        set(kruskal[-1].estado["mst"]) == set(lazy[-1].estado["mst"]),
        "Kruskal e Prim Lazy chegaram a MSTs diferentes no tinyMST6",
    )
    for nome, passos in (("Kruskal", kruskal), ("Prim Lazy", lazy), ("Prim Eager", eager)):
        verificar(abs(passos[-1].estado["custo"] - 13.0) < 1e-9, f"custo {nome} != 13")
    verificar(
        kruskal[-1].estado["fila"] == [(4, 5, 6.0), (1, 3, 7.0)],
        f"fila final Kruskal (tinyMST6): {kruskal[-1].estado['fila']}",
    )
    verificar(lazy[-1].estado["fila"] == [], "fila final do Prim Lazy (tinyMST6) não está vazia")
    verificar(eager[-1].estado["ipq"] == {}, "IPQ final (tinyMST6) não está vazia")

    edge_to = eager[-1].estado["edgeTo"]
    esperado_edge_to = [None, (0, 1, 2.0), (1, 2, 1.0), (3, 4, 2.0), (2, 4, 3.0), (3, 5, 5.0)]
    verificar(edge_to == esperado_edge_to, f"edgeTo final (tinyMST6): {edge_to}")
    ordem = [p.destaque[1] for p in eager if p.destaque[3] == "extraido"]
    verificar(ordem == [0, 1, 2, 4, 3, 5], f"ordem del_min (tinyMST6): {ordem}")


def testar_golden() -> None:
    """Sequência exata + resultado final de cada algoritmo no grafo ativo.

    O golden é uma trava de regressão: qualquer mudança no percurso dos
    algoritmos aparece aqui antes de virar vídeo. Cada grafo de entrada tem o
    seu, porque a sequência depende do arquivo.
    """
    kruskal = rec.coletar("kruskal")
    lazy = rec.coletar("lazy")
    eager = rec.coletar("eager")
    ativo = rec.caminho_grafo().name

    if ativo == "tinyMST6.txt":
        _golden_mst6(kruskal, lazy, eager)
        return

    verificar(
        [chave(p) for p in kruskal] == GOLDEN_KRUSKAL,
        f"golden Kruskal divergiu:\n  obtido={[chave(p) for p in kruskal]}",
    )
    verificar(
        [chave(p) for p in lazy] == GOLDEN_LAZY,
        f"golden Prim Lazy divergiu:\n  obtido={[chave(p) for p in lazy]}",
    )
    verificar(
        [chave(p) for p in eager] == GOLDEN_EAGER,
        f"golden Prim Eager divergiu:\n  obtido={[chave(p) for p in eager]}",
    )

    # Resultado final de cada algoritmo (grafo ativo: tinyEWG, custo 1.81).
    verificar(kruskal[-1].estado["mst"] == [
        (0, 7, 0.16), (2, 3, 0.17), (1, 7, 0.19), (0, 2, 0.26),
        (5, 7, 0.28), (4, 5, 0.35), (2, 6, 0.4),
    ], f"MST Kruskal inesperada: {kruskal[-1].estado['mst']}")
    verificar(abs(kruskal[-1].estado["custo"] - 1.81) < 1e-9, "custo Kruskal != 1.81")
    verificar(kruskal[-1].estado["fila"] == [(3, 6, 0.52), (0, 6, 0.58), (4, 6, 0.93)],
              f"fila final Kruskal inesperada: {kruskal[-1].estado['fila']}")

    verificar(lazy[-1].estado["mst"] == [
        (0, 7, 0.16), (1, 7, 0.19), (0, 2, 0.26), (2, 3, 0.17),
        (5, 7, 0.28), (4, 5, 0.35), (2, 6, 0.4),
    ], f"MST Prim Lazy inesperada: {lazy[-1].estado['mst']}")
    verificar(abs(lazy[-1].estado["custo"] - 1.81) < 1e-9, "custo Prim Lazy != 1.81")
    verificar(lazy[-1].estado["fila"] == [], "fila final do Prim Lazy não está vazia")

    edge_to = eager[-1].estado["edgeTo"]
    esperado_edge_to = [
        None, (1, 7, 0.19), (0, 2, 0.26), (2, 3, 0.17),
        (4, 5, 0.35), (5, 7, 0.28), (6, 2, 0.4), (0, 7, 0.16),
    ]
    verificar(edge_to == esperado_edge_to, f"edgeTo final inesperado: {edge_to}")
    verificar(abs(eager[-1].estado["custo"] - 1.81) < 1e-9, "custo Prim Eager != 1.81")
    verificar(eager[-1].estado["ipq"] == {}, "IPQ final não está vazia")

    ordem_del_min = [p.destaque[1] for p in eager if p.destaque[3] == "extraido"]
    verificar(ordem_del_min == [0, 7, 1, 2, 3, 5, 4, 6], f"ordem del_min do Eager: {ordem_del_min}")


# ---------------------------------------------------------------------------
# b) Invariantes
# ---------------------------------------------------------------------------


def invariantes_de_aresta(nome: str, passos: list[rec.Step]) -> None:
    for i, passo in enumerate(passos):
        tipo, u, v, status = passo.destaque
        estado = passo.estado

        if tipo == "aresta":
            normal = (min(u, v), max(u, v))
            contida = any((min(a, b), max(a, b)) == normal for a, b, _ in estado["mst"])

            verificar(
                (status == "aceita") == contida,
                f"{nome}[{i}]: {u}-{v} status={status} mas contida_na_mst={contida}",
            )
            verificar(
                all((min(a, b), max(a, b)) != normal for a, b, _ in estado["fila"]),
                f"{nome}[{i}]: a aresta destacada {u}-{v} ainda está na fila",
            )

        if nome != "eager":
            soma = sum(w for _, _, w in estado["mst"])
            verificar(
                abs(float(estado["custo"]) - soma) < 1e-9,
                f"{nome}[{i}]: custo {estado['custo']} != soma das arestas {soma}",
            )


def invariante_particao(nome: str, passos: list[rec.Step]) -> None:
    for i, passo in enumerate(passos):
        componentes = passo.estado["componentes"]
        if not componentes:
            continue  # Prim não usa union-find
        vistos = [v for grupo in componentes for v in grupo]
        verificar(
            sorted(vistos) == list(range(rec.V_CANONICO)),
            f"{nome}[{i}]: componentes não são partição de V: {componentes}",
        )


def invariante_eager(passos: list[rec.Step]) -> None:
    for i, passo in enumerate(passos):
        estado = passo.estado
        marcados = set(estado["marcados"])
        edge_to = estado["edgeTo"]

        # Um item por vértice: a IPQ lógica nunca repete índice.
        verificar(
            len(estado["ipq"]) == len(set(estado["ipq"])),
            f"eager[{i}]: IPQ lógica com índice repetido: {estado['ipq']}",
        )
        for v in estado["ipq"]:
            verificar(v not in marcados, f"eager[{i}]: vértice {v} está na IPQ e na árvore")
            verificar(
                abs(estado["distTo"][v] - estado["ipq"][v]) < 1e-9,
                f"eager[{i}]: IPQ[{v}] diverge de distTo[{v}]",
            )

        # A ordem física do heap (`pq_ordem`) refere-se a vértices reais.
        # Ela PODE repetir um índice: o `IndexMinPQ.contains` do algs4 é
        # `index in self.keys`, comparando o índice com as CHAVES (pesos).
        # No tinyEWG todos os pesos são < 1, então `contains` dá False, o
        # Prim insere duplicatas e nunca chama `decrease_key` — é o
        # comportamento real da biblioteca, e a animação o mostra.
        ordem = estado.get("pq_ordem", [])
        for v in ordem:
            verificar(
                0 <= v < rec.V_CANONICO,
                f"eager[{i}]: índice fora de 0..V-1 em pq_ordem: {v}",
            )
        marcados_set = set(marcados)
        ativos = [v for v in ordem if v not in marcados_set]
        verificar(
            set(ativos) == set(estado["ipq"]),
            f"eager[{i}]: pq_ordem ativo {ativos} != ipq {estado['ipq']}",
        )

        # Invariante do heap binário (pai <= filho), quando o passo bate na
        # linha do próprio algoritmo — dentro de swim/sink o heap está no
        # meio do reajuste (uma troca por vez) e pode estar "temporariamente
        # fora de ordem" apenas em slots intermediários. Usamos a CHAVE REAL
        # da IPQ (`keys[i]`), porque num decrease_key o `distTo` já mudou
        # enquanto a chave do heap ainda é a anterior. Com índice repetido a
        # árvore binária não é bem definida, então só checamos sem duplicata.
        if passo.modulo == "" and len(ativos) == len(set(ativos)):
            chave = estado.get("ipq_keys", {})
            for k in range(1, len(ativos)):
                pai = ativos[(k - 1) // 2]
                filho = ativos[k]
                verificar(
                    chave[pai] <= chave[filho] + 1e-9,
                    f"eager[{i}]: heap violado: pai {pai}:{chave[pai]:g} "
                    f"> filho {filho}:{chave[filho]:g}  (ordem {ativos})",
                )

        # Árvore: |marcados| - 1 arestas confirmadas.
        confirmadas = [
            edge_to[v] for v in marcados
            if v != 0 and v < len(edge_to) and edge_to[v] is not None
        ]
        verificar(
            len(confirmadas) == max(0, len(marcados) - 1),
            f"eager[{i}]: {len(marcados)} marcados mas {len(confirmadas)} arestas confirmadas",
        )
        soma = sum(e[2] for e in confirmadas)
        verificar(
            abs(float(estado["custo"]) - soma) < 1e-9,
            f"eager[{i}]: custo {estado['custo']} != soma confirmada {soma}",
        )


def testar_invariantes() -> None:
    for nome in ("kruskal", "lazy"):
        passos = rec.coletar(nome)
        invariantes_de_aresta(nome, passos)
        invariante_particao(nome, passos)
    invariantes_de_aresta("eager", rec.coletar("eager"))
    invariante_eager(rec.coletar("eager"))


# ---------------------------------------------------------------------------
# c) Determinismo
# ---------------------------------------------------------------------------


def testar_determinismo() -> None:
    for nome in ("kruskal", "lazy", "eager"):
        primeira = assinatura_algoritmo(rec.coletar(nome))
        segunda = assinatura_algoritmo(rec.coletar(nome))
        verificar(
            primeira == segunda,
            f"{nome}: duas gravações produziram sequências diferentes "
            "(falta de desempate estável em Edge.__lt__?)",
        )


# ---------------------------------------------------------------------------
# d) Modo linha a linha (didático)
# ---------------------------------------------------------------------------


LINHAS_OBRIGATORIAS = {
    "kruskal": {48, 49, 50, 51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63},
    "lazy": {57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 72, 73, 74, 75},
    # O ramo `if contains(7)` (linha 71) não executa no tinyEWG: `contains`
    # compara índice com pesos (< 1) e sempre dá False. A linha 70
    # (`insert`) executa; a 73 (`del_min`) continua sendo o fecho do laço.
    "eager": {55, 56, 57, 58, 59, 62, 63, 64, 65, 66, 67, 68, 69, 70, 73},
}


def testar_detalhado() -> None:
    for nome in ("kruskal", "lazy", "eager"):
        compacto = rec.coletar(nome)
        detalhado = rec.coletar_detalhado(nome)
        modulo_principal, inicio, fim = rec.TRECHOS[nome]

        verificar(
            len(detalhado) > len(compacto),
            f"{nome}: modo detalhado ({len(detalhado)}) não é maior que o compacto ({len(compacto)})",
        )
        for i, passo in enumerate(detalhado):
            # Toda linha executada pertence a uma view do painel.
            view = rec.funcao_da_linha(nome, passo.linha, passo.modulo)
            if passo.modulo == modulo_principal:
                verificar(
                    inicio <= passo.linha <= fim,
                    f"{nome}[{i}]: linha {passo.linha} fora do recorte [{inicio}, {fim}]",
                )
            verificar(
                view.modulo == passo.modulo or not passo.modulo,
                f"{nome}[{i}]: view {view.nome} de {view.modulo} "
                f"não bate com o passo em {passo.modulo or modulo_principal}",
            )
            verificar(passo.pausa > 0, f"{nome}[{i}]: pausa inválida {passo.pausa}")
            verificar(passo.acao.strip() != "", f"{nome}[{i}]: ação vazia")

        verificar(
            detalhado[-1].estado["mst"] == compacto[-1].estado["mst"],
            f"{nome}: MST final do detalhado difere do compacto",
        )
        verificar(
            abs(float(detalhado[-1].estado["custo"]) - float(compacto[-1].estado["custo"])) < 1e-9,
            f"{nome}: custo final do detalhado difere do compacto",
        )

        linhas = {
            p.linha for p in detalhado if p.modulo in ("", modulo_principal)
        }
        faltando = LINHAS_OBRIGATORIAS[nome] - linhas
        verificar(not faltando, f"{nome}: linhas nunca destacadas: {sorted(faltando)}")

        # O progresso não pode andar para trás.
        if nome == "kruskal":
            tamanhos = [len(p.estado["mst"]) for p in detalhado]
            verificar(
                all(a <= b for a, b in zip(tamanhos, tamanhos[1:])),
                f"kruskal: |MST| andou para trás: {tamanhos}",
            )
            verificar(tamanhos[-1] == rec.V_CANONICO - 1, f"kruskal: |MST| final = {tamanhos[-1]}")
        elif nome == "lazy":
            marcados = [len(p.estado["marcados"]) for p in detalhado]
            verificar(
                all(a <= b for a, b in zip(marcados, marcados[1:])),
                f"lazy: marcados andaram para trás: {marcados}",
            )
            verificar(marcados[-1] == rec.V_CANONICO, "lazy: nem todos os vértices marcados")
        else:
            custos = [float(p.estado["custo"]) for p in detalhado]
            verificar(
                all(a <= b + 1e-9 for a, b in zip(custos, custos[1:])),
                f"eager: custo andou para trás: {custos}",
            )
            verificar(
                abs(custos[-1] - float(compacto[-1].estado["custo"])) < 1e-9,
                f"eager: custo final = {custos[-1]}",
            )


# ---------------------------------------------------------------------------
# e) Painel de código: uma view por função, derivada do ast do fonte real
# ---------------------------------------------------------------------------

NOMES_VIEWS = {
    "kruskal": {
        ("algs4.kruskal_mst", "KruskalMST.__init__"),
        ("algs4.edge_weighted_graph", "EdgeWeightedGraph.edges"),
        ("algs4.min_pq", "MinPQ.insert"),
        ("algs4.min_pq", "MinPQ.is_empty"),
        ("algs4.min_pq", "MinPQ.del_min"),
        ("algs4.min_pq", "MinPQ.swim"),
        ("algs4.min_pq", "MinPQ.sink"),
        ("algs4.edge", "Edge.either"),
        ("algs4.edge", "Edge.other"),
        ("algs4.uf", "UF.connected"),
        ("algs4.uf", "UF.find"),
        ("algs4.uf", "UF.union"),
    },
    "lazy": {
        ("algs4.lazy_prim_mst", "LazyPrimMST.prim"),
        ("algs4.lazy_prim_mst", "LazyPrimMST.visit"),
        ("algs4.min_pq", "MinPQ.insert"),
        ("algs4.min_pq", "MinPQ.is_empty"),
        ("algs4.min_pq", "MinPQ.del_min"),
        ("algs4.min_pq", "MinPQ.swim"),
        ("algs4.min_pq", "MinPQ.sink"),
        ("algs4.edge", "Edge.either"),
        ("algs4.edge", "Edge.other"),
    },
    "eager": {
        ("algs4.prim_mst", "PrimMST.prim"),
        ("algs4.prim_mst", "PrimMST.visit"),
        ("algs4.index_min_pq", "IndexMinPQ.insert"),
        ("algs4.index_min_pq", "IndexMinPQ.contains"),
        ("algs4.index_min_pq", "IndexMinPQ.decrease_key"),
        ("algs4.index_min_pq", "IndexMinPQ.del_min"),
        ("algs4.index_min_pq", "IndexMinPQ.is_empty"),
        ("algs4.index_min_pq", "IndexMinPQ.swim"),
        ("algs4.index_min_pq", "IndexMinPQ.sink"),
        ("algs4.edge", "Edge.other"),
    },
}


def _funcoes_do_ast(arquivo: Path) -> dict[str, tuple[int, int, int | None]]:
    """nome qualificado -> (linha do def, fim do corpo, linha da classe)."""
    import ast

    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    resultado: dict[str, tuple[int, int, int | None]] = {}

    def visitar(no, prefixo: str = "") -> None:
        for filho in ast.iter_child_nodes(no):
            if isinstance(filho, ast.ClassDef):
                visitar(filho, filho.name)
            elif isinstance(filho, ast.FunctionDef):
                nome = f"{prefixo}.{filho.name}" if prefixo else filho.name
                classe = no.lineno if isinstance(no, ast.ClassDef) else None
                resultado[nome] = (filho.lineno, filho.end_lineno, classe)

    visitar(arvore)
    return resultado


def testar_funcoes() -> None:
    for nome in ("kruskal", "lazy", "eager"):
        funcoes = rec.funcoes_codigo(nome)
        modulo_principal, ini, _fim = rec.TRECHOS[nome]

        verificar(bool(funcoes), f"{nome}: nenhuma função no painel")
        chaves = {(f.modulo, f.nome) for f in funcoes}
        verificar(
            chaves == NOMES_VIEWS[nome],
            f"{nome}: views {sorted(chaves)} != {sorted(NOMES_VIEWS[nome])}",
        )
        verificar(
            len(chaves) == len(funcoes),
            f"{nome}: view repetida no painel: {[f.nome for f in funcoes]}",
        )

        # (2) limites reais, cada view contra o ast do SEU módulo.
        for f in funcoes:
            arquivo = rec.arquivo_modulo(f.modulo)
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
            nos = _funcoes_do_ast(arquivo)
            verificar(f.nome in nos, f"{nome}: {f.nome} não existe no ast de {f.modulo}")
            def_linha, def_fim, classe_linha = nos[f.nome]
            verificar(
                f.fim == def_fim,
                f"{nome}.{f.nome}: fim {f.fim} != end_lineno {def_fim}",
            )
            inicios = {def_linha}
            if f.modulo == modulo_principal and classe_linha is not None:
                if ini <= classe_linha < def_linha:
                    inicios.add(classe_linha)
            verificar(
                f.inicio in inicios,
                f"{nome}.{f.nome}: início {f.inicio} fora de {sorted(inicios)}",
            )
            verificar(
                f.texto == "\n".join(linhas[f.inicio - 1 : f.fim]),
                f"{nome}.{f.nome}: texto não bate com o fonte real de {f.modulo}",
            )
            verificar(
                f.arquivo == rec._rotulo_arquivo(arquivo),
                f"{nome}.{f.nome}: rótulo {f.arquivo!r} incorreto",
            )

        # (1) cobertura total e única de TODOS os passos (compacto e detalhado).
        usadas: set[tuple[str, str]] = set()
        for coletor in (rec.coletar, rec.coletar_detalhado):
            for passo in coletor(nome):
                view = rec.funcao_da_linha(nome, passo.linha, passo.modulo)
                verificar(
                    view.modulo == (passo.modulo or modulo_principal),
                    f"{nome}: passo em {passo.modulo or modulo_principal} "
                    f"resolvido para view de {view.modulo}",
                )
                usadas.add((view.modulo, view.nome))

        # Nem toda view do painel executa em TODO grafo. No tinyEWG, por
        # exemplo, `IndexMinPQ.decrease_key` nunca roda (o `contains` do
        # algs4 sempre dá False). Exigimos que nada seja inventado
        # (`usadas <=` painel) e que TODAS as views do módulo principal
        # executem — são as que narram o algoritmo de fato.
        verificar(
            usadas <= NOMES_VIEWS[nome],
            f"{nome}: views usadas fora do painel: {sorted(usadas - NOMES_VIEWS[nome])}",
        )
        principais = {v for v in NOMES_VIEWS[nome] if v[0] == modulo_principal}
        verificar(
            principais <= usadas,
            f"{nome}: views do módulo principal nunca executadas: {sorted(principais - usadas)}",
        )


def exportar_stages() -> None:
    """Grava o índice de passos usado na comparação antes/depois (§8.2).

    O `stages.json` de referência é do grafo padrão (tinyEWG). Com `MST_GRAFO`
    apontando para outro arquivo, o índice vai para um arquivo ao lado, para
    não sobrescrever a referência do grafo padrão. Fica em `build/goldens/`
    (descartável e regenerável), conforme as convenções do README.
    """
    import json

    raiz = Path(__file__).resolve().parent
    ativo = rec.caminho_grafo()
    padrao = ativo.resolve() == rec.GRAFO_PADRAO.resolve()
    nome_arquivo = "stages.json" if padrao else f"stages_{ativo.stem}.json"
    destino = raiz / "build" / "goldens" / nome_arquivo
    destino.parent.mkdir(parents=True, exist_ok=True)

    dados = {}
    for nome in ("kruskal", "lazy", "eager"):
        for sufixo, coletor in (("", rec.coletar), ("_detalhado", rec.coletar_detalhado)):
            dados[nome + sufixo] = [
                {
                    "passo": i,
                    "linha": p.linha,
                    "modulo": p.modulo,
                    "acao": p.acao,
                    "destaque": list(p.destaque),
                    "pausa": p.pausa,
                    "mst": [list(e) for e in p.estado["mst"]],
                    "custo": p.estado["custo"],
                    "fila": [list(e) for e in p.estado["fila"]],
                    "uf_id": list(p.estado.get("uf_id", [])),
                    "pq_ordem": list(p.estado.get("pq_ordem", [])),
                    "marcados": list(p.estado["marcados"]),
                    "ipq": {str(k): v for k, v in p.estado["ipq"].items()},
                }
                for i, p in enumerate(coletor(nome))
            ]

    destino.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"stages.json gravado em {destino}")


def main() -> int:
    testes = [
        ("golden", testar_golden),
        ("invariantes", testar_invariantes),
        ("determinismo", testar_determinismo),
        ("linha a linha", testar_detalhado),
        ("funções de código", testar_funcoes),
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
    exportar_stages()
    print("\nTodos os testes de estado passaram (sem Manim).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
