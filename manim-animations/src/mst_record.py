"""
Gravador das execuções reais do `algs4-py`.

Este módulo **não implementa** Kruskal nem Prim. Ele roda a implementação
original do `algs4` sob `sys.settrace` e converte os eventos de linha
observados em uma lista de `Step` (estado + ação + destaque).

O trace acompanha o módulo do algoritmo **e** as estruturas que ele chama
(MinPQ, IndexMinPQ, Edge, UF, EdgeWeightedGraph): o painel mostra a função
real em execução, com troca de view quando a pilha de chamadas desce.

Consequências:
- existe uma única fonte da verdade (o `algs4-py`);
- o número de linha do destaque é o `frame.f_lineno` real;
- o painel mostra `frame.f_locals` real, não um snapshot digitado à mão.

O `IndexMinPQ` segue a lógica do `algs4-java`: `contains` lê o vetor
inverso `qp`, então cada vértice tem no máximo uma entrada na fila e
`decrease_key` roda quando uma aresta melhora a prioridade de um vértice
que já está nela. O painel da IPQ é derivado do heap real (`pq.pq`) e das
chaves reais (`keys`).
"""

from __future__ import annotations

import ast
import importlib
import os
import sys
from dataclasses import dataclass, replace
from functools import lru_cache
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
# Grafo de entrada (lido de um arquivo .txt no formato do algs4)
#
# Formato `EdgeWeightedGraph`: 1ª linha = V; 2ª = E; depois E linhas
# "u v peso". Linhas em branco e comentários com `#` são ignorados.
# A fonte é configurável por `MST_GRAFO` (caminho absoluto ou relativo à raiz
# do projeto). Padrão: `dataset/tinyEWG.txt`.
# ---------------------------------------------------------------------------

GRAFO_PADRAO = RAIZ_PROJETO / "dataset" / "tinyEWG.txt"

# Fallback hardcoded (grafo de 6 vértices usado nas rodadas anteriores): só
# entra se o arquivo não existir, para o módulo nunca quebrar.
_FALLBACK_V = 6
_FALLBACK_ARESTAS: tuple[tuple[int, int, float], ...] = (
    (1, 2, 1.0),
    (0, 1, 2.0),
    (3, 4, 2.0),
    (2, 4, 3.0),
    (0, 2, 4.0),
    (3, 5, 5.0),
    (4, 5, 6.0),
    (1, 3, 7.0),
)


def caminho_grafo() -> Path:
    """Arquivo de grafo ativo (env `MST_GRAFO` ou o tinyEWG padrão)."""
    env = os.environ.get("MST_GRAFO")
    if env:
        p = Path(env)
        return p if p.is_absolute() else (RAIZ_PROJETO / p)
    return GRAFO_PADRAO


def ler_grafo_txt(caminho: Path) -> tuple[int, list[tuple[int, int, float]]]:
    """Lê o formato `EdgeWeightedGraph` do algs4: V, E e depois `u v peso`.

    Aceita espaços/tabs arbitrários, linhas em branco e comentários `#`.
    Levanta `ValueError` para cabeçalho/arestas inconsistentes.
    """
    linhas: list[str] = []
    # `utf-8-sig` aceita o BOM que o Bloco de Notas do Windows grava.
    for bruta in Path(caminho).read_text(encoding="utf-8-sig").splitlines():
        s = bruta.split("#", 1)[0].strip()
        if s:
            linhas.append(s)
    if len(linhas) < 2:
        raise ValueError(f"{caminho}: arquivo de grafo vazio ou incompleto")

    v = int(linhas[0].split()[0])
    e = int(linhas[1].split()[0])
    arestas: list[tuple[int, int, float]] = []
    for s in linhas[2 : 2 + e]:
        partes = s.split()
        if len(partes) < 3:
            raise ValueError(f"{caminho}: linha de aresta inválida: {s!r}")
        try:
            u, vv, w = int(partes[0]), int(partes[1]), float(partes[2])
        except ValueError as erro:
            raise ValueError(f"{caminho}: aresta com número inválido: {s!r}") from erro
        if not (0 <= u < v and 0 <= vv < v):
            raise ValueError(
                f"{caminho}: aresta {u}-{vv} fora do intervalo 0..{v - 1} "
                f"(o cabeçalho declara {v} vértices)"
            )
        arestas.append((u, vv, w))
    if len(arestas) != e:
        raise ValueError(f"{caminho}: esperava {e} arestas, encontrei {len(arestas)}")
    return v, arestas


def _carregar_grafo_ativo() -> tuple[int, tuple[tuple[int, int, float], ...]]:
    """Carrega o grafo de `MST_GRAFO`/tinyEWG.

    Só cai no fallback quando o arquivo NÃO EXISTE. Um arquivo presente mas
    malformado levanta `ValueError`: melhor falhar alto do que gerar um
    vídeo com outro grafo silenciosamente.
    """
    caminho = caminho_grafo()
    try:
        v, arestas = ler_grafo_txt(caminho)
    except FileNotFoundError:
        print(
            f"[mst_record] aviso: {caminho} não encontrado; usando o grafo "
            f"de {_FALLBACK_V} vértices embutido.",
            file=sys.stderr,
        )
        return _FALLBACK_V, _FALLBACK_ARESTAS
    return v, tuple(arestas)


