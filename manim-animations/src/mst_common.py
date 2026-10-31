"""
Componentes visuais compartilhados pelas animações MST (revisão 2).

Todo o estado exibido vem de `mst_record.Step`. Nenhuma cena calcula
Kruskal/Prim: ela só desenha o que o gravador observou no `algs4`.

Regras de desenho:
- `play_step` altera código, grafo e painel no MESMO `self.play`, e depois
  faz um hold, para não existir frame com estado misturado.
- O painel troca linha por linha com FadeOut/FadeIn (Succession). Nunca
  `Transform` entre dois `Text` de conteúdo diferente — era isso que
  produzia texto fantasma.
- O grafo é recomposto a partir do estado a cada passo: cor de componente
  e cor de vértice marcado sempre batem com o painel.
"""

from __future__ import annotations

import numpy as np
from manim import *

import mst_record as rec

# ---------------------------------------------------------------------------
# Paleta (mesma dos vídeos antigos, para a comparação continuar justa)
# ---------------------------------------------------------------------------

COR_FUNDO = "#0f111a"
COR_PAINEL = "#151824"
COR_NO = "#2b2d42"
COR_BORDA_NO = "#8d99ae"
COR_ARESTA_FORA = "#8d99ae"
COR_ANALISE = "#f9c74f"
COR_ACEITA = "#06d6a0"
COR_DESCARTE = "#ef476f"
COR_TEXTO = "#48cae4"
COR_DESTAQUE = "#ffd166"
COR_PESO_ACEITO = "#f2f4f8"
# Extração da IPQ: magenta, para não competir com o amarelo das arestas
# relaxadas (`COR_ANALISE`) nem com o verde das arestas aceitas.
COR_EXTRACAO = "#e879f9"

# Cor própria dos vértices que já estão na árvore. É um verde distinto do
# `COR_ACEITA` das arestas para o guia visual não ter dois itens iguais.
# (Vértices usam marcador em anel; arestas usam ponto cheio.)
COR_NO_ARVORE = "#80ed99"

# Cores de componente: sem amarelo e sem vermelho, para não colidir com
# "em análise" e "descartada".
PALETA_COMPONENTES = [
    "#4cc9f0",  # ciano
    "#b388ff",  # violeta
    "#3a86ff",  # azul
    "#ff70a6",  # rosa
    "#80ed99",  # verde-claro
    "#f4a261",  # areia
]

# Layout único para os três vídeos. O grafo fica à direita do card de
# código, com folga suficiente para o nó 0 não encostar na moldura.
COORDS = {
    0: np.array([1.90, 2.15, 0]),
    1: np.array([4.30, 2.45, 0]),
    2: np.array([3.00, 0.95, 0]),
    3: np.array([6.30, 2.15, 0]),
    4: np.array([5.10, 0.75, 0]),
    5: np.array([6.60, 0.75, 0]),
}

ALTURA_CODIGO = 3.9
LARGURA_MAX_PAINEL = 6.1


def _chave(u: int, v: int) -> tuple[int, int]:
    return (min(u, v), max(u, v))


def _fmt_aresta(u: int, v: int, w: float) -> str:
    return f"{u}-{v}({w:g})"


# ---------------------------------------------------------------------------
# Grafo
# ---------------------------------------------------------------------------


