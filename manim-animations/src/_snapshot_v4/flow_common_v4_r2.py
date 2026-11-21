"""
Linguagem visual compartilhada das cenas de fluxo máximo (tinyFN).

Edmonds-Karp (BFS) e Ford-Fulkerson (DFS) usam este módulo. Tudo o que
aparece na tela deriva do trace real (`flow_record`): fluxos, capacidades,
residuais, fila/pilha, caminho, gargalo, corte e as views de código por
função. Nenhum número é digitado à mão.

Contrato: `PLANO_VISUAL_FLUXO.md` §1–§8. Este arquivo é autossuficiente (não
importa `mst_common`/`dijkstra_common`): a paleta de fluxo tem papéis próprios.
"""

from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from manim import *

import flow_record as rec

# ---------------------------------------------------------------------------
# Paleta e superfícies (§3)
# ---------------------------------------------------------------------------

COR_FUNDO = "#0f111a"
COR_PAINEL = "#151824"
COR_NO = "#2b2d42"
COR_BORDA_NO = "#8d99ae"
COR_TEXTO = "#f2f4f8"
COR_ACENTO = "#48cae4"
COR_LINHA_TABELA = "#2a2f45"
COR_CABECALHO = "#48cae4"

# papel -> (hex, texto da legenda, símbolo)
PALETA: dict[str, tuple[str, str, str]] = {
    "fora": ("#8d99ae", "sem fluxo", "dot"),
    "fluxo": ("#4cc9f0", "com fluxo", "dot"),
    "saturada": ("#06d6a0", "saturada", "dot"),
    "exame": ("#e879f9", "em exame", "dot"),
    "caminho": ("#ffd166", "caminho", "dot"),
    "reversa": ("#ef476f", "reversa (res. f)", "dash"),
    "alcancado": ("#80ed99", "alcançado/lado S", "ring"),
}

ESTRUTURAIS = dict(
    fundo=COR_FUNDO,
    painel=COR_PAINEL,
    no=COR_NO,
    borda=COR_BORDA_NO,
    texto=COR_TEXTO,
    rotulo_no="#ffffff",
)

# Ordem do guia visual: 4 itens na primeira linha, 3 na segunda (§3).
ORDEM_GUIA = ("fora", "fluxo", "saturada", "exame", "caminho", "reversa", "alcancado")

# ---------------------------------------------------------------------------
# Layout (§1)
# ---------------------------------------------------------------------------

CODIGO = dict(largura=7.86, altura=4.55, buff=0.55)
ESTRUTURA = dict(centro=(-2.63, -2.51), largura=7.86, altura=2.42)
# O plano pedia centro x=4.17; com 5.33 de largura a borda direita ia a 6.835,
# 0.005 além do safe frame (6.83). Centro 4.165 fecha em 1.50..6.83.
ESTADO = dict(centro=(4.165, -2.66), largura=5.33, altura=2.12)
TITULO_X = 1.55

# Área útil do desenho do grafo (folga 0.20 até a moldura do código e o guia).
GRAFO_AREA = (1.63, -0.25, 6.79, 3.05)

COORDS = {
    0: (1.90, 1.40),  # s (origem)
    1: (3.42, 2.78),
    2: (3.42, 0.02),
    3: (5.05, 2.62),
    4: (5.05, 0.18),
    5: (6.52, 1.40),  # t (sumidouro, = V-1)
}
RAIO_NO = 0.27
RAIO_ANEL = 0.34
BUFF_SETA = 0.30
LARG_SETA = 3.2
PONTA = 0.16

# Ritmo (PLANO_VISUAL_FLUXO_V2 §A.1). Tudo em múltiplos EXATOS de 1/15 s
# para o render 480p (15 fps) não arredondar para cima. `pausa` indexa pelo
# valor do gravador (0,55 / 1,0 / 1,7); a cena não recalcula o tier.
RITMO = dict(
    play=0.40,            # 6/15
    play_destaque=7 / 15, # 0.4667
    fade=2 / 15,          # 0.1333 — CADA um dos dois plays da troca
    pausa={0.55: 3 / 15,  # 0.2000
           1.00: 5 / 15,  # 0.3333
           1.70: 8 / 15}, # 0.5333
)

# Paginação do código (§B.1)
COLUNAS_MAX = 82
MAX_LINHAS_PAGINA = 23

# ---------------------------------------------------------------------------
# Formatação e regras de cor
# ---------------------------------------------------------------------------

SEM_VALOR = "—"

ARESTAS_REDE_SET = frozenset((u, v) for u, v, _c in rec.ARESTAS_REDE)


def fmt_num(x) -> str:
    """Número do trace em forma curta (`4.0` -> `4`, `2.5` -> `2.5`)."""
    if x is None:
        return SEM_VALOR
    return f"{x:g}"


def cor_destaque(passo) -> str:
    """Cor da ação no painel de estado (§6)."""
    tipo = passo.destaque[0]
    if tipo == "busca":
        return PALETA["exame"][0]
    if tipo in ("caminho", "aumento", "valor"):
        return PALETA["caminho"][0]
    if tipo == "corte":
        return PALETA["saturada"][0]
    if tipo == "aresta":
        return PALETA["fora"][0]
    return ESTRUTURAIS["texto"]


def dividir_acao(acao: str, limite: int = 44) -> tuple[str, str]:
    """Quebra determinística da ação em duas linhas fixas (§6).

    A maior ação tem 76 caracteres (6,68 unidades em fonte 12) e o painel tem
    5,33. A quebra é no último espaço antes de `limite`; a segunda linha pode
    ser mais curta, nunca maior que o resto.
    """
    if len(acao) <= limite:
        return acao, ""
    corte = acao.rfind(" ", 0, limite + 1)
    if corte <= 0:
        corte = limite
    return acao[:corte], acao[corte + 1 :].strip()


def fmt_caminho(caminho) -> str:
    """`[(0,2),(2,4),(4,5)]` -> `0→2→4→5`."""
    if not caminho:
        return SEM_VALOR
    nos = [caminho[0][0]] + [v for _u, v in caminho]
    return "→".join(str(v) for v in nos)


def fmt_fila(estado: dict) -> str:
    fila = estado.get("fila") or []
    return "fila [" + ", ".join(map(str, fila)) + "]" if fila else "fila []"


def fmt_pilha(estado: dict) -> str:
    pilha = estado.get("pilha") or []
    return "pilha [" + ", ".join(map(str, pilha)) + "]" if pilha else "pilha []"


def fmt_marcados(estado: dict) -> str:
    marcados = estado.get("marcados") or []
    return "marcados {" + (", ".join(map(str, marcados)) or "") + "}"


def fmt_edge_to(estado: dict) -> str:
    """`edgeTo` na ORDEM DE DESCOBERTA (a mesma fila da aba `edgeTo`)."""
    edge_to = estado.get("edge_to") or {}
    ordem = [v for v in (estado.get("ordem_descoberta") or []) if v in edge_to]
    restantes = [v for v in sorted(edge_to) if v not in set(ordem)]
    itens = []
    for v in ordem + restantes:
        u, w = edge_to[v]
        anterior = w if u == v else u
        itens.append(f"{v}←{anterior}")
    return "edgeTo " + (" ".join(itens) if itens else SEM_VALOR)


def estado_da_busca(passo) -> dict:
    """Estado com o efeito da linha visível na aba `busca`.

    `estado` já é pós-linha; só o push do `dfs` (chamada dentro de `if`,
    linha pré-chamada) fica uma linha atrás — ali `estado_pos` é o pós-linha.
    A troca é só da LISTA da pilha: contadores/inspeções continuam vindo de
    `estado`, para nada mais andar um passo à frente.
    """
    est = passo.estado
    if passo.escrita != "busca" or passo.estado_pos is None:
        return est
    if len(passo.estado_pos.get("pilha") or []) > len(est.get("pilha") or []):
        return {**est, "pilha": list(passo.estado_pos["pilha"])}
    return est


def chips_fila(
    itens: list[dict],
    *,
    x0: float,
    y: float,
    largura: float,
    altura: float,
    passo: float,
    fonte: int,
    fonte_sub: int | None = None,
) -> tuple[list[VGroup], list[Arrow]]:
    """Abstração de FILA: chips em ordem + setas no vão (geometria fixa).

    Cada item é `{"texto", "sub"?, "cor", "fill", "fill_opacity"?}`. O chip é
    um retângulo com borda na cor do papel; o subtexto (opcional) fica embaixo
    do rótulo principal. As setas só ocupam o vão entre chips consecutivos —
    nunca entram no chip (mesmo contrato da pilha do DFS).
    """
    chips: list[VGroup] = []
    setas: list[Arrow] = []
    for i, item in enumerate(itens):
        centro = np.array([x0 + largura / 2 + i * passo, y, 0.0])
        cor = item["cor"]
        caixa = RoundedRectangle(
            corner_radius=0.06,
            width=largura,
            height=altura,
            fill_color=item.get("fill", COR_CHIP),
            fill_opacity=item.get("fill_opacity", 1.0),
            stroke_color=cor,
            stroke_width=1.6,
        ).move_to(centro)
        textos: list[Text] = [
            Text(item["texto"], font_size=fonte, color=COR_TEXTO)
        ]
        if fonte_sub is not None and item.get("sub"):
            textos.append(
                Text(item["sub"], font_size=fonte_sub, color=cor)
            )
        grupo_texto = VGroup(*textos).arrange(DOWN, buff=0.02)
        grupo_texto.move_to(centro)
        chips.append(VGroup(caixa, grupo_texto))
    for i in range(1, len(itens)):
        x_ini = x0 + largura / 2 + (i - 1) * passo + largura / 2 + 0.01
        x_fim = x0 + largura / 2 + i * passo - largura / 2 - 0.01
        setas.append(
            Arrow(
                np.array([x_ini, y, 0.0]),
                np.array([x_fim, y, 0.0]),
                buff=0.0,
                stroke_width=1.2,
                tip_length=0.05,
                color=COR_BORDA_NO,
            )
        )
    return chips, setas


def fmt_contadores(estado: dict, max_iteracao: int) -> str:
    """Faixa fixa do rodapé da estrutura (§5.4)."""
    it = estado.get("iteracao") or 0
    return (
        f"it {it}/{max_iteracao} · |f| = {fmt_num(estado.get('valor'))}"
        f" · inspeções {estado.get('inspecoes', 0)}"
        f" · caminho {fmt_caminho(estado.get('caminho'))}"
        f" · b = {fmt_num(estado.get('gargalo'))}"
    )


def arcos_de(u: int, v: int, arestas: set[tuple[int, int]]) -> tuple[str, tuple[int, int]]:
    """Como o par `(u,v)` do destaque aparece na rede.

    Se `(u,v)` é aresta do arquivo, o foco é a **direta**; se `(v,u)` é aresta,
    o foco é a **reversa** (o trace nomeia a reversa pelo sentido do residual,
    ex.: `(2,0)` para a reversa de `0→2`). Devolve `("direta"|"reversa"|"",
    chave)`.
    """
    if (u, v) in arestas:
        return "direta", (u, v)
    if (v, u) in arestas:
        return "reversa", (v, u)
    return "", (u, v)


# ---------------------------------------------------------------------------
# Geometria: caixas, colisões e pontos de rótulo
# ---------------------------------------------------------------------------


def caixa(centro, largura: float, altura: float) -> tuple[float, float, float, float]:
    """(xmin, ymin, xmax, ymax) de um retângulo centrado."""
    cx, cy = float(centro[0]), float(centro[1])
    return (cx - largura / 2, cy - altura / 2, cx + largura / 2, cy + altura / 2)


def caixas_colidem(a, b, folga: float = 0.0) -> bool:
    return not (
        a[2] + folga <= b[0]
        or b[2] + folga <= a[0]
        or a[3] + folga <= b[1]
        or b[3] + folga <= a[1]
    )


def segmento_cruza_caixa(p0, p1, box, margem: float = 0.0) -> bool:
    """Liang–Barsky: o segmento p0→p1 toca o retângulo (com margem)?"""
    xmin, ymin, xmax, ymax = box
    xmin -= margem
    ymin -= margem
    xmax += margem
    ymax += margem
    dx = float(p1[0]) - float(p0[0])
    dy = float(p1[1]) - float(p0[1])
    t0, t1 = 0.0, 1.0
    for p, q in (
        (-dx, float(p0[0]) - xmin),
        (dx, xmax - float(p0[0])),
        (-dy, float(p0[1]) - ymin),
        (dy, ymax - float(p0[1])),
    ):
        if abs(p) < 1e-12:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return False
                t0 = max(t0, r)
            else:
                if r < t0:
                    return False
                t1 = min(t1, r)
    return t0 <= t1


def caixa_dentro(box, area, margem: float = 0.0) -> bool:
    return (
        box[0] >= area[0] + margem
        and box[1] >= area[1] + margem
        and box[2] <= area[2] - margem
        and box[3] <= area[3] - margem
    )


def ponto_na_aresta(u: int, v: int, t: float, desvio: float = 0.0):
    """Ponto a fração `t` do segmento u→v, deslocado `desvio` na perpendicular."""
    p0 = np.array([COORDS[u][0], COORDS[u][1], 0.0])
    p1 = np.array([COORDS[v][0], COORDS[v][1], 0.0])
    d = p1 - p0
    norma = np.linalg.norm(d)
    perp = np.array([-d[1], d[0], 0.0]) / norma
    return p0 + d * t + perp * desvio


def amostras_reversa(u: int, v: int, n: int = 21):
    """Polilinha amostrada do arco tracejado v→u (mesma geometria da cena)."""
    p0 = np.array([COORDS[u][0], COORDS[u][1], 0.0])
    p1 = np.array([COORDS[v][0], COORDS[v][1], 0.0])
    d = p1 - p0
    norma = np.linalg.norm(d)
    perp = np.array([-d[1], d[0], 0.0]) / norma
    inicio = p1 - d / norma * (RAIO_NO + 0.10)
    fim = p0 + d / norma * (RAIO_NO + 0.10)
    arco = ArcBetweenPoints(inicio, fim, angle=-0.45).shift(perp * 0.15)
    return [arco.point_from_proportion(i / (n - 1)) for i in range(n)]


FONTE_LINHA1 = 13
FONTE_LINHA2 = 11
BUFF_LINHA2 = 0.06  # espaço entre `→C−f` e `←f` (dois `Text`, duas cores)


def textos_bloco(fluxo: float, capacidade: float) -> tuple[str, str, str]:
    """Conteúdo do bloco de 2 linhas: `f/C`, `→C−f` e `←f` (§C.2)."""
    return (
        f"{fluxo:g}/{capacidade:g}",
        f"→{capacidade - fluxo:g}",
        f"←{fluxo:g}",
    )


def cores_bloco(fluxo: float, capacidade: float) -> tuple[str, str, str]:
    """Cores das três partes do bloco (§C.2) — nenhuma cor nova."""
    return (
        COR_TEXTO,
        PALETA["saturada"][0] if capacidade - fluxo == 0 else COR_TEXTO,
        PALETA["reversa"][0] if fluxo > 0 else PALETA["fora"][0],
    )


def linha2_bloco(fluxo: float, capacidade: float) -> VGroup:
    """`→C−f ←f` como dois `Text` (cores diferentes na mesma linha)."""
    _l1, texto_dir, texto_rev = textos_bloco(fluxo, capacidade)
    _c1, cor_dir, cor_rev = cores_bloco(fluxo, capacidade)
    return VGroup(
        Text(texto_dir, font_size=FONTE_LINHA2, color=cor_dir),
        Text(texto_rev, font_size=FONTE_LINHA2, color=cor_rev),
    ).arrange(RIGHT, buff=BUFF_LINHA2)