V_CANONICO, ARESTAS_CANONICAS = _carregar_grafo_ativo()


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
    # Módulo do algs4 que contém a linha. Vazio = módulo principal do
    # algoritmo (TRECHOS); preenchido nos passos de funções auxiliares
    # (MinPQ, IndexMinPQ, Edge, UF, EdgeWeightedGraph).
    modulo: str = ""


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
    # A própria aresta (`Edge`): permite narrar `either()`/`other()` com
    # os extremos reais, sem inventar valores.
    if hasattr(obj, "v") and hasattr(obj, "w") and isinstance(getattr(obj, "v"), int):
        d["v"] = obj.v
        d["w"] = obj.w

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
        # Chaves reais da IndexMinPQ (`keys[i]` = prioridade do vértice i).
        # Necessárias para narrar/validar o heap físico fora de distTo (o
        # snapshot de um `decrease_key` tem distTo novo mas key antiga).
        chaves = getattr(pq, "keys", None)
        if chaves is not None:
            d["pq_keys"] = list(chaves)

    return d


def _name_of(frame, modulos: dict[str, str]) -> tuple[str, str] | None:
    """(módulo, nome qualificado) do frame, se ele pertence ao escopo."""
    caminho = os.path.normcase(os.path.abspath(frame.f_code.co_filename))
    modulo = modulos.get(caminho)
    if modulo is None:
        return None
    return modulo, frame.f_code.co_qualname


def _self_do_algoritmo(frame) -> Any:
    """Sobe a pilha até o `self` do objeto do algoritmo (MST).

    Dentro de `MinPQ.insert`, o `self` local é a própria MinPQ; o estado que
    o painel precisa é o da MST (`KruskalMST`, `LazyPrimMST`, `PrimMST`),
    que está em um frame ancestral.
    """
    atual = frame
    while atual is not None:
        obj = atual.f_locals.get("self")
        if obj is not None and hasattr(obj, "pq") and (
            hasattr(obj, "mst") or hasattr(obj, "distTo") or hasattr(obj, "edgeTo")
        ):
            return obj
        atual = atual.f_back
    return None


def _ids_uf(frame) -> list[int] | None:
    """Vetor `id` do union-find, achado no frame atual ou em um ancestral."""
    atual = frame
    while atual is not None:
        uf = atual.f_locals.get("uf")
        if uf is None:
            obj = atual.f_locals.get("self")
            if obj is not None and hasattr(obj, "id") and hasattr(obj, "sz"):
                uf = obj
        if uf is not None and hasattr(uf, "id"):
            return list(uf.id)
        atual = atual.f_back
    return None


def _instantanea_aux(obj: Any) -> dict:
    """Snapshot curto do `self` auxiliar (Edge, UF, MinPQ...)."""
    if obj is None:
        return {}
    d: dict[str, Any] = {}
    for nome in ("v", "w", "weight"):
        valor = getattr(obj, nome, None)
        if isinstance(valor, (int, float)):
            d[nome] = valor
    ids = getattr(obj, "id", None)
    if ids is not None:
        d["id"] = list(ids)
    keys = getattr(obj, "keys", None)
    if keys is not None:
        d["keys"] = list(keys)
    qp = getattr(obj, "qp", None)
    if qp is not None:
        d["qp"] = list(qp)
    return d