class GraphView:
    """Grafo canônico desenhável + tradução de destaque em animações."""

    def __init__(self, coords: dict | None = None):
        self.coords = coords or COORDS
        self.circulos: dict[int, Circle] = {}
        self._cor_atual: dict[int, str] = {}
        self.rotulos: dict[int, Text] = {}
        self.linhas: dict[tuple[int, int], Line] = {}
        self.pesos: dict[tuple[int, int], Text] = {}
        self._status: dict[tuple[int, int], str] = {
            _chave(u, v): "fora" for u, v, _ in rec.ARESTAS_CANONICAS
        }

        elementos: list[Mobject] = []

        for u, v, w in rec.ARESTAS_CANONICAS:
            p1, p2 = self.coords[u], self.coords[v]
            linha = Line(p1, p2, color=COR_ARESTA_FORA, stroke_width=3.5, z_index=0)
            diretor = np.array([-(p2[1] - p1[1]), p2[0] - p1[0], 0.0])
            norma = np.linalg.norm(diretor)
            if norma:
                diretor = diretor / norma
            lbl = Text(f"{w:g}", font_size=15, color=GRAY_A)
            lbl.move_to((p1 + p2) / 2 + diretor * 0.20)
            # Casos em que o rótulo cairia em cima de outro nó.
            if _chave(u, v) in {(3, 4), (0, 1), (4, 5)}:
                lbl.move_to((p1 + p2) / 2 + UP * 0.20)
            self.linhas[_chave(u, v)] = linha
            self.pesos[_chave(u, v)] = lbl
            elementos += [linha, lbl]

        for i, pt in self.coords.items():
            circ = Circle(radius=0.27, color=COR_BORDA_NO, fill_color=COR_NO, fill_opacity=1.0)
            circ.move_to(pt)
            lbl = Text(str(i), font_size=17, color=WHITE).move_to(pt)
            self.circulos[i] = circ
            self._cor_atual[i] = COR_NO
            self.rotulos[i] = lbl
            elementos += [circ, lbl]

        self.mobject = VGroup(*elementos)

    # -- estado visual acumulado -------------------------------------------

    def _pintar(self, chave: tuple[int, int], status: str) -> list[Animation]:
        linha = self.linhas[chave]
        peso = self.pesos[chave]
        self._status[chave] = status
        if status == "aceita":
            return [
                linha.animate.set_color(COR_ACEITA).set_stroke(width=5.5),
                peso.animate.set_color(COR_PESO_ACEITO),
            ]
        if status in ("rejeitada", "obsoleta"):
            return [
                linha.animate.set_color(COR_DESCARTE).set_stroke(width=3.0),
                peso.animate.set_color(COR_DESCARTE),
            ]
        if status == "analise":
            return [
                linha.animate.set_color(COR_ANALISE).set_stroke(width=5.0),
                peso.animate.set_color(COR_DESTAQUE),
            ]
        return [
            linha.animate.set_color(COR_ARESTA_FORA).set_stroke(width=3.5),
            peso.animate.set_color(GRAY_A),
        ]

    def _cores_dos_nos(self, estado: dict, modo: str) -> dict[int, str]:
        if modo == "arvore":
            # Kruskal: verde para quem já está conectado pela árvore aceita.
            # É monotônico (cinza -> verde), ao contrário de colorir por
            # componente, que trocava todas as cores no fim.
            na_arvore: set[int] = set()
            for u, v, _ in estado.get("mst", []):
                na_arvore.update((int(u), int(v)))
            return {v: (COR_NO_ARVORE if v in na_arvore else COR_NO) for v in self.coords}
        if modo == "componentes" and estado.get("componentes"):
            cores = {}
            for grupo in estado["componentes"]:
                cor = PALETA_COMPONENTES[min(grupo) % len(PALETA_COMPONENTES)]
                for v in grupo:
                    cores[v] = cor
            return cores
        if modo == "marcados":
            marcados = set(estado.get("marcados", []))
            return {v: (COR_NO_ARVORE if v in marcados else COR_NO) for v in self.coords}
        return {}

    def animar(self, destaque: tuple, estado: dict, modo: str = "arvore") -> list[Animation]:
        tipo, u, v, status = destaque
        anims: list[Animation] = []

        cores = self._cores_dos_nos(estado, modo)
        animados = set()
        for vertice, cor in cores.items():
            if self._cor_atual.get(vertice, COR_NO).lower() != cor.lower():
                anims.append(self.circulos[vertice].animate.set_fill(cor, opacity=1.0))
                self._cor_atual[vertice] = cor
                animados.add(vertice)

        if tipo in ("aresta", "relax") and u is not None and v is not None:
            chave = _chave(u, v)
            if chave in self.linhas:
                cor = {
                    "aceita": "aceita",
                    "rejeitada": "rejeitada",
                    "obsoleta": "obsoleta",
                    "decrease_key": "analise",
                    "insert": "analise",
                }.get(status, "analise")
                anims += self._pintar(chave, cor)

            # Destaca os extremos da aresta analisada, exceto quem já está
            # recebendo outra animação de cor neste mesmo play.
            for vertice in (u, v):
                if vertice in self.circulos and vertice not in animados:
                    anims.append(self._flash(vertice))

        # Prim Eager: toda aresta confirmada em `edgeTo` fica verde.
        if modo == "marcados":
            marcados = set(estado.get("marcados", []))
            for v in marcados:
                if v == 0:
                    continue
                e = (estado.get("edgeTo") or [])
                if v >= len(e) or e[v] is None:
                    continue
                chave = _chave(e[v][0], e[v][1])
                if chave in self.linhas and self._status.get(chave) != "aceita":
                    anims += self._pintar(chave, "aceita")

        if tipo == "vertice" and u is not None and u not in animados:
            anims.append(
                self._flash(
                    u,
                    raio=0.50,
                    cor=COR_EXTRACAO,
                    comprimento=0.30,
                    espessura=4,
                )
            )

        return anims

    def _flash(
        self,
        vertice: int,
        raio: float = 0.44,
        cor: str = COR_DESTAQUE,
        comprimento: float = 0.12,
        espessura: float = 3,
    ) -> Animation:
        """Brilho em volta do nó, sem alterar o preenchimento/número."""
        return Flash(
            self.circulos[vertice].get_center(),
            color=cor,
            flash_radius=raio,
            line_length=comprimento,
            line_stroke_width=espessura,
            num_lines=10,
            run_time=0.35,
        )