def dim_bloco_rotulo() -> tuple[float, float]:
    """Dimensão (largura, altura) do bloco de 2 linhas, pelo PIOR caso do arquivo.

    Linha 1 = `f/C` a fonte 13; linha 2 = `→{C−f} ←{f}` a fonte 11 (§C.4).
    Calculada uma vez e usada em todas as arestas: o bloco não muda de tamanho
    quando o fluxo muda (sem reflow no meio do passo).
    """
    largura1 = largura2 = 0.0
    altura1 = altura2 = 0.0
    for _u, _v, capacidade in rec.ARESTAS_REDE:
        inteiro = int(round(capacidade))
        fluxos = (
            [float(f) for f in range(inteiro + 1)]
            if inteiro <= 20
            else [0.0, capacidade / 2, float(capacidade)]
        )
        for fluxo in fluxos:
            t1 = Text(textos_bloco(fluxo, capacidade)[0], font_size=FONTE_LINHA1)
            t2 = linha2_bloco(fluxo, capacidade)
            largura1 = max(largura1, t1.width)
            largura2 = max(largura2, t2.width)
            altura1 = max(altura1, t1.height)
            altura2 = max(altura2, t2.height)
    return max(largura1, largura2) + 0.12, altura1 + altura2 + 0.06


def posicao_rotulo(
    u: int,
    v: int,
    largura: float,
    altura: float,
    ocupados,
    nos,
    arcos,
    proprio=(),
):
    """Posição do bloco `f/C` + `→C−f ←f` (§C.4): centro → ao longo → perpendicular.

    A ordem dos candidatos é fixa (determinística, ordem do arquivo). Conta
    colisões contra nós, arcos reversos ALHEIOS (margem 0,02), o arco reverso
    da PRÓPRIA aresta (`proprio`, que precisa ficar inteiro visível: margem
    0,00 no traço central), rótulos já postos e o limite da área útil.
    Devolve (centro, caixa, colisoes).

    A grade é a do contrato (15 posições ao longo × 11 desvios). A ordem dos
    `t` é a que reproduz as posições medidas no plano (§C.4) — pares
    simétricos com o lado `> 0.50` primeiro; o conjunto é o mesmo.
    """
    candidatos_t = (
        0.50, 0.44, 0.56, 0.40, 0.60, 0.64, 0.36, 0.68,
        0.32, 0.72, 0.28, 0.76, 0.24, 0.80, 0.20,
    )
    desvios = (
        0.0, 0.16, -0.16, 0.24, -0.24, 0.30, -0.30, 0.36, -0.36, 0.42, -0.42,
    )
    melhor = None
    for t in candidatos_t:
        for desvio in desvios:
            centro = ponto_na_aresta(u, v, t, desvio)
            box = caixa(centro, largura, altura)
            colisoes = 0
            if not caixa_dentro(box, GRAFO_AREA, margem=0.02):
                colisoes += 1
            for no in nos:
                if caixas_colidem(box, no, folga=0.06):
                    colisoes += 1
            for chave, outro in arcos.items():
                if chave == (u, v):
                    continue
                for i in range(len(outro) - 1):
                    if segmento_cruza_caixa(outro[i], outro[i + 1], box, margem=0.02):
                        colisoes += 1
                        break
            for i in range(len(proprio) - 1):
                if segmento_cruza_caixa(proprio[i], proprio[i + 1], box, margem=0.0):
                    colisoes += 1
                    break
            for outra in ocupados:
                if caixas_colidem(box, outra, folga=0.02):
                    colisoes += 1
            if melhor is None or colisoes < melhor[2]:
                melhor = (centro, box, colisoes)
            if colisoes == 0:
                return centro, box, 0
    return melhor


# ---------------------------------------------------------------------------
# Grafo: nós, arestas `f/C`, reversas tracejadas e foco (§2)
# ---------------------------------------------------------------------------