def _gravar(
    modulos: str | tuple[str, ...],
    executar: Callable[[], Any],
) -> tuple[Any, list[dict]]:
    """Roda `executar()` observando as linhas dos módulos indicados.

    O escopo inclui o módulo do algoritmo **e** os módulos das estruturas
    que ele chama (MinPQ, Edge, UF...). Assim o painel pode mostrar a função
    real em execução, inclusive quando a pilha de chamadas desce para elas.
    """
    if isinstance(modulos, str):
        modulos = (modulos,)

    mapa: dict[str, str] = {}
    for nome_modulo in modulos:
        modulo = sys.modules[nome_modulo]
        chave = os.path.normcase(os.path.abspath(modulo.__file__))
        mapa[chave] = nome_modulo

    eventos: list[dict] = []

    def trace(frame, event, arg):
        identificacao = _name_of(frame, mapa)
        if identificacao is None:
            return None
        nome_modulo, funcao = identificacao

        def local(frame, event, arg):
            if event == "line":
                loc = frame.f_locals
                eventos.append(
                    {
                        "modulo": nome_modulo,
                        "funcao": funcao,
                        "lineno": frame.f_lineno,
                        "self": _instantanea_self(_self_do_algoritmo(frame)),
                        "aux": _instantanea_aux(loc.get("self")),
                        "e": _aresta(loc.get("e")),
                        "v": loc.get("v"),
                        "w": loc.get("w"),
                        "s": loc.get("s"),
                        "uf": _ids_uf(frame),
                        # Parâmetros escalares úteis para descrever as
                        # funções auxiliares (MinPQ, IndexMinPQ, UF, Edge).
                        "locais": {
                            nome: loc[nome]
                            for nome in (
                                "p", "q", "i", "index", "key", "m", "n",
                                "k", "j", "N", "pId", "qId",
                            )
                            if nome in loc and isinstance(loc[nome], (int, float))
                        },
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
    # Ordem FÍSICA do vetor `pq.pq` (heap binário), sem ordenar. É ela que
    # mostra o swim/sink no painel de estrutura.
    est["pq_fisico"] = list(fila)
    # Vetor `id` do union-find (pai de cada vértice) e os componentes que ele
    # induz. Alimenta a floresta do painel de estrutura (`EstruturaPanel`).
    ids = snap.get("uf")
    est["uf_id"] = list(ids) if ids else []
    return est


def _estado_lazy(snap: dict) -> dict:
    est = _estado_base(snap)
    fila = [_normalizar(e) for e in snap["self"].get("pq", [])]
    est["fila"] = sorted(fila, key=lambda e: (e[2], e[0], e[1]))
    est["pq_fisico"] = list(fila)
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
    # Ordem real do heap (a posição k de `pq.pq` é o vértice naquele slot).
    # Alimenta a árvore heap do painel de estrutura (`EstruturaPanel`).
    est["pq_ordem"] = list(indices) if indices is not None and all(
        isinstance(i, int) for i in indices
    ) else []
    # Prioridades reais da IPQ por vértice (`keys[i]`). Para validar/animar
    # o heap físico usamos a chave da IPQ, não `distTo` — num decrease_key a
    # `distTo` já mudou enquanto a chave do heap ainda é a antiga.
    est["ipq_keys"] = {i: k for i, k in enumerate(dados.get("pq_keys") or [])}
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

# Módulos observados no modo linha a linha: o algoritmo + toda estrutura
# auxiliar cujo código também aparece no painel.
MODULOS_DETALHADO: dict[str, tuple[str, ...]] = {
    "kruskal": (
        "algs4.kruskal_mst",
        "algs4.edge_weighted_graph",
        "algs4.min_pq",
        "algs4.edge",
        "algs4.uf",
    ),
    "lazy": (
        "algs4.lazy_prim_mst",
        "algs4.min_pq",
        "algs4.edge",
    ),
    "eager": (
        "algs4.prim_mst",
        "algs4.index_min_pq",
        "algs4.edge",
    ),
}

# Views do painel: (módulo, nome qualificado). Lista explícita = o painel
# não mostra função morta (nunca executada) e o teste de cobertura cobra
# exatamente este conjunto. Inclui as funções executadas pelas próprias
# estruturas (`MinPQ.swim/sink`, `IndexMinPQ.swim/sink`, `UF.find`) — o
# `greater` do IndexMinPQ fica de fora só porque é uma comparação de uma
# linha; as linhas que o chamam já aparecem dentro de `swim`/`sink`.
FUNCOES_PAINEL: dict[str, tuple[tuple[str, str], ...]] = {
    "kruskal": (
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
    ),
    "lazy": (
        ("algs4.lazy_prim_mst", "LazyPrimMST.prim"),
        ("algs4.lazy_prim_mst", "LazyPrimMST.visit"),
        ("algs4.min_pq", "MinPQ.insert"),
        ("algs4.min_pq", "MinPQ.is_empty"),
        ("algs4.min_pq", "MinPQ.del_min"),
        ("algs4.min_pq", "MinPQ.swim"),
        ("algs4.min_pq", "MinPQ.sink"),
        ("algs4.edge", "Edge.either"),
        ("algs4.edge", "Edge.other"),
    ),
    "eager": (
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
    ),
}


def funcao_permitida(algoritmo: str, modulo: str, funcao: str) -> bool:
    """A função participa do modo linha a linha e tem view no painel?"""
    return (modulo, funcao) in FUNCOES_PAINEL[algoritmo]



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

        # O `IndexMinPQ.contains` lê o vetor inverso `qp` (como no Java);
        # o Prim só chega ao `insert` quando o vértice ainda não está na
        # fila. A extração duplicada que existia com o `contains` baseado
        # em `keys` não acontece mais; os filtros abaixo ficam como
        # proteção histórica e não encontram nada a pular.
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


@lru_cache(maxsize=None)
def _faixas_simples(modulo: str) -> dict[int, tuple[int, int]]:
    """Linha inicial -> (inicial, final) de cada comando SIMPLES do módulo.

    O `sys.settrace` dispara um evento por linha **física**. Quando o fonte
    quebra um comando em várias linhas — como a troca do `MinPQ.swim`:

        28:            self.pq[k], self.pq[
        29:                (k - 1) // 2] = self.pq[(k - 1) // 2], self.pq[k]

    o segundo evento acontece **no meio da atribuição**: o heap aparece
    momentaneamente com um item duplicado e outro faltando. Esse estado não
    existe para o algoritmo, só para o trace — e era ele que fazia um
    elemento "sumir e reaparecer" no painel. Mapeamos o comando inteiro para
    colapsar as linhas de continuação e usar o estado DEPOIS do comando.
    """
    arquivo = arquivo_modulo(modulo)
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    simples = (
        ast.Assign,
        ast.AugAssign,
        ast.Expr,
        ast.Return,
        ast.Raise,
        ast.Assert,
        ast.Delete,
        ast.Pass,
        ast.Break,
        ast.Continue,
        ast.Import,
        ast.ImportFrom,
        ast.Global,
        ast.Nonlocal,
    )
    faixas: dict[int, tuple[int, int]] = {}
    for no in ast.walk(arvore):
        if isinstance(no, simples):
            fim = getattr(no, "end_lineno", None) or no.lineno
            # Todas as linhas físicas do comando apontam para o início: assim
            # um evento na continuação (linha 29) é reconhecido como parte do
            # comando que começou na linha 28.
            for linha in range(no.lineno, fim + 1):
                faixas[linha] = (no.lineno, fim)
    return faixas


def _montar_detalhado(
    eventos: list[dict],
    algoritmo: str,
    estado_fn: Callable[[dict], dict],
    descrever: Callable[[dict, dict, dict], tuple[str, tuple, float]],
    ignorar: set[int] | None = None,
) -> list[Step]:
    modulo_principal = TRECHOS[algoritmo][0]
    ignorar = ignorar or set()
    passos: list[Step] = []

    for i, ev in enumerate(eventos):
        if i in ignorar:
            continue
        if not funcao_permitida(algoritmo, ev["modulo"], ev["funcao"]):
            continue

        faixa = _faixas_simples(ev["modulo"]).get(ev["lineno"])
        # Linha de continuação do mesmo comando: não é um passo novo.
        if faixa is not None and faixa[0] != ev["lineno"]:
            continue

        # Estado: o primeiro evento DEPOIS do comando inteiro. Se o comando
        # ocupa várias linhas físicas, pulamos os eventos intermediários
        # (que veriam a atribuição pela metade).
        j = i + 1
        if faixa is not None and faixa[1] > ev["lineno"]:
            while (
                j < len(eventos)
                and eventos[j]["modulo"] == ev["modulo"]
                and eventos[j]["lineno"] <= faixa[1]
            ):
                j += 1
        depois = eventos[j] if j < len(eventos) else ev
        estado = estado_fn(depois)

        # Descrição: o próximo evento da MESMA função. Os roteiros do
        # algoritmo comparam `depois["lineno"]` para saber o caminho do
        # `if`/`for`; um evento de função auxiliar no meio quebraria isso.
        proximo = next(
            (
                eventos[k]
                for k in range(i + 1, len(eventos))
                if eventos[k]["modulo"] == ev["modulo"]
                and eventos[k]["funcao"] == ev["funcao"]
            ),
            ev,
        )
        # Já os valores (`v`, `w`, `e`) de uma linha que CHAMA uma função
        # auxiliar estão no primeiro evento da função chamada (ex.:
        # `visit(g, w)` -> o `v` de `visit`). Misturamos só esses campos,
        # mantendo o `lineno` do próximo evento da mesma função.
        descricao = dict(proximo)
        # Para comandos de várias linhas, `j` já aponta para o evento
        # seguinte ao comando inteiro (nunca para a metade da atribuição).
        imediato = eventos[j] if j < len(eventos) else ev
        for campo in ("v", "w", "e", "s"):
            if imediato.get(campo) is not None:
                descricao[campo] = imediato[campo]

        if ev["modulo"] == modulo_principal:
            acao, destaque, pausa = descrever(ev, descricao, estado)
        else:
            acao, destaque, pausa = _descrever_auxiliar(ev, proximo, estado)

        passos.append(
            Step(
                linha=ev["lineno"],
                acao=acao,
                destaque=destaque,
                estado=estado,
                pausa=pausa,
                modulo=ev["modulo"],
            )
        )

    _marcar_inserts_duplicados(passos)
    return passos


def _marcar_inserts_duplicados(passos: list[Step]) -> None:
    """Troca "vértice novo" por "2ª entrada" quando o `insert` duplica.

    O passo da chamada `pq.insert(w, ...)` é gravado ANTES de o `append`
    rodar, então o estado dele ainda mostra uma entrada só. Basta olhar os
    passos seguintes (o `append` e o `swim`): se `w` passa a aparecer mais
    de uma vez em `pq.pq`, a marcação entra. Com o `contains` baseado em
    `qp` (como no Java) a duplicata não acontece; a função é rede de
    segurança para o trace e não altera nada no caso normal.
    """
    for i, p in enumerate(passos):
        if not (p.destaque and p.destaque[0] == "relax" and p.destaque[3] == "insert"):
            continue
        w = p.destaque[2]
        if w is None or "2ª entrada" in p.acao:
            continue
        duplicou = any(
            (q.estado.get("pq_ordem") or []).count(w) > 1
            for q in passos[i + 1 : i + 6]
        )
        if not duplicou:
            continue
        dist = p.estado.get("distTo") or []
        chave = dist[w] if w < len(dist) else None
        chave_txt = f"{chave:g}" if isinstance(chave, (int, float)) else "?"
        passos[i] = replace(
            p,
            acao=(
                f"insert({w}, {chave_txt}): 2ª entrada de {w} no pq"
            ),
        )


def _no_mesmo_componente(estado: dict, p: int | None, q: int | None) -> bool | None:
    if p is None or q is None:
        return None
    for grupo in estado.get("componentes", []):
        if p in grupo and q in grupo:
            return True
    return False


def _descrever_auxiliar(ev: dict, proximo: dict, estado: dict) -> tuple[str, tuple, float]:
    """Narração das funções auxiliares (MinPQ, IPQ, Edge, UF, grafo)."""
    linha = ev["lineno"]
    funcao = ev["funcao"]
    aux = ev.get("aux") or {}
    locais = ev.get("locais") or {}
    fila = estado.get("fila", [])
    ipq = estado.get("ipq", {})

    # -- grafo -------------------------------------------------------------
    if funcao == "EdgeWeightedGraph.edges":
        if linha == 57:
            return "edges = []: lista que vai receber as arestas", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 58:
            return f"for v in range(self.V): percorre os {V_CANONICO} vértices", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 59:
            return "for e in adj[v]: percorre a lista de adjacência", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 60:
            return "if e.other(v) > v: conta cada aresta uma única vez", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 61:
            return "edges.append(e): a aresta entra na lista do grafo", SEM_DESTAQUE, PAUSA_CURTA
        return "return edges: entrega as arestas para o algoritmo", SEM_DESTAQUE, PAUSA_MEDIA

    # -- MinPQ (arestas) ---------------------------------------------------
    if funcao == "MinPQ.insert":
        if linha == 7:
            aresta = _aresta(ev.get("v"))
            return (
                f"self.pq.append({_fmt_aresta(aresta)}): entra na MinPQ",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        return "self.swim(n): reposiciona a aresta no heap", SEM_DESTAQUE, PAUSA_CURTA

    if funcao == "MinPQ.is_empty":
        vazia = not fila
        return (
            f"return not self.pq: {'True → vazia' if vazia else f'False → {len(fila)} aresta(s)'}",
            SEM_DESTAQUE,
            PAUSA_CURTA,
        )

    if funcao == "MinPQ.del_min":
        if linha == 14:
            return "m = self.pq[0]: guarda a menor aresta", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 15:
            return "troca o topo com o último item do heap", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 16:
            return "self.pq = self.pq[:-1]: remove o último item", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 17:
            return "self.sink(0): restaura a propriedade do heap", SEM_DESTAQUE, PAUSA_CURTA
        return "return m: devolve a aresta extraída", SEM_DESTAQUE, PAUSA_MEDIA

    # -- MinPQ.swim / MinPQ.sink (reordenação interna do heap) --------------

    if funcao == "MinPQ.swim":
        if linha == 27:
            k = locais.get("k")
            return (
                f"while k={k} > 0 e pai > pq[k]: a aresta sobe?",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        if linha == 30:
            return "k = (k-1)//2: sobe para a posição do pai", SEM_DESTAQUE, PAUSA_CURTA
        return "troca o filho com o pai no heap", SEM_DESTAQUE, PAUSA_CURTA

    if funcao == "MinPQ.sink":
        if linha == 33:
            n = (proximo.get("locais") or {}).get("N")
            return (
                f"N = len(pq) = {n}: tamanho atual do heap",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        if linha == 35:
            return "while 2k+1 <= N-1: enquanto houver filho esquerdo", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 36:
            return (
                f"j = 2k+1 = {locais.get('j')}: posição do filho esquerdo",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        if linha == 37:
            return "if j < N-1 e filho direito < filho esquerdo:", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 38:
            return "j += 1: escolhe o filho menor (direito)", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 40:
            return "if not pq[j] < pq[k]: o pai já é o menor?", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 41:
            return "break: o heap já está ok", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 43:
            return "troca pq[k] com pq[j]: o pai desce", SEM_DESTAQUE, PAUSA_CURTA
        return "k = j: continua descendo", SEM_DESTAQUE, PAUSA_CURTA

    # -- IndexMinPQ.swim / IndexMinPQ.sink ----------------------------------

    if funcao == "IndexMinPQ.insert":
        i = locais.get("i")
        if linha == 36:
            return f"pq.contains({i})? o vértice já está na fila?", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 38:
            return f"self.pq.append({i}): vértice entra na IPQ", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 39:
            k = (proximo.get("locais") or {}).get("k")
            return f"k = len(pq) - 1 = {k}: posição no heap", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 40:
            return f"self.qp[{i}] = k: guarda a posição do vértice", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 41:
            chave = ipq.get(i) if i in ipq else estado.get("distTo", [None] * 64)[i] if i is not None else None
            return f"self.keys[{i}] = {chave:g}: prioridade inicial", SEM_DESTAQUE, PAUSA_CURTA
        return "self.swim(k): reposiciona o vértice no heap", SEM_DESTAQUE, PAUSA_CURTA

    if funcao == "IndexMinPQ.contains":
        index = locais.get("index")
        if linha == 32:
            return (
                f"self._validate_index({index}): 0 <= {index} < V?",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        qp = ev.get("aux", {}).get("qp") or []
        dentro = index is not None and index < len(qp) and qp[index] != -1
        if index is None:
            resposta = ""
        elif dentro:
            resposta = f"True → qp[{index}] = {qp[index]}: está no heap"
        else:
            resposta = f"False → qp[{index}] = -1: fora do heap"
        return (
            f"return self.qp[{index}] != -1: {resposta}".rstrip(),
            SEM_DESTAQUE,
            PAUSA_CURTA,
        )

    if funcao == "IndexMinPQ.decrease_key":
        i = locais.get("i")
        chave = locais.get("key")
        if linha == 65:
            return f"pq.contains({i})? o vértice está na IPQ?", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 67:
            return (
                f"if keys[{i}] <= {chave:g}: o novo valor é menor?",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        if linha == 69:
            return f"self.keys[{i}] = {chave:g}: atualiza a prioridade", SEM_DESTAQUE, PAUSA_CURTA
        return "self.swim(qp[i]): sobe o vértice no heap", SEM_DESTAQUE, PAUSA_CURTA

    if funcao == "IndexMinPQ.del_min":
        m = locais.get("m")
        if linha == 81:
            return "if not pq: a fila está vazia?", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 83:
            return "m = self.pq[0]: vértice de menor distância", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 84:
            return "troca o topo com o último item do heap", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 85:
            return "self.pq.pop(): remove o último item", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 86:
            return "self.sink(0): restaura a propriedade do heap", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 87:
            return f"self.qp[{m}] = -1: o vértice sai da IPQ", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 88:
            return f"self.keys[{m}] = None: libera a prioridade antiga", SEM_DESTAQUE, PAUSA_CURTA
        return f"return m: devolve o vértice {m}", SEM_DESTAQUE, PAUSA_MEDIA

    if funcao == "IndexMinPQ.is_empty":
        vazia = not ipq
        return (
            f"return not self.pq: {'True → vazia' if vazia else f'False → {len(ipq)} vértice(s)'}",
            SEM_DESTAQUE,
            PAUSA_CURTA,
        )

    # -- IndexMinPQ.swim / IndexMinPQ.sink (reordenação interna do heap) ---

    if funcao == "IndexMinPQ.swim":
        if linha == 116:
            k = locais.get("k")
            return (
                f"while k={k} > 0 e pai > chave(k): o vértice sobe?",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        if linha == 118:
            return "k = (k-1)//2: sobe para a posição do pai", SEM_DESTAQUE, PAUSA_CURTA
        return "troca o vértice com o pai no heap", SEM_DESTAQUE, PAUSA_CURTA

    if funcao == "IndexMinPQ.sink":
        if linha == 121:
            n = (proximo.get("locais") or {}).get("N")
            return (
                f"N = len(pq) = {n}: tamanho atual do heap",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        if linha == 123:
            return "while 2k+1 <= N-1: enquanto houver filho esquerdo", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 124:
            return (
                f"j = 2k+1 = {locais.get('j')}: posição do filho esquerdo",
                SEM_DESTAQUE,
                PAUSA_CURTA,
            )
        if linha == 125:
            return "if j < N-1 e greater(j, j+1): filho direito menor?", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 126:
            return "j += 1: escolhe o filho menor (direito)", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 128:
            return "if not greater(k, j): o pai já é o menor?", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 129:
            return "break: o heap já está ok", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 131:
            return "troca pq[k] com pq[j]: o pai desce", SEM_DESTAQUE, PAUSA_CURTA
        return "k = j: continua descendo", SEM_DESTAQUE, PAUSA_CURTA

    # -- Edge --------------------------------------------------------------
    if funcao == "Edge.either":
        return f"return self.v: devolve o primeiro extremo ({aux.get('v')})", SEM_DESTAQUE, PAUSA_CURTA

    if funcao == "Edge.other":
        v = ev.get("v")
        if linha == 20:
            return f"if {v} == self.v ({aux.get('v')})?", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 21:
            return f"return self.w: o outro extremo é {aux.get('w')}", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 22:
            return f"elif {v} == self.w ({aux.get('w')})?", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 23:
            return f"return self.v: o outro extremo é {aux.get('v')}", SEM_DESTAQUE, PAUSA_CURTA
        return "raise: aresta inválida para este vértice", SEM_DESTAQUE, PAUSA_CURTA

    # -- UF ----------------------------------------------------------------
    if funcao == "UF.connected":
        p, q = locais.get("p"), locais.get("q")
        mesmo = _no_mesmo_componente(estado, p, q)
        if mesmo is None:
            resposta = ""
        else:
            resposta = "True → ciclo" if mesmo else "False → pode unir"
        return (
            f"return find({p}) == find({q}): {resposta}".rstrip(),
            SEM_DESTAQUE,
            PAUSA_MEDIA,
        )

    if funcao == "UF.find":
        if linha == 41:
            return f"while id[{locais.get('p')}] != {locais.get('p')}: já é a raiz?", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 42:
            return "id[p] = id[id[p]]: compressão de caminho", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 43:
            return f"p = id[{locais.get('p')}]: sobe na árvore", SEM_DESTAQUE, PAUSA_CURTA
        return f"return p: devolve a raiz {locais.get('p')}", SEM_DESTAQUE, PAUSA_MEDIA

    if funcao == "UF.union":
        p, q = locais.get("p"), locais.get("q")
        if linha == 47:
            return f"pId = find({p}): raiz do primeiro vértice", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 48:
            return f"qId = find({q}): raiz do segundo vértice", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 49:
            return "if pId == qId: já estão no mesmo componente?", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 50:
            return "return: nada a unir", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 51:
            return "if sz[pId] < sz[qId]: escolhe a árvore menor", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 52:
            return "self.id[pId] = qId: liga a árvore menor à maior", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 53:
            return "self.sz[qId] += sz[pId]: atualiza o tamanho", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 54:
            return "else: a primeira árvore é a maior", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 55:
            return "self.id[qId] = pId: liga a árvore menor à maior", SEM_DESTAQUE, PAUSA_CURTA
        if linha == 56:
            return "self.sz[pId] += sz[qId]: atualiza o tamanho", SEM_DESTAQUE, PAUSA_CURTA
        return "self.count -= 1: um componente a menos", SEM_DESTAQUE, PAUSA_MEDIA

    # Rede de segurança: nunca deixar um passo sem texto.
    return f"{funcao}(): linha {linha}", SEM_DESTAQUE, PAUSA_CURTA


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
    ordem = estado.get("pq_ordem") or []
    duplicado = vizinho is not None and ordem.count(vizinho) > 1
    if duplicado:
        return (
            f"insert({vizinho}, {dist[vizinho]:g}): 2ª entrada de {vizinho} no pq",
            ("relax", vertice, vizinho, "insert"),
            PAUSA_MEDIA,
        )
    return (
        f"insert({vizinho}, {dist[vizinho]:g}): vértice novo na IPQ",
        ("relax", vertice, vizinho, "insert"),
        PAUSA_MEDIA,
    )


def _ignorar_duplicado_eager(eventos: list[dict]) -> set[int]:
    """Remove um eventual bloco de extração duplicada (rede de segurança).

    Com o `contains` antigo (baseado em `keys`), `insert(5, 5)` criava uma
    segunda entrada para o vértice 5 e o `del_min` o extraía de novo já na
    árvore. Hoje o `contains` lê o vetor inverso `qp`, como no Java, e o
    Prim não insere duplicatas: a função não encontra nada para pular.
    Fica porque o roteiro não pode quebrar se um grafo estranho repetir.
    """
    modulo = "algs4.prim_mst"
    funcao = "PrimMST.prim"
    pulados: set[int] = set()
    for i, ev in enumerate(eventos):
        if ev["modulo"] != modulo or ev["funcao"] != funcao or ev["lineno"] != 59:
            continue
        v = ev["v"]
        marcados = ev["self"].get("marked", [])
        if v is None or not (0 <= v < len(marcados)) or not marcados[v]:
            continue
        inicio = i
        while inicio > 0 and not (
            eventos[inicio]["modulo"] == modulo
            and eventos[inicio]["funcao"] == funcao
            and eventos[inicio]["lineno"] == 57
        ):
            inicio -= 1
        fim = i + 1
        while fim < len(eventos) and not (
            eventos[fim]["modulo"] == modulo
            and eventos[fim]["funcao"] == funcao
            and eventos[fim]["lineno"] == 57
        ):
            fim += 1
        pulados.update(range(inicio, fim))
    return pulados


def passos_detalhados_kruskal() -> list[Step]:
    from algs4.kruskal_mst import KruskalMST

    grafo = grafo_canonico()  # montar o grafo NÃO entra no trace
    _, eventos = _gravar(MODULOS_DETALHADO["kruskal"], lambda: KruskalMST(grafo))
    return _montar_detalhado(eventos, "kruskal", _estado_kruskal, _descrever_kruskal)


def passos_detalhados_lazy() -> list[Step]:
    from algs4.lazy_prim_mst import LazyPrimMST

    grafo = grafo_canonico()  # montar o grafo NÃO entra no trace
    _, eventos = _gravar(MODULOS_DETALHADO["lazy"], lambda: LazyPrimMST(grafo))
    return _montar_detalhado(eventos, "lazy", _estado_lazy, _descrever_lazy)


def passos_detalhados_eager() -> list[Step]:
    from algs4.prim_mst import PrimMST

    grafo = grafo_canonico()  # montar o grafo NÃO entra no trace
    _, eventos = _gravar(MODULOS_DETALHADO["eager"], lambda: PrimMST(grafo))
    pulados = _ignorar_duplicado_eager(eventos)
    return _montar_detalhado(eventos, "eager", _estado_eager, _descrever_eager, pulados)


# ---------------------------------------------------------------------------
# Código-fonte real para o painel
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FuncaoCodigo:
    """Uma função executada, na íntegra, pronta para o painel.

    `modulo` é o módulo real do `algs4` (ex.: `algs4.min_pq`), `arquivo` é o
    caminho curto exibido no cabeçalho e `inicio`/`fim` são linhas reais do
    arquivo-fonte. Quando a linha da classe entra como contexto (Kruskal),
    `inicio` aponta para o `class`; o corpo termina no `end_lineno` do `def`.
    """

    nome: str
    modulo: str
    arquivo: str
    inicio: int
    fim: int
    texto: str


def _rotulo_arquivo(caminho: Path) -> str:
    try:
        return caminho.relative_to(DIR_ALGS4).as_posix()
    except ValueError:
        return caminho.name


def arquivo_modulo(nome_modulo: str) -> Path:
    """Caminho do arquivo-fonte de um módulo do `algs4`."""
    if nome_modulo not in sys.modules:
        importlib.import_module(nome_modulo)
    return Path(sys.modules[nome_modulo].__file__)


def arquivo_codigo(algoritmo: str) -> Path:
    """Arquivo real do `algs4` que contém o algoritmo (módulo principal)."""
    return arquivo_modulo(TRECHOS[algoritmo][0])


def _funcoes_do_ast(arquivo: Path) -> dict[str, tuple[int, int, int | None]]:
    """nome qualificado -> (linha do def, fim do corpo, linha da classe)."""
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    arvore = ast.parse("\n".join(linhas))
    resultado: dict[str, tuple[int, int, int | None]] = {}

    def visitar(no: ast.AST, prefixo: str = "") -> None:
        for filho in ast.iter_child_nodes(no):
            if isinstance(filho, ast.ClassDef):
                visitar(filho, filho.name)
            elif isinstance(filho, ast.FunctionDef):
                nome = f"{prefixo}.{filho.name}" if prefixo else filho.name
                classe = no.lineno if isinstance(no, ast.ClassDef) else None
                resultado[nome] = (filho.lineno, filho.end_lineno, classe)

    visitar(arvore)
    return resultado


@lru_cache(maxsize=None)
def funcoes_codigo(algoritmo: str) -> tuple[FuncaoCodigo, ...]:
    """Views do painel, derivadas do `ast` dos fontes reais do `algs4`.

    A lista `FUNCOES_PAINEL` define **quais** funções aparecem (o algoritmo
    e as estruturas auxiliares que ele executa). Linhas e textos vêm do
    `ast`/fonte; nada é digitado à mão.

    O resultado é imutável e cacheado: `funcao_da_linha` é chamada a cada
    passo, e reparsear os arquivos centenas de vezes não é aceitável.
    """
    modulo_principal, ini, _fim = TRECHOS[algoritmo]
    views: list[FuncaoCodigo] = []
    cache_ast: dict[str, dict[str, tuple[int, int, int | None]]] = {}

    for modulo, nome in FUNCOES_PAINEL[algoritmo]:
        arquivo = arquivo_modulo(modulo)
        if modulo not in cache_ast:
            cache_ast[modulo] = _funcoes_do_ast(arquivo)
        nos = cache_ast[modulo]
        if nome not in nos:
            raise LookupError(f"{modulo}: função {nome!r} não existe no fonte")

        def_linha, def_fim, classe_linha = nos[nome]
        inicio = def_linha
        # A linha `class` entra como contexto só para o algoritmo principal
        # (Kruskal vive inteiro no `__init__`); as estruturas auxiliares
        # aparecem a partir do `def`, para não inflar a moldura.
        if modulo == modulo_principal and classe_linha is not None:
            if ini <= classe_linha < def_linha:
                inicio = classe_linha

        linhas = arquivo.read_text(encoding="utf-8").splitlines()
        views.append(
            FuncaoCodigo(
                nome=nome,
                modulo=modulo,
                arquivo=_rotulo_arquivo(arquivo),
                inicio=inicio,
                fim=def_fim,
                texto="\n".join(linhas[inicio - 1 : def_fim]),
            )
        )

    return tuple(views)


def funcao_da_linha(algoritmo: str, linha: int, modulo: str = "") -> FuncaoCodigo:
    """View (função) que contém a linha executada.

    `modulo` vazio significa o módulo principal do algoritmo. As views são
    disjuntas dentro de cada módulo; `LookupError` aqui significa que a
    gravação e o recorte de código saíram de sincronia.
    """
    modulo = modulo or TRECHOS[algoritmo][0]
    candidatas = [
        f
        for f in funcoes_codigo(algoritmo)
        if f.modulo == modulo and f.inicio <= linha <= f.fim
    ]
    if len(candidatas) != 1:
        raise LookupError(
            f"{algoritmo}/{modulo}: linha {linha} pertence a {len(candidatas)} "
            f"funções ({[f.nome for f in candidatas]})"
        )
    return candidatas[0]


def trecho_codigo(algoritmo: str) -> tuple[str, int]:
    """Retorna (texto do trecho real do algs4, número da primeira linha)."""
    _, inicio, fim = TRECHOS[algoritmo]
    arquivo = arquivo_codigo(algoritmo)
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
