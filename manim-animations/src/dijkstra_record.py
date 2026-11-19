"""
Gravador das execuções reais do algoritmo de Dijkstra no `algs4-py`.

Este módulo **não implementa** Dijkstra. Ele lê o grafo de um arquivo `.txt`
no formato do `algs4` (padrão: `dataset/tinyEWD.txt`, V=8, E=15), roda a
implementação original sob `sys.settrace` e converte os eventos de linha em
uma lista de `Step` (estado + ação + destaque).

Módulos observados no trace:
- algs4.dijkstra_sp
- algs4.index_min_pq
- algs4.directed_edge

O estado exibido é sempre o estado **depois** da linha executada: cada passo
usa o snapshot do evento seguinte (o `sys.settrace` avisa a linha antes de
executá-la). `pq_ordem`, `ipq_keys` e `qp` vêm diretamente da `IndexMinPQ`
real, não de uma reconstrução manual.
"""

from __future__ import annotations

import ast
import importlib
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Garantir que algs4-py está no sys.path
# ---------------------------------------------------------------------------

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
DIR_ALGS4 = RAIZ_PROJETO / "algs4-py"

if (DIR_ALGS4 / "algs4").is_dir() and str(DIR_ALGS4) not in sys.path:
    sys.path.insert(0, str(DIR_ALGS4))

import algs4  # noqa: F401
from algs4.directed_edge import DirectedEdge  # noqa: E402
from algs4.edge_weighted_digraph import EdgeWeightedDigraph  # noqa: E402
from algs4.dijkstra_sp import DijkstraSP  # noqa: E402

# ---------------------------------------------------------------------------
# Grafo de entrada (lido de um .txt no formato do algs4)
#
# Formato `EdgeWeightedDigraph`: 1ª linha = V; 2ª = E; depois E linhas
# "u v peso" (arestas dirigidas). Linhas em branco e comentários com `#`
# são ignorados. A fonte é configurável por `DIJKSTRA_GRAFO`.
# ---------------------------------------------------------------------------

GRAFO_PADRAO = RAIZ_PROJETO / "dataset" / "tinyEWD.txt"

# Fallback embutido: só entra se o arquivo não existir, para o módulo nunca
# quebrar. Grafos com pesos iguais ao índice do vértice acionam o
# `contains` quebrado do algs4, por isso o fallback evita essa coincidência.
_FALLBACK_V = 5
_FALLBACK_ARESTAS: tuple[tuple[int, int, float], ...] = (
    (0, 1, 4.1),
    (0, 2, 1.1),
    (2, 1, 2.0),
    (1, 3, 1.0),
    (2, 3, 5.0),
    (3, 4, 3.0),
)


def caminho_grafo() -> Path:
    """Arquivo de grafo ativo (env `DIJKSTRA_GRAFO` ou o tinyEWD padrão)."""
    env = os.environ.get("DIJKSTRA_GRAFO")
    if env:
        p = Path(env)
        return p if p.is_absolute() else (RAIZ_PROJETO / p)
    return GRAFO_PADRAO


