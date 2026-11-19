"""
Gravador das execuções reais de fluxo máximo do `algs4-py`.

Este módulo **não implementa** Ford-Fulkerson/Edmonds-Karp. Ele roda o port
real (`algs4.ford_fulkerson`, `algs4.ford_fulkerson_dfs`, `algs4.flow_network`,
`algs4.flow_edge`) sob `sys.settrace` e converte os eventos de linha em uma
lista de `Step` (estado + ação + destaque).

Uma única fonte da verdade:

- a rede vem de um arquivo `.txt` real, no formato do `FlowNetwork` do algs4
  (`dataset/tinyFN.txt`, override `FLUXO_GRAFO`): V, E e E linhas
  `u w capacidade`;
- `s = 0` e `t = V - 1`, como no `main` do `FordFulkerson.java`;
- o número de linha do destaque é o `frame.f_lineno` real;
- o estado do painel (fluxos, residuais, fila/pilha, corte) sai de
  `frame.f_locals`/`self` do próprio algoritmo, nunca de uma recontagem.

O trace acompanha o algoritmo **e** as estruturas que ele chama (FlowNetwork,
FlowEdge): cada função executada vira uma view do painel de código
(`FUNCOES_PAINEL`), com troca fade-out → fade-in na cena.

Dois modos, mesma projeção:

- `coletar()` — passos compactos (golden e determinismo);
- `coletar_detalhado()` — um passo por linha executada (material didático).
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

from algs4.flow_edge import FlowEdge  # noqa: E402
from algs4.flow_network import FlowNetwork  # noqa: E402


# ---------------------------------------------------------------------------
# Rede de entrada (lida de um arquivo .txt no formato do algs4)
#
# Formato `FlowNetwork`: 1ª linha = V; 2ª = E; depois E linhas
# "u w capacidade". Linhas em branco e comentários com `#` são ignorados.
# A fonte é configurável por `FLUXO_GRAFO` (caminho absoluto ou relativo à
# raiz do projeto). Padrão: `dataset/tinyFN.txt`.
#
# Não existe fallback embutido de propósito: a rede é a fonte única dos dados
# do vídeo; arquivo ausente/ilegível tem de falhar alto, não virar outro grafo.
# ---------------------------------------------------------------------------

REDE_PADRAO = RAIZ_PROJETO / "dataset" / "tinyFN.txt"


def caminho_rede() -> Path:
    """Arquivo de rede ativo (env `FLUXO_GRAFO` ou o tinyFN padrão)."""
    env = os.environ.get("FLUXO_GRAFO")
    if env:
        p = Path(env)
        return p if p.is_absolute() else (RAIZ_PROJETO / p)
    return REDE_PADRAO


def ler_rede_txt(caminho: Path) -> tuple[int, tuple[tuple[int, int, float], ...]]:
    """Lê o formato `FlowNetwork` do algs4: V, E e depois `u w capacidade`.

    Aceita espaços/tabs arbitrários, linhas em branco e comentários `#`.
    Levanta `ValueError` para cabeçalho/arestas inconsistentes.

    A ordem das arestas é a do ARQUIVO (ordem de inserção no `FlowNetwork`);
    é ela que o painel usa nas linhas da tabela.
    """
    linhas: list[str] = []
    # `utf-8-sig` aceita o BOM que o Bloco de Notas do Windows grava.
    for bruta in Path(caminho).read_text(encoding="utf-8-sig").splitlines():
        s = bruta.split("#", 1)[0].strip()
        if s:
            linhas.append(s)
    if len(linhas) < 2:
        raise ValueError(f"{caminho}: arquivo de rede vazio ou incompleto")

    v = int(linhas[0].split()[0])
    e = int(linhas[1].split()[0])
    arestas: list[tuple[int, int, float]] = []
    for s in linhas[2 : 2 + e]:
        partes = s.split()
        if len(partes) < 3:
            raise ValueError(f"{caminho}: linha de aresta inválida: {s!r}")
        try:
            u, w, capacidade = int(partes[0]), int(partes[1]), float(partes[2])
        except ValueError as erro:
            raise ValueError(f"{caminho}: aresta com número inválido: {s!r}") from erro
        if not (0 <= u < v and 0 <= w < v):
            raise ValueError(
                f"{caminho}: aresta {u}->{w} fora do intervalo 0..{v - 1} "
                f"(o cabeçalho declara {v} vértices)"
            )
        if u == w:
            raise ValueError(f"{caminho}: laço {u}->{u} não é suportado pelo painel")
        arestas.append((u, w, capacidade))
    if len(arestas) != e:
        raise ValueError(f"{caminho}: esperava {e} arestas, encontrei {len(arestas)}")

    # O estado do painel indexa aresta por (u, w): arestas paralelas
    # colidiriam. Falha alto em vez de mostrar fluxo trocado.
    chaves = [(u, w) for u, w, _c in arestas]
    if len(set(chaves)) != len(chaves):
        repetidas = sorted({c for c in chaves if chaves.count(c) > 1})
        raise ValueError(
            f"{caminho}: arestas paralelas {repetidas} não são suportadas pelo painel"
        )
    return v, tuple(arestas)


V_REDE, ARESTAS_REDE = ler_rede_txt(caminho_rede())
# Posição de cada aresta na ordem do arquivo (usada para ordenar o painel).
INDICE_ARESTA = {(u, w): i for i, (u, w, _c) in enumerate(ARESTAS_REDE)}
S_FONTE = 0
T_SUMIDOURO = V_REDE - 1


def construir_rede() -> FlowNetwork:
    """Monta o `FlowNetwork` real a partir do arquivo ativo."""
    return FlowNetwork(caminho_rede())


# ---------------------------------------------------------------------------
# Step
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Step:
    """Um passo observado da execução real.

    linha    -- número de linha do arquivo do algs4 (vem do trace)
    acao     -- frase curta para o painel/legenda
    destaque -- ("inicio"|"busca"|"caminho"|"aumento"|"corte"|"aresta"|"fim",
                 u, v, status)
    estado   -- dicionário com fluxos/capacidades/residuais/marcados/edgeTo/
                adj (Bag real)/nivel (derivado do edgeTo)/caminho/gargalo/
                valor/fila/pilha/iteracao/inspecoes/corte
    pausa    -- segundos de pausa depois da animação deste passo
    modulo   -- módulo do algs4 que contém a linha
    funcao   -- nome qualificado da função (a view do painel de código)
    """

    linha: int
    acao: str
    destaque: tuple
    estado: dict
    pausa: float = 0.9
    modulo: str = ""
    funcao: str = ""

    # Chaves sempre presentes em `estado` (listas/dicts vazios quando não se
    # aplica, nunca KeyError): marcados, edge_to, adj, nivel, valor, fila,
    # pilha, inspecoes, corte, corte_capacidade. `adj` é a Bag real na ordem
    # de iteração do `FlowNetwork`; `nivel` é DERIVADO do `edgeTo` (o algs4
    # não tem profundidade em fluxo máximo) — ver `_adj_da_rede`/`_niveis`.


# ---------------------------------------------------------------------------
# Módulos observados, recortes e views do painel
# ---------------------------------------------------------------------------


def arquivo_modulo(nome_modulo: str) -> Path:
    """Caminho do arquivo-fonte de um módulo do `algs4`."""
    if nome_modulo not in sys.modules:
        importlib.import_module(nome_modulo)
    return Path(sys.modules[nome_modulo].__file__)


def _limites_classe(modulo: str, classe: str) -> tuple[str, int, int]:
    """(módulo, linha do `class`, fim da classe) lidos do ast do fonte real."""
    arvore = ast.parse(arquivo_modulo(modulo).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.ClassDef) and no.name == classe:
            return modulo, no.lineno, no.end_lineno
    raise LookupError(f"{modulo}: classe {classe!r} não existe no fonte")


# Recorte do módulo principal: (módulo, primeira linha, última linha).
TRECHOS: dict[str, tuple[str, int, int]] = {
    "edmonds_karp": _limites_classe("algs4.ford_fulkerson", "FordFulkerson"),
    "ford_fulkerson_dfs": _limites_classe("algs4.ford_fulkerson_dfs", "FordFulkersonDFS"),
}

# Módulos observados no modo linha a linha: o algoritmo + toda estrutura
# auxiliar cujo código também aparece no painel.
MODULOS_DETALHADO: dict[str, tuple[str, ...]] = {
    "edmonds_karp": (
        "algs4.ford_fulkerson",
        "algs4.flow_network",
        "algs4.flow_edge",
    ),
    "ford_fulkerson_dfs": (
        "algs4.ford_fulkerson_dfs",
        "algs4.flow_network",
        "algs4.flow_edge",
    ),
}

# Views do painel: (módulo, nome qualificado). Lista explícita = o painel não
# mostra função morta (nunca executada) e o teste de cobertura cobra
# exatamente este conjunto.
#
# Ficam de fora só as funções de UMA linha que não ensinam nada
# (`FlowEdge.from_`, `FlowEdge.to`, `FlowEdge.__str__`, `FlowNetwork.edges`):
# as linhas que as chamam continuam aparecendo nas views que chamaram.
FUNCOES_PAINEL: dict[str, tuple[tuple[str, str], ...]] = {
    "edmonds_karp": (
        ("algs4.ford_fulkerson", "FordFulkerson.__init__"),
        ("algs4.ford_fulkerson", "FordFulkerson.in_cut"),
        ("algs4.ford_fulkerson", "FordFulkerson.validate"),
        ("algs4.ford_fulkerson", "FordFulkerson.has_augmenting_path"),
        ("algs4.ford_fulkerson", "FordFulkerson.excess"),
        ("algs4.ford_fulkerson", "FordFulkerson.is_feasible"),
        ("algs4.ford_fulkerson", "FordFulkerson.check"),
        ("algs4.flow_network", "FlowNetwork.__init__"),
        ("algs4.flow_network", "FlowNetwork.validate_vertex"),
        ("algs4.flow_network", "FlowNetwork.add_edge"),
        ("algs4.flow_network", "FlowNetwork.adj"),
        ("algs4.flow_edge", "FlowEdge.other"),
        ("algs4.flow_edge", "FlowEdge.residual_capacity_to"),
        ("algs4.flow_edge", "FlowEdge.add_residual_flow_to"),
    ),
    "ford_fulkerson_dfs": (
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.__init__"),
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.in_cut"),
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.validate"),
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.has_augmenting_path"),
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.dfs"),
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.excess"),
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.is_feasible"),
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.check"),
        ("algs4.flow_network", "FlowNetwork.__init__"),
        ("algs4.flow_network", "FlowNetwork.validate_vertex"),
        ("algs4.flow_network", "FlowNetwork.add_edge"),
        ("algs4.flow_network", "FlowNetwork.adj"),
        ("algs4.flow_edge", "FlowEdge.other"),
        ("algs4.flow_edge", "FlowEdge.residual_capacity_to"),
        ("algs4.flow_edge", "FlowEdge.add_residual_flow_to"),
    ),
}


def funcao_permitida(algoritmo: str, modulo: str, funcao: str) -> bool:
    """A função participa do modo linha a linha e tem view no painel?"""
    return (modulo, funcao) in FUNCOES_PAINEL[algoritmo]


def classe_do_algoritmo(algoritmo: str) -> type:
    if algoritmo == "edmonds_karp":
        from algs4.ford_fulkerson import FordFulkerson

        return FordFulkerson
    if algoritmo == "ford_fulkerson_dfs":
        from algs4.ford_fulkerson_dfs import FordFulkersonDFS

        return FordFulkersonDFS
    raise ValueError(f"algoritmo desconhecido: {algoritmo!r}")


# ---------------------------------------------------------------------------
# Captura (sys.settrace multi-módulo)
# ---------------------------------------------------------------------------

# Escalares que interessam à narração: nomes de parâmetro/variável por função.
NOMES_ESCALARES = (
    "v",
    "w",
    "s",
    "t",
    "bottle",
    "vertex",
    "delta",
    "a",
    "b",
    "capacidade",
    "mincut_value",
)


def _name_of(frame, modulos: dict[str, str]) -> tuple[str, str] | None:
    """(módulo, nome qualificado) do frame, se ele pertence ao escopo."""
    caminho = os.path.normcase(os.path.abspath(frame.f_code.co_filename))
    modulo = modulos.get(caminho)
    if modulo is None:
        return None
    return modulo, frame.f_code.co_qualname


def _chamador(frame, modulos: dict[str, str]) -> str:
    """Nome qualificado da função que chamou este frame ("" se fora do escopo)."""
    tras = frame.f_back
    if tras is None:
        return ""
    identificacao = _name_of(tras, modulos)
    return identificacao[1] if identificacao else ""


def _objetos(frame) -> tuple[Any, Any]:
    """(algoritmo, rede) encontrados na pilha de frames.

    Dentro de `FlowEdge.residual_capacity_to` o `self` local é a aresta; o
    estado que o painel precisa é o do `FordFulkerson` (valor/marked/edgeTo) e
    o da rede (fluxo de cada aresta), que estão em frames ancestrais.
    """
    algoritmo = None
    rede = None
    atual = frame
    while atual is not None:
        loc = atual.f_locals
        self_local = loc.get("self")
        if (
            algoritmo is None
            and self_local is not None
            and hasattr(self_local, "edgeTo")
            and hasattr(self_local, "value")
            and hasattr(self_local, "marked")
        ):
            algoritmo = self_local
        # A rede pode aparecer como `g` (parâmetro do algoritmo) ou como o
        # `self` do próprio FlowNetwork (durante a montagem da rede).
        if rede is None and self_local is not None and hasattr(self_local, "_adj") and hasattr(self_local, "V"):
            rede = self_local
        for nome in ("g", "G", "rede"):
            obj = loc.get(nome)
            if rede is None and obj is not None and hasattr(obj, "_adj") and hasattr(obj, "V"):
                rede = obj
        atual = atual.f_back
    return algoritmo, rede


def _locais(frame) -> dict:
    """Escalares do frame e dos ancestrais (o mais interno vence)."""
    dados: dict[str, Any] = {}
    atual = frame
    while atual is not None:
        loc = atual.f_locals
        for nome in NOMES_ESCALARES:
            if nome in dados:
                continue
            valor = loc.get(nome)
            if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                dados[nome] = valor
        if "e" not in dados and isinstance(loc.get("e"), FlowEdge):
            aresta = loc["e"]
            dados["e"] = (aresta.v, aresta.w)
        atual = atual.f_back
    return dados


def _aux(frame) -> dict:
    """Snapshot curto do `self` do frame (FlowEdge ou FlowNetwork).

    Num evento de `call` o corpo do `__init__` ainda não rodou: os atributos
    da aresta não existem e os valores vêm dos parâmetros do próprio frame.
    """
    obj = frame.f_locals.get("self")
    loc = frame.f_locals
    if isinstance(obj, FlowEdge):
        capacidade = getattr(obj, "capacity", loc.get("capacity"))
        fluxo = getattr(obj, "flow", loc.get("flow"))
        return {
            "tipo": "aresta",
            "v": getattr(obj, "v", loc.get("v")),
            "w": getattr(obj, "w", loc.get("w")),
            "capacity": None if capacidade is None else float(capacidade),
            "flow": 0.0 if fluxo is None else float(fluxo),
        }
    if isinstance(obj, FlowNetwork):
        return {"tipo": "rede", "V": getattr(obj, "V", 0), "E": getattr(obj, "E", 0)}
    return {}


def _fila(frame) -> list[int]:
    """Conteúdo da fila da BFS (`queue`) neste instante."""
    atual = frame
    while atual is not None:
        fila = atual.f_locals.get("queue")
        if fila is not None:
            try:
                return [int(x) for x in fila]
            except TypeError:
                return []
        atual = atual.f_back
    return []


def _pilha(frame) -> list[int]:
    """Caminho de recursão aberto na DFS (`v` de cada frame de `dfs`)."""
    valores: list[int] = []
    atual = frame
    while atual is not None:
        if atual.f_code.co_qualname.endswith(".dfs"):
            v = atual.f_locals.get("v")
            if isinstance(v, int) and not isinstance(v, bool):
                valores.append(v)
        atual = atual.f_back
    return list(reversed(valores))


def _instantanea_algoritmo(alg) -> dict:
    """Valor, marcados e `edgeTo` do objeto do algoritmo."""
    if alg is None:
        return {}
    edge_to: dict[int, tuple[int, int]] = {}
    for v, e in enumerate(alg.edgeTo):
        if e is not None:
            edge_to[int(v)] = (e.v, e.w)
    return {
        "valor": float(alg.value),
        "marcados": [i for i, m in enumerate(alg.marked) if m],
        "edge_to": edge_to,
    }


def _instantanea_rede(rede) -> dict:
    """(capacidade, fluxo) de cada aresta, na ordem do ARQUIVO."""
    if rede is None:
        return {}
    dados: dict[tuple[int, int], tuple[float, float]] = {}
    for v in range(rede.V):
        for e in rede._adj[v]:
            if e.from_() != v:
                continue
            dados[(e.v, e.w)] = (float(e.capacity), float(e.flow))
    ordenado = sorted(
        dados.items(), key=lambda item: INDICE_ARESTA.get(item[0], len(INDICE_ARESTA))
    )
    return dict(ordenado)


def _adj_da_rede(rede) -> dict[int, list[dict]]:
    """Lista de adjacência REAL de cada vértice, na ORDEM da `Bag`.

    `FlowNetwork._adj[v]` é uma `Bag` do algs4 (`bag.py`: `Node(item,
    oldfirst)`): `add` insere no INÍCIO, então iterar a Bag devolve as arestas
    na ordem REVERSA de inserção (LIFO). É essa ordem que decide qual aresta a
    BFS/DFS examina primeiro e, portanto, o caminho aumentante e o golden — por
    isso é copiada aqui **sem ordenar nem deduplicar** (a mesma aresta aparece
    uma vez na Bag de cada ponta).

    Cada entrada descreve a aresta do ponto de vista de `v`:
    `{"w": extremo oposto, "saida": v é a cauda (`from_()`) → sentido direto,
    "cap": capacidade, "fluxo": fluxo atual}`.

    Barato de propósito: uma passada sobre `_adj` (já percorrida por
    `_instantanea_rede`), sem recomputar nada a partir do algoritmo.
    """
    if rede is None:
        return {}
    adjacencia: dict[int, list[dict]] = {}
    for v in range(rede.V):
        entradas: list[dict] = []
        for e in rede._adj[v]:
            origem = getattr(e, "v", None)
            destino = getattr(e, "w", None)
            if origem is None or destino is None:
                continue  # aresta em construção (evento de `call` do __init__)
            entradas.append(
                {
                    "w": int(destino if origem == v else origem),
                    "saida": bool(origem == v),
                    "cap": float(e.capacity),
                    "fluxo": float(e.flow),
                }
            )
        adjacencia[v] = entradas
    return adjacencia


def _niveis(edge_to: dict, marcados: list[int], s: int) -> dict[int, int | None]:
    """Profundidade de cada vértice na árvore de busca — DERIVADA do `edgeTo`.

    O algs4 **não** tem campo de profundidade em fluxo máximo (`distTo` é do
    Dijkstra): a busca guarda só `marked` + `edgeTo`. Aqui o nível é
    *calculado*, não lido — a árvore é a de `edgeTo` (cada vértice aponta para
    a aresta que o descobriu), com `nivel[s] = 0` e
    `nivel[filho] = nivel[pai] + 1`. Vértice fora da árvore desta busca fica
    `None` (inclusive todos, enquanto `s` ainda não foi marcado). Nada é
    escrito no algoritmo.
    """
    niveis: dict[int, int | None] = {v: None for v in range(V_REDE)}
    if s not in set(marcados):
        return niveis  # nenhuma árvore montada ainda nesta busca

    niveis[s] = 0
    pais: dict[int, int] = {}
    for filho, aresta in edge_to.items():
        filho = int(filho)
        u, w = aresta
        pai = w if u == filho else u
        if int(pai) != filho:
            pais[filho] = int(pai)

    for v in sorted(pais):
        if niveis.get(v) is not None:
            continue
        cadeia: list[int] = []
        atual = v
        vistos: set[int] = set()
        while atual != s and niveis.get(atual) is None:
            if atual in vistos:  # defesa: `edgeTo` nunca tem ciclo
                break
            vistos.add(atual)
            pai = pais.get(atual)
            if pai is None:
                break
            cadeia.append(atual)
            atual = pai
        # A cadeia termina em `s` (nível 0) ou num ancestral já nivelado.
        altura = niveis.get(atual)
        if altura is not None:
            for no in reversed(cadeia):
                altura += 1
                niveis[no] = altura
        # cadeia que não chega a `s`: fica None (não deveria acontecer)
    return niveis


def _janela_augmentacao(algoritmo: str) -> tuple[int, int]:
    """Linhas do `__init__` em que o fluxo está sendo atualizado aresta a aresta.

    Do `v = t` que prepara o 2º laço até o `self.value += bottle`. Entre esses
    eventos a conservação e `|f| = saída(s)` ainda NÃO valem (estado real do
    algoritmo); depois do `+=` voltam a valer. Derivado do ast — nunca digitado.
    """
    modulo = TRECHOS[algoritmo][0]
    arvore = ast.parse(arquivo_modulo(modulo).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.FunctionDef) and no.name == "__init__"):
            continue
        corpo = no.body
        for pos, stmt in enumerate(corpo):
            if not isinstance(stmt, ast.While):
                continue
            augmenta = any(
                isinstance(chamada, ast.Call)
                and getattr(chamada.func, "attr", "") == "add_residual_flow_to"
                for chamada in ast.walk(stmt)
            )
            if augmenta and pos > 0:
                return corpo[pos - 1].lineno, _linha_aumento(modulo)
    raise LookupError(f"{modulo}: não achei o laço de augmentação no fonte")


# Janela por arquivo-fonte: `_em_augmentacao` só tem o frame nas mãos.
@lru_cache(maxsize=None)
def _janelas_augmentacao() -> dict[str, tuple[int, int]]:
    return {
        os.path.normcase(os.path.abspath(arquivo_modulo(TRECHOS[a][0]))): _janela_augmentacao(a)
        for a in TRECHOS
    }


def _em_augmentacao(frame) -> bool:
    """A execução está dentro da janela de augmentação (ver acima)?"""
    janelas = _janelas_augmentacao()
    atual = frame
    while atual is not None:
        janela = janelas.get(os.path.normcase(os.path.abspath(atual.f_code.co_filename)))
        if (
            janela is not None
            and atual.f_code.co_qualname.endswith(".__init__")
            and janela[0] <= atual.f_lineno <= janela[1]
        ):
            return True
        atual = atual.f_back
    return False


def _snapshot(frame, modulo: str, funcao: str, tipo: str, chamador: str) -> dict:
    algoritmo, rede = _objetos(frame)
    return {
        "frame": frame,
        "modulo": modulo,
        "funcao": funcao,
        "tipo": tipo,
        "lineno": frame.f_lineno,
        "chamador": chamador,
        "augmentando": _em_augmentacao(frame),
        "alg": _instantanea_algoritmo(algoritmo),
        "rede": _instantanea_rede(rede),
        "adj": _adj_da_rede(rede),
        "aux": _aux(frame),
        "locais": _locais(frame),
        "fila": _fila(frame),
        "pilha": _pilha(frame),
    }


def _gravar(
    modulos: str | tuple[str, ...],
    executar: Callable[[], Any],
) -> tuple[Any, list[dict]]:
    """Roda `executar()` observando as linhas dos módulos indicados.

    O escopo inclui o módulo do algoritmo **e** os módulos das estruturas que
    ele chama (FlowNetwork, FlowEdge). Assim o painel pode mostrar a função
    real em execução, inclusive quando a pilha de chamadas desce para elas.
    """
    if isinstance(modulos, str):
        modulos = (modulos,)

    mapa: dict[str, str] = {}
    for nome_modulo in modulos:
        modulo = sys.modules[nome_modulo]
        mapa[os.path.normcase(os.path.abspath(modulo.__file__))] = nome_modulo

    eventos: list[dict] = []

    def trace(frame, event, arg):
        identificacao = _name_of(frame, mapa)
        if identificacao is None:
            return None
        nome_modulo, funcao = identificacao

        def local(frame, event, arg):
            if event == "line":
                eventos.append(
                    _snapshot(frame, nome_modulo, funcao, "line", _chamador(frame, mapa))
                )
            return local

        if event == "call":
            eventos.append(
                _snapshot(frame, nome_modulo, funcao, "call", _chamador(frame, mapa))
            )
            return local
        if event == "line":
            eventos.append(
                _snapshot(frame, nome_modulo, funcao, "line", _chamador(frame, mapa))
            )
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

PAUSA_CURTA = 0.55
PAUSA_MEDIA = 1.0
PAUSA_LONGA = 1.7

SEM_DESTAQUE: tuple = ("linha", None, None, None)


def _caminho(edge_to: dict, marcados: list[int], s: int, t: int) -> list[tuple[int, int]]:
    """Caminho s→t em `edgeTo`, como pares (de, para) na direção do fluxo."""
    if t == s or t not in marcados:
        return []
    passos: list[tuple[int, int]] = []
    vistos: set[int] = set()
    v = t
    while v != s:
        if v in vistos:
            return []
        vistos.add(v)
        aresta = edge_to.get(v)
        if aresta is None:
            return []
        u, w = aresta
        anterior = w if u == v else u
        passos.append((anterior, v))
        v = anterior
    passos.reverse()
    return passos


def _corte_capacidade(rede: dict, corte: list[int]) -> float:
    """Soma das capacidades das arestas que cruzam o corte (S → T)."""
    lado = set(corte)
    total = 0.0
    for (u, w), (capacidade, _fluxo) in rede.items():
        if u in lado and w not in lado:
            total += capacidade
    return total


def _estado(snap: dict, contador: dict) -> dict:
    """Estado completo do painel para um evento do trace."""
    rede = snap.get("rede") or {}
    alg = snap.get("alg") or {}
    locais = snap.get("locais") or {}

    arestas: list[tuple[int, int, float]] = []
    capacidades: dict[tuple[int, int], float] = {}
    fluxos: dict[tuple[int, int], float] = {}
    residual_direta: dict[tuple[int, int], float] = {}
    residual_reversa: dict[tuple[int, int], float] = {}

    for (u, w), (capacidade, fluxo) in rede.items():
        arestas.append((u, w, capacidade))
        capacidades[(u, w)] = capacidade
        fluxos[(u, w)] = fluxo
        residual_direta[(u, w)] = capacidade - fluxo
        residual_reversa[(u, w)] = fluxo

    marcados = list(alg.get("marcados") or [])
    edge_to = dict(alg.get("edge_to") or {})
    caminho = _caminho(edge_to, marcados, S_FONTE, T_SUMIDOURO)

    return {
        "V": V_REDE,
        "E": len(arestas),
        "s": S_FONTE,
        "t": T_SUMIDOURO,
        "arestas": arestas,
        "capacidades": capacidades,
        "fluxos": fluxos,
        "residual_direta": residual_direta,
        "residual_reversa": residual_reversa,
        "marcados": marcados,
        "edge_to": edge_to,
        # Bag REAL de cada vértice, na ordem de iteração do `FlowNetwork`
        # (`{v: [{"w", "saida", "cap", "fluxo"}, ...]}`). Ordem = dado do
        # algoritmo; não reordene no painel.
        "adj": dict(snap.get("adj") or {}),
        # Profundidade na árvore de busca DERIVADA do `edgeTo` (o algs4 não
        # tem `distTo` aqui): `{v: int|None}`, raiz s=0, filho=pai+1.
        "nivel": _niveis(edge_to, marcados, S_FONTE),
        "caminho": caminho,
        "gargalo": contador.get("gargalo"),
        "valor": float(alg.get("valor") or 0.0),
        "fila": list(snap.get("fila") or []),
        "pilha": list(snap.get("pilha") or []),
        "iteracao": contador.get("iteracao", 0),
        "augmentacoes": contador.get("augmentacoes", 0),
        "inspecoes": contador.get("inspecoes", 0),
        # Entre `v = t` do 2º laço e o `value += bottle` o fluxo é atualizado
        # aresta por aresta: conservação e |f| ainda NÃO valem (estado real).
        "augmentando": bool(snap.get("augmentando")),
        "corte": list(marcados),
        "corte_capacidade": _corte_capacidade(rede, marcados),
        # Parâmetros escalares do frame que executou a linha.
        "v": locais.get("v"),
        "w": locais.get("w"),
        "s_frame": locais.get("s"),
        "t_frame": locais.get("t"),
        "e": locais.get("e"),
        "bottle": locais.get("bottle"),
        "vertex": locais.get("vertex"),
        "delta": locais.get("delta"),
        "aux": dict(snap.get("aux") or {}),
    }


def _linha_aumento(modulo: str) -> int:
    """Linha do `self.value += bottle` (o fecho de cada augmentação)."""
    arvore = ast.parse(arquivo_modulo(modulo).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if (
            isinstance(no, ast.AugAssign)
            and isinstance(no.target, ast.Attribute)
            and no.target.attr == "value"
        ):
            return no.lineno
    raise LookupError(f"{modulo}: não achei 'self.value += ...' no fonte")


@lru_cache(maxsize=None)
def _contadores_base(algoritmo: str) -> tuple[str, tuple[str, ...], int]:
    """(função de busca, chamadores que inspecionam aresta, linha do aumento)."""
    modulo_principal = TRECHOS[algoritmo][0]
    classe = "FordFulkerson" if algoritmo == "edmonds_karp" else "FordFulkersonDFS"
    busca = f"{classe}.has_augmenting_path"
    if algoritmo == "edmonds_karp":
        inspetores = (busca,)
    else:
        inspetores = (f"{classe}.dfs",)
    return busca, inspetores, _linha_aumento(modulo_principal)


def _contadores(eventos: list[dict], algoritmo: str) -> list[dict]:
    """Contadores acumulados por evento (determinísticos, sem timestamp).

    inspecoes   -- quantas arestas a BUSCA examinou até aqui
                   (`e.residual_capacity_to(w) > 0`), somando todas as buscas;
    iteracao    -- número da busca em curso (1-based);
    augmentacoes-- quantas augmentações já terminaram (`value += bottle`);
    gargalo     -- gargalo da última augmentação concluída.
    """
    busca, inspetores, linha_aumento = _contadores_base(algoritmo)
    modulo_principal = TRECHOS[algoritmo][0]
    inspecoes = 0
    iteracao = 0
    augmentacoes = 0
    gargalo = None
    resultado: list[dict] = []
    for ev in eventos:
        if ev["tipo"] == "call" and ev["funcao"] == busca:
            iteracao += 1
        if (
            ev["tipo"] == "call"
            and ev["funcao"] == "FlowEdge.residual_capacity_to"
            and ev["chamador"] in inspetores
        ):
            inspecoes += 1
        if (
            ev["tipo"] == "line"
            and ev["modulo"] == modulo_principal
            and ev["lineno"] == linha_aumento
        ):
            augmentacoes += 1
            if "bottle" in ev["locais"]:
                gargalo = ev["locais"]["bottle"]
        resultado.append(
            {
                "inspecoes": inspecoes,
                "iteracao": iteracao,
                "augmentacoes": augmentacoes,
                "gargalo": gargalo,
            }
        )
    return resultado


# ---------------------------------------------------------------------------
# Narração
# ---------------------------------------------------------------------------

# Cada entrada é (texto, destaque, pausa). `texto` é formatado com o contexto
# do passo; `destaque` é None (sem destaque) ou uma função do contexto. O
# validador cobra que TODA linha executada das views tenha entrada aqui —
# nenhum passo cai na rede de segurança em silêncio.
TEXTOS: dict[tuple[str, int], tuple[str, Any, float]] = {}


def _linha_do_def(modulo: str, qualname: str) -> int:
    """Linha do `def` de `Classe.metodo` no fonte real do módulo."""
    classe, _, nome = qualname.rpartition(".")
    arvore = ast.parse(arquivo_modulo(modulo).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.ClassDef) and no.name == classe:
            for filho in no.body:
                if isinstance(filho, ast.FunctionDef) and filho.name == nome:
                    return filho.lineno
    raise LookupError(f"{modulo}: função {qualname!r} não existe no fonte")


# Os textos abaixo estão escritos com os números de linha de
# `FordFulkerson` (BFS). `excess`, `is_feasible` e `check` têm o MESMO corpo
# nas duas variantes, mas começam em linhas diferentes no fonte da DFS; o
# deslocamento é medido no ast, nunca digitado.
DESLOC_FUNCAO: dict[str, int] = {}
for _qual in ("FordFulkersonDFS.excess", "FordFulkersonDFS.is_feasible", "FordFulkersonDFS.check"):
    _nome = _qual.split(".", 1)[1]
    DESLOC_FUNCAO[_qual] = _linha_do_def("algs4.ford_fulkerson_dfs", _qual) - _linha_do_def(
        "algs4.ford_fulkerson", f"FordFulkerson.{_nome}"
    )


def _texto(funcao: str, linha: int, texto: str, destaque: Any = None, pausa: float = PAUSA_CURTA) -> None:
    TEXTOS[(funcao, linha + DESLOC_FUNCAO.get(funcao, 0))] = (texto, destaque, pausa)


def _d_busca(status: str) -> Callable[[dict], tuple]:
    def montar(ctx: dict) -> tuple:
        return ("busca", ctx["v"], ctx["w"], status)

    return montar


def _d_descoberto(ctx: dict) -> tuple:
    return ("busca", ctx["v"], ctx["w"], "descoberto")


def _d_caminho(ctx: dict) -> tuple:
    return ("caminho", ctx["caminho_u"], ctx["caminho_v"], "aumentante")


def _d_aumento(ctx: dict) -> tuple:
    return ("aumento", ctx["caminho_u"], ctx["caminho_v"], "augmenta")


def _d_valor(ctx: dict) -> tuple:
    return ("valor", None, None, None)


def _d_corte_aresta(ctx: dict) -> tuple:
    return ("corte", ctx["e_u"], ctx["e_v"], "cruza")


def _d_corte_vertice(ctx: dict) -> tuple:
    return ("corte", ctx["v"], None, "lado_s" if ctx["no_corte"] else "lado_t")


def _d_insere(ctx: dict) -> tuple:
    return ("aresta", ctx["e_u"], ctx["e_v"], "insere")


def _d_inicio(ctx: dict) -> tuple:
    return ("inicio", None, None, None)


def _d_while_busca(ctx: dict) -> tuple:
    return ("busca", None, None, "nova" if ctx["achou_caminho"] else "fim")


def _d_corte_ok(ctx: dict) -> tuple:
    return ("corte", None, None, "fechado")


# -- FlowNetwork -----------------------------------------------------------

_texto("FlowNetwork.__init__", 121, "arquivo = kwargs.get('file'): a rede vem de um arquivo?")
_texto("FlowNetwork.__init__", 122, "if isinstance(v, (str, Path)): o 1º argumento é o caminho?")
_texto("FlowNetwork.__init__", 123, "arquivo = v: o caminho passa a ser a fonte da rede")
_texto("FlowNetwork.__init__", 124, "v = 0: V vem do cabeçalho do arquivo, não do argumento")
_texto("FlowNetwork.__init__", 125, "if arquivo is not None: lê a rede do arquivo", pausa=PAUSA_MEDIA)
_texto("FlowNetwork.__init__", 126, "V, arestas = _ler_arquivo(arquivo): V, E e as triplas u w capacidade", pausa=PAUSA_MEDIA)
_texto("FlowNetwork.__init__", 127, "self.V = {V}: {V} vértices declarados no cabeçalho")
_texto("FlowNetwork.__init__", 128, "self.E = 0: nenhuma aresta inserida ainda")
_texto("FlowNetwork.__init__", 129, "self._adj = [Bag() for _ in range(V)]: uma Bag por vértice")
_texto("FlowNetwork.__init__", 130, "for a, b, capacidade in arestas: próxima aresta do arquivo")
_texto("FlowNetwork.__init__", 131, "self.add_edge(FlowEdge({e_u}, {e_v}, {cap_aresta:g})): aresta entra na rede", _d_insere, PAUSA_MEDIA)
_texto("FlowNetwork.__init__", 132, "return: rede montada a partir do arquivo", pausa=PAUSA_MEDIA)

_texto("FlowNetwork.validate_vertex", 148, "if not (0 <= {v} < {V}): o vértice existe?")
_texto("FlowNetwork.validate_vertex", 149, "raise: vértice fora do intervalo", pausa=PAUSA_MEDIA)

_texto("FlowNetwork.add_edge", 152, "v = e.from_() = {e_u}: extremo de saída")
_texto("FlowNetwork.add_edge", 153, "w = e.to() = {e_v}: extremo de chegada")
_texto("FlowNetwork.add_edge", 154, "self.validate_vertex({e_u})")
_texto("FlowNetwork.add_edge", 155, "self.validate_vertex({e_v})")
_texto("FlowNetwork.add_edge", 156, "self._adj[{e_u}].add(e): a aresta entra na Bag de {e_u}")
_texto("FlowNetwork.add_edge", 157, "self._adj[{e_v}].add(e): e também na Bag de {e_v} (aresta incidente)")
_texto("FlowNetwork.add_edge", 158, "self.E += 1: E = {E}", pausa=PAUSA_MEDIA)

_texto("FlowNetwork.adj", 161, "self.validate_vertex({v})")
_texto("FlowNetwork.adj", 162, "return self._adj[{v}]: Bag das arestas incidentes a {v}", pausa=PAUSA_MEDIA)

# -- FlowEdge --------------------------------------------------------------

_texto("FlowEdge.other", 56, "if {vertex} == self.v ({aux_v}): o vértice é o rabo?")
_texto("FlowEdge.other", 57, "return self.w = {aux_w}: o outro extremo")
_texto("FlowEdge.other", 58, "elif {vertex} == self.w ({aux_w}): é a cabeça?")
_texto("FlowEdge.other", 59, "return self.v = {aux_v}: o outro extremo")
_texto("FlowEdge.other", 60, "else: nenhum dos dois extremos", pausa=PAUSA_MEDIA)
_texto("FlowEdge.other", 61, "raise: aresta inválida para este vértice", pausa=PAUSA_MEDIA)

_texto("FlowEdge.residual_capacity_to", 64, "if {vertex} == self.v ({aux_v}): sentido REVERSO (desfazer)?")
_texto("FlowEdge.residual_capacity_to", 65, "return flow = {aux_flow:g}: residual reverso = fluxo", pausa=PAUSA_MEDIA)
_texto("FlowEdge.residual_capacity_to", 66, "elif {vertex} == self.w ({aux_w}): sentido DIRETO?")
_texto("FlowEdge.residual_capacity_to", 67, "return capacity - flow = {aux_cap:g} - {aux_flow:g} = {aux_res:g}: residual direto", pausa=PAUSA_MEDIA)
_texto("FlowEdge.residual_capacity_to", 68, "else: nenhum dos dois extremos", pausa=PAUSA_MEDIA)
_texto("FlowEdge.residual_capacity_to", 69, "raise: aresta inválida para este vértice", pausa=PAUSA_MEDIA)

_texto("FlowEdge.add_residual_flow_to", 72, "if not (delta >= 0): delta = {delta:g} é válido?")
_texto("FlowEdge.add_residual_flow_to", 74, "if {vertex} == self.v ({aux_v}): sentido reverso?")
_texto("FlowEdge.add_residual_flow_to", 75, "self.flow -= {delta:g}: desfaz fluxo na aresta reversa", pausa=PAUSA_MEDIA)
_texto("FlowEdge.add_residual_flow_to", 76, "elif {vertex} == self.w ({aux_w}): sentido direto?")
_texto("FlowEdge.add_residual_flow_to", 77, "self.flow += {delta:g}: aumenta o fluxo da aresta", pausa=PAUSA_MEDIA)
_texto("FlowEdge.add_residual_flow_to", 79, "raise: aresta inválida para este vértice", pausa=PAUSA_MEDIA)
_texto("FlowEdge.add_residual_flow_to", 81, "if abs(flow) <= eps: arredonda para 0?")
_texto("FlowEdge.add_residual_flow_to", 82, "self.flow = 0.0: zera o resíduo numérico")
_texto("FlowEdge.add_residual_flow_to", 83, "if abs(flow - capacity) <= eps: arredonda para a capacidade?")
_texto("FlowEdge.add_residual_flow_to", 84, "self.flow = capacity: satura exatamente")
_texto("FlowEdge.add_residual_flow_to", 85, "if not (flow >= 0): o fluxo ficou negativo?", pausa=PAUSA_MEDIA)
_texto("FlowEdge.add_residual_flow_to", 87, "if not (flow <= capacity): o fluxo passou da capacidade?", pausa=PAUSA_MEDIA)

# -- FordFulkerson(__init__) — comum às duas variantes ----------------------

for _classe in ("FordFulkerson", "FordFulkersonDFS"):
    _f = _classe + ".__init__"
    _texto(_f, 32, "self.V = g.V = {V}: o algoritmo herda o tamanho da rede")
    _texto(_f, 33, "self.validate({s}): a origem é um vértice válido?")
    _texto(_f, 34, "self.validate({t}): o sumidouro é um vértice válido?")
    _texto(_f, 35, "if {s} == {t}: origem igual ao sumidouro?", pausa=PAUSA_MEDIA)
    _texto(_f, 36, "raise: origem igual ao sumidouro", pausa=PAUSA_MEDIA)
    _texto(_f, 38, "self.marked = [False] * V: ninguém alcançado na residual")
    _texto(_f, 39, "self.edgeTo = [None] * V: caminho aumentante vazio")
    _texto(_f, 40, "self.value = 0.0: fluxo inicial zero")
    _texto(_f, 41, "if not self.is_feasible(g, {s}, {t}): o fluxo inicial é viável?", pausa=PAUSA_MEDIA)
    _texto(_f, 42, "raise: fluxo inicial inviável", pausa=PAUSA_MEDIA)
    _texto(_f, 45, "self.value = self.excess(g, {t}) = {valor:g}: valor inicial do fluxo", pausa=PAUSA_MEDIA)
    _texto(
        _f,
        46,
        "while has_augmenting_path(g, {s}, {t}): pergunta se ainda há caminho na residual",
        None,
        PAUSA_MEDIA,
    )
    _texto(_f, 49, "bottle = inf: começa o cálculo do gargalo")
    _texto(_f, 50, "v = {t}: volta pelo caminho a partir do sumidouro")
    _texto(_f, 51, "while v != {s}: percorre o caminho de trás para frente")
    _texto(
        _f,
        52,
        "bottle = min(bottle, residual de {caminho_u}->{caminho_v}) = {bottle:g}",
        _d_caminho,
        PAUSA_MEDIA,
    )
    _texto(_f, 53, "v = edgeTo[v].other(v) = {v}: passo anterior", None, PAUSA_CURTA)
    _texto(_f, 56, "v = {t}: segundo laço, agora para augmentar")
    _texto(_f, 57, "while v != {s}: percorre o caminho de novo")
    _texto(
        _f,
        58,
        "add_residual_flow_to({caminho_v}, {gargalo:g}): empurra o gargalo no sentido do caminho",
        _d_aumento,
        PAUSA_MEDIA,
    )
    _texto(_f, 59, "v = edgeTo[v].other(v) = {v}: passo anterior")
    _texto(_f, 61, "self.value += {gargalo:g}: |f| = {valor:g}", _d_valor, PAUSA_LONGA)
    _texto(_f, 64, "assert self.check(g, {s}, {t}): viabilidade e max-flow = min-cut", pausa=PAUSA_LONGA)

    _texto(_classe + ".in_cut", 67, "self.validate({v})")
    _texto(_classe + ".in_cut", 68, "return self.marked[{v}] = {no_corte}: {v} está do lado de s?", _d_corte_vertice, PAUSA_MEDIA)

    _texto(_classe + ".validate", 71, "if 0 <= {v} < {V}: vértice válido?")
    _texto(_classe + ".validate", 72, "raise: vértice fora do intervalo", pausa=PAUSA_MEDIA)

    _texto(_classe + ".excess", 99, "excess = 0.0: saldo de fluxo no vértice {v}")
    _texto(_classe + ".excess", 100, "for e in g.adj({v}): arestas incidentes a {v}")
    _texto(_classe + ".excess", 101, "if {v} == e.from_(): a aresta SAI de {v}?")
    _texto(_classe + ".excess", 102, "excess -= {aux_flow:g}: fluxo que sai desconta")
    _texto(_classe + ".excess", 103, "else: a aresta ENTRA em {v}")
    _texto(_classe + ".excess", 104, "excess += {aux_flow:g}: fluxo que entra soma")
    _texto(_classe + ".excess", 105, "return excess: excesso de fluxo em {v}", pausa=PAUSA_MEDIA)

    _texto(_classe + ".is_feasible", 109, "for v in range(V): confere a capacidade de toda aresta")
    _texto(_classe + ".is_feasible", 110, "for e in g.adj({v})")
    _texto(_classe + ".is_feasible", 111, "if 0 - eps <= flow <= capacity + eps: capacidade respeitada?")
    _texto(_classe + ".is_feasible", 112, "print: aresta viola a capacidade", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 113, "return False", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 116, "if abs(value + excess({s})) > eps: a saída de {s} bate com |f|?", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 117, "print: excesso na origem", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 118, "print: valor do fluxo", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 119, "return False", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 120, "if abs(value - excess({t})) > eps: a entrada em {t} bate com |f|?", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 121, "print: excesso no sumidouro", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 122, "print: valor do fluxo", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 123, "return False", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 124, "for v in range(V): agora os vértices internos")
    _texto(_classe + ".is_feasible", 125, "if {v} == {s} or {v} == {t}: pula origem e sumidouro")
    _texto(_classe + ".is_feasible", 126, "continue: origem/sumidouro podem ter excesso")
    _texto(_classe + ".is_feasible", 127, "elif abs(excess({v})) > eps: conservação em {v}?", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 128, "print: fluxo líquido diferente de zero", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 129, "return False", pausa=PAUSA_MEDIA)
    _texto(_classe + ".is_feasible", 130, "return True: o fluxo é viável", pausa=PAUSA_MEDIA)

    _texto(_classe + ".check", 134, "if not is_feasible(g, s, t): o fluxo é viável?", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 135, "print: fluxo inviável", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 136, "return False", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 139, "if not in_cut({s}): {s} está do lado da origem?", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 140, "print: origem fora do lado da origem", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 141, "return False", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 142, "if in_cut({t}): {t} ficou fora do lado da origem?", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 143, "print: sumidouro no lado da origem", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 144, "return False", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 147, "mincut_value = 0.0: soma das capacidades que cruzam o corte")
    _texto(_classe + ".check", 148, "for v in range(V): percorre todos os vértices")
    _texto(_classe + ".check", 149, "for e in g.adj({v})")
    _texto(
        _classe + ".check",
        150,
        "if v == e.from_() and in_cut(from) and not in_cut(to): {e_u}->{e_v} cruza o corte?",
        _d_corte_aresta,
        PAUSA_MEDIA,
    )
    _texto(_classe + ".check", 151, "mincut_value += {aux_cap:g}: capacidade do corte = {corte_capacidade:g}")
    _texto(_classe + ".check", 152, "if abs(min_cut - value) > eps: valor do corte = valor do fluxo?", pausa=PAUSA_LONGA)
    _texto(_classe + ".check", 153, "print: valores diferentes", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 154, "return False", pausa=PAUSA_MEDIA)
    _texto(_classe + ".check", 156, "return True: |f| = {valor:g} = capacidade do corte", _d_corte_ok, PAUSA_LONGA)

# -- Busca: BFS (Edmonds-Karp) --------------------------------------------

_texto("FordFulkerson.has_augmenting_path", 75, "self.edgeTo = [None] * V: caminho novo a cada busca")
_texto("FordFulkerson.has_augmenting_path", 76, "self.marked = [False] * V: ninguém alcançado")
_texto("FordFulkerson.has_augmenting_path", 79, "queue = deque(): fila FIFO da BFS")
_texto("FordFulkerson.has_augmenting_path", 80, "queue.append({s}): a origem entra na fila")
_texto("FordFulkerson.has_augmenting_path", 81, "self.marked[{s}] = True: origem marcada")
_texto(
    "FordFulkerson.has_augmenting_path",
    82,
    "while queue: {fila_qtd} na fila · {t} {resposta_t}",
    None,
    PAUSA_MEDIA,
)
_texto(
    "FordFulkerson.has_augmenting_path",
    83,
    "v = queue.popleft() = {v}: próximo vértice da BFS",
    None,
    PAUSA_MEDIA,
)
_texto("FordFulkerson.has_augmenting_path", 84, "for e in g.adj({v}): arestas de {v} (Bag = ordem reversa de inserção)")
_texto("FordFulkerson.has_augmenting_path", 85, "w = e.other({v}) = {w}", _d_busca("olhando"))
_texto(
    "FordFulkerson.has_augmenting_path",
    88,
    "if residual_capacity_to({w}) > 0: residual {residual:g} → {resposta_residual}",
    _d_busca("examina"),
    PAUSA_MEDIA,
)
_texto(
    "FordFulkerson.has_augmenting_path",
    89,
    "if not marked[{w}]: {resposta_marcado}",
    None,
    PAUSA_MEDIA,
)
_texto("FordFulkerson.has_augmenting_path", 90, "edgeTo[{w}] = {e_u}->{e_v}: aresta que descobriu {w}", _d_descoberto, PAUSA_MEDIA)
_texto("FordFulkerson.has_augmenting_path", 91, "marked[{w}] = True: {w} descoberto")
_texto("FordFulkerson.has_augmenting_path", 92, "queue.append({w}): {w} entra na fila")
_texto(
    "FordFulkerson.has_augmenting_path",
    95,
    "return marked[{t}] = {achou_caminho}: {resposta_busca}",
    _d_while_busca,
    PAUSA_LONGA,
)

# -- Busca: DFS (Ford-Fulkerson) ------------------------------------------

_texto("FordFulkersonDFS.has_augmenting_path", 75, "self.edgeTo = [None] * V: caminho novo a cada busca")
_texto("FordFulkersonDFS.has_augmenting_path", 76, "self.marked = [False] * V: ninguém alcançado")
_texto("FordFulkersonDFS.has_augmenting_path", 79, "self.marked[{s}] = True: a origem começa marcada")
_texto("FordFulkersonDFS.has_augmenting_path", 80, "self.dfs(g, {s}, {t}): mergulha na rede residual", None, PAUSA_MEDIA)
_texto(
    "FordFulkersonDFS.has_augmenting_path",
    83,
    "return marked[{t}] = {achou_caminho}: {resposta_busca}",
    _d_while_busca,
    PAUSA_LONGA,
)

_texto("FordFulkersonDFS.dfs", 86, "if {v} == {t}: chegou ao sumidouro?", None, PAUSA_MEDIA)
_texto("FordFulkersonDFS.dfs", 87, "return True: caminho encontrado — a busca para aqui", None, PAUSA_LONGA)
_texto("FordFulkersonDFS.dfs", 88, "for e in g.adj({v}): arestas de {v} (Bag = ordem reversa de inserção)")
_texto("FordFulkersonDFS.dfs", 89, "w = e.other({v}) = {w}", _d_busca("olhando"))
_texto(
    "FordFulkersonDFS.dfs",
    92,
    "if residual_capacity_to({w}) > 0: residual {residual:g} → {resposta_residual}",
    _d_busca("examina"),
    PAUSA_MEDIA,
)
_texto("FordFulkersonDFS.dfs", 93, "if not marked[{w}]: {resposta_marcado}", None, PAUSA_MEDIA)
_texto("FordFulkersonDFS.dfs", 94, "edgeTo[{w}] = {e_u}->{e_v}: aresta que descobriu {w}", _d_descoberto, PAUSA_MEDIA)
_texto("FordFulkersonDFS.dfs", 95, "marked[{w}] = True: {w} descoberto")
_texto("FordFulkersonDFS.dfs", 96, "if self.dfs(g, {w}, {t}): desce para {w}", None, PAUSA_MEDIA)
_texto("FordFulkersonDFS.dfs", 97, "return True: propaga o achado para quem chamou", None, PAUSA_LONGA)
_texto("FordFulkersonDFS.dfs", 98, "return False: beco sem saída em {v}", None, PAUSA_MEDIA)


def _gargalo_do_caminho(estado: dict, caminho: list[tuple[int, int]]) -> float:
    """Menor residual ao longo do caminho (o `bottle` que o algoritmo vai achar).

    Usado na legenda do `while` que decide a próxima augmentação: nesse
    instante `bottle` ainda não foi calculado (ou é o da iteração anterior).
    """
    if not caminho:
        return 0.0
    minimo = float("inf")
    for u, v in caminho:
        if (u, v) in estado["residual_direta"]:
            minimo = min(minimo, estado["residual_direta"][(u, v)])
        else:
            minimo = min(minimo, estado["residual_reversa"].get((v, u), 0.0))
    return 0.0 if minimo == float("inf") else minimo


def _contexto(ev: dict, depois: dict, estado: dict) -> dict:
    """Valores usados nos templates de narração (todos reais do trace).

    Os escalares vêm do estado DEPOIS da linha: uma linha que atribui
    `v = queue.popleft()` já aparece com o `v` novo na legenda. Quando a linha
    encerra o frame (o evento seguinte é do chamador), ficamos com os valores
    do próprio frame.
    """
    locais = dict(ev.get("locais") or {})
    proximos = dict(depois.get("locais") or {})
    base = {**locais, **proximos} if depois.get("frame") is ev.get("frame") else locais
    aux = dict(estado.get("aux") or {})
    if not aux:
        aux = dict(ev.get("aux") or {})
    aresta = base.get("e")
    if aresta is not None and aux.get("tipo") != "aresta":
        # A aresta do laço: usamos o snapshot do frame (fluxo do instante).
        aux = {
            "tipo": "aresta",
            "v": aresta[0],
            "w": aresta[1],
            "capacity": estado["capacidades"].get(aresta, 0.0),
            "flow": estado["fluxos"].get(aresta, 0.0),
        }

    v = base.get("v")
    w = base.get("w")
    vertex = base.get("vertex")

    # Identidade da aresta em foco: `e` do laço > `self` (FlowEdge) > `a`/`b`
    # da montagem da rede > `v`/`w` do construtor da aresta.
    if aresta is not None:
        e_u, e_v = aresta
    elif aux.get("tipo") == "aresta" and aux.get("v") is not None:
        e_u, e_v = aux.get("v"), aux.get("w")
    elif "a" in base and "b" in base:
        e_u, e_v = base.get("a"), base.get("b")
    elif base.get("v") is not None and base.get("w") is not None:
        e_u, e_v = base.get("v"), base.get("w")
    else:
        e_u, e_v = None, None

    # `w = e.other(v)` ainda não atribuiu `w` no instante do evento.
    if w is None and e_u is not None and v is not None:
        w = e_v if v == e_u else e_u
    if v is None and e_u is not None:
        v = e_u

    # Residual no sentido `v -> w` (o que a busca está testando).
    residual = None
    if e_u is not None and e_v is not None and w is not None:
        if w == e_v:
            residual = estado["residual_direta"].get((e_u, e_v))
        elif w == e_u:
            residual = estado["residual_reversa"].get((e_u, e_v))
    if residual is None:
        residual = 0.0

    marcados = set(estado.get("marcados") or [])
    caminho = estado.get("caminho") or []
    # Aresta do caminho que chega no vértice `v` do frame (se houver).
    caminho_u = caminho_v = None
    for de, para in caminho:
        if v is not None and para == v:
            caminho_u, caminho_v = de, para
    if caminho_u is None and caminho:
        caminho_u, caminho_v = caminho[-1]
    if caminho_u is None:
        caminho_u, caminho_v = v, w

    proximo_no_caminho = None
    if v is not None:
        for de, para in caminho:
            if para == v:
                proximo_no_caminho = de
                break
    achou = estado["t"] in marcados
    corte_txt = "{" + ", ".join(str(x) for x in sorted(marcados)) + "}"
    caminho_txt = (
        " → ".join([str(estado["s"])] + [str(para) for _de, para in caminho])
        if caminho
        else "—"
    )
    bottle_frame = base.get("bottle")
    gargalo_caminho = _gargalo_do_caminho(estado, caminho)
    gargalo = bottle_frame if bottle_frame is not None else gargalo_caminho

    return {
        "V": estado["V"],
        "E": estado["E"],
        "s": estado["s"],
        "t": estado["t"],
        "v": v,
        "w": w,
        "vertex": vertex,
        "e": aresta,
        "e_u": e_u,
        "e_v": e_v,
        "delta": base.get("delta"),
        "bottle": bottle_frame,
        "aux_v": aux.get("v"),
        "aux_w": aux.get("w"),
        "aux_cap": aux.get("capacity"),
        "aux_flow": aux.get("flow"),
        "aux_res": (aux.get("capacity") or 0.0) - (aux.get("flow") or 0.0),
        "cap_aresta": estado["capacidades"].get((e_u, e_v), 0.0),
        "fluxo_aresta": estado["fluxos"].get((e_u, e_v), 0.0),
        "residual": residual,
        "w_marcado": w in marcados if w is not None else False,
        "resposta_residual": "passa" if residual > 0 else "saturada → ignora",
        "resposta_marcado": (
            "já marcado → ignora" if w in marcados else f"novo → descobre {w}"
        ),
        "resposta_t": "alcançado" if achou else "ainda não alcançado",
        "resposta_busca": (
            f"achou caminho {caminho_txt} (gargalo {gargalo_caminho:g})"
            if achou and caminho
            else "sem caminho aumentante — o laço termina"
        ),
        "achou_caminho": achou,
        "fila_qtd": len(estado.get("fila") or []),
        "fila_txt": "[" + ", ".join(str(x) for x in (estado.get("fila") or [])) + "]",
        "pilha_txt": "[" + ", ".join(str(x) for x in (estado.get("pilha") or [])) + "]",
        "marcados_txt": corte_txt,
        "corte_txt": corte_txt,
        "corte_capacidade": estado.get("corte_capacidade") or 0.0,
        "valor": estado["valor"],
        "gargalo": gargalo,
        "gargalo_caminho": gargalo_caminho,
        "iteracao": estado["iteracao"],
        "augmentacoes": estado["augmentacoes"],
        "inspecoes": estado["inspecoes"],
        "caminho_txt": caminho_txt,
        "caminho_u": caminho_u,
        "caminho_v": caminho_v,
        "proximo_no_caminho": proximo_no_caminho,
        "no_corte": v in marcados if v is not None else False,
    }


def _descrever(ev: dict, depois: dict, estado: dict) -> tuple[str, tuple, float]:
    """(ação, destaque, pausa) do passo, a partir dos textos declarados."""
    chave = (ev["funcao"], ev["lineno"])
    entrada = TEXTOS.get(chave)
    if entrada is None:
        # Rede de segurança: o validador cobra que ela nunca seja usada.
        return f"{ev['funcao']}(): linha {ev['lineno']}", SEM_DESTAQUE, PAUSA_CURTA
    modelo, destaque, pausa = entrada
    ctx = _contexto(ev, depois, estado)
    acao = modelo.format(**ctx)
    marca = destaque(ctx) if callable(destaque) else SEM_DESTAQUE
    return acao, marca, pausa


# ---------------------------------------------------------------------------
# Montagem dos passos
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def _linhas_pre_chamada(algoritmo: str, modulo: str) -> frozenset[int]:
    """Linhas cujo passo usa o estado ANTERIOR à chamada (regra pré-chamada).

    São os comandos em que a chamada de uma função COM view **não é consumida
    por uma atribuição**: o teste de um `if`/`while`/`assert` ou uma chamada
    solta (`self.dfs(g, s, t)`). Neles o estado pós-linha é o resultado da
    chamada INTEIRA, mas os passos da chamada vêm logo depois — usar o pós
    faria o filme voltar no tempo (inspeções de 3 para 0, marcados já
    completos antes da busca). Em `x = f(...)` o valor atribuído é o que
    interessa e o estado pós é o correto.
    """
    nomes = {
        nome.rsplit(".", 1)[-1]
        for mod, nome in FUNCOES_PAINEL[algoritmo]
        if mod == modulo
    }

    def chama_view(no: ast.AST) -> bool:
        return any(
            isinstance(chamada, ast.Call)
            and (getattr(chamada.func, "attr", None) or getattr(chamada.func, "id", None))
            in nomes
            for chamada in ast.walk(no)
        )

    arvore = ast.parse(arquivo_modulo(modulo).read_text(encoding="utf-8"))
    linhas: set[int] = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.While, ast.If, ast.Assert)):
            if chama_view(no.test):
                linhas.add(no.lineno)
        elif isinstance(no, ast.Expr) and chama_view(no.value):
            linhas.add(no.lineno)
    return frozenset(linhas)


@lru_cache(maxsize=None)
def _faixas_simples(modulo: str) -> dict[int, tuple[int, int]]:
    """Linha inicial -> (inicial, final) de cada comando SIMPLES do módulo.

    O `sys.settrace` dispara um evento por linha **física**. Quando o fonte
    quebra um comando em várias linhas, o evento da continuação cai no MEIO da
    atribuição e mostraria um estado que o algoritmo nunca tem. Mapeamos o
    comando inteiro para colapsar as continuações e usar o snapshot DEPOIS do
    comando completo.
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
            for linha in range(no.lineno, fim + 1):
                faixas[linha] = (no.lineno, fim)
    return faixas


