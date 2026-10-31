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
    ("aresta", 1, 2, "aceita"),
    ("aresta", 0, 1, "aceita"),
    ("aresta", 3, 4, "aceita"),
    ("aresta", 2, 4, "aceita"),
    ("aresta", 0, 2, "rejeitada"),
    ("aresta", 3, 5, "aceita"),
    ("fim", None, None, None),
]

GOLDEN_LAZY = [
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

GOLDEN_EAGER = [
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


def testar_golden() -> None:
    kruskal = rec.coletar("kruskal")
    lazy = rec.coletar("lazy")
    eager = rec.coletar("eager")

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

    # Resultado final de cada algoritmo.
    verificar(kruskal[-1].estado["mst"] == [(1, 2, 1), (0, 1, 2), (3, 4, 2), (2, 4, 3), (3, 5, 5)],
              f"MST Kruskal inesperada: {kruskal[-1].estado['mst']}")
    verificar(abs(kruskal[-1].estado["custo"] - 13) < 1e-9, "custo Kruskal != 13")
    verificar(kruskal[-1].estado["fila"] == [(4, 5, 6), (1, 3, 7)],
              f"fila final Kruskal inesperada: {kruskal[-1].estado['fila']}")

    verificar(lazy[-1].estado["mst"] == [(0, 1, 2), (1, 2, 1), (2, 4, 3), (3, 4, 2), (3, 5, 5)],
              f"MST Prim Lazy inesperada: {lazy[-1].estado['mst']}")
    verificar(abs(lazy[-1].estado["custo"] - 13) < 1e-9, "custo Prim Lazy != 13")
    verificar(lazy[-1].estado["fila"] == [], "fila final do Prim Lazy não está vazia")

    edge_to = eager[-1].estado["edgeTo"]
    esperado_edge_to = [None, (0, 1, 2), (1, 2, 1), (3, 4, 2), (2, 4, 3), (3, 5, 5)]
    verificar(edge_to == esperado_edge_to, f"edgeTo final inesperado: {edge_to}")
    verificar(abs(eager[-1].estado["custo"] - 13) < 1e-9, "custo Prim Eager != 13")
    verificar(eager[-1].estado["ipq"] == {}, "IPQ final não está vazia")

    ordem_del_min = [p.destaque[1] for p in eager if p.destaque[3] == "extraido"]
    verificar(ordem_del_min == [0, 1, 2, 4, 3, 5], f"ordem del_min do Eager: {ordem_del_min}")


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
    "eager": {55, 56, 57, 58, 59, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 73},
}


def testar_detalhado() -> None:
    for nome in ("kruskal", "lazy", "eager"):
        compacto = rec.coletar(nome)
        detalhado = rec.coletar_detalhado(nome)
        _, inicio, fim = rec.TRECHOS[nome]

        verificar(
            len(detalhado) > len(compacto),
            f"{nome}: modo detalhado ({len(detalhado)}) não é maior que o compacto ({len(compacto)})",
        )
        for i, passo in enumerate(detalhado):
            verificar(
                inicio <= passo.linha <= fim,
                f"{nome}[{i}]: linha {passo.linha} fora do recorte [{inicio}, {fim}]",
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

        linhas = {p.linha for p in detalhado}
        faltando = LINHAS_OBRIGATORIAS[nome] - linhas
        verificar(not faltando, f"{nome}: linhas nunca destacadas: {sorted(faltando)}")

        # O progresso não pode andar para trás.
        if nome == "kruskal":
            tamanhos = [len(p.estado["mst"]) for p in detalhado]
            verificar(
                all(a <= b for a, b in zip(tamanhos, tamanhos[1:])),
                f"kruskal: |MST| andou para trás: {tamanhos}",
            )
            verificar(tamanhos[-1] == 5, f"kruskal: |MST| final = {tamanhos[-1]}")
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
            verificar(abs(custos[-1] - 13) < 1e-9, f"eager: custo final = {custos[-1]}")


# ---------------------------------------------------------------------------
# e) Painel de código: recorte do arquivo real
# ---------------------------------------------------------------------------


def testar_trechos() -> None:
    esperado = {
        "kruskal": "class KruskalMST",
        "lazy": "def prim",
        "eager": "def prim",
    }
    for nome, marca in esperado.items():
        texto, inicio = rec.trecho_codigo(nome)
        verificar(marca in texto, f"trecho de {nome} não contém {marca!r}")
        verificar(inicio > 0, f"trecho de {nome} sem linha inicial")
        # Toda linha destacada precisa cair dentro do recorte exibido.
        _, ini, fim = rec.TRECHOS[nome]
        for passo in rec.coletar(nome):
            verificar(
                ini <= passo.linha <= fim,
                f"{nome}: linha {passo.linha} fora do recorte [{ini}, {fim}]",
            )


def exportar_stages() -> None:
    """Grava o índice de passos usado na comparação antes/depois (§8.2)."""
    import json

    destino = Path(__file__).resolve().parent / "media_corrigido" / "stages.json"
    destino.parent.mkdir(parents=True, exist_ok=True)

    dados = {}
    for nome in ("kruskal", "lazy", "eager"):
        for sufixo, coletor in (("", rec.coletar), ("_detalhado", rec.coletar_detalhado)):
            dados[nome + sufixo] = [
                {
                    "passo": i,
                    "linha": p.linha,
                    "acao": p.acao,
                    "destaque": list(p.destaque),
                    "pausa": p.pausa,
                    "mst": [list(e) for e in p.estado["mst"]],
                    "custo": p.estado["custo"],
                    "fila": [list(e) for e in p.estado["fila"]],
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
        ("recorte de código", testar_trechos),
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