class FlowGraphView:
    """Desenho do `tinyFN` dirigido por `Step.estado`.

    - arestas diretas com rótulo `f/C` (fundo opaco abre o vão da linha);
    - aresta reversa tracejada (`v→u`) só quando `f > 0`;
    - nó em foco com anel magenta, alcançados com fill verde-claro;
    - tudo por *diff*: num passo de bookkeeping o custo é zero ou um mobject.
    """

    def __init__(self, mostrar_rede: bool = False, estado_inicial: dict | None = None):
        self.arestas_arquivo = {(u, v) for u, v, _c in rec.ARESTAS_REDE}
        self.capacidade_arquivo = {(u, v): c for u, v, c in rec.ARESTAS_REDE}

        self.arestas: dict[tuple[int, int], Arrow] = {}
        self.fundos: dict[tuple[int, int], RoundedRectangle] = {}
        self.textos: dict[tuple[int, int], VGroup] = {}
        self.fluxo_atual: dict[tuple[int, int], str] = {}
        self.res_atual: dict[tuple[int, int], tuple[str, str]] = {}
        self.cor_atual: dict[tuple[int, int], str] = {}
        self.larg_atual: dict[tuple[int, int], float] = {}
        self.presentes: set[tuple[int, int]] = set()

        self.reversas: dict[tuple[int, int], VGroup] = {}
        self.cor_reversa: dict[tuple[int, int], str] = {}

        self.circulos: dict[int, Circle] = {}
        self.rotulos_no: dict[int, Text] = {}
        self.etiquetas_papel: dict[int, Text] = {}
        self.aneis_papel: dict[int, Circle] = {}
        self.aneis_corte: dict[int, Circle] = {}
        self.fill_atual: dict[int, str] = {}

        self.anel_foco = Circle(radius=RAIO_ANEL, color=PALETA["exame"][0], stroke_width=2.0)
        self.anel_foco.set_stroke(opacity=0.0)
        self.anel_foco.set_z_index(6)
        # nasce em cima de s: invisível, mas o bbox do grupo não sai da área
        self.anel_foco.move_to(
            np.array([COORDS[rec.S_FONTE][0], COORDS[rec.S_FONTE][1], 0.0])
        )
        self.foco: int | None = None

        self.dim_rotulo: dict[tuple[int, int], tuple[float, float]] = {}
        self.pos_rotulo: dict[tuple[int, int], np.ndarray] = {}
        self.caixa_rotulo: dict[tuple[int, int], tuple] = {}
        self.colisoes_rotulo: dict[tuple[int, int], int] = {}

        self._montar_nos()
        self._calcular_rotulos()

        if mostrar_rede:
            for u, v, c in rec.ARESTAS_REDE:
                self._criar_aresta(u, v, c)
                self.presentes.add((u, v))
        if estado_inicial is not None:
            self._aplicar_imediato(estado_inicial)

        self.mobject = VGroup(
            *self.arestas.values(),
            *self.reversas.values(),
            *self.fundos.values(),
            *self.textos.values(),
            *[self.circulos[v] for v in range(rec.V_REDE)],
            *[self.rotulos_no[v] for v in range(rec.V_REDE)],
            *self.etiquetas_papel.values(),
            *[self.aneis_papel[v] for v in range(rec.V_REDE)],
            *[self.aneis_corte[v] for v in range(rec.V_REDE)],
            self.anel_foco,
        )

    # -- montagem ----------------------------------------------------------

    def _montar_nos(self) -> None:
        for v in range(rec.V_REDE):
            pos = np.array([COORDS[v][0], COORDS[v][1], 0.0])
            circulo = Circle(
                radius=RAIO_NO,
                fill_color=COR_NO,
                fill_opacity=1.0,
                stroke_color=COR_BORDA_NO,
                stroke_width=1.8,
            ).move_to(pos)
            circulo.set_z_index(4)
            rotulo = Text(str(v), font_size=17, color=ESTRUTURAIS["rotulo_no"])
            rotulo.move_to(pos).set_z_index(5)
            self.circulos[v] = circulo
            self.rotulos_no[v] = rotulo
            self.fill_atual[v] = COR_NO

            anel = Circle(radius=RAIO_ANEL, stroke_width=2.2).move_to(pos)
            anel.set_stroke(opacity=0.0)
            anel.set_z_index(5.5)
            self.aneis_papel[v] = anel

            corte = Circle(radius=RAIO_ANEL + 0.04, stroke_width=2.2).move_to(pos)
            corte.set_stroke(opacity=0.0)
            corte.set_z_index(5.7)
            self.aneis_corte[v] = corte

        for v, texto, cor in ((rec.S_FONTE, "s", PALETA["fluxo"][0]),
                              (rec.T_SUMIDOURO, "t", PALETA["caminho"][0])):
            self.aneis_papel[v].set_stroke(color=cor, width=2.2, opacity=1.0)
            etiqueta = Text(texto, font_size=11, color=cor)
            etiqueta.move_to(
                np.array([COORDS[v][0] - 0.40, COORDS[v][1] + 0.34, 0.0])
            ).set_z_index(5)
            self.etiquetas_papel[v] = etiqueta

    def _calcular_rotulos(self) -> None:
        """Posições dos blocos calculadas UMA vez (§2.3), na ordem do arquivo."""
        nos = [caixa(COORDS[v], 0.68, 0.68) for v in range(rec.V_REDE)]
        arcos = {(u, v): amostras_reversa(u, v) for u, v, _c in rec.ARESTAS_REDE}
        largura, altura = dim_bloco_rotulo()
        ocupados: list[tuple] = []
        for u, v, _c in rec.ARESTAS_REDE:
            self.dim_rotulo[(u, v)] = (largura, altura)
            centro, box, colisoes = posicao_rotulo(
                u,
                v,
                largura,
                altura,
                ocupados,
                nos,
                arcos,
                proprio=amostras_reversa(u, v),
            )
            self.pos_rotulo[(u, v)] = centro
            self.caixa_rotulo[(u, v)] = box
            self.colisoes_rotulo[(u, v)] = colisoes
            ocupados.append(box)

    def _montar_bloco(self, u: int, v: int, fluxo: float, capacidade: float) -> VGroup:
        """Bloco de 2 linhas (`f/C` + `→C−f ←f`) centrado na posição fixa."""
        linha1 = Text(
            textos_bloco(fluxo, capacidade)[0],
            font_size=FONTE_LINHA1,
            color=COR_TEXTO,
        )
        linha2 = linha2_bloco(fluxo, capacidade)
        bloco = VGroup(linha1, linha2).arrange(DOWN, buff=0.06)
        bloco.move_to(self.pos_rotulo[(u, v)])
        bloco.set_z_index(3)
        return bloco

    def _criar_aresta(self, u: int, v: int, capacidade: float) -> None:
        if (u, v) in self.arestas:
            return
        p0 = np.array([COORDS[u][0], COORDS[u][1], 0.0])
        p1 = np.array([COORDS[v][0], COORDS[v][1], 0.0])
        seta = Arrow(
            p0,
            p1,
            buff=BUFF_SETA,
            stroke_width=LARG_SETA,
            tip_length=PONTA,
            color=PALETA["fora"][0],
        )
        seta.set_z_index(1)

        largura, altura = self.dim_rotulo[(u, v)]
        fundo = RoundedRectangle(
            corner_radius=0.05,
            width=largura,
            height=altura,
            fill_color=COR_FUNDO,
            fill_opacity=1.0,
            stroke_width=0.0,
        ).move_to(self.pos_rotulo[(u, v)])
        fundo.set_z_index(2.5)
        bloco = self._montar_bloco(u, v, 0.0, capacidade)

        linha1, res_dir, res_rev = textos_bloco(0.0, capacidade)
        self.arestas[(u, v)] = seta
        self.fundos[(u, v)] = fundo
        self.textos[(u, v)] = bloco
        self.fluxo_atual[(u, v)] = linha1
        self.res_atual[(u, v)] = (res_dir, res_rev)
        self.cor_atual[(u, v)] = PALETA["fora"][0]
        self.larg_atual[(u, v)] = LARG_SETA

    def _criar_reversa(self, u: int, v: int) -> VGroup:
        """Arco tracejado v→u deslocado 0,15 na perpendicular (§2.4)."""
        p0 = np.array([COORDS[u][0], COORDS[u][1], 0.0])
        p1 = np.array([COORDS[v][0], COORDS[v][1], 0.0])
        d = p1 - p0
        norma = np.linalg.norm(d)
        perp = np.array([-d[1], d[0], 0.0]) / norma
        inicio = p1 - d / norma * (RAIO_NO + 0.10)
        fim = p0 + d / norma * (RAIO_NO + 0.10)
        arco = ArcBetweenPoints(inicio, fim, angle=-0.45).shift(perp * 0.15)
        tracejado = DashedVMobject(
            arco,
            num_dashes=14,
            dashed_ratio=0.55,
            color=PALETA["reversa"][0],
            stroke_width=1.8,
        )
        a = arco.point_from_proportion(0.97)
        b = arco.point_from_proportion(1.0)
        direcao = b - a
        ponta = Triangle(
            color=PALETA["reversa"][0], fill_opacity=1.0, stroke_width=0.0
        ).scale(0.055)
        ponta.rotate(np.arctan2(direcao[1], direcao[0]) - PI / 2).move_to(b)
        grupo = VGroup(tracejado, ponta)
        grupo.set_z_index(2)
        self.reversas[(u, v)] = grupo
        self.cor_reversa[(u, v)] = PALETA["reversa"][0]
        return grupo

    def ponto_reversa(self, u: int, v: int, frac: float = 0.5, desloc: float = 0.16):
        """Ponto no meio do arco reverso de `u→v`, fora dele (para rótulo)."""
        amostras = amostras_reversa(u, v)
        ponto = amostras[int(frac * (len(amostras) - 1))]
        p0 = np.array([COORDS[u][0], COORDS[u][1], 0.0])
        p1 = np.array([COORDS[v][0], COORDS[v][1], 0.0])
        d = p1 - p0
        perp = np.array([-d[1], d[0], 0.0]) / np.linalg.norm(d)
        return ponto + perp * desloc

    # -- destaques avulsos (introduções) -----------------------------------

    def pintar(self, u: int, v: int, cor: str, largura: float = LARG_SETA):
        """Pinta a aresta (direta ou reversa) e devolve a animação."""
        lado, chave = arcos_de(u, v, self.arestas_arquivo)
        if lado == "direta" and chave in self.arestas:
            self.cor_atual[chave] = cor
            self.larg_atual[chave] = largura
            return self.arestas[chave].animate.set_color(cor).set_stroke(width=largura)
        if lado == "reversa" and chave in self.reversas:
            self.cor_reversa[chave] = cor
            return self.reversas[chave].animate.set_color(cor)
        return None

    def flash(self, u: int, v: int, cor: str | None = None) -> Flash:
        lado, _chave = arcos_de(u, v, self.arestas_arquivo)
        ponto = (
            self.ponto_reversa(u, v, 0.5, 0.0)
            if lado == "reversa"
            else ponto_na_aresta(u, v, 0.5)
        )
        return self._flash(ponto, cor or PALETA["exame"][0])

    def rotulo_residual(self, chave: tuple[int, int], texto: str) -> VGroup:
        """Rótulo `res = f` no meio do arco reverso da aresta `chave`."""
        u, v = chave
        return self._rotulo_com_fundo(
            texto, self.ponto_reversa(u, v), 12, PALETA["reversa"][0]
        )

    def _rotulo_com_fundo(self, texto: str, centro, fonte: int, cor: str) -> VGroup:
        t = Text(texto, font_size=fonte, color=cor)
        fundo = RoundedRectangle(
            corner_radius=0.05,
            width=t.width + 0.10,
            height=t.height + 0.06,
            fill_color=COR_FUNDO,
            fill_opacity=1.0,
            stroke_width=0.0,
        ).move_to(centro)
        t.move_to(centro)
        grupo = VGroup(fundo, t)
        grupo.set_z_index(6)
        return grupo

    # -- troca do bloco (nunca Transform de string) ------------------------

    def _troca_bloco(
        self, u: int, v: int, fluxo: float, capacidade: float
    ) -> Animation:
        antigo = self.textos[(u, v)]
        novo = self._montar_bloco(u, v, fluxo, capacidade)
        linha1, res_dir, res_rev = textos_bloco(fluxo, capacidade)
        self.textos[(u, v)] = novo
        self.fluxo_atual[(u, v)] = linha1
        self.res_atual[(u, v)] = (res_dir, res_rev)
        return AnimationGroup(
            FadeOut(antigo, run_time=RITMO["play"]),
            FadeIn(novo, run_time=RITMO["play"]),
        )

    def _atualizar_bloco(
        self, u: int, v: int, fluxo: float, capacidade: float
    ) -> list[Animation]:
        linha1, res_dir, res_rev = textos_bloco(fluxo, capacidade)
        if (
            linha1 == self.fluxo_atual[(u, v)]
            and (res_dir, res_rev) == self.res_atual[(u, v)]
        ):
            return []
        return [self._troca_bloco(u, v, fluxo, capacidade)]

    # -- estado imediato (introduções) -------------------------------------

    def _aplicar_imediato(self, estado: dict) -> None:
        """Constrói o desenho já no estado dado, sem animação (introduções)."""
        for u, v, c in estado["arestas"]:
            self._criar_aresta(u, v, c)
            self.presentes.add((u, v))

        for u, v in sorted(self.presentes):
            fluxo = estado["fluxos"].get((u, v), 0.0)
            cap = estado["capacidades"].get((u, v), 0.0)
            papel = "fora" if fluxo <= 0 else ("saturada" if fluxo >= cap else "fluxo")
            cor = PALETA[papel][0]
            larg = LARG_SETA if papel == "fora" else 4.2
            self.arestas[(u, v)].set_color(cor).set_stroke(width=larg)
            self.cor_atual[(u, v)] = cor
            self.larg_atual[(u, v)] = larg
            linha1, res_dir, res_rev = textos_bloco(fluxo, cap)
            if (
                linha1 != self.fluxo_atual[(u, v)]
                or (res_dir, res_rev) != self.res_atual[(u, v)]
            ):
                self.textos[(u, v)] = self._montar_bloco(u, v, fluxo, cap)
                self.fluxo_atual[(u, v)] = linha1
                self.res_atual[(u, v)] = (res_dir, res_rev)

        for u, v in sorted(self.presentes):
            if estado["residual_reversa"].get((u, v), 0.0) > 0:
                self._criar_reversa(u, v)

        marcados = set(estado.get("marcados") or [])
        for v in range(rec.V_REDE):
            cor = PALETA["alcancado"][0] if v in marcados else COR_NO
            self.circulos[v].set_fill(cor, opacity=1.0)
            self.fill_atual[v] = cor

    def aplicar(self, estado: dict, run_time: float = 0.4) -> list[Animation]:
        """Leva o desenho ao estado dado, animando só o que muda."""
        anims: list[Animation] = []
        presentes = {(u, v) for u, v, _c in estado["arestas"]}
        for u, v in sorted(presentes - self.presentes):
            self._criar_aresta(u, v, estado["capacidades"][(u, v)])
            self.presentes.add((u, v))
            anims += [
                FadeIn(self.arestas[(u, v)], run_time=run_time),
                FadeIn(self.fundos[(u, v)], run_time=run_time),
                FadeIn(self.textos[(u, v)], run_time=run_time),
            ]

        for u, v in sorted(self.presentes):
            fluxo = estado["fluxos"].get((u, v), 0.0)
            cap = estado["capacidades"].get((u, v), 0.0)
            papel = "fora" if fluxo <= 0 else ("saturada" if fluxo >= cap else "fluxo")
            cor = PALETA[papel][0]
            larg = LARG_SETA if papel == "fora" else 4.2
            if cor != self.cor_atual[(u, v)]:
                self.arestas[(u, v)].set_color(cor)
                self.cor_atual[(u, v)] = cor
            if abs(larg - self.larg_atual[(u, v)]) > 1e-6:
                self.arestas[(u, v)].set_stroke(width=larg)
                self.larg_atual[(u, v)] = larg
            anims += self._atualizar_bloco(u, v, fluxo, cap)

        for u, v in sorted(self.presentes):
            if estado["residual_reversa"].get((u, v), 0.0) > 0 and (u, v) not in self.reversas:
                grupo = self._criar_reversa(u, v)
                anims.append(FadeIn(grupo, run_time=run_time))
            elif (
                estado["residual_reversa"].get((u, v), 0.0) <= 0
                and (u, v) in self.reversas
            ):
                grupo = self.reversas.pop((u, v))
                self.cor_reversa.pop((u, v), None)
                anims.append(FadeOut(grupo, run_time=run_time))

        marcados = set(estado.get("marcados") or [])
        for v in range(rec.V_REDE):
            cor = PALETA["alcancado"][0] if v in marcados else COR_NO
            if cor != self.fill_atual[v]:
                self.circulos[v].set_fill(cor, opacity=1.0)
                self.fill_atual[v] = cor
        return anims

    # -- destaque de um passo ---------------------------------------------

    def _flash(self, ponto, cor: str) -> Flash:
        return Flash(
            ponto,
            color=cor,
            line_length=0.12,
            num_lines=8,
            flash_radius=0.22,
            run_time=RITMO["play_destaque"],
        )

    def animar(self, passo) -> tuple[list[Animation], list[Mobject], list[Mobject]]:
        """Devolve (animações, mobjects a adicionar, mobjects a remover)."""
        est = passo.estado
        tipo, u, v, status = passo.destaque
        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        # 1) aresta que entra na rede: a presença vem do estado (o passo
        #    `("aresta", u, v, "insere")` chega antes de a aresta existir).
        presentes = {(a, b) for a, b, _c in est["arestas"]}
        for a, b in sorted(presentes - self.presentes):
            self._criar_aresta(a, b, est["capacidades"][(a, b)])
            self.presentes.add((a, b))
            adicionar += [
                self.arestas[(a, b)],
                self.fundos[(a, b)],
                self.textos[(a, b)],
            ]
            anims += [
                FadeIn(self.arestas[(a, b)], run_time=RITMO["play"]),
                FadeIn(self.fundos[(a, b)], run_time=RITMO["play"]),
                FadeIn(self.textos[(a, b)], run_time=RITMO["play"]),
                self._flash(ponto_na_aresta(a, b, 0.5), PALETA["caminho"][0]),
            ]

        # 2) alvo de cor: foco do passo, senão o estado base da aresta
        lado, chave = "", (u, v)
        if u is not None and tipo in ("busca", "caminho", "aumento", "corte"):
            lado, chave = arcos_de(u, v, self.arestas_arquivo)

        cor_foco, larg_foco = None, LARG_SETA
        if tipo == "busca" and status in ("olhando", "examina", "descoberto"):
            cor_foco, larg_foco = PALETA["exame"][0], 4.2
        elif tipo == "caminho" and status == "aumentante":
            cor_foco, larg_foco = PALETA["caminho"][0], 5.5
        elif tipo == "aumento":
            cor_foco, larg_foco = PALETA["caminho"][0], 5.5
        elif tipo == "corte" and status == "cruza":
            lado_corte = set(est["corte"])
            if u in lado_corte and v not in lado_corte:
                cor_foco, larg_foco = PALETA["caminho"][0], 5.5
            else:
                # o trace dispara "cruza" para TODA aresta avaliada no check;
                # só é corte de verdade a que vai de S para T.
                cor_foco, larg_foco = PALETA["exame"][0], 4.2

        for a, b in sorted(self.presentes):
            fluxo = est["fluxos"].get((a, b), 0.0)
            cap = est["capacidades"].get((a, b), 0.0)
            papel = "fora" if fluxo <= 0 else ("saturada" if fluxo >= cap else "fluxo")
            cor = PALETA[papel][0]
            larg = LARG_SETA if papel == "fora" else 4.2
            if lado == "direta" and chave == (a, b) and cor_foco is not None:
                cor, larg = cor_foco, larg_foco
            if cor != self.cor_atual[(a, b)] or abs(larg - self.larg_atual[(a, b)]) > 1e-6:
                anims.append(
                    self.arestas[(a, b)].animate.set_color(cor).set_stroke(width=larg)
                )
                self.cor_atual[(a, b)] = cor
                self.larg_atual[(a, b)] = larg
            anims += self._atualizar_bloco(a, b, fluxo, cap)

        # 3) reversas: nascem quando o fluxo deixa de ser zero
        for a, b in sorted(self.presentes):
            tem = est["residual_reversa"].get((a, b), 0.0) > 0
            if tem and (a, b) not in self.reversas:
                grupo = self._criar_reversa(a, b)
                adicionar.append(grupo)
                anims.append(FadeIn(grupo, run_time=RITMO["play"]))
            elif not tem and (a, b) in self.reversas:
                grupo = self.reversas.pop((a, b))
                self.cor_reversa.pop((a, b), None)
                remover.append(grupo)
                anims.append(FadeOut(grupo, run_time=RITMO["play"]))

        for chave_rev, grupo in self.reversas.items():
            cor = PALETA["reversa"][0]
            if lado == "reversa" and chave == chave_rev and cor_foco is not None:
                cor = cor_foco
            if cor != self.cor_reversa.get(chave_rev):
                anims.append(grupo.animate.set_color(cor))
                self.cor_reversa[chave_rev] = cor

        # 4) alcançados (lado S)
        marcados = set(est.get("marcados") or [])
        for no in range(rec.V_REDE):
            cor = PALETA["alcancado"][0] if no in marcados else COR_NO
            if cor != self.fill_atual[no]:
                anims.append(self.circulos[no].animate.set_fill(cor, opacity=1.0))
                self.fill_atual[no] = cor

        # 5) anel de foco (sticky no bookkeeping, como pede o plano)
        foco = self.foco
        if tipo == "busca" and status in ("olhando", "examina") and u is not None:
            foco = u
        elif tipo == "busca" and status == "descoberto" and v is not None:
            foco = v
        elif tipo == "busca" and status in ("nova", "fim"):
            foco = None
        elif tipo in ("caminho", "aumento", "valor", "corte"):
            foco = None
        if foco != self.foco:
            if foco is None:
                anims.append(self.anel_foco.animate.set_stroke(opacity=0.0))
            else:
                alvo = np.array([COORDS[foco][0], COORDS[foco][1], 0.0])
                anims.append(
                    self.anel_foco.animate.move_to(alvo).set_stroke(
                        color=PALETA["exame"][0], width=2.0, opacity=1.0
                    )
                )
            self.foco = foco

        # 6) lados do corte (o fecho é gradual no trace)
        if tipo == "corte" and status in ("lado_s", "lado_t") and v is not None:
            cor = PALETA["alcancado"][0] if status == "lado_s" else COR_BORDA_NO
            anims.append(
                self.aneis_corte[v].animate.set_stroke(color=cor, width=2.2, opacity=1.0)
            )

        # flashes de inspeção / augmentação / valor
        if tipo == "busca" and status in ("olhando", "examina", "descoberto"):
            if lado == "reversa":
                ponto = self.ponto_reversa(u, v, 0.5, 0.0)
            else:
                ponto = ponto_na_aresta(u, v, 0.5)
            anims.append(self._flash(ponto, PALETA["exame"][0]))
        elif tipo in ("caminho", "aumento"):
            ponto = (
                self.ponto_reversa(u, v, 0.5, 0.0)
                if lado == "reversa"
                else ponto_na_aresta(u, v, 0.5)
            )
            anims.append(self._flash(ponto, PALETA["caminho"][0]))
        elif tipo == "valor":
            anims.append(
                self._flash(
                    np.array([COORDS[rec.T_SUMIDOURO][0], COORDS[rec.T_SUMIDOURO][1], 0.0]),
                    PALETA["caminho"][0],
                )
            )
        elif tipo == "busca" and status == "nova" and est.get("caminho"):
            for a, b in est["caminho"]:
                lado_p, chave_p = arcos_de(a, b, self.arestas_arquivo)
                if lado_p == "direta" and chave_p in self.arestas:
                    anims.append(
                        self.arestas[chave_p].animate.set_color(
                            PALETA["caminho"][0]
                        ).set_stroke(width=5.5)
                    )
                    self.cor_atual[chave_p] = PALETA["caminho"][0]
                    self.larg_atual[chave_p] = 5.5
            anims.append(
                self._flash(
                    np.array([COORDS[rec.T_SUMIDOURO][0], COORDS[rec.T_SUMIDOURO][1], 0.0]),
                    PALETA["caminho"][0],
                )
            )

        return anims, adicionar, remover

    # -- fecho: corte mínimo ----------------------------------------------

    def destacar_corte(self, estado: dict) -> list[Animation]:
        anims: list[Animation] = []
        lado = set(estado["corte"])
        for v in range(rec.V_REDE):
            cor = PALETA["alcancado"][0] if v in lado else COR_BORDA_NO
            anims.append(
                self.aneis_corte[v].animate.set_stroke(color=cor, width=2.2, opacity=1.0)
            )
        for a, b in sorted(self.presentes):
            if a in lado and b not in lado:
                anims.append(
                    self.arestas[(a, b)].animate.set_color(
                        PALETA["caminho"][0]
                    ).set_stroke(width=5.5)
                )
                self.cor_atual[(a, b)] = PALETA["caminho"][0]
                self.larg_atual[(a, b)] = 5.5
                anims.append(self._flash(ponto_na_aresta(a, b, 0.5), PALETA["caminho"][0]))
        if self.foco is not None:
            anims.append(self.anel_foco.animate.set_stroke(opacity=0.0))
            self.foco = None
        return anims


# ---------------------------------------------------------------------------
# Paginação do código (PLANO_VISUAL_FLUXO_V2 §B)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PaginaCodigo:
    """Uma página física do código de UMA função.

    `linhas_fisicas` é a lista `(lineno_real, texto)` já com as quebras de
    linha longa; a continuação repete o `lineno` da linha-fonte. `mapa_linha`
    leva o número REAL da linha-fonte ao índice da primeira linha física dela
    (é o que o indicador e o gutter usam).
    """

    funcao: rec.FuncaoCodigo
    k: int
    n: int
    linhas_fisicas: tuple[tuple[int, str], ...]
    mapa_linha: dict  # int -> row (primeira linha física da linha-fonte)
    texto: str
    inicio: int
    fim: int

    def contem(self, linha: int) -> bool:
        return linha in self.mapa_linha


def _marcas_corpo(funcao: rec.FuncaoCodigo) -> set[int]:
    """Linhas REAIS dos comandos de nível 1 do corpo da função (ast)."""
    arvore = ast.parse(textwrap.dedent(funcao.texto))
    alvo = next(n for n in ast.walk(arvore) if isinstance(n, ast.FunctionDef))
    return {stmt.lineno + funcao.inicio - 1 for stmt in alvo.body}


def _linhas_fisicas(funcao: rec.FuncaoCodigo) -> list[tuple[int, str]]:
    """Linhas do fonte com quebra só em espaço; nada de caractere removido."""
    fisicas: list[tuple[int, str]] = []
    for desloc, linha in enumerate(funcao.texto.splitlines()):
        lineno = funcao.inicio + desloc
        if len(linha) <= COLUNAS_MAX:
            pedacos = [linha]
        else:
            recuo = len(linha) - len(linha.lstrip())
            pedacos = textwrap.wrap(
                linha,
                width=COLUNAS_MAX,
                subsequent_indent=" " * (recuo + 4),
                break_long_words=False,
                break_on_hyphens=False,
            ) or [linha]
            # invariante explícito: só espaços saem, nenhum token se perde
            if "".join(pedacos).split() != linha.split():
                raise AssertionError(f"{funcao.nome}: quebra de linha perdeu token")
        fisicas.extend((lineno, pedaco) for pedaco in pedacos)
    return fisicas


def paginar_funcao(funcao: rec.FuncaoCodigo) -> list[PaginaCodigo]:
    """Pagina a função em blocos de ≤ `MAX_LINHAS_PAGINA` linhas físicas.

    A fronteira é SEMPRE um comando de nível 1 do corpo (nunca no meio de um
    `for`/`if`/`while`), escolhendo o maior candidato que ainda cabe. O
    fallback (comando de nível 1 maior que a página) corta duro em 23; o
    validador falha se ele for necessário.
    """
    fisicas = _linhas_fisicas(funcao)
    marcas = _marcas_corpo(funcao)
    candidatos = [
        i
        for i in range(1, len(fisicas))
        if fisicas[i][0] in marcas and fisicas[i - 1][0] != fisicas[i][0]
    ]

    blocos: list[list[tuple[int, str]]] = []
    ini = 0
    while ini < len(fisicas):
        if len(fisicas) - ini <= MAX_LINHAS_PAGINA:
            blocos.append(fisicas[ini:])
            break
        opcoes = [c for c in candidatos if ini < c <= ini + MAX_LINHAS_PAGINA]
        fim = max(opcoes) if opcoes else ini + MAX_LINHAS_PAGINA
        blocos.append(fisicas[ini:fim])
        ini = fim

    paginas: list[PaginaCodigo] = []
    n = len(blocos)
    for k, bloco in enumerate(blocos, start=1):
        mapa: dict[int, int] = {}
        for row, (lineno, _texto) in enumerate(bloco):
            mapa.setdefault(lineno, row)
        paginas.append(
            PaginaCodigo(
                funcao=funcao,
                k=k,
                n=n,
                linhas_fisicas=tuple(bloco),
                mapa_linha=mapa,
                texto="\n".join(texto for _lineno, texto in bloco),
                inicio=funcao.inicio,
                fim=funcao.fim,
            )
        )
    return paginas