# ---------------------------------------------------------------------------
# Painel de código: recorte do arquivo real do algs4
# ---------------------------------------------------------------------------


class CodePanel:
    def __init__(self, algoritmo: str, altura: float = ALTURA_CODIGO):
        texto, inicio = rec.trecho_codigo(algoritmo)
        self.inicio = inicio

        self.code = Code(
            code_string=texto,
            language="python",
            formatter_style="monokai",
            add_line_numbers=True,
            line_numbers_from=inicio,
            background="rectangle",
        ).scale_to_fit_height(altura)

        # A moldura nativa do `Code` não acompanha o texto (cortava a última
        # linha e ficava duplicada). Removemos a nativa e desenhamos a nossa.
        self.code.remove(self.code.background)

        esquerda = self.code.get_left()[0] - 0.30
        direita = self.code.get_right()[0] + 0.34
        topo = self.code.code_lines[0].get_top()[1] + 0.16
        base = self.code.code_lines[-1].get_bottom()[1] - 0.16

        self.moldura = RoundedRectangle(
            corner_radius=0.08,
            width=direita - esquerda,
            height=topo - base,
            color=GRAY_C,
            stroke_width=1.2,
            fill_color="#12141d",
            fill_opacity=0.85,
        ).move_to([(esquerda + direita) / 2, (topo + base) / 2, 0])

        bloco = VGroup(self.moldura, self.code)
        bloco.to_corner(UL, buff=0.45).shift(DOWN * 0.45)

        self.indicador = SurroundingRectangle(
            self.code.code_lines[0],
            color=COR_DESTAQUE,
            buff=0.04,
            stroke_width=2.5,
            fill_color=YELLOW,
            fill_opacity=0.15,
        )

    @property
    def mobject(self) -> VGroup:
        return VGroup(self.moldura, self.code, self.indicador)

    def encaixar(self, linha: int) -> None:
        """Posiciona o indicador sem animação (primeiro passo da cena)."""
        indice = max(0, min(linha - self.inicio, len(self.code.code_lines) - 1))
        alvo = self.code.code_lines[indice]
        self.indicador.move_to(alvo.get_center())
        self.indicador.stretch_to_fit_width(alvo.width + 0.25)
        self.indicador.stretch_to_fit_height(alvo.height + 0.12)

    def destacar(self, linha: int) -> Animation:
        indice = max(0, min(linha - self.inicio, len(self.code.code_lines) - 1))
        alvo = self.code.code_lines[indice]
        # `set_width`/`set_height` escalam proporcionalmente; para a caixa
        # acompanhar a linha real (inclusive as longas) é preciso esticar
        # cada eixo de forma independente.
        return (
            self.indicador.animate.move_to(alvo.get_center())
            .stretch_to_fit_width(alvo.width + 0.25)
            .stretch_to_fit_height(alvo.height + 0.12)
        )


# ---------------------------------------------------------------------------
# Painel de estado: linhas fixas, troca sem Transform
# ---------------------------------------------------------------------------