def _executar(algoritmo: str):
    """Roda a implementação real (montagem da rede + algoritmo) sob trace."""
    classe = classe_do_algoritmo(algoritmo)

    def executar():
        rede = construir_rede()
        return classe(rede, S_FONTE, T_SUMIDOURO)

    return _gravar(MODULOS_DETALHADO[algoritmo], executar)


def passos_detalhados(algoritmo: str) -> list[Step]:
    """Um passo por linha executada (modo didático, linha a linha)."""
    _, eventos = _executar(algoritmo)
    contadores = _contadores(eventos, algoritmo)
    estados = [_estado(ev, contadores[i]) for i, ev in enumerate(eventos)]
    modulo_principal = TRECHOS[algoritmo][0]
    passos: list[Step] = []
    ultimo_ev: dict | None = None

    for i, ev in enumerate(eventos):
        if ev["tipo"] != "line":
            continue
        if not funcao_permitida(algoritmo, ev["modulo"], ev["funcao"]):
            continue

        faixa = _faixas_simples(ev["modulo"]).get(ev["lineno"])
        # Linha de continuação do mesmo comando: não é um passo novo.
        if faixa is not None and faixa[0] != ev["lineno"]:
            continue

        # Estado: o primeiro evento DEPOIS do comando inteiro, **no mesmo
        # frame**. O `sys.settrace` dispara a linha ANTES de executá-la; o
        # próximo evento do mesmo frame já reflete o retorno de qualquer
        # chamada feita por esta linha.
        # Se a linha encerra o frame, o próximo evento geral é o do chamador.
        def _continuacao(lineno: int) -> bool:
            return faixa is not None and faixa[0] < lineno <= faixa[1]

        j = i + 1
        while j < len(eventos) and not (
            eventos[j]["frame"] is ev["frame"]
            and not _continuacao(eventos[j]["lineno"])
        ):
            j += 1
        if j >= len(eventos):
            j = i + 1
        depois = eventos[j] if j < len(eventos) else ev
        estado = estados[j] if j < len(estados) else estados[-1]

        # Regra pré-chamada: quando a linha é o TESTE de um `if`/`while` ou uma
        # chamada solta de uma função com view, o estado pós-linha é o
        # resultado da chamada INTEIRA — mas os passos da chamada vêm logo
        # depois. O passo mostra o estado ANTERIOR à chamada; a resposta é
        # narrada no `return` da função chamada.
        if ev["lineno"] in _linhas_pre_chamada(algoritmo, ev["modulo"]):
            estado = estados[i]
            depois = ev

        acao, destaque, pausa = _descrever(ev, depois, estado)
        if not passos:
            destaque = ("inicio", None, None, None)
        # Uma list comprehension executa a MESMA linha uma vez por item; são
        # eventos idênticos, não passos novos. Colapsa repetição consecutiva.
        if (
            passos
            and ultimo_ev is not None
            and ultimo_ev["frame"] is ev["frame"]
            and ultimo_ev["lineno"] == ev["lineno"]
            and passos[-1].acao == acao
        ):
            continue

        passos.append(
            Step(
                linha=ev["lineno"],
                acao=acao,
                destaque=destaque,
                estado=estado,
                pausa=pausa,
                modulo=ev["modulo"],
                funcao=ev["funcao"],
            )
        )
        ultimo_ev = ev

    return passos