def _code_de_pagina(pagina: PaginaCodigo) -> Code:
    codigo = Code(
        code_string=pagina.texto,
        language="python",
        formatter_style="monokai",
        add_line_numbers=False,
        background="rectangle",
    )
    codigo.remove(codigo.background)
    return codigo


# Medidas comuns aos dois painéis (a escala é UMA para as duas cenas, §B.4).
GUTTER_LARGURA = 0.733  # 3 dígitos a fonte 24 (0,593) + respiro 0,14
_ESCALA_CODIGO: float | None = None


def escala_codigo() -> float:
    """Escala única: a MAIOR página das duas cenas manda (sem zoom na troca)."""
    global _ESCALA_CODIGO
    if _ESCALA_CODIGO is not None:
        return _ESCALA_CODIGO

    largura_util = CODIGO["largura"] - CodePanel.PADDING_ESQ - CodePanel.PADDING_DIR
    altura_util = CODIGO["altura"] - CodePanel.PADDING_TOPO - CodePanel.PADDING_BASE
    altura_cabecalho = Text("x\ny", font_size=CodePanel.FONTE_CABECALHO).height
    altura_cabecalho += CodePanel.BUFF_CABECALHO

    maior_altura = 0.0
    maior_largura = 0.0
    for alg in ("edmonds_karp", "ford_fulkerson_dfs"):
        for funcao in rec.funcoes_codigo(alg):
            for pagina in paginar_funcao(funcao):
                codigo = _code_de_pagina(pagina)
                maior_altura = max(maior_altura, codigo.height)
                maior_largura = max(maior_largura, codigo.width + GUTTER_LARGURA)

    _ESCALA_CODIGO = min(
        (altura_util - altura_cabecalho) / maior_altura,
        largura_util / maior_largura,
    )
    return _ESCALA_CODIGO


# ---------------------------------------------------------------------------
# Painel de código: moldura fixa 7,86 × 4,55, uma página por view (§B)
# ---------------------------------------------------------------------------


class CodePanel:
    """Código real da função executada, na íntegra, paginado, com moldura fixa.

    - uma `Code` por PÁGINA (não por função), sem numeração nativa;
    - gutter próprio com os números REAIS (nenhum número na continuação);
    - a escala é calculada UMA vez pela maior página das duas cenas;
    - o grupo estável contém só a moldura; conteúdo, gutter e indicador são
      mobjects de cena (sem texto fantasma);
    - troca de página em DOIS `play`: FadeOut total e só depois FadeIn.
    """

    PADDING_ESQ = 0.16
    PADDING_DIR = 0.16
    PADDING_TOPO = 0.12
    PADDING_BASE = 0.12
    BUFF_CABECALHO = 0.06
    TEMPO_FADE = RITMO["fade"]
    FONTE_CODIGO = 24  # fonte nativa do `Code` (base do pt efetivo)
    FONTE_CABECALHO = 11
    FONTE_GUTTER = 24

    def __init__(self, algoritmo: str):
        self.algoritmo = algoritmo
        self.funcoes = list(rec.funcoes_codigo(algoritmo))
        self._por_chave = {(f.modulo, f.nome): i for i, f in enumerate(self.funcoes)}

        self.paginas: list[PaginaCodigo] = []
        self._paginas_da_funcao: list[list[int]] = []
        for funcao in self.funcoes:
            indices = []
            for pagina in paginar_funcao(funcao):
                indices.append(len(self.paginas))
                self.paginas.append(pagina)
            self._paginas_da_funcao.append(indices)

        self.escala = escala_codigo()
        self.fonte_efetiva = self.FONTE_CODIGO * self.escala

        self.codigos: list[Code] = []
        self.gutters: list[VGroup] = []
        self.conteudos: list[VGroup] = []
        self.cabecalhos: list[Text] = []
        for pagina in self.paginas:
            codigo = _code_de_pagina(pagina)
            gutter = self._gutter(codigo, pagina)
            corpo = VGroup(gutter, codigo)
            corpo.scale(self.escala)
            cabecalho = Text(
                self._rotulo(pagina),
                font_size=self.FONTE_CABECALHO,
                color=COR_CABECALHO,
            )
            conteudo = VGroup(cabecalho, corpo).arrange(
                DOWN, aligned_edge=LEFT, buff=self.BUFF_CABECALHO
            )
            self.codigos.append(codigo)
            self.gutters.append(gutter)
            self.conteudos.append(conteudo)
            self.cabecalhos.append(cabecalho)

        # Moldura FIXA do contrato (§1); nunca é reconstruída.
        self.moldura = RoundedRectangle(
            corner_radius=0.08,
            width=CODIGO["largura"],
            height=CODIGO["altura"],
            color=COR_BORDA_NO,
            stroke_width=1.2,
            fill_color="#12141d",
            fill_opacity=0.85,
        )
        self.moldura.to_corner(UL, buff=CODIGO["buff"])

        ancora = (
            self.moldura.get_corner(UL)
            + RIGHT * self.PADDING_ESQ
            + DOWN * self.PADDING_TOPO
        )
        for conteudo in self.conteudos:
            conteudo.move_to(ancora, aligned_edge=UL)

        self.indicadores = [
            SurroundingRectangle(
                codigo.code_lines[0],
                color=PALETA["caminho"][0],
                buff=0.04,
                stroke_width=2.2,
                fill_color=PALETA["caminho"][0],
                fill_opacity=0.12,
            )
            for codigo in self.codigos
        ]

        self.mobject = VGroup(self.moldura)
        self.ativo: int | None = None
        self.visivel: VGroup | None = None
        self.indicador: SurroundingRectangle | None = None

    # -- gutter ------------------------------------------------------------

    def _gutter(self, codigo: Code, pagina: PaginaCodigo) -> VGroup:
        """Um número por linha-FONTE; a continuação não recebe número."""
        x = codigo.get_left()[0] - 0.14
        numeros = []
        for lineno, row in pagina.mapa_linha.items():
            y = codigo.code_lines[row].get_center()[1]
            numero = Text(
                str(lineno), font_size=self.FONTE_GUTTER, color=COR_BORDA_NO
            )
            numero.move_to(np.array([x, y, 0.0]), aligned_edge=RIGHT)
            numeros.append(numero)
        return VGroup(*numeros)

    # -- cabeçalho e indicador --------------------------------------------

    def _rotulo(
        self, pagina: PaginaCodigo, origem: PaginaCodigo | None = None
    ) -> str:
        """Cabeçalho de DUAS linhas (§B.2); o sufixo depende só da TROCA real.

        Linha 1 = `{nome} · {arquivo}:{inicio}–{fim}`; linha 2 = `parte k de n`
        (+ marcador quando a página é alcançada por troca adjacente na mesma
        função). Página de função com `n == 1` tem só a linha 1: `parte 1 de 1`
        é ruído (ajuste do usuário sobre o §B.3 do plano).
        """
        f = pagina.funcao
        arquivo = Path(f.arquivo).name
        texto = f"{f.nome} · {arquivo}:{f.inicio}–{f.fim}"
        if pagina.n == 1:
            return texto
        linha2 = f"parte {pagina.k} de {pagina.n}"
        if origem is None:
            return texto + "\n" + linha2
        adjacente = (
            origem.funcao is pagina.funcao
            and origem.n == pagina.n
            and abs(origem.k - pagina.k) == 1
        )
        if not adjacente:
            return texto + "\n" + linha2
        if pagina.k == origem.k + 1:
            linha2 += f" · ▸ continuação da parte {origem.k} de {pagina.n}"
        else:
            linha2 += f" · ◂ volta da parte {origem.k} de {pagina.n}"
        return texto + "\n" + linha2

    def _atualizar_cabecalho(self, indice: int, origem_ind: int) -> None:
        """Reescreve o cabeçalho da página que vai entrar, conforme a troca."""
        pagina = self.paginas[indice]
        antigo = self.cabecalhos[indice]
        texto = self._rotulo(pagina, self.paginas[origem_ind])
        if antigo.original_text == texto:
            return
        novo = Text(texto, font_size=self.FONTE_CABECALHO, color=COR_CABECALHO)
        # topo fixo: a página com `n == 1` tem 1 linha e não pode descer
        # meia linha em relação ao cabeçalho de 2 linhas que ela substitui.
        novo.move_to(antigo, aligned_edge=UL)
        self.conteudos[indice].submobjects[0] = novo
        self.cabecalhos[indice] = novo

    def _view(self, passo: rec.Step) -> int:
        """Índice plano da PÁGINA que contém a linha executada."""
        funcao = rec.funcao_da_linha(self.algoritmo, passo.linha, passo.modulo)
        indice_funcao = self._por_chave[(funcao.modulo, funcao.nome)]
        for indice in self._paginas_da_funcao[indice_funcao]:
            if self.paginas[indice].contem(passo.linha):
                return indice
        raise LookupError(
            f"{self.algoritmo}: linha {passo.linha} de {funcao.nome} fora das páginas"
        )

    def _pagina_de(self, passo: rec.Step) -> PaginaCodigo:
        return self.paginas[self._view(passo)]

    def _posicionar(self, indicador, indice: int, linha: int) -> None:
        pagina = self.paginas[indice]
        row = pagina.mapa_linha.get(linha, 0)
        alvo = self.codigos[indice].code_lines[row]
        indicador.move_to(alvo.get_center())
        indicador.stretch_to_fit_width(alvo.width + 0.25)
        indicador.stretch_to_fit_height(alvo.height + 0.12)

    def encaixar(self, passo: rec.Step) -> None:
        """Primeira montagem: o indicador nasce na linha executada."""
        indice = self._view(passo)
        self.ativo = indice
        self.visivel = self.conteudos[indice]
        self.indicador = self.indicadores[indice]
        self._posicionar(self.indicador, indice, passo.linha)

    def mudou(self, passo: rec.Step) -> bool:
        return self._view(passo) != self.ativo

    def trocar(self, passo: rec.Step) -> tuple[list[Animation], list[Animation]]:
        """Troca de página: devolve `(sai, entra)` para DOIS `play`."""
        indice = self._view(passo)
        if indice == self.ativo:
            return [], []

        antigo, antigo_ind = self.visivel, self.indicador
        self._atualizar_cabecalho(indice, self.ativo)
        novo, novo_ind = self.conteudos[indice], self.indicadores[indice]
        self._posicionar(novo_ind, indice, passo.linha)
        self.ativo = indice
        self.visivel = novo
        self.indicador = novo_ind

        t = self.TEMPO_FADE
        sai = [
            FadeOut(antigo, run_time=t, shift=DOWN * 0.10),
            FadeOut(antigo_ind, run_time=t, shift=DOWN * 0.10),
        ]
        entra = [
            FadeIn(novo, run_time=t, shift=UP * 0.10),
            FadeIn(novo_ind, run_time=t, shift=UP * 0.10),
        ]
        return sai, entra

    def destacar(self, passo: rec.Step) -> Animation:
        indice = self.ativo
        pagina = self.paginas[indice]
        row = pagina.mapa_linha.get(passo.linha, 0)
        alvo = self.codigos[indice].code_lines[row]
        return (
            self.indicador.animate.move_to(alvo.get_center())
            .stretch_to_fit_width(alvo.width + 0.25)
            .stretch_to_fit_height(alvo.height + 0.12)
        )



# ---------------------------------------------------------------------------
# Painel de estado: 5 slots fixos (§6)
# ---------------------------------------------------------------------------


class StatePanel:
    """5 slots fixos, alinhados à esquerda, sem trepidação.

    Slot 1/2 = ação em duas linhas (quebra determinística em 44 ch), 3 = fila
    ou pilha, 4 = marcados, 5 = veredito do corte (só no fecho).
    """

    N_SLOTS = 5

    def __init__(self, algoritmo: str):
        self.algoritmo = algoritmo
        self.centro = np.array([ESTADO["centro"][0], ESTADO["centro"][1], 0.0])
        self.largura = ESTADO["largura"]
        self.altura = ESTADO["altura"]
        self.fundo = RoundedRectangle(
            corner_radius=0.15,
            width=self.largura,
            height=self.altura,
            color=COR_BORDA_NO,
            stroke_width=1.5,
            fill_color=COR_PAINEL,
            fill_opacity=0.9,
        ).move_to(self.centro)

        x0 = self.centro[0] - self.largura / 2 + 0.22
        util = self.altura - 0.40
        passo = util / (self.N_SLOTS - 1)
        topo = self.centro[1] + util / 2
        self.posicoes = [
            np.array([x0, topo - i * passo, 0.0]) for i in range(self.N_SLOTS)
        ]

        self.linhas: list[Text | None] = [None] * self.N_SLOTS
        self.conteudos: list[str] = [""] * self.N_SLOTS
        self.cores: list[str] = [""] * self.N_SLOTS
        self.fontes: list[int] = [12] * self.N_SLOTS

    def _criar(self, i: int, texto: str, cor: str, fonte: int) -> Text:
        t = Text(texto, font_size=fonte, color=cor)
        t.move_to(self.posicoes[i], aligned_edge=LEFT)
        return t

    def iniciar(self, textos: list[tuple[str, str, int]]) -> list[Mobject]:
        for i, (texto, cor, fonte) in enumerate(textos):
            # slot vazio NÃO vira mobject: `Text(" ")` não tem pontos e ficaria
            # parado na origem. O slot nasce no FadeIn quando o texto chega.
            self.linhas[i] = self._criar(i, texto, cor, fonte) if texto else None
            self.conteudos[i] = texto
            self.cores[i] = cor
            self.fontes[i] = fonte
        return [self.fundo, *[l for l in self.linhas if l is not None]]

    def atualizar(self, textos: list[tuple[str, str, int]]) -> list[Animation]:
        anims: list[Animation] = []
        for i, (texto, cor, fonte) in enumerate(textos):
            if texto == self.conteudos[i] and cor == self.cores[i] and fonte == self.fontes[i]:
                continue
            novo = self._criar(i, texto, cor, fonte)
            antigo = self.linhas[i]
            if antigo is None:
                anims.append(FadeIn(novo, run_time=RITMO["play"]))
            else:
                deslize = UP * 0.12 if i > 0 else ORIGIN
                anims.append(
                    AnimationGroup(
                        FadeOut(antigo, run_time=RITMO["play"], shift=deslize),
                        FadeIn(novo, run_time=RITMO["play"], shift=deslize),
                    )
                )
            self.linhas[i] = novo
            self.conteudos[i] = texto
            self.cores[i] = cor
            self.fontes[i] = fonte
        return anims

    def textos_do_passo(self, passo, max_iteracao: int) -> list[tuple[str, str, int]]:
        """Os 5 slots a partir do passo (slot 5 só no fecho)."""
        est = passo.estado
        cor = cor_destaque(passo)
        linha1, linha2 = dividir_acao(passo.acao)
        if self.algoritmo == "edmonds_karp":
            busca = fmt_fila(est)
            if est.get("fila"):
                busca += f" · frente {est['fila'][0]}"
        else:
            busca = fmt_pilha(est)
            if est.get("pilha"):
                busca += f" · topo {est['pilha'][-1]}"
        return [
            (linha1, cor, 12),
            (linha2, cor, 12),
            (busca, COR_BORDA_NO, 11),
            (fmt_marcados(est), PALETA["alcancado"][0], 11),
            ("", ESTRUTURAIS["texto"], 12),
        ]