class StatePanel:
    """Painel de N linhas fixas.

    Cada linha é um `Text` independente. Quando o conteúdo muda, a linha
    antiga sai e a nova entra em `Succession` — nunca há dois textos
    diferentes sobrepostos no mesmo frame.
    """

    def __init__(self, centro: np.ndarray, largura: float, altura: float, n_linhas: int):
        self.centro = centro
        self.largura = largura
        self.altura = altura
        self.n = n_linhas

        self.fundo = RoundedRectangle(
            corner_radius=0.15,
            width=largura,
            height=altura,
            color=GRAY_D,
            stroke_width=1.5,
            fill_color=COR_PAINEL,
            fill_opacity=0.9,
        ).move_to(centro)

        self.linhas: list[Text | None] = [None] * n_linhas
        self.conteudos: list[str] = [""] * n_linhas
        self.cores: list[str] = [WHITE] * n_linhas
        self.fontes: list[int] = [14] * n_linhas

        # Distribui as linhas de cima para baixo dentro do painel.
        util = altura - 0.35
        passo = util / max(1, n_linhas - 1)
        self.posicoes = [
            np.array([centro[0] - largura / 2 + 0.22, centro[1] + util / 2 - i * passo, 0])
            for i in range(n_linhas)
        ]

    def _criar(self, i: int, texto: str, cor: str, fonte: int) -> Text:
        t = Text(texto, font_size=fonte, color=cor)
        if t.width > LARGURA_MAX_PAINEL:
            t.scale_to_fit_width(LARGURA_MAX_PAINEL)
        t.move_to(self.posicoes[i], aligned_edge=LEFT)
        return t

    def iniciar(self, textos: list[tuple[str, str, int]]) -> list[Mobject]:
        """Primeira montagem: devolve os mobjects para `self.add`."""
        for i, (texto, cor, fonte) in enumerate(textos):
            self.linhas[i] = self._criar(i, texto, cor, fonte)
            self.conteudos[i] = texto
            self.cores[i] = cor
            self.fontes[i] = fonte
        return [self.fundo, *[l for l in self.linhas if l is not None]]

    def atualizar(self, textos: list[tuple[str, str, int]]) -> list[Animation]:
        anims: list[Animation] = []
        for i, (texto, cor, fonte) in enumerate(textos):
            if texto == self.conteudos[i] and cor == self.cores[i]:
                continue
            novo = self._criar(i, texto, cor, fonte)
            antigo = self.linhas[i]
            if antigo is None:
                anims.append(FadeIn(novo, run_time=0.2))
            else:
                # Crossfade curto: sem frame em branco (Succession deixava a
                # linha invisível entre o FadeOut e o FadeIn).
                anims.append(
                    AnimationGroup(
                        FadeOut(antigo, run_time=0.18, shift=UP * 0.15),
                        FadeIn(novo, run_time=0.18, shift=UP * 0.15),
                    )
                )
            self.linhas[i] = novo
            self.conteudos[i] = texto
            self.cores[i] = cor
            self.fontes[i] = fonte
        return anims


# ---------------------------------------------------------------------------
# Formatação do painel (compartilhada pelas cenas e pelos vídeos completos)
# ---------------------------------------------------------------------------

INF = float("inf")


def cor_destaque(passo) -> str:
    status = passo.destaque[3]
    if status == "aceita":
        return COR_ACEITA
    if status in ("rejeitada", "obsoleta"):
        return COR_DESCARTE
    if status == "extraido":
        return COR_EXTRACAO
    if status in ("decrease_key", "insert", "marcado", "inicio"):
        return COR_DESTAQUE
    return COR_TEXTO


def fmt_fila(estado: dict) -> str:
    fila = estado.get("fila") or []
    if not fila:
        return "MinPQ: []"
    return "MinPQ: [" + ", ".join(f"{u}-{v}({w:g})" for u, v, w in fila) + "]"


def fmt_fila_lazy(estado: dict) -> str:
    fila = estado.get("fila") or []
    if not fila:
        return "MinPQ: []"
    marcados = set(estado.get("marcados", []))
    partes = []
    for u, v, w in fila:
        sufixo = " obs" if (u in marcados and v in marcados) else ""
        partes.append(f"{u}-{v}({w:g}){sufixo}")
    return "MinPQ: [" + ", ".join(partes) + "]"


def fmt_componentes(estado: dict) -> str:
    grupos = estado.get("componentes") or []
    if not grupos:
        return "Componentes: -"
    return "Componentes: " + " ".join(
        "{" + ",".join(str(v) for v in g) + "}" for g in grupos
    )


def fmt_mst_prim(estado: dict) -> str:
    n = (
        max(0, len(estado.get("marcados", [])) - 1)
        if estado.get("edgeTo")
        else len(estado.get("mst", []))
    )
    return f"MST: {n} / 5 arestas  |  Custo: {estado['custo']:g}"


def fmt_marcados(estado: dict) -> str:
    marcados = estado.get("marcados", [])
    conjunto = set(marcados)
    pendentes = [v for v in range(rec.V_CANONICO) if v not in conjunto]
    return (
        "Marcados: " + (", ".join(map(str, marcados)) or "-")
        + "  |  Pendentes: " + (", ".join(map(str, pendentes)) or "-")
    )


