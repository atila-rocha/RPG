"""
Gravador das execuções reais do `algs4-py`.

Este módulo **não implementa** Kruskal nem Prim. Ele roda a implementação
original do `algs4` sob `sys.settrace` e converte os eventos de linha
observados em uma lista de `Step` (estado + ação + destaque).

Consequências:
- existe uma única fonte da verdade (o `algs4-py`);
- o número de linha do destaque é o `frame.f_lineno` real;
- o painel mostra `frame.f_locals` real, não um snapshot digitado à mão.

Decisão registrada no plano: gravamos o `algs4` exatamente como está,
inclusive o comportamento de `IndexMinPQ.contains`. O painel da IPQ é
derivado de `distTo`/`marked` (um item por vértice), então a tela nunca
exibe entradas repetidas do heap.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Dependência: algs4-py é um diretório irmão, sem pyproject.toml.
# ---------------------------------------------------------------------------

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
DIR_ALGS4 = RAIZ_PROJETO / "algs4-py"


def _garantir_algs4() -> None:
    """Torna o `algs4-py` importável sem instalá-lo no venv."""
    if "algs4" in sys.modules:
        return
    try:  # caso algum dia vire dependência de caminho no pyproject
        import algs4  # noqa: F401
        return
    except ModuleNotFoundError:
        pass
    if (DIR_ALGS4 / "algs4").is_dir():
        sys.path.insert(0, str(DIR_ALGS4))
    import algs4  # noqa: F401


_garantir_algs4()

from algs4.edge import Edge  # noqa: E402
from algs4.edge_weighted_graph import EdgeWeightedGraph  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture canônico (grafo único dos três vídeos)
# ---------------------------------------------------------------------------

V_CANONICO = 6

# A ORDEM importa: `Edge.__lt__` compara somente o peso, então arestas de
# mesmo peso (0-1 e 3-4) são desempatadas pela ordem de inserção no heap.
# Alterar esta lista muda o roteiro do vídeo.
ARESTAS_CANONICAS: tuple[tuple[int, int, float], ...] = (
    (1, 2, 1.0),
    (0, 1, 2.0),
    (3, 4, 2.0),
    (2, 4, 3.0),
    (0, 2, 4.0),
    (3, 5, 5.0),
    (4, 5, 6.0),
    (1, 3, 7.0),
)


def grafo_canonico() -> EdgeWeightedGraph:
    g = EdgeWeightedGraph(V_CANONICO)
    for u, v, peso in ARESTAS_CANONICAS:
        g.add_edge(Edge(u, v, peso))
    return g


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Step:
    """Um passo observado da execução real.

    linha   -- número de linha do arquivo do algs4 (vem do trace)
    acao    -- frase curta para o painel
    destaque-- ("inicio"|"aresta"|"vertice"|"relax"|"fim", u, v, status)
    estado  -- dicionário com fila/mst/custo/marcados/componentes/distTo/edgeTo/ipq
    """

    linha: int
    acao: str
    destaque: tuple
    estado: dict
    # Tempo de pausa depois da animação deste passo (segundos). Os passos
    # "linha a linha" usam pausas maiores nas decisões e menores no
    # bookkeeping do laço; o modo compacto mantém o ritmo antigo.
    pausa: float = 0.9


# ---------------------------------------------------------------------------
# Captura
# ---------------------------------------------------------------------------


def _aresta(e: Any) -> tuple[int, int, float] | None:
    if e is None:
        return None
    return (int(e.v), int(e.w), float(e.weight))


def _instantanea_self(obj: Any) -> dict:
    """Copia o estado mutável do objeto do algs4 naquele instante."""
    if obj is None:
        return {}

    d: dict[str, Any] = {}

    if hasattr(obj, "weight"):
        d["weight"] = obj.weight

    mst = getattr(obj, "mst", None)
    if mst is not None:
        d["mst"] = [_aresta(e) for e in mst]

    for nome in ("marked", "distTo"):
        valor = getattr(obj, nome, None)
        if valor is not None:
            d[nome] = list(valor)

    edge_to = getattr(obj, "edgeTo", None)
    if edge_to is not None:
        d["edgeTo"] = [_aresta(e) for e in edge_to]

    pq = getattr(obj, "pq", None)
    if pq is not None:
        interno = list(getattr(pq, "pq", []))
        # MinPQ guarda arestas; IndexMinPQ guarda índices de vértice.
        d["pq"] = interno if (interno and isinstance(interno[0], int)) else [_aresta(e) for e in interno]

    return d


def _gravar(nome_modulo: str, executar: Callable[[], Any]) -> tuple[Any, list[dict]]:
    """Roda `executar()` observando as linhas do módulo do algs4 indicado."""
    modulo = sys.modules[nome_modulo]
    alvo = os.path.normcase(os.path.abspath(modulo.__file__))
    eventos: list[dict] = []

    def trace(frame, event, arg):
        if os.path.normcase(os.path.abspath(frame.f_code.co_filename)) != alvo:
            return None

        def local(frame, event, arg):
            if event == "line":
                loc = frame.f_locals
                eventos.append(
                    {
                        "lineno": frame.f_lineno,
                        "self": _instantanea_self(loc.get("self")),
                        "e": _aresta(loc.get("e")),
                        "v": loc.get("v"),
                        "w": loc.get("w"),
                        "s": loc.get("s"),
                        "uf": list(loc["uf"].id) if "uf" in loc else None,
                    }
                )
            return local

        return local

    sys.settrace(trace)
    try:
        resultado = executar()
    finally:
        sys.settrace(None)

    return resultado, eventos


# ---------------------------------------------------------------------------
# Estado derivado (somente leitura dos snapshots)
# ---------------------------------------------------------------------------


def _componentes(ids: list[int] | None) -> list[list[int]]:
    """Partição induzida pelo vetor `id` do union-find."""
    if ids is None:
        return []
    raizes = []
    for p in range(len(ids)):
        q = p
        while ids[q] != q:
            q = ids[q]
        raizes.append(q)
    grupos: dict[int, list[int]] = {}
    for vertice, raiz in enumerate(raizes):
        grupos.setdefault(raiz, []).append(vertice)
    return sorted(grupos.values(), key=lambda g: g[0])


def _normalizar(aresta: tuple[int, int, float]) -> tuple[int, int, float]:
    u, v, w = aresta
    return (min(u, v), max(u, v), w)


def _estado_base(snap: dict) -> dict:
    dados = snap["self"]
    mst = [_normalizar(e) for e in dados.get("mst", [])]
    marcados = [i for i, m in enumerate(dados.get("marked", [])) if m]
    return {
        "mst": mst,
        "custo": dados.get("weight", 0),
        "marcados": marcados,
        "fila": [],
        "componentes": _componentes(snap.get("uf")),
        "distTo": list(dados.get("distTo", [])),
        "edgeTo": list(dados.get("edgeTo", [])),
        "ipq": {},
    }


def _estado_kruskal(snap: dict) -> dict:
    est = _estado_base(snap)
    fila = [_normalizar(e) for e in snap["self"].get("pq", [])]
    est["fila"] = sorted(fila, key=lambda e: (e[2], e[0], e[1]))
    return est


def _estado_lazy(snap: dict) -> dict:
    est = _estado_base(snap)
    fila = [_normalizar(e) for e in snap["self"].get("pq", [])]
    est["fila"] = sorted(fila, key=lambda e: (e[2], e[0], e[1]))
    return est


def _estado_eager(snap: dict) -> dict:
    est = _estado_base(snap)
    dados = snap["self"]
    marcados = list(dados.get("marked", []))
    dist = list(dados.get("distTo", []))
    edge_to = list(dados.get("edgeTo", []))

    est["marcados"] = [i for i, m in enumerate(marcados) if m]
    est["distTo"] = dist
    est["edgeTo"] = edge_to
    # Estado da IPQ: usamos os índices que estão de fato no heap (`pq.pq`).
    # Derivar só de `distTo`/`marked` mostraria um vértice na IPQ entre
    # `distTo[s] = 0` e `insert(s, 0)`, quando ele ainda não foi inserido.
    indices = dados.get("pq")
    if indices is not None and all(isinstance(i, int) for i in indices):
        est["ipq"] = {
            v: dist[v]
            for v in sorted(set(indices))
            if v < len(dist) and not marcados[v]
        }
    else:
        # Fallback (snapshot sem o heap): um item por vértice não marcado.
        est["ipq"] = {
            v: dist[v]
            for v in range(len(dist))
            if not marcados[v] and dist[v] != float("inf")
        }
    # Custo confirmado: soma das arestas que efetivamente entraram na árvore.
    est["custo"] = float(
        sum(
            edge_to[v][2]
            for v in est["marcados"]
            if v != 0 and v < len(edge_to) and edge_to[v] is not None
        )
    )
    return est


# ---------------------------------------------------------------------------
# Roteiros
# ---------------------------------------------------------------------------

# (módulo, primeira linha, última linha) do trecho exibido na tela.
TRECHOS: dict[str, tuple[str, int, int]] = {
    "kruskal": ("algs4.kruskal_mst", 46, 63),
    "lazy": ("algs4.lazy_prim_mst", 56, 75),
    "eager": ("algs4.prim_mst", 54, 73),
}


def _primeiro(eventos: list[dict], linha: int, inicio: int = 0) -> int:
    for i in range(inicio, len(eventos)):
        if eventos[i]["lineno"] == linha:
            return i
    raise LookupError(f"linha {linha} não apareceu no trace")


def _proximo(eventos: list[dict], linhas: tuple[int, ...], inicio: int) -> int:
    for i in range(inicio, len(eventos)):
        if eventos[i]["lineno"] in linhas:
            return i
    raise LookupError(f"nenhuma das linhas {linhas} apareceu após o evento {inicio}")


def passos_kruskal() -> list[Step]:
    from algs4.kruskal_mst import KruskalMST

    _, eventos = _gravar("algs4.kruskal_mst", lambda: KruskalMST(grafo_canonico()))

    estado_inicial = _estado_kruskal(eventos[_primeiro(eventos, 55)])
    u0, v0, _w0 = estado_inicial["fila"][0]
    passos = [
        Step(
            linha=55,
            acao=f"Kruskal não tem raiz: começa pela menor aresta ({u0}-{v0})",
            destaque=("inicio", None, None, None),
            estado=estado_inicial,
        )
    ]

    for i, ev in enumerate(eventos):
        if ev["lineno"] != 57:  # `v = e.either()` -> del_min já executou
            continue

        aresta = ev["e"]
        if aresta is None:
            continue
        u, v, w = aresta

        decisao = _proximo(eventos, (60, 61), i)
        aceita = eventos[decisao]["lineno"] == 61

        fim = _proximo(eventos, (55,), decisao)
        estado = _estado_kruskal(eventos[fim])

        passos.append(
            Step(
                linha=62 if aceita else 60,
                acao=(
                    f"Aceita {u}-{v} ({w:g}): uf.union, MST com {len(estado['mst'])} arestas"
                    if aceita
                    else f"Descarta {u}-{v} ({w:g}): uf.connected -> ciclo"
                ),
                destaque=("aresta", u, v, "aceita" if aceita else "rejeitada"),
                estado=estado,
            )
        )

    passos.append(
        Step(
            linha=55,
            acao="MST concluída",
            destaque=("fim", None, None, None),
            estado=_estado_kruskal(eventos[-1]),
        )
    )
    return passos


def passos_lazy() -> list[Step]:
    from algs4.lazy_prim_mst import LazyPrimMST

    _, eventos = _gravar("algs4.lazy_prim_mst", lambda: LazyPrimMST(grafo_canonico()))

    passos = [
        Step(
            linha=57,
            acao="visit(0): marca a raiz e insere as arestas do corte",
            destaque=("vertice", 0, None, "marcado"),
            estado=_estado_lazy(eventos[_primeiro(eventos, 58)]),
        )
    ]

    for i, ev in enumerate(eventos):
        if ev["lineno"] != 60:  # `v = e.either()` -> del_min já executou
            continue

        aresta = ev["e"]
        if aresta is None:
            continue
        u, v, w = aresta

        decisao = _proximo(eventos, (63, 64), i)
        obsoleta = eventos[decisao]["lineno"] == 63

        fim = _proximo(eventos, (58,), decisao)
        estado = _estado_lazy(eventos[fim])

        passos.append(
            Step(
                linha=63 if obsoleta else 64,
                acao=(
                    f"Descarta {u}-{v} ({w:g}): ambos marcados -> obsoleta"
                    if obsoleta
                    else f"Aceita {u}-{v} ({w:g}) e visita o nó novo"
                ),
                destaque=("aresta", u, v, "obsoleta" if obsoleta else "aceita"),
                estado=estado,
            )
        )

    passos.append(
        Step(
            linha=58,
            acao="MST concluída (fila drenada)",
            destaque=("fim", None, None, None),
            estado=_estado_lazy(eventos[-1]),
        )
    )
    return passos


def passos_eager() -> list[Step]:
    from algs4.prim_mst import PrimMST

    _, eventos = _gravar("algs4.prim_mst", lambda: PrimMST(grafo_canonico()))

    passos = [
        Step(
            linha=56,
            acao="IPQ.insert(0, 0): raiz na fila de prioridade",
            destaque=("vertice", 0, None, "inicio"),
            estado=_estado_eager(eventos[_primeiro(eventos, 57)]),
        )
    ]

    for i, ev in enumerate(eventos):
        if ev["lineno"] != 59:  # `self.visit(g, v)` -> v já saiu da IPQ
            continue

        v = ev["v"]

        # O `IndexMinPQ.contains` do algs4 faz `index in self.keys`, então o
        # `insert(5, 5)` cria uma segunda entrada para o vértice 5. O último
        # `del_min()` devolve 5 de novo, quando ele já está na árvore: a
        # extração não altera estado nenhum. Gravamos como está, mas não
        # renderizamos um passo que não muda nada.
        marcados_no_evento = ev["self"].get("marked", [])
        if v is not None and 0 <= v < len(marcados_no_evento) and marcados_no_evento[v]:
            continue

        marcacao = _primeiro(eventos, 63, i)
        estado = _estado_eager(eventos[marcacao])

        passos.append(
            Step(
                linha=58,
                acao=f"del_min() -> vértice {v}",
                destaque=("vertice", v, None, "extraido"),
                estado=estado,
            )
        )

        proximo_del_min = next(
            (k for k in range(i + 1, len(eventos)) if eventos[k]["lineno"] == 59),
            len(eventos),
        )

        for k in range(i + 1, proximo_del_min):
            if eventos[k]["lineno"] not in (71, 73):
                continue
            w = eventos[k]["w"]
            aresta = eventos[k]["e"]
            if aresta is None:
                continue
            chave = _estado_eager(eventos[k])["distTo"][w]
            eh_decrease = eventos[k]["lineno"] == 71
            passos.append(
                Step(
                    linha=eventos[k]["lineno"],
                    acao=(
                        f"decrease_key({w}, {chave:g}): caminho menor via {v}"
                        if eh_decrease
                        else f"insert({w}, {chave:g}): vértice entra na IPQ"
                    ),
                    destaque=("relax", v, w, "decrease_key" if eh_decrease else "insert"),
                    estado=_estado_eager(eventos[k]),
                )
            )

    passos.append(
        Step(
            linha=57,
            acao="MST concluída (IPQ vazia)",
            destaque=("fim", None, None, None),
            estado=_estado_eager(eventos[-1]),
        )
    )
    return passos


# ---------------------------------------------------------------------------
# Roteiros detalhados: um passo por linha executada
# ---------------------------------------------------------------------------
#
# O modo compacto (`coletar`) continua sendo a fonte do golden test: ele
# resume cada aresta em um passo. O modo detalhado (`coletar_detalhado`)
# percorre TODOS os eventos de linha do trace, para a cena poder destacar o
# código linha a linha, na ordem real de execução.
#
# Para cada evento usamos o estado do evento seguinte: o `sys.settrace`
# dispara a linha ANTES de executá-la, então o snapshot de `eventos[i+1]` é,
# na prática, o estado depois da linha `i` — é isso que o painel e o grafo
# devem mostrar.

PAUSA_CURTA = 0.55
PAUSA_MEDIA = 1.0
PAUSA_LONGA = 1.7

SEM_DESTAQUE: tuple = ("linha", None, None, None)


def _fmt_aresta(e: tuple[int, int, float] | None) -> str:
    if e is None:
        return "?"
    return f"{e[0]}-{e[1]}({e[2]:g})"


def _outro(aresta: tuple[int, int, float] | None, v: int | None) -> int | None:
    """`e.other(v)` a partir da tupla (u, v, peso)."""
    if aresta is None or v is None:
        return None
    return aresta[1] if aresta[0] == v else aresta[0]


def _montar_detalhado(
    eventos: list[dict],
    algoritmo: str,
    estado_fn: Callable[[dict], dict],
    descrever: Callable[[dict, dict, dict], tuple[str, tuple, float]],
    ignorar: set[int] | None = None,
) -> list[Step]:
    inicio, fim = TRECHOS[algoritmo][1], TRECHOS[algoritmo][2]
    ignorar = ignorar or set()
    passos: list[Step] = []

    for i, ev in enumerate(eventos):
        if i in ignorar:
            continue
        linha = ev["lineno"]
        if not (inicio <= linha <= fim):
            continue

        depois = eventos[i + 1] if i + 1 < len(eventos) else ev
        estado = estado_fn(depois)
        acao, destaque, pausa = descrever(ev, depois, estado)
        passos.append(
            Step(linha=linha, acao=acao, destaque=destaque, estado=estado, pausa=pausa)
        )

    return passos


def _descrever_kruskal(ev: dict, depois: dict, estado: dict) -> tuple[str, tuple, float]:
    linha = ev["lineno"]
    aresta = depois.get("e") or ev.get("e")
    u, v, w = aresta if aresta else (None, None, None)
    fila = estado["fila"]
    mst = estado["mst"]

    if linha == 48:
        return "self.weight = 0: o custo começa em zero", SEM_DESTAQUE, PAUSA_CURTA
    if linha == 49:
        return "self.mst = deque(): a árvore começa vazia", SEM_DESTAQUE, PAUSA_CURTA
    if linha == 50:
        return "self.pq = MinPQ(): cria a fila de prioridade", SEM_DESTAQUE, PAUSA_CURTA
    if linha == 51:
        if depois["lineno"] == 52:
            return (
                f"for e in g.edges(): pega a aresta {_fmt_aresta(aresta)}",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        return "for e in g.edges(): fim da lista de arestas", SEM_DESTAQUE, PAUSA_CURTA
    if linha == 52:
        return (
            f"pq.insert({_fmt_aresta(aresta)}): {len(fila)} aresta(s) na MinPQ",
            SEM_DESTAQUE,
            PAUSA_CURTA,
        )
    if linha == 54:
        return (
            "uf = UF(6): cada vértice no seu próprio componente",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 55:
        if len(mst) >= V_CANONICO - 1:
            return (
                f"while: MST completa ({len(mst)}/5) — o laço termina",
                SEM_DESTAQUE,
                PAUSA_MEDIA,
            )
        if mst:
            return (
                f"while: MinPQ com {len(fila)} arestas e |MST| = {len(mst)}/5",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        menor = _fmt_aresta(fila[0]) if fila else "-"
        return (
            f"while: Kruskal não tem raiz — começa pela menor aresta {menor}",
            SEM_DESTAQUE,
            PAUSA_LONGA,
        )
    if linha == 56:
        return (
            f"e = pq.del_min(): retira a aresta mais leve {_fmt_aresta(aresta)}",
            ("aresta", u, v, "analise"),
            PAUSA_MEDIA,
        )
    if linha == 57:
        return f"v = e.either(): escolhe v = {depois.get('v')}", SEM_DESTAQUE, PAUSA_CURTA
    if linha == 58:
        return f"w = e.other(v): o outro extremo é w = {depois.get('w')}", SEM_DESTAQUE, PAUSA_CURTA
    if linha == 59:
        ciclo = depois["lineno"] == 60
        return (
            f"if uf.connected({u}, {v}): {'True → formaria ciclo' if ciclo else 'False → pode unir'}",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 60:
        return (
            f"continue: descarta {_fmt_aresta(aresta)} (ciclo)",
            ("aresta", u, v, "rejeitada"),
            PAUSA_LONGA,
        )
    if linha == 61:
        return (
            f"uf.union({u}, {v}): funde os dois componentes",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 62:
        return (
            f"mst.append(e): {_fmt_aresta(aresta)} entra na árvore ({len(mst)}/5)",
            ("aresta", u, v, "aceita"),
            PAUSA_LONGA,
        )
    # linha == 63
    return (
        f"weight += {w:g}: custo total = {estado['custo']:g}",
        SEM_DESTAQUE,
        PAUSA_MEDIA,
    )


def _descrever_lazy(ev: dict, depois: dict, estado: dict) -> tuple[str, tuple, float]:
    linha = ev["lineno"]
    aresta = depois.get("e") or ev.get("e")
    u, v, w = aresta if aresta else (None, None, None)
    # Em `visit`, `w` não é uma variável local: a expressão é
    # `self.marked[e.other(v)]`. Derivamos o outro extremo da aresta.
    vizinho = _outro(aresta, depois.get("v"))
    fila = estado["fila"]
    marcados = estado["marcados"]

    if linha == 57:
        return f"prim({depois.get('v')}): chama visit para a raiz", SEM_DESTAQUE, PAUSA_MEDIA
    if linha == 58:
        if not fila:
            return "while: MinPQ vazia — o laço termina", SEM_DESTAQUE, PAUSA_MEDIA
        return (
            f"while: MinPQ com {len(fila)} aresta(s)",
            SEM_DESTAQUE,
            PAUSA_CURTA,
        )
    if linha == 59:
        return (
            f"e = pq.del_min(): retira {_fmt_aresta(aresta)}",
            ("aresta", u, v, "analise"),
            PAUSA_MEDIA,
        )
    if linha == 60:
        return f"v = e.either(): v = {depois.get('v')}", SEM_DESTAQUE, PAUSA_CURTA
    if linha == 61:
        return f"w = e.other(v): w = {depois.get('w')}", SEM_DESTAQUE, PAUSA_CURTA
    if linha == 62:
        obsoleta = depois["lineno"] == 63
        return (
            f"if marked[{u}] and marked[{v}]: {'True → obsoleta' if obsoleta else 'False → aceita'}",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 63:
        return (
            f"continue: {_fmt_aresta(aresta)} é obsoleta",
            ("aresta", u, v, "obsoleta"),
            PAUSA_LONGA,
        )
    if linha == 64:
        return (
            f"mst.append(e): {_fmt_aresta(aresta)} entra na árvore",
            ("aresta", u, v, "aceita"),
            PAUSA_LONGA,
        )
    if linha == 65:
        return f"weight += {w:g}: custo total = {estado['custo']:g}", SEM_DESTAQUE, PAUSA_MEDIA
    if linha == 66:
        visita = depois["lineno"] == 67
        return (
            f"if not marked[{depois.get('v')}]: {'True → visit(v)' if visita else 'False → v já estava na árvore'}",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 67:
        return f"visit({depois.get('v')}): marca o vértice e insere o corte", SEM_DESTAQUE, PAUSA_MEDIA
    if linha == 68:
        visita = depois["lineno"] == 69
        return (
            f"if not marked[{vizinho}]: {'True → visit(w)' if visita else 'False → w já estava na árvore'}",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 69:
        return (
            f"visit({depois.get('v')}): marca o vértice e insere o corte",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 72:
        return (
            f"marked[{depois.get('v')}] = True: vértice entra na árvore",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 73:
        if depois["lineno"] == 74:
            return (
                f"for e in g.adj[{depois.get('v')}]: próxima aresta {_fmt_aresta(aresta)}",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        return (
            f"for e in g.adj[{depois.get('v')}]: fim dos vizinhos",
            SEM_DESTAQUE,
            PAUSA_CURTA,
        )
    if linha == 74:
        entra = depois["lineno"] == 75
        return (
            f"if not marked[{vizinho}]: {'True → insert' if entra else 'False → já marcado'}",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    # linha == 75
    return (
        f"pq.insert({_fmt_aresta(aresta)}): {len(fila)} na MinPQ",
        SEM_DESTAQUE,
        PAUSA_MEDIA,
    )


def _descrever_eager(ev: dict, depois: dict, estado: dict) -> tuple[str, tuple, float]:
    linha = ev["lineno"]
    aresta = depois.get("e") or ev.get("e")
    u, v, w = aresta if aresta else (None, None, None)
    vertice = depois.get("v")
    vizinho = depois.get("w")
    dist = estado["distTo"]

    if linha == 55:
        s = depois.get("s")
        return (
            f"distTo[{s}] = 0: a raiz começa com distância zero",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 56:
        s = depois.get("s")
        return (
            f"pq.insert({s}, 0): a raiz entra na IndexMinPQ",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 57:
        if not estado["ipq"]:
            return "while: IPQ vazia — o laço termina", SEM_DESTAQUE, PAUSA_MEDIA
        return (
            f"while: IPQ com {len(estado['ipq'])} vértice(s)",
            SEM_DESTAQUE,
            PAUSA_CURTA,
        )
    if linha == 58:
        return (
            f"del_min(): sai da IPQ o vértice {vertice}",
            ("vertice", vertice, None, "extraido"),
            PAUSA_LONGA,
        )
    if linha == 59:
        return f"visit({vertice}): marca o vértice e relaxa as arestas do corte", SEM_DESTAQUE, PAUSA_MEDIA
    if linha == 62:
        return f"marked[{vertice}] = True: vértice entra na árvore", SEM_DESTAQUE, PAUSA_MEDIA
    if linha == 63:
        if depois["lineno"] == 64:
            return (
                f"for e in g.adj[{vertice}]: olha a aresta {_fmt_aresta(aresta)}",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        return (
            f"for e in g.adj[{vertice}]: fim dos vizinhos",
            SEM_DESTAQUE,
            PAUSA_CURTA,
        )
    if linha == 64:
        return f"w = e.other({vertice}): o outro extremo é {vizinho}", SEM_DESTAQUE, PAUSA_CURTA
    if linha == 65:
        pula = depois["lineno"] == 66
        return (
            f"if marked[{vizinho}]: {'True → continue' if pula else 'False → pode relaxar'}",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 66:
        return f"continue: o vizinho {vizinho} já está na árvore", SEM_DESTAQUE, PAUSA_CURTA
    if linha == 67:
        melhora = depois["lineno"] == 68
        atual = dist[vizinho] if vizinho is not None and vizinho < len(dist) else float("inf")
        atual_txt = "inf" if atual == float("inf") else f"{atual:g}"
        return (
            f"if {w:g} < distTo[{vizinho}] ({atual_txt}): {'True → relaxa' if melhora else 'False → mantém'}",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 68:
        return f"distTo[{vizinho}] = {dist[vizinho]:g}: distância melhora", SEM_DESTAQUE, PAUSA_MEDIA
    if linha == 69:
        return f"edgeTo[{vizinho}] = {_fmt_aresta(aresta)}: guarda a aresta", SEM_DESTAQUE, PAUSA_MEDIA
    if linha == 70:
        ja_esta = depois["lineno"] == 71
        return (
            f"if pq.contains({vizinho}): {'True → decrease_key' if ja_esta else 'False → insert'}",
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )
    if linha == 71:
        return (
            f"decrease_key({vizinho}, {dist[vizinho]:g}): caminho menor via {vertice}",
            ("relax", vertice, vizinho, "decrease_key"),
            PAUSA_MEDIA,
        )
    # linha == 73
    return (
        f"insert({vizinho}, {dist[vizinho]:g}): vértice novo na IPQ",
        ("relax", vertice, vizinho, "insert"),
        PAUSA_MEDIA,
    )


def _ignorar_duplicado_eager(eventos: list[dict]) -> set[int]:
    """Remove o bloco da extração duplicada do vértice 5.

    `IndexMinPQ.contains` do algs4 devolve True para qualquer índice já
    visto (o `keys[i]` nunca volta a None), então `insert(5, 5)` cria uma
    segunda entrada para o 5. O `del_min` extra não muda estado nenhum.
    Gravamos o `algs4` como está, mas não animamos esse laço: ele não
    ensina nada e só repetiria linhas sem efeito.
    """
    pulados: set[int] = set()
    for i, ev in enumerate(eventos):
        if ev["lineno"] != 59:
            continue
        v = ev["v"]
        marcados = ev["self"].get("marked", [])
        if v is None or not (0 <= v < len(marcados)) or not marcados[v]:
            continue
        inicio = i
        while inicio > 0 and eventos[inicio]["lineno"] != 57:
            inicio -= 1
        fim = i + 1
        while fim < len(eventos) and eventos[fim]["lineno"] != 57:
            fim += 1
        pulados.update(range(inicio, fim))
    return pulados


def passos_detalhados_kruskal() -> list[Step]:
    from algs4.kruskal_mst import KruskalMST

    _, eventos = _gravar("algs4.kruskal_mst", lambda: KruskalMST(grafo_canonico()))
    return _montar_detalhado(eventos, "kruskal", _estado_kruskal, _descrever_kruskal)


def passos_detalhados_lazy() -> list[Step]:
    from algs4.lazy_prim_mst import LazyPrimMST

    _, eventos = _gravar("algs4.lazy_prim_mst", lambda: LazyPrimMST(grafo_canonico()))
    return _montar_detalhado(eventos, "lazy", _estado_lazy, _descrever_lazy)


def passos_detalhados_eager() -> list[Step]:
    from algs4.prim_mst import PrimMST

    _, eventos = _gravar("algs4.prim_mst", lambda: PrimMST(grafo_canonico()))
    pulados = _ignorar_duplicado_eager(eventos)
    return _montar_detalhado(eventos, "eager", _estado_eager, _descrever_eager, pulados)


# ---------------------------------------------------------------------------
# Código-fonte real para o painel
# ---------------------------------------------------------------------------


def trecho_codigo(algoritmo: str) -> tuple[str, int]:
    """Retorna (texto do trecho real do algs4, número da primeira linha)."""
    modulo, inicio, fim = TRECHOS[algoritmo]
    arquivo = Path(sys.modules[modulo].__file__)
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    return "\n".join(linhas[inicio - 1 : fim]), inicio


def coletar(algoritmo: str) -> list[Step]:
    if algoritmo == "kruskal":
        return passos_kruskal()
    if algoritmo == "lazy":
        return passos_lazy()
    if algoritmo == "eager":
        return passos_eager()
    raise ValueError(f"algoritmo desconhecido: {algoritmo!r}")


def coletar_detalhado(algoritmo: str) -> list[Step]:
    """Um passo por linha executada (modo didático, linha a linha)."""
    if algoritmo == "kruskal":
        return passos_detalhados_kruskal()
    if algoritmo == "lazy":
        return passos_detalhados_lazy()
    if algoritmo == "eager":
        return passos_detalhados_eager()
    raise ValueError(f"algoritmo desconhecido: {algoritmo!r}")


if __name__ == "__main__":
    for nome in ("kruskal", "lazy", "eager"):
        print("=" * 70)
        print(nome.upper())
        for n, passo in enumerate(coletar(nome)):
            print(f"{n:2d}  linha {passo.linha:3d}  {passo.acao}")