# ---------------------------------------------------------------------------
# Guia visual: 7 papéis, fonte única 12, duas linhas (4 + 3) (§3)
# ---------------------------------------------------------------------------


class GuiaVisual:
    FONTE = 12
    BUFF_ITEM = 0.26

    def __init__(self):
        itens = []
        for papel in ORDEM_GUIA:
            cor, texto, forma = PALETA[papel]
            if forma == "ring":
                marca = Circle(radius=0.075, color=cor, stroke_width=2.6, fill_opacity=0.0)
            elif forma == "dash":
                marca = DashedLine(
                    LEFT * 0.08,
                    RIGHT * 0.08,
                    dash_length=0.035,
                    stroke_width=1.8,
                    color=cor,
                )
            else:
                marca = Dot(color=cor, radius=0.075)
            itens.append(
                VGroup(marca, Text(texto, font_size=self.FONTE, color=COR_TEXTO)).arrange(
                    RIGHT, buff=0.10
                )
            )

        linha1 = VGroup(*itens[:4]).arrange(RIGHT, buff=self.BUFF_ITEM)
        linha2 = VGroup(*itens[4:]).arrange(RIGHT, buff=self.BUFF_ITEM)
        self.mobject = VGroup(linha1, linha2).arrange(
            DOWN, aligned_edge=LEFT, buff=0.10
        )
        self.mobject.move_to(np.array([TITULO_X, -0.44, 0.0]), aligned_edge=UL)
        self.larguras = (linha1.width, linha2.width)


# ---------------------------------------------------------------------------
# Painel de estrutura: 5 abas em trilho vertical (§C)
# ---------------------------------------------------------------------------


ABAS = {
    "edmonds_karp": (
        ("rede", "Rede residual"),
        ("busca", "Fila (BFS)"),
        ("marcados", "marked[]"),
        ("edge_to", "edgeTo[]"),
        ("adj", "adj[]"),
    ),
    "ford_fulkerson_dfs": (
        ("rede", "Rede residual"),
        ("busca", "Pilha (DFS)"),
        ("marcados", "marked[]"),
        ("edge_to", "edgeTo[]"),
        ("adj", "adj[]"),
    ),
}

ORDEM_ABAS = ("rede", "busca", "marcados", "edge_to", "adj")

# Guia de símbolos (§A.2): uma linha contextual por aba, fonte 10. A notação
# `C_f` é a do material do aluno; o grafo usa a forma curta `→`/`←` (§C.3).
GUIA_SIMBOLOS = {
    "rede": "C = C(u,v) nominal · f = f(u,v) · res→ = C_f(u,v) = C−f · res← = C_f(v,u) = f",
    "busca_bfs": "frente = próximo a sair · fim = último a entrar",
    "busca_dfs": "base = primeiro da pilha · topo = chamada atual",
    "marcados": "marked[v] = alcançado pela residual · S* = lado da fonte",
    "edge_to": "edgeTo[v] = aresta que descobriu v · fila = ordem de descoberta · frente = 1º",
    "adj": "adj[v] · fila de inspeção · frente = 1ª aresta do for · ▸sai ◂entra",
}

COR_TAB_ATIVA = "#1f2637"
COR_TAB_INATIVA = "#0f111a"
COR_CHIP = "#1f2637"
COR_CHIP_FOCO = COR_LINHA_TABELA

X0_ESTRUTURA = -5.00  # origem do corpo da aba (§C.5)
Y_CAPTION = -1.52
Y_CABECALHO = -1.80