def fmt_ipq(estado: dict) -> str:
    ipq = estado.get("ipq") or {}
    if not ipq:
        return "IPQ: {}"
    itens = sorted(ipq.items(), key=lambda kv: (kv[1], kv[0]))
    return "IPQ: {" + ", ".join(f"{v}:{k:g}" for v, k in itens) + "}"


def fmt_edge_to(estado: dict) -> str:
    edge_to = estado.get("edgeTo") or []
    partes = ["-" if e is None else f"{e[0]}-{e[1]}" for e in edge_to]
    return "edgeTo: [" + ", ".join(partes) + "]"


def fmt_dist_to(estado: dict) -> str:
    dist = estado.get("distTo") or []
    return "distTo: [" + ", ".join("inf" if d == INF else f"{d:g}" for d in dist) + "]"


# ---------------------------------------------------------------------------
# Cena base
# ---------------------------------------------------------------------------


class MSTExecucaoBase(Scene):
    algoritmo: str = ""
    titulo: str = ""
    modo_nos: str = "componentes"
    n_linhas_painel: int = 4
    # Modo didático: um passo por linha executada do algs4. O modo compacto
    # (`por_linha = False`) continua disponível para quem quiser o resumo.
    por_linha: bool = True

    def configurar(self, modelo) -> None:
        """Copia a configuração da cena-modelo (usado pelos vídeos completos)."""
        self.algoritmo = modelo.algoritmo
        self.titulo = modelo.titulo
        self.modo_nos = modelo.modo_nos
        self.n_linhas_painel = modelo.n_linhas_painel
        self.por_linha = modelo.por_linha

    def montar_estrutura(self, legenda: list[tuple[str, str]]) -> None:
        self.camera.background_color = COR_FUNDO
        self.passos = (
            rec.coletar_detalhado(self.algoritmo)
            if self.por_linha
            else rec.coletar(self.algoritmo)
        )

        titulo = Text(self.titulo, font_size=26, color=WHITE, weight=BOLD)
        titulo.to_edge(UP, buff=0.25)
        self.add(titulo)

        self.codigo = CodePanel(self.algoritmo)
        # O indicador nasce na primeira linha exibida; sem isso a cena abre
        # destacando `class KruskalMST:` (linha 46), que nunca executa.
        self.codigo.encaixar(self.passos[0].linha)

        self.grafo = GraphView()

        self.painel = StatePanel(
            centro=np.array([3.55, -2.30, 0]),
            largura=6.5,
            altura=2.55,
            n_linhas=self.n_linhas_painel,
        )

        self.play(FadeIn(self.codigo.mobject, shift=RIGHT), run_time=0.8)
        self.play(FadeIn(self.grafo.mobject), run_time=0.8)

        legenda_bloco = self._montar_legenda(legenda)
        self.add(legenda_bloco)

        textos_iniciais = [(texto, cor, fonte) for texto, cor, fonte in self.textos_iniciais()]
        self.add(*self.painel.iniciar(textos_iniciais))
        self.play(FadeIn(legenda_bloco), run_time=0.4)
        self.wait(0.6)

    def limpar(self, run_time: float = 0.5) -> None:
        """Apaga tudo antes de iniciar a próxima cena do vídeo completo.

        Sem isso, o título/legenda/painel da cena anterior continuam no
        frame seguinte e aparecem sobrepostos (texto fantasma).
        """
        if self.mobjects:
            self.play(FadeOut(Group(*self.mobjects)), run_time=run_time)
        self.clear()

    def _montar_legenda(self, itens: list[tuple[str, str] | tuple[str, str, str]]) -> VGroup:
        """Monta o guia visual.

        Cada item é `(cor, texto)` ou `(cor, texto, forma)`, com
        `forma="dot"` (aresta) ou `"ring"` (vértice). O anel diferencia os
        vértices das arestas mesmo quando as cores se repetem.
        """
        titulo = Text("Guia visual", font_size=15, color=COR_TEXTO, weight=BOLD)
        linhas = [titulo]
        for item in itens:
            cor, texto = item[0], item[1]
            forma = item[2] if len(item) > 2 else "dot"
            if forma == "ring":
                marca = Circle(
                    radius=0.08,
                    color=cor,
                    stroke_width=2.2,
                    fill_opacity=0.0,
                )
            else:
                marca = Dot(color=cor, radius=0.08)
            linhas.append(
                VGroup(
                    marca,
                    Text(texto, font_size=13, color=WHITE),
                ).arrange(RIGHT, buff=0.15)
            )
        bloco = VGroup(*linhas).arrange(DOWN, aligned_edge=LEFT, buff=0.10)
        bloco.next_to(self.codigo.code, DOWN, buff=0.22, aligned_edge=LEFT)
        return bloco

    # -- painel ------------------------------------------------------------

    def textos_iniciais(self) -> list[tuple[str, str, int]]:
        return self.textos_painel(self.passos[0])

    def textos_painel(self, passo: rec.Step) -> list[tuple[str, str, int]]:
        est = passo.estado
        cor = cor_destaque(passo)

        if self.algoritmo == "kruskal":
            return [
                (passo.acao, cor, 14),
                (f"MST: {len(est['mst'])} / 5 arestas  |  Custo: {est['custo']:g}", WHITE, 15),
                (fmt_fila(est), "#8d99ae", 12),
                (fmt_componentes(est), GRAY_A, 12),
            ]

        if self.algoritmo == "lazy":
            return [
                (passo.acao, cor, 14),
                (fmt_mst_prim(est), WHITE, 15),
                (fmt_fila_lazy(est), "#8d99ae", 11),
                (fmt_marcados(est), GRAY_A, 12),
            ]

        return [
            (passo.acao, cor, 13),
            (fmt_mst_prim(est), WHITE, 15),
            (fmt_ipq(est), "#8d99ae", 12),
            (fmt_edge_to(est), COR_TEXTO, 11),
            (fmt_dist_to(est), GRAY_A, 11),
        ]

    # -- encerramento -------------------------------------------------------

    def fechar(self) -> None:
        est = self.passos[-1].estado

        if self.algoritmo == "kruskal":
            self.play(
                *[
                    anim
                    for u, v, _ in est["mst"]
                    for anim in self.grafo._pintar((min(u, v), max(u, v)), "aceita")
                ],
                run_time=0.8,
            )
            textos = [
                ("MST concluída: 5 arestas, custo 13", COR_ACEITA, 15),
                (fmt_fila(est), "#8d99ae", 12),
                (fmt_componentes(est), GRAY_A, 12),
                ("Um único componente: a árvore conecta todos os vértices", COR_TEXTO, 13),
            ]
        elif self.algoritmo == "lazy":
            textos = [
                ("MST concluída: 5 arestas, custo 13", COR_ACEITA, 15),
                ("A MinPQ foi drenada: nenhuma aresta sobrou", WHITE, 13),
                ("As 3 arestas obsoletas foram descartadas por continue", COR_DESCARTE, 12),
                (fmt_marcados(est), GRAY_A, 12),
            ]
        else:
            # Arestas apenas relaxadas continuam amarelas nos passos; no
            # encerramento voltam ao cinza para o frame final mostrar só a MST.
            na_arvore = {
                _chave(e[0], e[1])
                for e in est["edgeTo"]
                if e is not None
            }
            self.play(
                *[
                    anim
                    for chave, status in self.grafo._status.items()
                    if chave not in na_arvore and status != "fora"
                    for anim in self.grafo._pintar(chave, "fora")
                ],
                run_time=0.8,
            )
            textos = [
                ("MST concluída: 5 arestas, custo 13", COR_ACEITA, 15),
                ("Um item por vértice na IPQ; nenhuma aresta obsoleta guardada", WHITE, 12),
                (fmt_edge_to(est), COR_TEXTO, 11),
                (fmt_dist_to(est), GRAY_A, 11),
                ("Árvore confirmada em edgeTo: 5 arestas", COR_DESTAQUE, 12),
            ]

        self.play(*self.painel.atualizar(textos), run_time=0.6)
        self.wait(2.2)

    # -- o único ponto de atualização --------------------------------------

    def play_step(self, passo: rec.Step) -> None:
        anims: list[Animation] = [self.codigo.destacar(passo.linha)]
        anims += self.grafo.animar(passo.destaque, passo.estado, modo=self.modo_nos)
        anims += self.painel.atualizar(self.textos_painel(passo))
        self.play(*anims, run_time=0.45)
        # O ritmo vem do gravador: decisões ficam mais tempo na tela,
        # linhas de bookkeeping (for/while/if) passam mais rápido.
        self.wait(passo.pausa)

    def executar_passos(self) -> list[rec.Step]:
        for passo in self.passos:
            self.play_step(passo)
        return self.passos
