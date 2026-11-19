"""
Testes de estado das animações de FLUXO MÁXIMO — sem Manim.

Roda o gravador (`flow_record.py`) sobre o `algs4-py` e verifica:

a) golden: valor 4, corte {0,2}, os 4 caminhos aumentantes e os fluxos finais,
   nas duas variantes (Edmonds-Karp/BFS e Ford-Fulkerson/DFS);
b) invariantes: capacidade, conservação, resíduos, valor do fluxo e corte,
   em TODO passo (compacto e linha a linha);
c) determinismo: duas gravações produzem a mesma sequência;
d) modo linha a linha: cobertura de linhas, views e ausência de fallback;
e) painel de código: uma view por função, derivada do ast dos fontes reais;
f) entrada: o `.txt` do formato `FlowNetwork` é lido e validado com linha.

Se o `algs4` mudar de comportamento, este arquivo falha alto em vez de gerar
um vídeo errado.

Uso:  python validate_flow_scenes.py
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import flow_record as rec  # noqa: E402

VERDE = "\033[92m"
VERMELHO = "\033[91m"
RESET = "\033[0m"

EPS = 1e-9


class Falha(AssertionError):
    pass


def verificar(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise Falha(mensagem)


def chave(passo: rec.Step) -> tuple:
    """Assinatura estável de um passo, para o golden."""
    tipo, u, v, status = passo.destaque
    return (tipo, u, v, status)


# ---------------------------------------------------------------------------
# a) Golden (entrada padrão: dataset/tinyFN.txt)
# ---------------------------------------------------------------------------

# 1 passo de abertura (montagem da rede) + 5 buscas + 4 augmentações + corte.
GOLDEN_COMPACTO = [
    ("inicio", None, None, None),
    ("busca", None, None, "nova"),
    ("valor", None, None, None),
    ("busca", None, None, "nova"),
    ("valor", None, None, None),
    ("busca", None, None, "nova"),
    ("valor", None, None, None),
    ("busca", None, None, "nova"),
    ("valor", None, None, None),
    ("busca", None, None, "fim"),
    ("corte", None, None, "fechado"),
]

CAMINHOS_GOLDEN = [
    [(0, 2), (2, 4), (4, 5)],
    [(0, 2), (2, 3), (3, 5)],
    [(0, 1), (1, 4), (4, 5)],
    [(0, 1), (1, 3), (3, 5)],
]

# (u, w) -> fluxo final (capacidades no arquivo, na ordem de inserção).
FLUXOS_GOLDEN = {
    (0, 1): 2.0,
    (0, 2): 2.0,
    (1, 3): 1.0,
    (1, 4): 1.0,
    (2, 3): 1.0,
    (2, 4): 1.0,
    (3, 5): 2.0,
    (4, 5): 2.0,
}

CAPACIDADES_GOLDEN = {
    (0, 1): 2.0,
    (0, 2): 3.0,
    (1, 3): 3.0,
    (1, 4): 1.0,
    (2, 3): 1.0,
    (2, 4): 1.0,
    (3, 5): 2.0,
    (4, 5): 3.0,
}

# Inspeções de aresta acumuladas: a BFS esvazia a fila (16/16/16/16/5) e a
# DFS para ao alcançar `t` (3/4/7/8/5).
INSPECOES_GOLDEN = {"edmonds_karp": 69, "ford_fulkerson_dfs": 27}

CORTE_GOLDEN = [0, 2]


def testar_entrada() -> None:
    """O `.txt` é a fonte única: V, E e capacidades vêm do arquivo real."""
    caminho = rec.caminho_rede()
    v, arestas = rec.ler_rede_txt(caminho)
    verificar(v == rec.V_REDE, f"V do arquivo ({v}) != V_REDE ({rec.V_REDE})")
    verificar(
        len(arestas) == len(rec.ARESTAS_REDE),
        f"E lido ({len(arestas)}) != E ({len(rec.ARESTAS_REDE)})",
    )
    verificar(rec.S_FONTE == 0, f"fonte s={rec.S_FONTE}, esperada 0")
    verificar(rec.T_SUMIDOURO == v - 1, f"sumidouro t={rec.T_SUMIDOURO}, esperado {v - 1}")
    for u, w, capacidade in arestas:
        verificar(0 <= u < v and 0 <= w < v, f"aresta {u}->{w} fora de 0..{v - 1}")
        verificar(capacidade >= 0, f"capacidade negativa em {u}->{w}: {capacidade}")

    if caminho.resolve() == rec.REDE_PADRAO.resolve():
        obtido = {(u, w): c for u, w, c in arestas}
        verificar(obtido == CAPACIDADES_GOLDEN, f"capacidades do tinyFN: {obtido}")

    # Arquivo malformado falha com caminho + linha, nunca em silêncio.
    with tempfile.TemporaryDirectory() as pasta:
        ruim = Path(pasta) / "rede_ruim.txt"
        ruim.write_text("3\n1\n0 5 1.0\n", encoding="utf-8")
        try:
            rec.ler_rede_txt(ruim)
        except ValueError as erro:
            verificar("0 5" in str(erro) or "fora do intervalo" in str(erro), f"erro pouco claro: {erro}")
        else:
            raise Falha("aresta fora do intervalo 0..V-1 foi aceita")

        curto = Path(pasta) / "rede_curta.txt"
        curto.write_text("3\n2\n0 1 1.0\n", encoding="utf-8")
        try:
            rec.ler_rede_txt(curto)
        except ValueError:
            pass
        else:
            raise Falha("arquivo com E=2 e uma aresta foi aceito")


def _golden_por_variante(nome: str) -> None:
    compacto = rec.coletar(nome)
    detalhado = rec.coletar_detalhado(nome)
    assinaturas = [chave(p) for p in compacto]
    verificar(
        assinaturas == GOLDEN_COMPACTO,
        f"{nome}: golden do modo compacto divergiu:\n  obtido={assinaturas}",
    )

    final = compacto[-1].estado
    verificar(abs(final["valor"] - 4.0) < EPS, f"{nome}: valor final {final['valor']} != 4")
    verificar(final["corte"] == CORTE_GOLDEN, f"{nome}: corte {final['corte']} != {CORTE_GOLDEN}")
    verificar(
        abs(final["corte_capacidade"] - 4.0) < EPS,
        f"{nome}: capacidade do corte {final['corte_capacidade']} != 4",
    )
    verificar(final["augmentacoes"] == 4, f"{nome}: {final['augmentacoes']} augmentações != 4")
    verificar(
        final["inspecoes"] == INSPECOES_GOLDEN[nome],
        f"{nome}: {final['inspecoes']} inspeções != {INSPECOES_GOLDEN[nome]}",
    )
    verificar(final["iteracao"] == 5, f"{nome}: {final['iteracao']} buscas != 5")

    caminhos = [
        p.estado["caminho"]
        for p in compacto
        if p.destaque[0] == "busca" and p.destaque[3] == "nova"
    ]
    verificar(caminhos == CAMINHOS_GOLDEN, f"{nome}: caminhos aumentantes divergiram: {caminhos}")

    gargalos = [
        rec._gargalo_do_caminho(p.estado, p.estado["caminho"])
        for p in compacto
        if p.destaque[0] == "busca" and p.destaque[3] == "nova"
    ]
    verificar(gargalos == [1.0, 1.0, 1.0, 1.0], f"{nome}: gargalos {gargalos} != 1")

    fluxos = {chave_aresta: f for chave_aresta, f in final["fluxos"].items()}
    for aresta, esperado in FLUXOS_GOLDEN.items():
        verificar(
            abs(fluxos.get(aresta, -1.0) - esperado) < EPS,
            f"{nome}: fluxo final de {aresta} = {fluxos.get(aresta)}, esperado {esperado}",
        )
    verificar(
        set(fluxos) == set(FLUXOS_GOLDEN),
        f"{nome}: arestas do estado {sorted(fluxos)} != {sorted(FLUXOS_GOLDEN)}",
    )

    # Os dois modos terminam no MESMO estado (projeção compartilhada).
    verificar(
        detalhado[-1].estado["fluxos"] == final["fluxos"],
        f"{nome}: fluxos finais do detalhado diferem do compacto",
    )
    verificar(
        abs(detalhado[-1].estado["valor"] - final["valor"]) < EPS,
        f"{nome}: valor final do detalhado difere do compacto",
    )


def testar_golden() -> None:
    for nome in ("edmonds_karp", "ford_fulkerson_dfs"):
        _golden_por_variante(nome)

    # As duas variantes chegam ao mesmo fluxo máximo e ao mesmo corte.
    ek = rec.coletar("edmonds_karp")[-1].estado
    dfs = rec.coletar("ford_fulkerson_dfs")[-1].estado
    verificar(ek["fluxos"] == dfs["fluxos"], "BFS e DFS terminaram com fluxos diferentes")
    verificar(ek["corte"] == dfs["corte"], "BFS e DFS terminaram com cortes diferentes")


# ---------------------------------------------------------------------------
# b) Invariantes
# ---------------------------------------------------------------------------


def _em_augmentacao(passo: rec.Step) -> bool:
    """Verdadeiro entre `v = t` do 2º laço e o `value += bottle`.

    Nesse intervalo o fluxo é atualizado aresta por aresta: a conservação
    ainda NÃO vale (é um estado intermediário real do algoritmo). A flag vem
    do trace (pilha de frames), não da função/linha do passo: a chamada de
    `FlowEdge.other` dentro do 2º laço também está em plena augmentação.
    """
    return bool(passo.estado.get("augmentando"))


def _e_aresta_da_rede(estado: dict, u: int, v: int) -> bool:
    return (u, v) in estado["capacidades"] or (v, u) in estado["capacidades"]


def invariantes(nome: str, passos: list[rec.Step]) -> None:
    for i, passo in enumerate(passos):
        estado = passo.estado
        s, t = estado["s"], estado["t"]

        verificar(estado["V"] == rec.V_REDE, f"{nome}[{i}]: V {estado['V']} != {rec.V_REDE}")
        verificar(estado["E"] == len(estado["arestas"]), f"{nome}[{i}]: E não bate com as arestas")

        # Capacidade e resíduos (valem em TODO instante, inclusive no meio da
        # augmentação: `add_residual_flow_to` mantém 0 <= f <= C).
        for (u, w), capacidade in estado["capacidades"].items():
            fluxo = estado["fluxos"][(u, w)]
            verificar(
                -EPS <= fluxo <= capacidade + EPS,
                f"{nome}[{i}]: fluxo {fluxo:g} fora de [0, {capacidade:g}] em {u}->{w}",
            )
            verificar(
                abs(estado["residual_direta"][(u, w)] - (capacidade - fluxo)) < EPS,
                f"{nome}[{i}]: residual direto de {u}->{w} != C - f",
            )
            verificar(
                abs(estado["residual_reversa"][(u, w)] - fluxo) < EPS,
                f"{nome}[{i}]: residual reverso de {u}->{w} != f",
            )

        # O caminho é estruturalmente válido sempre que existe.
        caminho = estado["caminho"]
        if caminho:
            verificar(caminho[0][0] == s, f"{nome}[{i}]: caminho não começa em {s}: {caminho}")
            verificar(caminho[-1][1] == t, f"{nome}[{i}]: caminho não termina em {t}: {caminho}")
            for (a, b), (c, d) in zip(caminho, caminho[1:]):
                verificar(b == c, f"{nome}[{i}]: caminho com salto {b} != {c}: {caminho}")
            for u, w in caminho:
                verificar(
                    _e_aresta_da_rede(estado, u, w),
                    f"{nome}[{i}]: caminho usa {u}->{w}, que não é aresta da rede",
                )
            # Na busca, a aresta do caminho tem residual positivo.
            if "has_augmenting_path" in passo.funcao or passo.funcao.endswith(".dfs"):
                for u, w in caminho:
                    residual = (
                        estado["residual_direta"].get((u, w))
                        if (u, w) in estado["residual_direta"]
                        else estado["residual_reversa"].get((w, u))
                    )
                    verificar(
                        residual is not None and residual > 0,
                        f"{nome}[{i}]: caminho usa {u}->{w} sem residual positivo",
                    )

        verificar(
            all(0 <= x < estado["V"] for x in estado["marcados"]),
            f"{nome}[{i}]: marcados fora de 0..V-1: {estado['marcados']}",
        )
        verificar(
            len(estado["marcados"]) == len(set(estado["marcados"])),
            f"{nome}[{i}]: marcados repetidos: {estado['marcados']}",
        )
        verificar(estado["corte"] == estado["marcados"], f"{nome}[{i}]: corte != marcados")
        for v, aresta in estado["edge_to"].items():
            verificar(
                0 <= v < estado["V"],
                f"{nome}[{i}]: edge_to de vértice inválido {v}",
            )
            verificar(
                _e_aresta_da_rede(estado, aresta[0], aresta[1]),
                f"{nome}[{i}]: edge_to[{v}]={aresta} não é aresta da rede",
            )

        # Valor do fluxo = excesso na origem = excesso no sumidouro.
        if not _em_augmentacao(passo):
            saida_s = sum(
                f for (u, _w), f in estado["fluxos"].items() if u == s
            ) - sum(f for (_u, w), f in estado["fluxos"].items() if w == s)
            entrada_t = sum(
                f for (_u, w), f in estado["fluxos"].items() if w == t
            ) - sum(f for (u, _w), f in estado["fluxos"].items() if u == t)
            verificar(
                abs(estado["valor"] - saida_s) < EPS,
                f"{nome}[{i}]: |f| = {estado['valor']:g} != saída de s = {saida_s:g}",
            )
            verificar(
                abs(estado["valor"] - entrada_t) < EPS,
                f"{nome}[{i}]: |f| = {estado['valor']:g} != entrada em t = {entrada_t:g}",
            )
            for v in range(estado["V"]):
                if v in (s, t):
                    continue
                saldo = sum(
                    f for (u, _w), f in estado["fluxos"].items() if u == v
                ) - sum(f for (_u, w), f in estado["fluxos"].items() if w == v)
                verificar(
                    abs(saldo) < EPS,
                    f"{nome}[{i}]: conservação violada em {v}: saldo {saldo:g}",
                )


def testar_invariantes() -> None:
    for nome in ("edmonds_karp", "ford_fulkerson_dfs"):
        invariantes(nome + " (compacto)", rec.coletar(nome))
        invariantes(nome + " (detalhado)", rec.coletar_detalhado(nome))


# ---------------------------------------------------------------------------
# c) Determinismo
# ---------------------------------------------------------------------------


def assinatura(passos: list[rec.Step]) -> list[tuple]:
    """Assinatura completa: destaque + valor + fluxos + fila/pilha."""
    return [
        (
            chave(p),
            p.linha,
            p.modulo,
            p.funcao,
            round(float(p.estado["valor"]), 9),
            tuple(sorted((a, round(f, 9)) for a, f in p.estado["fluxos"].items())),
            tuple(p.estado["marcados"]),
            tuple(p.estado["fila"]),
            tuple(p.estado["pilha"]),
            p.estado["inspecoes"],
        )
        for p in passos
    ]


def testar_determinismo() -> None:
    for nome in ("edmonds_karp", "ford_fulkerson_dfs"):
        for rotulo, coletor in (("compacto", rec.coletar), ("detalhado", rec.coletar_detalhado)):
            primeira = assinatura(coletor(nome))
            segunda = assinatura(coletor(nome))
            verificar(
                primeira == segunda,
                f"{nome} ({rotulo}): duas gravações produziram sequências diferentes "
                "(ordem de Bag ou de fila instável?)",
            )


# ---------------------------------------------------------------------------
# d) Modo linha a linha
# ---------------------------------------------------------------------------

# Linhas obrigatórias por view (números reais do fonte). Cobre início, laço,
# chamada, retorno e fecho de cada função do painel.
LINHAS_OBRIGATORIAS = {
    "edmonds_karp": {
        ("algs4.ford_fulkerson", "FordFulkerson.__init__"): {32, 46, 52, 58, 61, 64},
        ("algs4.ford_fulkerson", "FordFulkerson.has_augmenting_path"): {75, 82, 83, 88, 90, 95},
        ("algs4.ford_fulkerson", "FordFulkerson.excess"): {99, 100, 102, 105},
        ("algs4.ford_fulkerson", "FordFulkerson.is_feasible"): {109, 111, 116, 124, 130},
        ("algs4.ford_fulkerson", "FordFulkerson.check"): {134, 147, 150, 152, 156},
        ("algs4.flow_edge", "FlowEdge.other"): {56, 57},
        ("algs4.flow_edge", "FlowEdge.residual_capacity_to"): {64, 65, 67},
        ("algs4.flow_edge", "FlowEdge.add_residual_flow_to"): {72, 74, 77},
        ("algs4.flow_network", "FlowNetwork.__init__"): {121, 125, 131},
        ("algs4.flow_network", "FlowNetwork.add_edge"): {152, 156, 158},
        ("algs4.flow_network", "FlowNetwork.adj"): {161, 162},
    },
    "ford_fulkerson_dfs": {
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.__init__"): {32, 46, 52, 58, 61, 64},
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.has_augmenting_path"): {75, 79, 80, 83},
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.dfs"): {86, 87, 88, 92, 96, 98},
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.excess"): {102, 103, 105, 108},
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.is_feasible"): {112, 114, 119, 127, 133},
        ("algs4.ford_fulkerson_dfs", "FordFulkersonDFS.check"): {137, 150, 153, 155, 159},
        ("algs4.flow_edge", "FlowEdge.other"): {56, 57},
        ("algs4.flow_edge", "FlowEdge.residual_capacity_to"): {64, 65, 67},
        ("algs4.flow_edge", "FlowEdge.add_residual_flow_to"): {72, 74, 77},
        ("algs4.flow_network", "FlowNetwork.__init__"): {121, 125, 131},
        ("algs4.flow_network", "FlowNetwork.add_edge"): {152, 156, 158},
        ("algs4.flow_network", "FlowNetwork.adj"): {161, 162},
    },
}


def testar_detalhado() -> None:
    for nome in ("edmonds_karp", "ford_fulkerson_dfs"):
        compacto = rec.coletar(nome)
        detalhado = rec.coletar_detalhado(nome)
        modulo_principal, inicio, fim = rec.TRECHOS[nome]

        verificar(
            len(detalhado) > len(compacto),
            f"{nome}: detalhado ({len(detalhado)}) não é maior que o compacto ({len(compacto)})",
        )

        vistas_usadas: set[tuple[str, str]] = set()
        linhas_usadas: dict[tuple[str, str], set[int]] = {}
        for i, passo in enumerate(detalhado):
            # Toda linha executada pertence a UMA view do painel.
            view = rec.funcao_da_linha(nome, passo.linha, passo.modulo)
            verificar(
                view.modulo == passo.modulo,
                f"{nome}[{i}]: view {view.nome} de {view.modulo} != passo em {passo.modulo}",
            )
            verificar(
                view.inicio <= passo.linha <= view.fim,
                f"{nome}[{i}]: linha {passo.linha} fora da view [{view.inicio}, {view.fim}]",
            )
            if passo.modulo == modulo_principal:
                verificar(
                    inicio <= passo.linha <= fim,
                    f"{nome}[{i}]: linha {passo.linha} fora do recorte [{inicio}, {fim}]",
                )

            # Nenhum passo pode cair na rede de segurança de `_descrever`.
            verificar(
                (passo.funcao, passo.linha) in rec.TEXTOS,
                f"{nome}[{i}]: {passo.funcao} linha {passo.linha} sem texto declarado",
            )
            verificar(passo.pausa > 0, f"{nome}[{i}]: pausa inválida {passo.pausa}")
            verificar(passo.acao.strip() != "", f"{nome}[{i}]: ação vazia")

            vistas_usadas.add((view.modulo, view.nome))
            linhas_usadas.setdefault((view.modulo, view.nome), set()).add(passo.linha)

        # Toda view do painel tem de executar de fato (nada de view morta).
        painel = set(rec.FUNCOES_PAINEL[nome])
        verificar(
            vistas_usadas <= painel,
            f"{nome}: views usadas fora do painel: {sorted(vistas_usadas - painel)}",
        )
        verificar(
            painel <= vistas_usadas,
            f"{nome}: views do painel nunca executadas: {sorted(painel - vistas_usadas)}",
        )

        # Linhas obrigatórias de cada view.
        for chave_view, obrigatorias in LINHAS_OBRIGATORIAS[nome].items():
            obtidas = linhas_usadas.get(chave_view, set())
            faltando = obrigatorias - obtidas
            verificar(
                not faltando,
                f"{nome}.{chave_view[1]}: linhas nunca destacadas: {sorted(faltando)}",
            )

        # Progresso monotônico: valor e inspeções só crescem.
        valores = [float(p.estado["valor"]) for p in detalhado]
        verificar(
            all(a <= b + EPS for a, b in zip(valores, valores[1:])),
            f"{nome}: |f| andou para trás: {valores}",
        )
        inspecoes = [p.estado["inspecoes"] for p in detalhado]
        verificar(
            all(a <= b for a, b in zip(inspecoes, inspecoes[1:])),
            f"{nome}: inspeções andaram para trás",
        )

        # O compacto é um subconjunto do detalhado, na mesma ordem (o passo de
        # abertura muda só o `destaque` para "inicio").
        def _localizacao(p: rec.Step) -> tuple:
            return (p.modulo, p.linha, p.funcao, p.acao)

        localizacoes = [_localizacao(p) for p in detalhado]
        posicao = 0
        for passo in compacto:
            alvo = _localizacao(passo)
            while posicao < len(localizacoes) and localizacoes[posicao] != alvo:
                posicao += 1
            verificar(
                posicao < len(localizacoes),
                f"{nome}: passo compacto {alvo} ausente do detalhado",
            )
            posicao += 1


# ---------------------------------------------------------------------------
# e) Painel de código: uma view por função, derivada do ast do fonte real
# ---------------------------------------------------------------------------


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


def testar_funcoes() -> None:
    for nome in ("edmonds_karp", "ford_fulkerson_dfs"):
        funcoes = rec.funcoes_codigo(nome)
        modulo_principal, _ini, _fim = rec.TRECHOS[nome]

        chaves = {(f.modulo, f.nome) for f in funcoes}
        verificar(
            chaves == set(rec.FUNCOES_PAINEL[nome]),
            f"{nome}: views {sorted(chaves)} != FUNCOES_PAINEL",
        )
        verificar(
            len(chaves) == len(funcoes),
            f"{nome}: view repetida no painel: {[f.nome for f in funcoes]}",
        )

        for f in funcoes:
            arquivo = rec.arquivo_modulo(f.modulo)
            linhas = arquivo.read_text(encoding="utf-8").splitlines()
            nos = _funcoes_do_ast(arquivo)
            verificar(f.nome in nos, f"{nome}: {f.nome} não existe no ast de {f.modulo}")
            def_linha, def_fim, classe_linha = nos[f.nome]
            verificar(f.fim == def_fim, f"{nome}.{f.nome}: fim {f.fim} != end_lineno {def_fim}")

            inicios = {def_linha}
            if f.modulo == modulo_principal and classe_linha is not None:
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

        # Views do mesmo módulo não se sobrepõem (indicador inequívoco).
        por_modulo: dict[str, list[rec.FuncaoCodigo]] = {}
        for f in funcoes:
            por_modulo.setdefault(f.modulo, []).append(f)
        for modulo, lista in por_modulo.items():
            ordenadas = sorted(lista, key=lambda f: f.inicio)
            for a, b in zip(ordenadas, ordenadas[1:]):
                verificar(
                    a.fim < b.inicio,
                    f"{nome}/{modulo}: views {a.nome} e {b.nome} se sobrepõem",
                )


# ---------------------------------------------------------------------------
# stages.json (índice por passo, nunca por timestamp)
# ---------------------------------------------------------------------------


def exportar_stages() -> str:
    raiz = Path(__file__).resolve().parent
    ativo = rec.caminho_rede()
    padrao = ativo.resolve() == rec.REDE_PADRAO.resolve()
    nome_arquivo = "stages_fluxo.json" if padrao else f"stages_fluxo_{ativo.stem}.json"
    destino = raiz / "build" / "goldens" / nome_arquivo
    destino.parent.mkdir(parents=True, exist_ok=True)

    dados = {}
    for nome in ("edmonds_karp", "ford_fulkerson_dfs"):
        for sufixo, coletor in (("", rec.coletar), ("_detalhado", rec.coletar_detalhado)):
            dados[nome + sufixo] = [
                {
                    "passo": i,
                    "linha": p.linha,
                    "modulo": p.modulo,
                    "funcao": p.funcao,
                    "acao": p.acao,
                    "destaque": list(p.destaque),
                    "pausa": p.pausa,
                    "valor": p.estado["valor"],
                    "fluxos": {f"{u}->{w}": f for (u, w), f in p.estado["fluxos"].items()},
                    "residual_direta": {
                        f"{u}->{w}": r for (u, w), r in p.estado["residual_direta"].items()
                    },
                    "residual_reversa": {
                        f"{u}->{w}": r for (u, w), r in p.estado["residual_reversa"].items()
                    },
                    "marcados": list(p.estado["marcados"]),
                    "edge_to": {str(k): list(v) for k, v in p.estado["edge_to"].items()},
                    "caminho": [list(e) for e in p.estado["caminho"]],
                    "gargalo": p.estado["gargalo"],
                    "fila": list(p.estado["fila"]),
                    "pilha": list(p.estado["pilha"]),
                    "iteracao": p.estado["iteracao"],
                    "augmentacoes": p.estado["augmentacoes"],
                    "inspecoes": p.estado["inspecoes"],
                    "corte": list(p.estado["corte"]),
                    "corte_capacidade": p.estado["corte_capacidade"],
                }
                for i, p in enumerate(coletor(nome))
            ]

    texto = json.dumps(dados, indent=2, ensure_ascii=False)
    destino.write_text(texto, encoding="utf-8")
    digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    print(f"stages gravado em {destino}")
    print(f"sha256 do stages: {digest}")
    return digest


def main() -> int:
    testes = [
        ("entrada .txt", testar_entrada),
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