def ler_grafo_txt(caminho: Path) -> tuple[int, list[tuple[int, int, float]]]:
    """Lê o formato `EdgeWeightedDigraph` do algs4: V, E e `u v peso`.

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
                f"{caminho}: aresta {u}->{vv} fora do intervalo 0..{v - 1} "
                f"(o cabeçalho declara {v} vértices)"
            )
        arestas.append((u, vv, w))
    if len(arestas) != e:
        raise ValueError(f"{caminho}: esperava {e} arestas, encontrei {len(arestas)}")
    return v, arestas


def _carregar_grafo_ativo() -> tuple[int, tuple[tuple[int, int, float], ...]]:
    """Carrega o grafo de `DIJKSTRA_GRAFO`/tinyEWD.

    Só cai no fallback quando o arquivo NÃO EXISTE. Um arquivo presente mas
    malformado levanta `ValueError`: melhor falhar alto do que gerar um
    vídeo com outro grafo silenciosamente.
    """
    caminho = caminho_grafo()
    try:
        v, arestas = ler_grafo_txt(caminho)
    except FileNotFoundError:
        print(
            f"[dijkstra_record] aviso: {caminho} não encontrado; usando o "
            f"grafo de {_FALLBACK_V} vértices embutido.",
            file=sys.stderr,
        )
        return _FALLBACK_V, _FALLBACK_ARESTAS
    return v, tuple(arestas)


V_CANONICO, ARESTAS_CANONICAS = _carregar_grafo_ativo()
ORIGEM = 0


def grafo_canonico() -> EdgeWeightedDigraph:
    """Cria o digrafo valorado a partir do txt ativo."""
    g = EdgeWeightedDigraph(V_CANONICO)
    for u, v, w in ARESTAS_CANONICAS:
        g.add_edge(DirectedEdge(u, v, w))
    return g


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Step:
    """Um passo observado da execução real.

    linha    -- número de linha do arquivo do algs4 (vem do trace)
    acao     -- frase curta explicativa para o painel de narração
    destaque -- ("inicio"|"aresta"|"vertice"|"relax"|"fim", u, v, status)
    estado   -- snapshot com distTo, edgeTo, ipq, marcados, extraido, custo
    pausa    -- tempo de pausa didática (segundos)
    modulo   -- módulo do algs4 onde a linha foi executada
    """

    linha: int
    acao: str
    destaque: tuple
    estado: dict
    pausa: float = 0.9
    modulo: str = ""


# ---------------------------------------------------------------------------
# Roteiro de módulos e views de código
# ---------------------------------------------------------------------------

TRECHOS: dict[str, tuple[str, int, int]] = {
    "dijkstra": ("algs4.dijkstra_sp", 36, 58),
}

MODULOS_DETALHADO = (
    "algs4.dijkstra_sp",
    "algs4.index_min_pq",
    "algs4.directed_edge",
)

FUNCOES_PAINEL: tuple[tuple[str, str], ...] = (
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
)


def funcao_permitida(modulo: str, funcao: str) -> bool:
    return (modulo, funcao) in FUNCOES_PAINEL


# ---------------------------------------------------------------------------
# Captura de snapshots durante o trace
# ---------------------------------------------------------------------------


def _self_do_algoritmo(frame) -> Any:
    # `pq` só existe depois da linha 43; antes disso o objeto já é o DijkstraSP
    # (edgeTo/distTo definidos) e é ele que o painel precisa mostrar. Exigir
    # `pq` aqui deixava os primeiros passos com estado vazio.
    atual = frame
    while atual is not None:
        obj = atual.f_locals.get("self")
        if obj is not None and (hasattr(obj, "distTo") or hasattr(obj, "edgeTo")):
            return obj
        atual = atual.f_back
    return None


def _aresta(e: Any) -> tuple[int, int, float] | None:
    if e is None:
        return None
    try:
        return (int(e.From()), int(e.To()), float(e.weight))
    except Exception:
        return None


def _snapshot_self(obj: Any) -> dict:
    if obj is None:
        return {}
    edge_to = []
    for e in getattr(obj, "edgeTo", []) or []:
        edge_to.append(_aresta(e))
    dist_to = []
    for d in getattr(obj, "distTo", []) or []:
        dist_to.append(float(d))
    pq_obj = getattr(obj, "pq", None)
    pq_indices = []
    pq_keys = []
    qp = []
    if pq_obj is not None:
        if isinstance(getattr(pq_obj, "pq", None), list):
            pq_indices = list(pq_obj.pq)
        elif isinstance(pq_obj, list):
            pq_indices = list(pq_obj)
        if isinstance(getattr(pq_obj, "keys", None), list):
            pq_keys = list(pq_obj.keys)
        if isinstance(getattr(pq_obj, "qp", None), list):
            qp = list(pq_obj.qp)
    return {
        "edgeTo": edge_to,
        "distTo": dist_to,
        "pq": pq_indices,
        "pq_keys": pq_keys,
        "qp": qp,
    }


def _snapshot_aux(obj: Any) -> dict:
    if obj is None:
        return {}
    d: dict[str, Any] = {}
    for attr in ("v", "w", "weight"):
        val = getattr(obj, attr, None)
        if isinstance(val, (int, float)):
            d[attr] = val
    keys = getattr(obj, "keys", None)
    if isinstance(keys, list):
        d["keys"] = list(keys)
    qp = getattr(obj, "qp", None)
    if isinstance(qp, list):
        d["qp"] = list(qp)
    pq = getattr(obj, "pq", None)
    if isinstance(pq, list):
        d["pq"] = list(pq)
    elif pq is not None and isinstance(getattr(pq, "pq", None), list):
        d["pq"] = list(pq.pq)
    return d


def _name_of(frame, mapa: dict[str, str]) -> tuple[str, str] | None:
    caminho = os.path.normcase(os.path.abspath(frame.f_code.co_filename))
    modulo = mapa.get(caminho)
    if modulo is None:
        return None
    return (modulo, frame.f_code.co_qualname)


def _gravar(modulos: tuple[str, ...], executar: Callable[[], Any]) -> tuple[Any, list[dict]]:
    mapa: dict[str, str] = {}
    for nome_modulo in modulos:
        if nome_modulo not in sys.modules:
            importlib.import_module(nome_modulo)
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
                        "self": _snapshot_self(_self_do_algoritmo(frame)),
                        "aux": _snapshot_aux(loc.get("self")),
                        "e": _aresta(loc.get("e")),
                        "v": loc.get("v"),
                        "w": loc.get("w"),
                        "s": loc.get("s"),
                        "locais": {
                            nome: loc[nome]
                            for nome in (
                                "i", "index", "key", "m", "n", "k", "j",
                                "N", "w", "v", "item",
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
# Estado visual derivado
# ---------------------------------------------------------------------------

INF = float("inf")


def _extrair_estado(
    snap: dict,
    marcados: set[int],
    vertice_ativo: int | None = None,
) -> dict:
    dados = snap.get("self", {}) if snap else {}
    dist_to = [float(d) for d in dados.get("distTo", [])]
    edge_to = list(dados.get("edgeTo", []))
    pq_indices = list(dados.get("pq", []))
    pq_keys_lista = list(dados.get("pq_keys", []))
    qp = list(dados.get("qp", []))

    marcados_lista = sorted(int(v) for v in marcados)

    # `keys` reais da IPQ (num decrease_key a chave do heap ainda é a antiga,
    # mesmo com distTo já atualizado).
    ipq_keys: dict[int, float] = {}
    for v, chave in enumerate(pq_keys_lista):
        if chave is not None:
            ipq_keys[v] = float(chave)

    # IPQ lógica: um item por vértice ainda não finalizado que está no heap.
    ipq: dict[int, float] = {}
    for v in sorted(set(int(x) for x in pq_indices)):
        if v in marcados:
            continue
        if v in ipq_keys:
            ipq[v] = ipq_keys[v]
        elif v < len(dist_to):
            ipq[v] = dist_to[v]

    # SPT confirmada: apenas edgeTo de vértices já finalizados.
    spt_edges: list[tuple[int, int, float]] = []
    for v in marcados_lista:
        if v < len(edge_to) and edge_to[v] is not None:
            spt_edges.append(edge_to[v])

    custo_total = sum(e[2] for e in spt_edges)

    return {
        "distTo": dist_to,
        "edgeTo": edge_to,
        "marcados": marcados_lista,
        "ativo": vertice_ativo,
        "ipq": ipq,
        "pq_ordem": pq_indices,
        "ipq_keys": ipq_keys,
        "qp": qp,
        "spt": spt_edges,
        "custo": custo_total,
        "origem": ORIGEM,
    }


# ---------------------------------------------------------------------------
# Construção dos Passos (Step)
# ---------------------------------------------------------------------------

SEM_DESTAQUE = ("nenhum", None, None, None)
PAUSA_DECISAO = 1.8
PAUSA_MEDIA = 1.2
PAUSA_CURTA = 0.55


def _filtrar_eventos(eventos: list[dict]) -> list[dict]:
    """Remove eventos que não são estados intermediários reais.

    - `[None for _ in range(V)]` e `[inf for _ in range(V)]` disparam um
      evento de linha por iteração, todos com o mesmo estado: ficaria um
      passo repetido V vezes.
    - O `for v in range(V)` alterna as linhas 40/41; só a primeira volta é
      didática (o efeito é o mesmo para todos os vértices).
    """
    filtrados: list[dict] = []
    vistos_init: set[int] = set()

    for ev in eventos:
        if ev["funcao"] == "DijkstraSP.__init__":
            linha = ev["lineno"]
            if linha in (38, 39):
                if linha in vistos_init:
                    continue
                vistos_init.add(linha)
            elif linha in (40, 41):
                if linha in vistos_init:
                    continue
                vistos_init.add(linha)

        if filtrados:
            ant = filtrados[-1]
            if (
                (ant["modulo"], ant["funcao"], ant["lineno"])
                == (ev["modulo"], ev["funcao"], ev["lineno"])
                and ant.get("self") == ev.get("self")
                and ant.get("locais") == ev.get("locais")
                and ant.get("e") == ev.get("e")
            ):
                continue

        filtrados.append(ev)

    return filtrados


def _valor_futuro(eventos: list[dict], i: int, campo: str, limite: int = 4):
    for ev in eventos[i + 1 : i + 1 + limite]:
        if campo == "e":
            if ev.get("e") is not None:
                return ev["e"]
        elif campo == "w":
            w = ev.get("w")
            if w is None and isinstance(ev.get("aux"), dict):
                w = ev["aux"].get("w")
            if w is not None:
                return w
        elif campo in ("m", "n", "j", "k", "i", "index", "N"):
            val = ev.get("locais", {}).get(campo)
            if val is not None:
                return val
        elif campo == "item":
            val = ev.get("locais", {}).get("item")
            if val is not None:
                return val
    return None


def _fmt(v: Any) -> str:
    if v is None:
        return "?"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def coletar_detalhado() -> list[Step]:
    resultado = None
    grafo = grafo_canonico()
    resultado, eventos = _gravar(MODULOS_DETALHADO, lambda: DijkstraSP(grafo, ORIGEM))

    brutos = [
        ev for ev in eventos if funcao_permitida(ev["modulo"], ev["funcao"])
    ]
    eventos = _filtrar_eventos(brutos)

    passos: list[Step] = []
    marcados: set[int] = set()

    for idx, ev in enumerate(eventos):
        modulo = ev["modulo"]
        funcao = ev["funcao"]
        linha = ev["lineno"]
        loc = ev.get("locais", {})

        acao = ""
        destaque = SEM_DESTAQUE
        pausa = PAUSA_CURTA

        # A extração acontece no `return m` do del_min (linha 89).
        m = loc.get("m")
        if m is None and funcao == "IndexMinPQ.del_min":
            # Na linha 46 (`m = pq[0]`) o `m` ainda não está em f_locals; o
            # valor real aparece no evento seguinte. Sem isso a narração
            # mostrava "m = ?" nos dois primeiros passos do del_min.
            m = _valor_futuro(eventos, idx, "m")
        if funcao == "IndexMinPQ.del_min" and linha == 89 and m is not None:
            marcados.add(int(m))

        # O vértice ativo é o argumento do relax em execução.
        ativo = None
        if funcao == "DijkstraSP.relax":
            v_relax = ev.get("v")
            if v_relax is not None:
                ativo = int(v_relax)

        e = ev.get("e")
        if e is None and modulo == "algs4.dijkstra_sp":
            e = _valor_futuro(eventos, idx, "e")
        w = ev.get("w")
        if w is None:
            w = _valor_futuro(eventos, idx, "w") if modulo == "algs4.dijkstra_sp" else None

        # Estado do passo = estado do evento SEGUINTE (pós-execução da linha).
        proximo = eventos[idx + 1] if idx + 1 < len(eventos) else None
        estado = _extrair_estado(proximo or ev, marcados, ativo)
        dist_to = estado["distTo"]

        # --- DijkstraSP.__init__ ------------------------------------
        if funcao == "DijkstraSP.__init__":
            if linha == 38:
                acao = f"edgeTo = [None] * V: nenhum predecessor conhecido (V={V_CANONICO})"
                destaque = ("inicio", None, None, "inicio")
            elif linha == 39:
                acao = f"distTo = [inf] * V: distâncias estimadas para os {V_CANONICO} vértices"
                pausa = PAUSA_MEDIA
            elif linha == 40:
                acao = "for v in range(V): percorre todos os vértices"
            elif linha == 41:
                acao = "distTo[v] = POSITIVE_INFINITY (999999): nenhum caminho conhecido"
            elif linha == 42:
                acao = f"distTo[s={ORIGEM}] = 0.0: a distância da origem a si mesma é zero"
                destaque = ("vertice", ORIGEM, None, "origem")
                pausa = PAUSA_DECISAO
            elif linha == 43:
                acao = f"pq = IndexMinPQ({V_CANONICO}): cria a fila de prioridade indexada"
                pausa = PAUSA_MEDIA
            elif linha == 44:
                acao = f"pq.insert({ORIGEM}, 0.0): insere a origem na IPQ"
                destaque = ("relax", ORIGEM, None, "insert")
                pausa = PAUSA_DECISAO
            elif linha == 45:
                acao = "while not pq.is_empty(): ainda há vértices a extrair?"
            elif linha == 46:
                acao = "relax(g, pq.del_min()): extrai o vértice de menor distância"
                pausa = PAUSA_DECISAO

        # --- DijkstraSP.relax ----------------------------------------
        elif funcao == "DijkstraSP.relax":
            if linha == 48:
                acao = f"def relax(g, v={ativo}): examina as arestas que saem de {ativo}"
                destaque = ("vertice", ativo, None, "extraido")
                pausa = PAUSA_DECISAO
            elif linha == 49:
                if e is not None:
                    acao = f"for e in g.adj[{ativo}]: avalia {e[0]}->{e[1]} (peso {e[2]:g})"
                    destaque = ("aresta", e[0], e[1], "analise")
                else:
                    acao = f"for e in g.adj[{ativo}]: percorre as arestas de saída"
            elif linha == 50:
                acao = f"w = e.To(): o destino da aresta é w = {w}"
            elif linha == 51:
                dv = dist_to[ativo] if ativo is not None and ativo < len(dist_to) else None
                dw = dist_to[w] if w is not None and w < len(dist_to) else None
                acao = (
                    f"if distTo[{w}] ({_fmt(dw)}) > distTo[{ativo}] ({_fmt(dv)}) + "
                    f"peso ({_fmt(e[2] if e else None)}): testa a relaxação"
                )
                if e is not None:
                    destaque = ("aresta", e[0], e[1], "analise")
                pausa = PAUSA_MEDIA
            elif linha == 52:
                novo = dist_to[w] if w is not None and w < len(dist_to) else None
                acao = f"distTo[{w}] = {_fmt(novo)}: caminho menor encontrado, atualiza distTo"
                if e is not None:
                    destaque = ("aresta", e[0], e[1], "relaxada")
                pausa = PAUSA_DECISAO
            elif linha == 53:
                acao = f"edgeTo[{w}] = {e[0]}->{e[1]}: registra o predecessor no caminho" if e else f"edgeTo[{w}] = e"
                if e is not None:
                    destaque = ("aresta", e[0], e[1], "aceita")
                pausa = PAUSA_MEDIA
            elif linha == 54:
                # Descobre o ramo olhando a próxima linha executada no relax.
                ramo = next(
                    (
                        ev2["lineno"]
                        for ev2 in eventos[idx + 1 :]
                        if ev2["funcao"] == "DijkstraSP.relax"
                        and ev2["lineno"] in (55, 57)
                    ),
                    None,
                )
                if ramo == 55:
                    acao = f"if pq.contains({w}): true → {w} já está na IPQ"
                elif ramo == 57:
                    acao = f"if pq.contains({w}): false → {w} ainda não está na IPQ"
                else:
                    acao = f"if pq.contains({w}): consulta a presença na IPQ"
                destaque = ("vertice", w, None, "consulta")
            elif linha == 55:
                acao = f"pq.change({w}, {_fmt(dist_to[w] if w is not None and w < len(dist_to) else None)}): atualiza a chave na IPQ"
                destaque = ("vertice", w, None, "decrease_key")
                pausa = PAUSA_MEDIA
            elif linha == 57:
                acao = f"pq.insert({w}, {_fmt(dist_to[w] if w is not None and w < len(dist_to) else None)}): insere {w} na IPQ"
                destaque = ("vertice", w, None, "insert")
                pausa = PAUSA_MEDIA

        # --- IndexMinPQ.__init__ -------------------------------------
        elif funcao == "IndexMinPQ.__init__":
            if linha == 14:
                acao = "IndexMinPQ.__init__: a capacidade max_n é válida?"
            elif linha == 16:
                acao = f"self.max_n = {V_CANONICO}: capacidade da fila indexada"
            elif linha == 17:
                acao = "pq = []: heap vazio"
            elif linha == 18:
                acao = "qp = [-1] * V: posição de cada vértice no heap"
            elif linha == 19:
                acao = "keys = [None] * V: prioridade real de cada vértice"
            pausa = PAUSA_CURTA

        # --- IndexMinPQ.insert ---------------------------------------
        elif funcao == "IndexMinPQ.insert":
            i = loc.get("i")
            k = _valor_futuro(eventos, idx, "k")
            item = _valor_futuro(eventos, idx, "item")
            if linha == 36:
                acao = f"pq.contains({i})? já existe entrada para {i}?"
            elif linha == 38:
                acao = f"self.pq.append({i}): {i} entra no fim do heap"
            elif linha == 39:
                acao = f"k = len(pq) - 1 = {k}: posição do novo item"
            elif linha == 40:
                acao = f"qp[{i}] = {k}: registra onde {i} está no heap"
            elif linha == 41:
                acao = f"keys[{i}] = {_fmt(item)}: guarda a prioridade de {i}"
            elif linha == 42:
                acao = f"swim({k}): sobe {i} até restaurar a ordem do min-heap"
                pausa = PAUSA_MEDIA

        # --- IndexMinPQ.change ---------------------------------------
        elif funcao == "IndexMinPQ.change":
            i = loc.get("i")
            item = loc.get("item")
            if linha == 58:
                acao = f"pq.contains({i})? o vértice já está na IPQ?"
            elif linha == 60:
                acao = f"keys[{i}] = {_fmt(item)}: atualiza a prioridade"
            elif linha == 61:
                acao = f"swim(qp[{i}]): se a chave diminuiu, sobe no heap"
            elif linha == 62:
                acao = f"sink(qp[{i}]): garante a descida se necessário"
            pausa = PAUSA_MEDIA

        # --- IndexMinPQ.contains -------------------------------------
        elif funcao == "IndexMinPQ.contains":
            index = loc.get("index")
            if linha == 32:
                acao = f"self._validar_indice({index}): 0 <= {index} < V?"
            elif linha == 33:
                ramo = next(
                    (
                        ev2["lineno"]
                        for ev2 in eventos[idx + 1 :]
                        if ev2["funcao"] == "DijkstraSP.relax"
                        and ev2["lineno"] in (55, 57)
                    ),
                    None,
                )
                resp = "true" if ramo == 55 else "false" if ramo == 57 else "?"
                acao = (
                    f"return qp[{index}] != -1 → {resp}: "
                    f"{index} {'está' if resp == 'true' else 'não está'} na IPQ"
                )
                pausa = PAUSA_MEDIA

        # --- IndexMinPQ.del_min --------------------------------------
        elif funcao == "IndexMinPQ.del_min":
            if linha == 81:
                acao = "if not pq: a fila está vazia?"
            elif linha == 83:
                acao = f"m = pq[0] = {_fmt(m)}: a raiz é o vértice de menor distância"
            elif linha == 84:
                acao = "troca a raiz com o último item do heap"
            elif linha == 85:
                acao = "pq.pop(): remove o último item (a raiz antiga)"
            elif linha == 86:
                acao = "sink(0): desce o novo topo até restaurar o min-heap"
            elif linha == 87:
                acao = f"qp[{_fmt(m)}] = -1: marca {_fmt(m)} como fora da IPQ"
            elif linha == 88:
                acao = f"keys[{_fmt(m)}] = None: libera a prioridade antiga"
            elif linha == 89:
                dv = dist_to[m] if isinstance(m, int) and m < len(dist_to) else None
                acao = f"return m={_fmt(m)}: vértice {_fmt(m)} extraído com distTo {_fmt(dv)}"
                destaque = ("vertice", m, None, "extraido")
                pausa = PAUSA_DECISAO

        # --- IndexMinPQ.is_empty -------------------------------------
        elif funcao == "IndexMinPQ.is_empty":
            if linha == 22:
                vazio = not estado.get("pq_ordem")
                acao = f"return not pq → {vazio}: a fila {'está vazia' if vazio else 'ainda tem itens'}"

        # --- IndexMinPQ.swim -----------------------------------------
        elif funcao == "IndexMinPQ.swim":
            k = loc.get("k")
            if k is None:
                k = _valor_futuro(eventos, idx, "k")
            if linha == 115:
                acao = f"def swim(k={_fmt(k)}): restaura a ordem subindo o item"
            elif linha == 116:
                acao = f"while k>0 e pai > filho: {_fmt(k)} precisa subir no heap"
            elif linha == 117:
                acao = "troca o item com o pai"
            elif linha == 118:
                acao = "k = (k - 1) // 2: sobe um nível"
            pausa = PAUSA_CURTA

        # --- IndexMinPQ.sink -----------------------------------------
        elif funcao == "IndexMinPQ.sink":
            k = loc.get("k")
            if k is None:
                k = _valor_futuro(eventos, idx, "k")
            if linha == 120:
                acao = f"def sink(k={_fmt(k)}): restaura a ordem descendo o item"
            elif linha == 121:
                N = _valor_futuro(eventos, idx, "N")
                acao = f"N = len(pq) = {_fmt(N)}: tamanho atual do heap"
            elif linha == 123:
                acao = f"while 2k+1 <= N-1: o item k tem filho no heap?"
            elif linha == 124:
                j = _valor_futuro(eventos, idx, "j")
                acao = f"j = 2k+1 = {_fmt(j)}: filho esquerdo de {_fmt(k)}"
            elif linha == 125:
                acao = "if filho direito < filho esquerdo: escolhe o menor filho (j += 1)"
            elif linha == 126:
                acao = "j += 1: o menor filho é o direito"
            elif linha == 128:
                acao = "if pai <= menor filho: a ordem está restaurada (break)"
            elif linha == 129:
                acao = "break: o heap já está ordenado"
            elif linha in (131, 132):
                acao = "troca pai e filho; k = j: desce um nível"
            pausa = PAUSA_CURTA

        # --- DirectedEdge.To -----------------------------------------
        elif funcao == "DirectedEdge.To":
            if linha == 20:
                aux = ev.get("aux", {})
                u_e, v_e = aux.get("v"), aux.get("w")
                acao = f"DirectedEdge.To(): devolve o destino {u_e}->{v_e}"

        if not acao:
            acao = f"{funcao}:{linha}"

        # Último passo: estado final completo.
        if idx == len(eventos) - 1:
            destaque = ("fim", None, None, "concluido")
            acao = "Dijkstra concluído! Árvore de Caminhos Mínimos (SPT) calculada."
            estado = _extrair_estado({"self": _snapshot_self(resultado)}, marcados, None)
            pausa = 2.5

        passos.append(
            Step(
                linha=linha,
                acao=acao,
                destaque=destaque,
                estado=estado,
                pausa=pausa,
                modulo=modulo,
            )
        )

    return passos


def coletar() -> list[Step]:
    """Alias compacto: a cena didática usa o mesmo roteiro detalhado."""
    return coletar_detalhado()


# ---------------------------------------------------------------------------
# AST e Views de Código (FuncaoCodigo)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FuncaoCodigo:
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
    if nome_modulo not in sys.modules:
        importlib.import_module(nome_modulo)
    return Path(sys.modules[nome_modulo].__file__)


def _funcoes_do_ast(arquivo: Path) -> dict[str, tuple[int, int, int | None]]:
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
def funcoes_codigo() -> tuple[FuncaoCodigo, ...]:
    modulo_principal, ini, _fim = TRECHOS["dijkstra"]
    views: list[FuncaoCodigo] = []
    cache_ast: dict[str, dict[str, tuple[int, int, int | None]]] = {}
    cache_linhas: dict[str, list[str]] = {}

    for modulo, nome in FUNCOES_PAINEL:
        arquivo = arquivo_modulo(modulo)
        if modulo not in cache_ast:
            cache_ast[modulo] = _funcoes_do_ast(arquivo)
            cache_linhas[modulo] = arquivo.read_text(encoding="utf-8").splitlines()
        nos = cache_ast[modulo]
        if nome not in nos:
            raise LookupError(f"{modulo}: função {nome!r} não encontrada no fonte")

        def_linha, def_fim, classe_linha = nos[nome]
        inicio = def_linha
        if modulo == modulo_principal and classe_linha is not None and nome.endswith(".__init__"):
            if ini <= classe_linha < def_linha:
                inicio = classe_linha

        linhas = cache_linhas[modulo]
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


def funcao_da_linha(linha: int, modulo: str = "") -> FuncaoCodigo:
    modulo = modulo or TRECHOS["dijkstra"][0]
    candidatas = [
        f for f in funcoes_codigo() if f.modulo == modulo and f.inicio <= linha <= f.fim
    ]
    if len(candidatas) != 1:
        raise LookupError(
            f"Dijkstra/{modulo}: linha {linha} casou com {len(candidatas)} funções: "
            f"{[f.nome for f in candidatas]}"
        )
    return candidatas[0]