# Linhas do módulo principal que resumem o algoritmo no modo compacto:
# a condição do laço (uma por busca), o fecho de cada augmentação e o
# veredito do corte no `check`. Derivadas do ast — nunca digitadas.
@lru_cache(maxsize=None)
def _ancoras_compacto(algoritmo: str) -> frozenset[int]:
    modulo = TRECHOS[algoritmo][0]
    classe = "FordFulkerson" if algoritmo == "edmonds_karp" else "FordFulkersonDFS"
    arvore = ast.parse(arquivo_modulo(modulo).read_text(encoding="utf-8"))
    linha_busca = None
    linha_veredito = None
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.ClassDef) and no.name == classe):
            continue
        for filho in no.body:
            if not isinstance(filho, ast.FunctionDef):
                continue
            if filho.name == "has_augmenting_path":
                # O `return marked[t]` fecha cada busca: é ali que o desfecho
                # (caminho achado + gargalo, ou "sem caminho") é narrado.
                for sub in ast.walk(filho):
                    if isinstance(sub, ast.Return):
                        linha_busca = sub.lineno
            elif filho.name == "check":
                for sub in ast.walk(filho):
                    if isinstance(sub, ast.Return):
                        linha_veredito = sub.lineno
    return frozenset(
        x for x in (linha_busca, _linha_aumento(modulo), linha_veredito) if x is not None
    )