@lru_cache(maxsize=None)
def _faixa_gargalo(algoritmo: str) -> tuple[int, int]:
    """Linhas do bloco de gargalo do `__init__` (bottle = min(...)).

    Derivadas do ast do fonte real: o laço MAIS INTERNO que contém
    `residual_capacity_to` (`while v != s`) e as atribuições de preparo
    imediatamente acima (`bottle = inf`, `v = t`). É a janela em que a aba
    `edgeTo` (a fila de descoberta) é o sujeito.
    """
    modulo, _inicio, _fim = rec.TRECHOS[algoritmo]
    classe = "FordFulkerson" if algoritmo == "edmonds_karp" else "FordFulkersonDFS"
    arvore = ast.parse(rec.arquivo_modulo(modulo).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if not (isinstance(no, ast.ClassDef) and no.name == classe):
            continue
        for filho in no.body:
            if not (isinstance(filho, ast.FunctionDef) and filho.name == "__init__"):
                continue
            # Vários `while` ancestrais contêm a chamada; o laço do gargalo é
            # o MENOR deles (o mais interno), não o `while has_augmenting_path`.
            candidatos: list[tuple[int, ast.While]] = []
            for sub in ast.walk(filho):
                if not isinstance(sub, ast.While):
                    continue
                if any(
                    isinstance(chamada, ast.Call)
                    and getattr(chamada.func, "attr", "") == "residual_capacity_to"
                    for chamada in ast.walk(sub)
                ):
                    candidatos.append((sub.end_lineno - sub.lineno, sub))
            if not candidatos:
                continue
            _span, laco = min(candidatos, key=lambda par: par[0])
            inicio = laco.lineno

            # Sobe para o bloco que contém o laço e inclui o preparo contíguo
            # (sem linha em branco/comentário no meio) que o antecede.
            pai = next(
                (
                    ancestral
                    for ancestral in ast.walk(filho)
                    if any(item is laco for item in ast.iter_child_nodes(ancestral))
                ),
                None,
            )
            corpo = None
            if pai is not None:
                for campo in ("body", "orelse", "finalbody"):
                    lista = getattr(pai, campo, None)
                    if isinstance(lista, list) and any(item is laco for item in lista):
                        corpo = lista
                        break
            if corpo is not None:
                idx = next(i for i, item in enumerate(corpo) if item is laco)
                for anterior in reversed(corpo[:idx]):
                    fim_ant = getattr(anterior, "end_lineno", None) or anterior.lineno
                    if inicio - fim_ant <= 1:
                        inicio = anterior.lineno
                    else:
                        break
            return inicio, laco.end_lineno
    raise LookupError(f"{modulo}: não achei o laço do gargalo em {classe}.__init__")


def aba_do_passo(passo, aba_anterior: str) -> str:
    """Aba determinística do passo (§C.4) — cobre 100 % dos passos."""
    if passo.escrita is not None:  # a linha ESCREVE uma estrutura → a aba dela
        return passo.escrita
    fn, ln = passo.funcao, passo.linha
    if fn in ("FlowNetwork.__init__", "FlowNetwork.add_edge"):
        return "adj"  # janela de montagem da lista de adjacência
    if fn in ("FlowNetwork.adj", "FlowNetwork.validate_vertex") or fn.startswith("FlowEdge."):
        return aba_anterior  # getter/validador: herda do chamador
    if fn.endswith("has_augmenting_path") or fn.endswith(".dfs"):
        return "busca"
    if fn.endswith("__init__"):  # FordFulkerson.__init__
        algoritmo = (
            "edmonds_karp" if fn.startswith("FordFulkerson.") else "ford_fulkerson_dfs"
        )
        inicio, fim = _faixa_gargalo(algoritmo)
        return "edge_to" if inicio <= ln <= fim else "rede"
    if fn.endswith(("check", "in_cut", "validate")):
        return "marcados"
    return "rede"


def fundir_runs(
    abas, min_run: int = 2, protegidos: list[bool] | None = None
) -> list[str]:
    """Histerese da aba: run mais curto que `min_run` vira a aba anterior.

    `protegidos[i]` marca a posição i como escrita de estrutura: um run de
    1 passo protegido nunca é engolido — e um run de 1 passo imediatamente
    APÓS um protegido também não (o passo escrito não "puxa" a linha
    seguinte para a sua aba; é o vetor `["b","b","e","b"]` do plano).
    Sem `protegidos`, o comportamento antigo é idêntico.
    """
    saida = list(abas)
    i = 0
    while i < len(saida):
        j = i
        while j < len(saida) and saida[j] == saida[i]:
            j += 1
        if (j - i) < min_run and i > 0:
            protegido = bool(protegidos) and any(protegidos[i:j])
            if protegidos:
                protegido = protegido or bool(protegidos[i - 1])
            if not protegido:
                for k in range(i, j):
                    saida[k] = saida[i - 1]
        i = j
    return saida


def calcular_abas(algoritmo: str, passos) -> list[str]:
    """Sequência das 5 abas: regra total + fusão de runs de 1 passo."""
    abas: list[str] = []
    anterior = "rede"
    for passo in passos:
        atual = aba_do_passo(passo, anterior)
        abas.append(atual)
        anterior = atual
    return fundir_runs(abas, 2, [p.escrita is not None for p in passos])


class _AbaRede:
    """Tabela `aresta | C | f | res→ | res←`, duas metades de 4 arestas."""

    COLUNAS = (("aresta", 0.85), ("C", 0.42), ("f", 0.42), ("res→", 0.50), ("res←", 0.50))
    ALTURA_CHIP = 0.22

    def __init__(self, painel):
        self.p = painel
        self.chips: dict[tuple[int, int, int], RoundedRectangle] = {}
        self.textos: dict[tuple[int, int, int], Text] = {}
        self.valores: dict[tuple[int, int, int], str] = {}
        self.arestas = [(u, v) for u, v, _c in rec.ARESTAS_REDE]
        self.mobjects: list[Mobject] = []
        self.estaticos: list[Mobject] = []
        self.caption: Text | None = None

    def _colunas(self, metade: int):
        x = X0_ESTRUTURA + metade * 3.10
        centros = []
        for _nome, largura in self.COLUNAS:
            centros.append(x + largura / 2)
            x += largura
        return centros

    def _valores(self, estado: dict, u: int, v: int) -> tuple[str, ...]:
        cap = estado["capacidades"].get((u, v))
        fluxo = estado["fluxos"].get((u, v))
        direta = estado["residual_direta"].get((u, v))
        reversa = estado["residual_reversa"].get((u, v))
        if cap is None:
            return (f"{u}→{v}", "—", "—", "—", "—")
        return (
            f"{u}→{v}",
            f"{cap:g}",
            f"{fluxo:g}",
            f"{direta:g}",
            f"{reversa:g}",
        )

    def construir(self, passo) -> list[Mobject]:
        est = passo.estado
        self.chips, self.textos, self.valores = {}, {}, {}
        self.mobjects = []
        self.estaticos = []

        self.caption = Text(
            "Rede residual · C, f, res→, res←", font_size=9, color=COR_BORDA_NO
        )
        self.caption.move_to(np.array([X0_ESTRUTURA, Y_CAPTION, 0.0]), aligned_edge=LEFT)
        self.mobjects.append(self.caption)

        for metade in (0, 1):
            centros = self._colunas(metade)
            for i, (nome, _larg) in enumerate(self.COLUNAS):
                cab = Text(nome, font_size=9, color=COR_BORDA_NO)
                cab.move_to(np.array([centros[i], Y_CABECALHO, 0.0]))
                self.mobjects.append(cab)
                self.estaticos.append(cab)
            for linha, (u, v) in enumerate(self.arestas[metade * 4 : metade * 4 + 4]):
                y = -2.06 - linha * 0.28
                valores = self._valores(est, u, v)
                for i, texto in enumerate(valores):
                    largura = self.COLUNAS[i][1] - 0.04
                    chip = RoundedRectangle(
                        corner_radius=0.05,
                        width=largura,
                        height=self.ALTURA_CHIP,
                        fill_color=COR_CHIP,
                        fill_opacity=1.0,
                        stroke_width=0.0,
                    ).move_to(np.array([centros[i], y, 0.0]))
                    cor = (
                        PALETA["saturada"][0]
                        if i == 3 and texto == "0"
                        else COR_TEXTO
                    )
                    t = Text(texto, font_size=10, color=cor).move_to(chip.get_center())
                    self.chips[(u, v, i)] = chip
                    self.textos[(u, v, i)] = t
                    self.valores[(u, v, i)] = texto
                    self.mobjects += [chip, t]
        return list(self.mobjects)

    def sincronizar(self, passo):
        est = passo.estado
        foco = self.p._foco(passo)
        anims: list[Animation] = []
        for u, v in self.arestas:
            valores = self._valores(est, u, v)
            for i, texto in enumerate(valores):
                chave = (u, v, i)
                if texto == self.valores[chave]:
                    continue
                antigo = self.textos[chave]
                cor = PALETA["saturada"][0] if i == 3 and texto == "0" else COR_TEXTO
                novo = Text(texto, font_size=10, color=cor).move_to(
                    self.chips[chave].get_center()
                )
                anims.append(
                    AnimationGroup(
                        FadeOut(antigo, run_time=RITMO["play"]),
                        FadeIn(novo, run_time=RITMO["play"]),
                    )
                )
                self.textos[chave] = novo
                self.valores[chave] = texto
            # chip da aresta em foco
            on = (u, v) == foco
            for i in range(len(self.COLUNAS)):
                chip = self.chips[(u, v, i)]
                alvo_fill = COR_CHIP_FOCO if on else COR_CHIP
                alvo_stroke = 1.6 if on else 0.0
                atual_fill = chip.get_fill_color().to_hex()
                if atual_fill.lower() != alvo_fill.lower() or chip.get_stroke_width() != alvo_stroke:
                    anims.append(
                        chip.animate.set_fill(alvo_fill, opacity=1.0).set_stroke(
                            color=PALETA["exame"][0], width=alvo_stroke
                        )
                    )
        return anims, [], []

    def todos(self) -> list[Mobject]:
        # Ao vivo: `construir` monta uma vez, mas `sincronizar` troca textos.
        # Devolver `self.mobjects` (snapshot da montagem) faria o FadeOut da
        # troca de aba acertar mobjects já fora de cena e deixar fantasma.
        # A caption entra por `self.caption` (o objeto VIVO), nunca por
        # `estaticos`: se ela for recriada, a antiga vira fantasma na tela.
        return [
            self.caption,
            *self.estaticos,
            *self.chips.values(),
            *self.textos.values(),
        ]


class _AbaBusca:
    """Fronteira real da busca: fila (BFS) ou pilha de recursão (DFS)."""

    PASSO_CHIP = 0.54
    PASSO_PILHA = 0.66

    def __init__(self, painel):
        self.p = painel
        self.bfs = painel.algoritmo == "edmonds_karp"
        self.chips: dict[int, VGroup] = {}
        self.setas: dict[int, Arrow] = {}
        self.mobjects: list[Mobject] = []
        self.frente: Text | None = None
        self.fim: Text | None = None
        self.inspecoes: Text | None = None
        self.conteudos = {"inspecoes": ""}
        self.estaticos: list[Mobject] = []
        self.caption: Text | None = None

    # -- geometria ---------------------------------------------------------

    def _passo(self) -> float:
        return self.PASSO_CHIP if self.bfs else self.PASSO_PILHA

    def _x(self, i: int) -> float:
        return X0_ESTRUTURA + 0.10 + i * self._passo()

    def _lista(self, estado: dict) -> list[int]:
        return list(estado["fila"] if self.bfs else estado["pilha"])

    def _chip(self, v: int) -> VGroup:
        caixa = RoundedRectangle(
            corner_radius=0.06,
            width=0.42,
            height=0.30,
            fill_color=COR_CHIP_FOCO,
            fill_opacity=1.0,
            stroke_color=COR_BORDA_NO,
            stroke_width=1.2,
        )
        texto = Text(str(v), font_size=11, color=COR_TEXTO).move_to(caixa.get_center())
        return VGroup(caixa, texto)

    def _seta(self, indice: int) -> Arrow:
        """Seta do gutter entre os chips `indice-1` e `indice` (§D.2).

        O argumento é o ÍNDICE na fila/pilha, não o vértice: era esse o bug
        que fazia a seta entrar no chip do topo.
        """
        x0 = self._x(indice - 1) + 0.21 + 0.02
        x1 = self._x(indice) - 0.21 - 0.02
        return Arrow(
            np.array([x0, -2.30, 0.0]),
            np.array([x1, -2.30, 0.0]),
            buff=0.0,
            stroke_width=1.6,
            tip_length=0.07,
            color=COR_BORDA_NO,
        )

    # -- montagem ----------------------------------------------------------

    def construir(self, passo) -> list[Mobject]:
        est = estado_da_busca(passo)
        self.chips, self.setas = {}, {}
        self.mobjects = []

        self.caption = Text(
            "Fila (BFS) · ordem real"
            if self.bfs
            else "Pilha (DFS) · caminho de recursão",
            font_size=9,
            color=COR_BORDA_NO,
        )
        self.caption.move_to(np.array([X0_ESTRUTURA, Y_CAPTION, 0.0]), aligned_edge=LEFT)
        self.mobjects.append(self.caption)
        self.estaticos = []

        lista = self._lista(est)
        for i, v in enumerate(lista):
            chip = self._chip(v).move_to(np.array([self._x(i), -2.30, 0.0]))
            self.chips[v] = chip
            self.mobjects.append(chip)
        # setas do caminho de recursão (DFS), uma por GUTTER (índice 1..n-1)
        for i in range(1, len(lista)):
            seta = self._seta(i)
            self.setas[i] = seta
            self.mobjects.append(seta)

        # rótulos em palavra: ↓/↑ em fonte 9 vira "l"/"1" no render
        self.frente = Text("frente" if self.bfs else "base", font_size=9, color=COR_BORDA_NO)
        self.fim = Text("fim" if self.bfs else "topo", font_size=9, color=COR_BORDA_NO)
        if lista:
            self.frente.move_to(np.array([self._x(0), -2.02, 0.0]))
            self.fim.move_to(np.array([self._x(len(lista) - 1), -2.60, 0.0]))
        else:
            self.frente.move_to(np.array([self._x(0), -2.02, 0.0])).set_opacity(0.0)
            self.fim.move_to(np.array([self._x(0), -2.60, 0.0])).set_opacity(0.0)
        self.mobjects += [self.frente, self.fim]

        # A aba `busca` NÃO repete os textos de `edgeTo`/`marcados` (V4 §B.4):
        # a estrutura escrita por cada linha tem a sua própria aba.
        x_info = X0_ESTRUTURA + 3.60
        self.inspecoes = Text(
            f"inspeções {est['inspecoes']}", font_size=10, color=COR_BORDA_NO
        )
        self.inspecoes.move_to(np.array([x_info, -2.58, 0.0]), aligned_edge=LEFT)
        self.mobjects.append(self.inspecoes)
        self.conteudos = {"inspecoes": f"inspeções {est['inspecoes']}"}
        return list(self.mobjects)

    # -- atualização -------------------------------------------------------

    def _troca(self, atual: Text, texto: str, pos, cor: str, fonte: int = 10) -> tuple[Text, Animation]:
        novo = Text(texto, font_size=fonte, color=cor)
        novo.move_to(pos, aligned_edge=LEFT)
        return novo, AnimationGroup(
            FadeOut(atual, run_time=RITMO["play"]),
            FadeIn(novo, run_time=RITMO["play"]),
        )

    def sincronizar(self, passo):
        est = estado_da_busca(passo)
        lista = self._lista(est)
        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        alvo = {v: np.array([self._x(i), -2.30, 0.0]) for i, v in enumerate(lista)}
        for v in list(self.chips):
            if v not in alvo:
                chip = self.chips.pop(v)
                remover.append(chip)
                anims.append(FadeOut(chip, run_time=RITMO["play"]))
        for v, pos in alvo.items():
            if v not in self.chips:
                chip = self._chip(v).move_to(pos)
                self.chips[v] = chip
                adicionar.append(chip)
                anims.append(FadeIn(chip, run_time=RITMO["play"]))
                # V4 §B.5: a adição realça o vértice que acabou de entrar
                anims.append(
                    Flash(
                        pos,
                        color=COR_ACENTO,
                        line_length=0.14,
                        num_lines=8,
                        flash_radius=0.26,
                        line_stroke_width=2,
                    )
                )
            elif not np.allclose(self.chips[v].get_center(), pos, atol=1e-6):
                anims.append(self.chips[v].animate.move_to(pos))

        # setas do caminho de recursão (DFS), por ÍNDICE: sobras saem, novas
        # entram e TODAS são reposicionadas no gutter atual a cada passo.
        indices = set(range(1, len(lista))) if not self.bfs else set()
        for i in list(self.setas):
            if i not in indices:
                seta = self.setas.pop(i)
                remover.append(seta)
                anims.append(FadeOut(seta, run_time=RITMO["play"]))
        for i in sorted(indices):
            if i not in self.setas:
                seta = self._seta(i)
                self.setas[i] = seta
                adicionar.append(seta)
                anims.append(FadeIn(seta, run_time=RITMO["play"]))
            self.setas[i].put_start_and_end_on(
                np.array([self._x(i - 1) + 0.23, -2.30, 0.0]),
                np.array([self._x(i) - 0.23, -2.30, 0.0]),
            )

        if lista:
            anims += [
                self.frente.animate.move_to(np.array([self._x(0), -2.02, 0.0])).set_opacity(1.0),
                self.fim.animate.move_to(
                    np.array([self._x(len(lista) - 1), -2.60, 0.0])
                ).set_opacity(1.0),
            ]
        else:
            anims += [
                self.frente.animate.set_opacity(0.0),
                self.fim.animate.set_opacity(0.0),
            ]

        x_info = X0_ESTRUTURA + 3.60
        texto = f"inspeções {est['inspecoes']}"
        if texto != self.conteudos["inspecoes"]:
            novo, anim = self._troca(
                self.inspecoes, texto, self.inspecoes.get_left(), COR_BORDA_NO
            )
            anims.append(anim)
            self.conteudos["inspecoes"] = texto
            self.inspecoes = novo
        return anims, adicionar, remover

    def todos(self) -> list[Mobject]:
        # Ao vivo (ver `_AbaRede.todos`): caption pelo objeto atual.
        vivos = [
            self.caption,
            *self.estaticos,
            *self.chips.values(),
            *self.setas.values(),
            self.frente,
            self.fim,
            self.inspecoes,
        ]
        return [m for m in vivos if m is not None]


class _AbaMarcados:
    """`marked[]`: 6 chips + o lado S do corte."""

    def __init__(self, painel):
        self.p = painel
        self.chips: dict[int, RoundedRectangle] = {}
        self.textos: dict[int, Text] = {}
        self.acesos: dict[int, bool] = {}
        self.caption: Text | None = None
        self.lado_s: Text | None = None
        self.conteudo_caption = ""
        self.conteudo_s = ""

    def _chip_xy(self, v: int):
        return np.array([X0_ESTRUTURA + 0.31 + v * 0.72, -2.20, 0.0])

    def _texto_caption(self, estado: dict) -> str:
        k = len(estado.get("marcados") or [])
        return f"marked[] · {k}/6 vértices · alcançados na residual"

    def _texto_s(self, estado: dict) -> str:
        corte = estado.get("corte") or []
        return "S* = {" + ", ".join(map(str, corte)) + "}" if corte else "S* = —"

    def _posicionar_s(self, texto: Text) -> None:
        """Depois do último chip; se não couber na linha, desce para a própria."""
        ultimo = self.chips[rec.V_REDE - 1]
        x = ultimo.get_right()[0] + 0.12
        texto.move_to(np.array([x, -2.20, 0.0]), aligned_edge=LEFT)
        if texto.get_right()[0] > X0_ESTRUTURA + 6.20 + 1e-6:
            texto.move_to(
                np.array([X0_ESTRUTURA, -2.62, 0.0]), aligned_edge=LEFT
            )

    def _aplicar_estilo(self, v: int, marcado: bool) -> None:
        chip, texto = self.chips[v], self.textos[v]
        if marcado:
            chip.set_fill(PALETA["alcancado"][0], opacity=0.22)
            chip.set_stroke(color=PALETA["alcancado"][0], width=1.6)
            texto.set_color(COR_TEXTO)
        else:
            chip.set_fill(COR_CHIP, opacity=1.0)
            chip.set_stroke(color=COR_BORDA_NO, width=1.0)
            texto.set_color(COR_BORDA_NO)

    def construir(self, passo) -> list[Mobject]:
        est = passo.estado
        self.chips, self.textos, self.acesos = {}, {}, {}
        marcados = set(est.get("marcados") or [])

        self.conteudo_caption = self._texto_caption(est)
        self.caption = Text(self.conteudo_caption, font_size=9, color=COR_BORDA_NO)
        self.caption.move_to(np.array([X0_ESTRUTURA, Y_CAPTION, 0.0]), aligned_edge=LEFT)

        mobs: list[Mobject] = [self.caption]
        for v in range(rec.V_REDE):
            chip = RoundedRectangle(
                corner_radius=0.06,
                width=0.62,
                height=0.30,
                fill_color=COR_CHIP,
                fill_opacity=1.0,
                stroke_color=COR_BORDA_NO,
                stroke_width=1.0,
            ).move_to(self._chip_xy(v))
            texto = Text(str(v), font_size=11, color=COR_BORDA_NO).move_to(chip.get_center())
            self.chips[v] = chip
            self.textos[v] = texto
            self.acesos[v] = v in marcados
            self._aplicar_estilo(v, v in marcados)
            mobs += [chip, texto]

        self.conteudo_s = self._texto_s(est)
        self.lado_s = Text(self.conteudo_s, font_size=10, color=PALETA["alcancado"][0])
        self._posicionar_s(self.lado_s)
        mobs.append(self.lado_s)
        return mobs

    def sincronizar(self, passo):
        est = passo.estado
        marcados = set(est.get("marcados") or [])
        anims: list[Animation] = []
        for v in range(rec.V_REDE):
            marcado = v in marcados
            if marcado == self.acesos[v]:
                continue
            chip, texto = self.chips[v], self.textos[v]
            if marcado:
                # V4 §B.5: estilo aplicado na hora (o alvo do Indicate é a
                # cópia viva do chip) e a adição realçada por Flash+Indicate
                # dentro do play do passo — sem tempo extra.
                self._aplicar_estilo(v, True)
                anims.append(
                    Flash(
                        chip.get_center(),
                        color=PALETA["alcancado"][0],
                        line_length=0.12,
                        num_lines=8,
                        flash_radius=0.30,
                        line_stroke_width=2,
                    )
                )
                anims.append(
                    Indicate(chip, color=PALETA["alcancado"][0], scale_factor=1.12)
                )
            else:
                anims.append(
                    chip.animate.set_fill(COR_CHIP, opacity=1.0).set_stroke(
                        color=COR_BORDA_NO, width=1.0
                    )
                )
                anims.append(texto.animate.set_color(COR_BORDA_NO))
            self.acesos[v] = marcado

        caption = self._texto_caption(est)
        if caption != self.conteudo_caption:
            novo = Text(caption, font_size=9, color=COR_BORDA_NO)
            novo.move_to(np.array([X0_ESTRUTURA, Y_CAPTION, 0.0]), aligned_edge=LEFT)
            anims.append(
                AnimationGroup(
                    FadeOut(self.caption, run_time=RITMO["play"]),
                    FadeIn(novo, run_time=RITMO["play"]),
                )
            )
            self.caption = novo
            self.conteudo_caption = caption

        lado_s = self._texto_s(est)
        if lado_s != self.conteudo_s:
            novo = Text(lado_s, font_size=10, color=PALETA["alcancado"][0])
            self._posicionar_s(novo)
            anims.append(
                AnimationGroup(
                    FadeOut(self.lado_s, run_time=RITMO["play"]),
                    FadeIn(novo, run_time=RITMO["play"]),
                )
            )
            self.lado_s = novo
            self.conteudo_s = lado_s
        return anims, [], []

    def todos(self) -> list[Mobject]:
        vivos = [self.caption, *self.chips.values(), *self.textos.values(), self.lado_s]
        return [m for m in vivos if m is not None]


class _AbaEdgeTo:
    """`edgeTo[]` como FILA DE DESCOBERTA + caminho s→t e gargalo.

    A fila é a árvore real na ordem em que o algoritmo a construiu
    (`estado["ordem_descoberta"]`): frente = 1º descoberto (a origem),
    fim = último descoberto. Cada chip mostra `v` e o pai `←pai`. A cor da
    borda é o papel do vértice no passo (caminho/alcancado/neutro).

    V4 §A: o bloco `caminho`/`gargalo` fica SEMPRE abaixo da fila
    (`X_INFO = X0_ESTRUTURA`), no vão entre o `fim` e o guia — com 6 chips a
    fila termina em +0.42 e não colide mais com o texto.
    V4 §B.5: a fila é incremental por VÉRTICE (`chips`), com `Flash` na
    adição — nada é reconstruído a cada passo.
    """

    LARGURA = 0.72
    ALTURA = 0.42
    PASSO = 0.86
    # `chips_fila` recebe a BORDA esquerda; o primeiro chip fica centrado em
    # x0 + LARGURA/2. O recuo garante a borda dentro do corpo (x0 da estrutura).
    X_FILA = X0_ESTRUTURA + 0.40
    Y_FILA = -2.10
    X_INFO = X0_ESTRUTURA          # -5.00 (era X0_ESTRUTURA + 5.14)
    Y_CAMINHO = -2.74              # era -2.02
    Y_GARGALO = -2.96              # era -2.30

    def __init__(self, painel):
        self.p = painel
        self.chips: dict[int, VGroup] = {}
        self.estilos: dict[int, tuple] = {}
        self.setas: dict[int, Arrow] = {}
        self.frente: Text | None = None
        self.fim: Text | None = None
        self.vazio: Text | None = None
        self.caption: Text | None = None
        self.caminho: Text | None = None
        self.gargalo: Text | None = None
        self.conteudo_caminho = ""
        self.conteudo_gargalo = ""
        self.ordem: list[int] = []
        self._rotulos_visiveis = False

    def _pai(self, estado: dict, v: int):
        aresta = (estado.get("edge_to") or {}).get(v)
        if aresta is None:
            return None
        u, w = aresta
        return w if u == v else u

    def _itens(self, estado: dict) -> list[dict]:
        self.ordem = list(estado.get("ordem_descoberta") or [])
        caminho = set()
        for u, v in estado.get("caminho") or []:
            caminho.update((u, v))
        marcados = set(estado.get("marcados") or [])
        itens: list[dict] = []
        for v in self.ordem:
            pai = self._pai(estado, v)
            if v in caminho:
                cor, opacidade = PALETA["caminho"][0], 0.22
            elif v in marcados:
                cor, opacidade = PALETA["alcancado"][0], 0.18
            else:
                cor, opacidade = COR_BORDA_NO, 1.0
            itens.append(
                {
                    "texto": str(v),
                    "sub": "s" if pai is None else f"←{pai}",
                    "cor": cor,
                    "fill": COR_CHIP if opacidade == 1.0 else cor,
                    "fill_opacity": opacidade,
                }
            )
        return itens

    @staticmethod
    def _estilo(item: dict) -> tuple:
        return (item["cor"], item["fill"], item["fill_opacity"])

    def _alvo(self, i: int):
        return np.array(
            [
                self.X_FILA + self.LARGURA / 2 + i * self.PASSO,
                self.Y_FILA,
                0.0,
            ]
        )

    def _chip(self, item: dict) -> VGroup:
        chips, _setas = chips_fila(
            [item],
            x0=0.0,
            y=0.0,
            largura=self.LARGURA,
            altura=self.ALTURA,
            passo=self.PASSO,
            fonte=11,
            fonte_sub=8,
        )
        return chips[0]

    def _ponta_seta(self, i: int):
        centro_ant = self.X_FILA + self.LARGURA / 2 + (i - 1) * self.PASSO
        centro = self.X_FILA + self.LARGURA / 2 + i * self.PASSO
        inicio = np.array([centro_ant + self.LARGURA / 2 + 0.01, self.Y_FILA, 0.0])
        fim = np.array([centro - self.LARGURA / 2 - 0.01, self.Y_FILA, 0.0])
        return inicio, fim

    def _seta(self, i: int) -> Arrow:
        inicio, fim = self._ponta_seta(i)
        return Arrow(
            inicio,
            fim,
            buff=0.0,
            stroke_width=1.2,
            tip_length=0.05,
            color=COR_BORDA_NO,
        )

    def _pos_fim(self, n: int):
        x = self.X_FILA + self.LARGURA / 2 + max(0, n - 1) * self.PASSO
        return np.array([x, self.Y_FILA - 0.35, 0.0])

    def _animar_estilo(self, chip: VGroup, estilo: tuple) -> list[Animation]:
        """Troca cor/preenchimento/opacidade do chip e a cor do subtexto."""
        cor, fill, opacidade = estilo
        anims: list[Animation] = [
            chip[0].animate.set_fill(fill, opacity=opacidade).set_stroke(
                color=cor, width=1.6
            )
        ]
        if len(chip[1].submobjects) > 1:
            anims.append(chip[1].submobjects[1].animate.set_color(cor))
        return anims

    def _montar_fila(self, itens: list[dict]) -> list[Mobject]:
        """Montagem completa (primeiro frame da aba); a troca é incremental."""
        self.chips, self.estilos, self.setas = {}, {}, {}
        self.vazio = None
        mobs: list[Mobject] = []
        for i, item in enumerate(itens):
            v = int(item["texto"])
            chip = self._chip(item).move_to(self._alvo(i))
            self.chips[v] = chip
            self.estilos[v] = self._estilo(item)
            mobs.append(chip)
        for i in range(1, len(itens)):
            seta = self._seta(i)
            self.setas[i] = seta
            mobs.append(seta)
        if not itens:
            self.vazio = Text("∅ fila vazia", font_size=10, color=COR_BORDA_NO)
            self.vazio.move_to(
                np.array([self.X_FILA + 0.06, self.Y_FILA, 0.0]),
                aligned_edge=LEFT,
            )
            mobs.append(self.vazio)

        self.frente = Text("frente", font_size=9, color=COR_BORDA_NO)
        self.frente.move_to(
            np.array([self.X_FILA + self.LARGURA / 2, self.Y_FILA + 0.35, 0.0])
        )
        self.fim = Text("fim", font_size=9, color=COR_BORDA_NO)
        self.fim.move_to(self._pos_fim(len(itens)))
        self._rotulos_visiveis = bool(itens)
        if not itens:
            self.frente.set_opacity(0.0)
            self.fim.set_opacity(0.0)
        mobs += [self.frente, self.fim]
        return mobs

    def construir(self, passo) -> list[Mobject]:
        est = passo.estado
        self.caption = Text(
            "edgeTo[] · fila de descoberta · frente = 1º descoberto",
            font_size=9,
            color=COR_BORDA_NO,
        )
        self.caption.move_to(np.array([X0_ESTRUTURA, Y_CAPTION, 0.0]), aligned_edge=LEFT)
        itens = self._itens(est)
        mobs: list[Mobject] = [self.caption, *self._montar_fila(itens)]

        self.conteudo_caminho = fmt_caminho(est.get("caminho"))
        self.caminho = Text(self.conteudo_caminho, font_size=10, color=PALETA["caminho"][0])
        self.caminho.move_to(
            np.array([self.X_INFO, self.Y_CAMINHO, 0.0]), aligned_edge=LEFT
        )
        self.conteudo_gargalo = f"b = {fmt_num(est.get('gargalo'))}"
        self.gargalo = Text(self.conteudo_gargalo, font_size=10, color=COR_TEXTO)
        self.gargalo.move_to(
            np.array([self.X_INFO, self.Y_GARGALO, 0.0]), aligned_edge=LEFT
        )
        mobs += [self.caminho, self.gargalo]
        return mobs

    def _troca_texto(
        self, atual: Text, texto: str, pos, cor: str, fonte: int = 10
    ) -> tuple[Text, Animation]:
        novo = Text(texto, font_size=fonte, color=cor)
        novo.move_to(pos, aligned_edge=LEFT)
        return novo, AnimationGroup(
            FadeOut(atual, run_time=RITMO["play"]),
            FadeIn(novo, run_time=RITMO["play"]),
        )

    def sincronizar(self, passo):
        est = passo.estado
        itens = self._itens(est)
        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        alvo = {
            int(item["texto"]): (self._alvo(i), item)
            for i, item in enumerate(itens)
        }
        # 1) chips que saíram
        for v in list(self.chips):
            if v not in alvo:
                chip = self.chips.pop(v)
                self.estilos.pop(v, None)
                remover.append(chip)
                anims.append(FadeOut(chip, run_time=RITMO["play"]))

        # 2) chips novos (FadeIn + Flash), 3) índice (move) e 4) estilo
        for v, (pos, item) in alvo.items():
            estilo = self._estilo(item)
            if v not in self.chips:
                chip = self._chip(item).move_to(pos)
                self.chips[v] = chip
                self.estilos[v] = estilo
                adicionar.append(chip)
                anims.append(FadeIn(chip, run_time=RITMO["play"]))
                # V4 §B.5: realce da adição (parâmetros do plano; neste
                # Manim o `stroke_width` do Flash é `line_stroke_width`)
                anims.append(
                    Flash(
                        pos,
                        color=COR_ACENTO,
                        line_length=0.14,
                        num_lines=8,
                        flash_radius=0.26,
                        line_stroke_width=2,
                    )
                )
                continue
            chip = self.chips[v]
            if not np.allclose(chip.get_center(), pos, atol=1e-6):
                # `animate.move_to` no grupo + `animate` no filho no mesmo play
                # se anulam; mover na hora é determinístico e não há movimento
                # de chip no trace (a descoberta sempre ACRESCENTA no fim).
                chip.move_to(pos)
            if self.estilos[v] != estilo:
                anims += self._animar_estilo(chip, estilo)
                self.estilos[v] = estilo

        # 5) setas por ÍNDICE no gutter: sobras saem, novas entram e TODAS
        # recebem put_start_and_end_on na geometria atual (V3 §D.2).
        indices = set(range(1, len(itens)))
        for i in list(self.setas):
            if i not in indices:
                seta = self.setas.pop(i)
                remover.append(seta)
                anims.append(FadeOut(seta, run_time=RITMO["play"]))
        for i in sorted(indices):
            if i not in self.setas:
                seta = self._seta(i)
                self.setas[i] = seta
                adicionar.append(seta)
                anims.append(FadeIn(seta, run_time=RITMO["play"]))
            else:
                inicio, fim = self._ponta_seta(i)
                self.setas[i].put_start_and_end_on(inicio, fim)

        # 6) rótulos frente/fim e o estado vazio
        if itens:
            if self.vazio is not None:
                remover.append(self.vazio)
                anims.append(FadeOut(self.vazio, run_time=RITMO["play"]))
                self.vazio = None
            if not self._rotulos_visiveis:
                anims.append(self.frente.animate.set_opacity(1.0))
                anims.append(self.fim.animate.set_opacity(1.0))
                self._rotulos_visiveis = True
            pos_fim = self._pos_fim(len(itens))
            if not np.allclose(self.fim.get_center(), pos_fim, atol=1e-6):
                anims.append(self.fim.animate.move_to(pos_fim))
        else:
            if self.vazio is None:
                self.vazio = Text("∅ fila vazia", font_size=10, color=COR_BORDA_NO)
                self.vazio.move_to(
                    np.array([self.X_FILA + 0.06, self.Y_FILA, 0.0]),
                    aligned_edge=LEFT,
                )
                adicionar.append(self.vazio)
                anims.append(FadeIn(self.vazio, run_time=RITMO["play"]))
            if self._rotulos_visiveis:
                anims.append(self.frente.animate.set_opacity(0.0))
                anims.append(self.fim.animate.set_opacity(0.0))
                self._rotulos_visiveis = False

        # 7) caminho/gargalo: só trocam quando o TEXTO muda, no mesmo x/y
        caminho = fmt_caminho(est.get("caminho"))
        if caminho != self.conteudo_caminho:
            novo, anim = self._troca_texto(
                self.caminho,
                caminho,
                np.array([self.X_INFO, self.Y_CAMINHO, 0.0]),
                PALETA["caminho"][0],
            )
            anims.append(anim)
            self.caminho = novo
            self.conteudo_caminho = caminho

        gargalo = f"b = {fmt_num(est.get('gargalo'))}"
        if gargalo != self.conteudo_gargalo:
            novo, anim = self._troca_texto(
                self.gargalo,
                gargalo,
                np.array([self.X_INFO, self.Y_GARGALO, 0.0]),
                COR_TEXTO,
            )
            anims.append(anim)
            self.gargalo = novo
            self.conteudo_gargalo = gargalo
        return anims, adicionar, remover

    def todos(self) -> list[Mobject]:
        vivos = [
            self.caption,
            *self.chips.values(),
            *self.setas.values(),
            self.frente,
            self.fim,
            self.vazio,
            self.caminho,
            self.gargalo,
        ]
        return [m for m in vivos if m is not None]


class _AbaAdj:
    """`adj[]` como FILA DE INSPEÇÃO: a ordem real do `for e in g.adj(v)`.

    A lista de cada vértice entra na ordem em que o algoritmo a percorre
    (`insert(0, e)` = LIFO). O `▸` marca a FRENTE da fila: a primeira aresta
    que o `for` examina. As setas só ocupam o vão entre chips.
    """

    LARGURA = 0.66
    ALTURA = 0.24
    PASSO_CHIP = 0.78
    PASSO_LINHA = 0.25

    def __init__(self, painel):
        self.p = painel
        self.chips: dict[int, list[VGroup]] = {}
        self.textos: dict[int, list[Text]] = {}
        self.setas: dict[int, list[Arrow]] = {}
        self.assinaturas: dict[int, tuple] = {}
        self.caption: Text | None = None
        self.labels: dict[int, Text] = {}
        self.frentes: dict[int, Text] = {}
        self.conteudo_caption = ""
        self.estaticos: list[Mobject] = []

    def _texto_caption(self, estado: dict) -> str:
        n = sum(len(lista) for lista in (estado.get("adj") or {}).values())
        texto = f"adj[] · fila de inspeção · {n} entradas (2E=16)"
        if n < 16:
            texto += " · em construção"
        return texto

    def _assinatura(self, estado: dict, v: int, foco) -> tuple:
        entradas = (estado.get("adj") or {}).get(v) or []
        itens = []
        for entrada in entradas:
            w = entrada["w"]
            chave = (v, w) if entrada["saida"] else (w, v)
            itens.append(
                (
                    w,
                    entrada["saida"],
                    entrada["cap"],
                    entrada["fluxo"],
                    chave == foco,
                )
            )
        return tuple(itens)

    def _chips_de(self, v: int, assinatura) -> tuple[list[VGroup], list[Arrow]]:
        itens = []
        for w, saida, cap, fluxo, em_foco in assinatura:
            sinal = "▸" if saida else "◂"
            itens.append(
                {
                    "texto": f"{sinal}{w} · {fluxo:g}/{cap:g}",
                    "cor": PALETA["exame"][0] if em_foco else COR_BORDA_NO,
                    "fill": COR_CHIP,
                    "fill_opacity": 1.0,
                }
            )
        return chips_fila(
            itens,
            x0=X0_ESTRUTURA + 0.42,
            y=-1.78 - v * self.PASSO_LINHA,
            largura=self.LARGURA,
            altura=self.ALTURA,
            passo=self.PASSO_CHIP,
            fonte=11,
        )

    def construir(self, passo) -> list[Mobject]:
        est = passo.estado
        self.chips, self.textos, self.assinaturas = {}, {}, {}
        self.setas = {}
        self.labels = {}
        self.frentes = {}
        self.estaticos = []

        self.conteudo_caption = self._texto_caption(est)
        self.caption = Text(self.conteudo_caption, font_size=9, color=COR_BORDA_NO)
        self.caption.move_to(np.array([X0_ESTRUTURA, Y_CAPTION, 0.0]), aligned_edge=LEFT)
        mobs: list[Mobject] = [self.caption]

        foco = self.p._foco(passo)
        for v in range(rec.V_REDE):
            y = -1.78 - v * self.PASSO_LINHA
            rotulo = Text(f"{v}:", font_size=10, color=COR_BORDA_NO)
            rotulo.move_to(np.array([X0_ESTRUTURA, y, 0.0]), aligned_edge=LEFT)
            self.labels[v] = rotulo
            mobs.append(rotulo)

            frente = Text("▸", font_size=9, color=COR_BORDA_NO)
            frente.move_to(np.array([X0_ESTRUTURA + 0.22, y, 0.0]))
            self.frentes[v] = frente
            mobs.append(frente)

            assinatura = self._assinatura(est, v, foco)
            self.assinaturas[v] = assinatura
            grupos, setas = self._chips_de(v, assinatura)
            self.chips[v] = grupos
            self.setas[v] = setas
            self.textos[v] = [g[1].submobjects[0] for g in grupos]
            mobs.extend(grupos)
            mobs.extend(setas)
        return mobs

    def sincronizar(self, passo):
        est = passo.estado
        foco = self.p._foco(passo)
        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        for v in range(rec.V_REDE):
            assinatura = self._assinatura(est, v, foco)
            if assinatura == self.assinaturas[v]:
                continue
            for grupo in self.chips[v]:
                remover.append(grupo)
                anims.append(FadeOut(grupo, run_time=RITMO["play"]))
            for seta in self.setas[v]:
                remover.append(seta)
                anims.append(FadeOut(seta, run_time=RITMO["play"]))
            grupos, setas = self._chips_de(v, assinatura)
            self.chips[v] = grupos
            self.setas[v] = setas
            self.textos[v] = [g[1].submobjects[0] for g in grupos]
            self.assinaturas[v] = assinatura
            for grupo in grupos:
                adicionar.append(grupo)
                anims.append(FadeIn(grupo, run_time=RITMO["play"]))
            for seta in setas:
                adicionar.append(seta)
                anims.append(FadeIn(seta, run_time=RITMO["play"]))

        caption = self._texto_caption(est)
        if caption != self.conteudo_caption:
            novo = Text(caption, font_size=9, color=COR_BORDA_NO)
            novo.move_to(np.array([X0_ESTRUTURA, Y_CAPTION, 0.0]), aligned_edge=LEFT)
            anims.append(
                AnimationGroup(
                    FadeOut(self.caption, run_time=RITMO["play"]),
                    FadeIn(novo, run_time=RITMO["play"]),
                )
            )
            self.caption = novo
            self.conteudo_caption = caption
        return anims, adicionar, remover

    def todos(self) -> list[Mobject]:
        vivos = [
            self.caption,
            *self.estaticos,
            *self.labels.values(),
            *self.frentes.values(),
            *[g for grupos in self.chips.values() for g in grupos],
            *[s for setas in self.setas.values() for s in setas],
        ]
        return [m for m in vivos if m is not None]


class EstruturaPanel:
    """Cinco abas em trilho vertical, com faixa de contadores sempre visível.

    A aba ativa é derivada do trace (`aba_do_passo` + fusão de runs), nunca de
    um número de linha digitado. A troca é fade-out total e depois fade-in, em
    DOIS plays — nunca as duas abas no mesmo frame.
    """

    FONTE_CONTADORES = 11
    Y_CONTADORES = -3.50

    def __init__(self, algoritmo: str, passos):
        self.algoritmo = algoritmo
        self.max_iteracao = max((p.estado.get("iteracao") or 0) for p in passos)
        self.abas = calcular_abas(algoritmo, passos)
        self._i = 0
        self.centro = np.array([ESTRUTURA["centro"][0], ESTRUTURA["centro"][1], 0.0])

        self.fundo = RoundedRectangle(
            corner_radius=0.15,
            width=ESTRUTURA["largura"],
            height=ESTRUTURA["altura"],
            color=COR_BORDA_NO,
            stroke_width=1.5,
            fill_color=COR_PAINEL,
            fill_opacity=0.9,
        ).move_to(self.centro)

        self.x0 = X0_ESTRUTURA
        self.x1 = self.fundo.get_right()[0] - 0.16

        self.abas_visuais: dict[str, tuple[RoundedRectangle, Text]] = {}
        self._montar_abas()

        self.conteudos = {
            "rede": _AbaRede(self),
            "busca": _AbaBusca(self),
            "marcados": _AbaMarcados(self),
            "edge_to": _AbaEdgeTo(self),
            "adj": _AbaAdj(self),
        }
        self.ativa: str | None = None
        # Estado da busca visto pelo passo anterior (§B.6 rev. 4.1): base do
        # diff que decide qual elemento acabou de entrar na aba.
        self.estado_anterior: dict | None = None
        self.contadores: Text | None = None
        self.texto_contadores = ""
        self.guia: Text | None = None
        self.texto_guia = ""

        self.mobject = VGroup(
            self.fundo, *[m for par in self.abas_visuais.values() for m in par]
        )

    def _montar_abas(self) -> None:
        """Trilho vertical à esquerda (§C.2): 5 abas de 1,30 × 0,32."""
        largura, altura = 1.30, 0.32
        x = self.fundo.get_left()[0] + 0.08 + largura / 2
        centros_y = (-1.56, -1.93, -2.30, -2.67, -3.04)
        for (chave, rotulo), y in zip(ABAS[self.algoritmo], centros_y):
            caixa = RoundedRectangle(
                corner_radius=0.07,
                width=largura,
                height=altura,
                color=COR_BORDA_NO,
                stroke_width=1.2,
                fill_color=COR_TAB_INATIVA,
                fill_opacity=1.0,
            ).move_to(np.array([x, y, 0.0]))
            texto = Text(rotulo, font_size=10, color=COR_BORDA_NO).move_to(
                caixa.get_center()
            )
            self.abas_visuais[chave] = (caixa, texto)

    def _estilo_abas(self, ativa: str) -> list[Animation]:
        # Ritmo: estas animações dividem o `play(*sai_aba)` com os `FadeOut` do
        # conteúdo antigo, que usam `RITMO["fade"]`. `mobject.animate` sem
        # `run_time` explícito vira `_MethodAnimation` com o default de 1,0 s e
        # esticava a troca de aba inteira (bug de ritmo v4.2). O `run_time` vai
        # no construtor do builder: `animate(run_time=...)`.
        anims: list[Animation] = []
        for chave, (caixa, texto) in self.abas_visuais.items():
            on = chave == ativa
            anims += [
                caixa.animate(run_time=RITMO["fade"])
                .set_stroke(
                    COR_ACENTO if on else COR_BORDA_NO, width=1.6 if on else 1.2
                )
                .set_fill(COR_TAB_ATIVA if on else COR_TAB_INATIVA, opacity=1.0),
                texto.animate(run_time=RITMO["fade"]).set_color(
                    WHITE if on else COR_BORDA_NO
                ),
            ]
        return anims

    def _aplicar_abas(self, ativa: str) -> None:
        for chave, (caixa, texto) in self.abas_visuais.items():
            on = chave == ativa
            caixa.set_stroke(COR_ACENTO if on else COR_BORDA_NO, width=1.6 if on else 1.2)
            caixa.set_fill(COR_TAB_ATIVA if on else COR_TAB_INATIVA, opacity=1.0)
            texto.set_color(WHITE if on else COR_BORDA_NO)

    # -- regra da aba (derivada do trace) ---------------------------------

    def _alvo(self, passo) -> str:
        return self.abas[self._i]

    def _foco(self, passo):
        tipo, u, v, _status = passo.destaque
        if u is None or tipo not in ("busca", "caminho", "aumento", "corte"):
            return None
        _lado, chave = arcos_de(u, v, ARESTAS_REDE_SET)
        return chave

    # -- guia de símbolos (§A) ---------------------------------------------

    def _chave_guia(self, aba: str) -> str:
        if aba == "busca":
            return "busca_bfs" if self.algoritmo == "edmonds_karp" else "busca_dfs"
        return aba

    def _criar_guia(self, aba: str) -> Text:
        chave = self._chave_guia(aba)
        self.texto_guia = GUIA_SIMBOLOS[chave]
        return Text(
            self.texto_guia, font_size=10, color=COR_BORDA_NO
        ).move_to(np.array([X0_ESTRUTURA, -3.30, 0.0]), aligned_edge=LEFT)

    # -- primeiro frame ----------------------------------------------------

    def preparar(self, passo) -> list[Mobject]:
        self._i = 0
        self.estado_anterior = estado_da_busca(passo)
        alvo = self._alvo(passo)
        self.ativa = alvo
        self._aplicar_abas(alvo)
        conteudo = self.conteudos[alvo].construir(passo)
        self.texto_contadores = fmt_contadores(passo.estado, self.max_iteracao)
        self.contadores = Text(
            self.texto_contadores,
            font_size=self.FONTE_CONTADORES,
            color=COR_TEXTO,
        ).move_to(np.array([self.x0, self.Y_CONTADORES, 0.0]), aligned_edge=LEFT)
        self.guia = self._criar_guia(alvo)
        return [self.mobject, *conteudo, self.contadores, self.guia]

    # -- atualização -------------------------------------------------------

    def atualizar(self, passo):
        """(anims, adicionar, remover, troca); `troca` = (sai, novos)."""
        alvo = self._alvo(passo)
        self._i += 1

        if alvo != self.ativa:
            antigo = self.conteudos[self.ativa]
            # `todos()` de cada aba é a lista VIVA (caption recriada incluída):
            # usar snapshot de montagem deixa a caption antiga escrevendo por
            # cima da nova.
            sai = [FadeOut(m, run_time=RITMO["fade"]) for m in antigo.todos()]
            # O guia é chrome do painel (não entra em `todos()` da aba): sai
            # no mesmo fade-out e o novo entra com o corpo da aba.
            sai.append(FadeOut(self.guia, run_time=RITMO["fade"]))
            sai += self._estilo_abas(alvo)
            self.ativa = alvo
            novos = self.conteudos[alvo].construir(passo)
            self.guia = self._criar_guia(alvo)
            novos.append(self.guia)
            # Rev. 4.1 (§B.6): o FadeIn do corpo é fundo; o Flash do elemento
            # novo entra aqui para tocar no play seguinte ao fade-in, dentro do
            # `run_time` que já existe — sem play nem tempo extra.
            anims = self._realce(passo) + self._atualizar_contadores(passo)
            self.estado_anterior = estado_da_busca(passo)
            return anims, [], [], (sai, novos)

        anims, adicionar, remover = self.conteudos[alvo].sincronizar(passo)
        anims += self._atualizar_contadores(passo)
        self.estado_anterior = estado_da_busca(passo)
        return anims, adicionar, remover, None

    def _realce(self, passo) -> list[Animation]:
        """Flash do elemento que ESTA linha acrescentou à aba (rev. 4.1)."""
        aba = self.ativa
        if aba not in ("edge_to", "marcados", "busca") or passo.escrita != aba:
            return []
        ant = self.estado_anterior or {}
        if aba == "edge_to":
            novos = set(passo.estado.get("ordem_descoberta") or []) - set(
                ant.get("ordem_descoberta") or [])
            cor, linha, raio = COR_ACENTO, 0.14, 0.26
        elif aba == "marcados":
            novos = set(passo.estado.get("marcados") or []) - set(
                ant.get("marcados") or [])
            cor, linha, raio = PALETA["alcancado"][0], 0.12, 0.30
        else:
            chave = "pilha" if self.algoritmo == "ford_fulkerson_dfs" else "fila"
            novos = set(estado_da_busca(passo).get(chave) or []) - set(
                ant.get(chave) or [])
            cor, linha, raio = COR_ACENTO, 0.14, 0.26
        if len(novos) != 1:            # reset/reconstrução: o corpo inteiro basta
            return []
        alvo = self.conteudos[aba].chips.get(next(iter(novos)))
        if alvo is None:
            return []
        anims = [Flash(alvo.get_center(), color=cor, line_length=linha,
                       num_lines=8, flash_radius=raio, line_stroke_width=2)]
        if aba == "marcados":
            anims.append(Indicate(alvo, color=cor, scale_factor=1.12))
        return anims

    def _atualizar_contadores(self, passo) -> list[Animation]:
        texto = fmt_contadores(passo.estado, self.max_iteracao)
        if texto == self.texto_contadores:
            return []
        antigo = self.contadores
        novo = Text(
            texto, font_size=self.FONTE_CONTADORES, color=COR_TEXTO
        ).move_to(np.array([self.x0, self.Y_CONTADORES, 0.0]), aligned_edge=LEFT)
        self.contadores = novo
        self.texto_contadores = texto
        return [
            AnimationGroup(
                FadeOut(antigo, run_time=RITMO["play"]),
                FadeIn(novo, run_time=RITMO["play"]),
            )
        ]



# ---------------------------------------------------------------------------
# Cena base de execução (§7.3)
# ---------------------------------------------------------------------------


class FlowExecucaoBase(Scene):
    """Execução linha a linha com código, grafo, estrutura e estado juntos."""

    algoritmo: str = ""
    titulo: str = ""
    subtitulo: str = ""
    por_linha: bool = True

    # -- montagem ----------------------------------------------------------

    def montar(self) -> None:
        self.camera.background_color = COR_FUNDO
        self.passos = (
            rec.coletar_detalhado(self.algoritmo)
            if self.por_linha
            else rec.coletar(self.algoritmo)
        )
        self.max_iteracao = max((p.estado.get("iteracao") or 0) for p in self.passos)
        # Selo do `validate_vertex` (§E.4): contagem derivada do trace, nunca
        # digitada. `_vv_vistos` anda em `play_step`; violações = linha 149.
        self._vv_vistos = 0
        self._vv_violacoes = sum(
            1
            for p in self.passos
            if p.funcao == "FlowNetwork.validate_vertex" and p.linha == 149
        )

        titulo = Text(self.titulo, font_size=15, color=WHITE, weight=BOLD)
        titulo.move_to(np.array([TITULO_X, 3.62, 0.0]), aligned_edge=UL)
        subtitulo = Text(self.subtitulo, font_size=11, color=COR_ACENTO)
        subtitulo.next_to(titulo, DOWN, buff=0.05, aligned_edge=LEFT)
        self.cabecalho = VGroup(titulo, subtitulo)
        self.add(self.cabecalho)

        self.codigo = CodePanel(self.algoritmo)
        self.codigo.encaixar(self.passos[0])
        self.grafo = FlowGraphView()
        self.estrutura = EstruturaPanel(self.algoritmo, self.passos)
        self.painel = StatePanel(self.algoritmo)
        self.guia = GuiaVisual()

        self.play(
            FadeIn(self.codigo.mobject, shift=RIGHT),
            FadeIn(self.codigo.visivel),
            FadeIn(self.codigo.indicador),
            run_time=0.8,
        )
        self.play(FadeIn(self.grafo.mobject), run_time=0.7)
        mobs_estrutura = self.estrutura.preparar(self.passos[0])
        self.add(*mobs_estrutura)
        self.play(*[FadeIn(m, run_time=0.5) for m in mobs_estrutura], run_time=0.5)
        self.add(self.guia.mobject)
        self.play(FadeIn(self.guia.mobject), run_time=0.4)
        self.add(*self.painel.iniciar(self.painel.textos_do_passo(self.passos[0], self.max_iteracao)))
        self.wait(0.5)

    def limpar(self, run_time: float = 0.5) -> None:
        if self.mobjects:
            self.play(FadeOut(Group(*self.mobjects)), run_time=run_time)
        self.clear()

    # -- um passo ----------------------------------------------------------

    @staticmethod
    def _tem_flash(passo) -> bool:
        tipo, _u, _v, status = passo.destaque
        if tipo == "busca":
            return status in ("olhando", "examina", "descoberto", "nova")
        return tipo in ("caminho", "aumento", "valor", "corte")

    def _textos_do_passo(self, passo) -> list[tuple[str, str, int]]:
        """Textos do painel com o selo de `validate_vertex` no slot 5 (§E.4)."""
        textos = self.painel.textos_do_passo(passo, self.max_iteracao)
        if passo.funcao == "FlowNetwork.validate_vertex":
            self._vv_vistos += 1
        if self._vv_vistos:
            plural = "violação" if self._vv_violacoes == 1 else "violações"
            textos[4] = (
                f"validate_vertex {self._vv_vistos}× · {self._vv_violacoes} {plural}",
                COR_BORDA_NO,
                10,
            )
        return textos

    def play_step(self, passo) -> None:
        primeiro_vv = (
            passo.funcao == "FlowNetwork.validate_vertex" and self._vv_vistos == 0
        )
        # 1) troca de página: sai a antiga e SÓ DEPOIS entra a nova (dois plays)
        troca_view = self.codigo.mudou(passo)
        if troca_view:
            sai, entra = self.codigo.trocar(passo)
            self.play(*sai)
            self.play(*entra)

        # 2) estrutura: troca de aba em dois plays; conteúdo novo entra depois
        anims_estrutura, adicionar, remover, troca = self.estrutura.atualizar(passo)
        if troca:
            sai_aba, novos = troca
            self.play(*sai_aba)
            self.add(*novos)
            self.play(*[FadeIn(m, run_time=RITMO["fade"]) for m in novos])
        if adicionar:
            self.add(*adicionar)

        # 3) um único play com indicador + grafo + estado + estrutura
        anims: list[Animation] = [self.codigo.destacar(passo)]
        anims_grafo, add_grafo, rem_grafo = self.grafo.animar(passo)
        if add_grafo:
            self.add(*add_grafo)
        anims += anims_grafo
        anims += self.painel.atualizar(self._textos_do_passo(passo))
        anims += anims_estrutura
        if primeiro_vv:
            # realce único na 1ª chamada; o run_time do play já limita o Flash
            anims.append(
                Flash(
                    self.codigo.indicador.get_center(),
                    color=COR_ACENTO,
                    line_length=0.16,
                    num_lines=10,
                    flash_radius=0.30,
                )
            )

        run_time = RITMO["play_destaque"] if self._tem_flash(passo) else RITMO["play"]
        self.play(*anims, run_time=run_time)

        if remover:
            self.remove(*remover)
        if rem_grafo:
            self.remove(*rem_grafo)

        # §A.3: a troca (página ou aba) custa 2·fade e esse tempo sai da pausa;
        # o passo não fica mais longo por trocar.
        pausa = RITMO["pausa"].get(round(passo.pausa, 2), RITMO["pausa"][0.55])
        extra = 2 * RITMO["fade"] if (troca_view or troca) else 0.0
        espera = pausa - extra
        # Manim recusa wait(0): quando o fade (2·0,1333 = 0,2667 s) já cobre a
        # pausa do tier 0,55 (0,2000 s), o passo termina no próprio fade.
        if espera > 0:
            self.wait(espera)

    def executar_passos(self) -> list[rec.Step]:
        for passo in self.passos:
            self.play_step(passo)
        return self.passos

    # -- fecho: corte mínimo (§7.4) ---------------------------------------

    def fechar(self) -> None:
        est = self.passos[-1].estado
        self.play(*self.grafo.destacar_corte(est), run_time=0.9)

        lado = set(est["corte"])
        cortadas = [
            (u, v, c) for u, v, c in rec.ARESTAS_REDE if u in lado and v not in lado
        ]
        soma = " + ".join(f"{c:g}" for _u, _v, c in cortadas)
        saida_s = sum(c for u, _v, c in rec.ARESTAS_REDE if u == rec.S_FONTE)
        s_txt = "{" + ", ".join(map(str, est["corte"])) + "}"
        textos = [
            (
                f"Saída de s soma {saida_s:g}, mas |f| = {fmt_num(est['valor'])}",
                PALETA["caminho"][0],
                12,
            ),
            ("o corte S* está saturado: não há folga", PALETA["caminho"][0], 12),
            (
                fmt_fila(est) if self.algoritmo == "edmonds_karp" else fmt_pilha(est),
                COR_BORDA_NO,
                11,
            ),
            (fmt_marcados(est), PALETA["alcancado"][0], 11),
            (
                f"S*={s_txt} · C(S,T)={soma}={fmt_num(est['corte_capacidade'])} = |f|",
                PALETA["caminho"][0],
                12,
            ),
        ]
        self.play(*self.painel.atualizar(textos), run_time=0.7)
        self.wait(2.2)