def coletar(algoritmo: str) -> list[Step]:
    """Passos compactos: 1 por busca + 1 por augmentação + o corte.

    Derivado do modo detalhado (mesma projeção de estado), para o golden e o
    teste de determinismo. O último passo do compacto é o último do detalhado:
    os dois modos terminam exatamente no mesmo estado.
    """
    detalhado = coletar_detalhado(algoritmo)
    modulo_principal = TRECHOS[algoritmo][0]
    ancoras = _ancoras_compacto(algoritmo)
    compacto = [
        p for p in detalhado if p.modulo == modulo_principal and p.linha in ancoras
    ]
    if detalhado:
        # O compacto abre com a montagem da rede (o primeiro passo real),
        # marcado como início, e fecha no mesmo estado do detalhado.
        abertura = replace(detalhado[0], destaque=("inicio", None, None, None))
        compacto.insert(0, abertura)
    if detalhado and (not compacto or compacto[-1] is not detalhado[-1]):
        compacto.append(detalhado[-1])
    return compacto


def coletar_detalhado(algoritmo: str) -> list[Step]:
    """Um passo por linha executada (material didático)."""
    return passos_detalhados(algoritmo)


# ---------------------------------------------------------------------------
# Código-fonte real para o painel
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FuncaoCodigo:
    """Uma função executada, na íntegra, pronta para o painel.

    `modulo` é o módulo real do `algs4` (ex.: `algs4.flow_edge`), `arquivo` é
    o caminho curto exibido no cabeçalho e `inicio`/`fim` são linhas reais do
    arquivo-fonte. Para o `__init__` do algoritmo, a linha `class` entra como
    contexto.
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


def _funcoes_do_ast(arquivo: Path) -> dict[str, tuple[int, int, int | None]]:
    """nome qualificado -> (linha do def, fim do corpo, linha da classe)."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
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
    """Views do painel, derivadas do `ast` dos fontes reais do `algs4`."""
    modulo_principal = TRECHOS[algoritmo][0]
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
        # A linha `class` entra como contexto só no `__init__` do algoritmo
        # principal (as demais views começam no `def`, para não inflar a
        # moldura).
        if modulo == modulo_principal and nome.endswith(".__init__") and classe_linha is not None:
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


if __name__ == "__main__":
    for nome in ("edmonds_karp", "ford_fulkerson_dfs"):
        print("=" * 78)
        print(nome.upper())
        passos = coletar_detalhado(nome)
        print(f"{len(passos)} passos linha a linha")
        for n, passo in enumerate(coletar(nome)):
            print(f"{n:2d}  linha {passo.linha:3d}  {passo.acao}")
        final = passos[-1].estado
        print("valor final:", final["valor"], "| corte:", final["corte"],
              "| cap. do corte:", final["corte_capacidade"],
              "| inspeções:", final["inspecoes"])
