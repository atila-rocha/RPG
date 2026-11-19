"""
Componentes visuais compartilhados pela animação do algoritmo de Dijkstra.

Todo o estado exibido vem de `dijkstra_record.Step`. Nenhuma cena calcula
Dijkstra à mão: ela desenha o que o gravador observou no `algs4-py`.

Componentes (mesmo padrão das animações MST):
- DirectedGraphView: digrafo com setas, pesos e cores por estado
- CodePanel: uma view por função, troca fade-out/fade-in em dois plays
- EstruturaPanel: abas [IndexMinPQ | distTo | edgeTo] derivadas do trace
- StatePanel: linhas fixas de narração e métricas
- DijkstraExecucaoBase: orquestra a execução linha a linha
"""

from __future__ import annotations

import numpy as np
from manim import *

import dijkstra_record as rec

# ---------------------------------------------------------------------------
# Paleta de Cores Unívoca (conforme manim-visual)
# ---------------------------------------------------------------------------

COR_FUNDO = "#0f111a"
COR_PAINEL = "#151824"
COR_NO = "#2b2d42"
COR_BORDA_NO = "#8d99ae"
COR_ARESTA_FORA = "#8d99ae"
COR_ANALISE = "#f9c74f"          # amarelo: aresta/nó sob análise
COR_ACEITA = "#06d6a0"           # verde: aresta confirmada na SPT
COR_DESCARTE = "#ef476f"         # vermelho: aresta que não melhora o caminho
COR_TEXTO = "#48cae4"            # ciano claro: cabeçalhos e rótulos
COR_DESTAQUE = "#ffd166"         # dourado: indicador de código
COR_PESO_ACEITO = "#f2f4f8"
COR_EXTRACAO = "#e879f9"         # magenta: vértice extraído da IPQ
COR_NO_FINALIZADO = "#80ed99"    # verde suave: distância ótima consolidada
COR_TENTATIVA = "#e0e1dd"        # branco-osso: aresta em edgeTo (não confirmada)
COR_REPETIDO = "#f9844a"         # laranja: entrada repetida no heap

COR_TAB_ATIVA = "#1f2637"
COR_TAB_INATIVA = "#0f111a"
COR_LINHA_HEAP = "#2a2f45"

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

# tinyEWD (8 vértices): anel 0-7-1-5-4-6-3-2, o mesmo desenho do tinyEWG do
# MST. O anel deixa as arestas recíprocas (4<->5 e 5<->7) lado a lado e as
# cordas do Dijkstra (0->4, 4->7, 2->7, 7->3, 1->3) atravessam o interior.
COORDS_TINYEWD = {
    0: np.array([4.30, 2.85, 0]),
    7: np.array([5.89, 2.47, 0]),
    1: np.array([6.55, 1.55, 0]),
    5: np.array([5.89, 0.63, 0]),
    4: np.array([4.30, 0.25, 0]),
    6: np.array([2.71, 0.63, 0]),
    3: np.array([2.05, 1.55, 0]),
    2: np.array([2.71, 2.47, 0]),
}


def coords_do_grafo() -> dict[int, np.ndarray]:
    """Layout do grafo ativo.

    O anel do tinyEWD só vale para os 8 vértices dele. Para qualquer outro
    arquivo (inclusive o fallback de 5 vértices) desenha um círculo no mesmo
    quadrante; a animação continua fiel, só perde o ajuste fino do anel.
    """
    if rec.V_CANONICO == 8 and set(COORDS_TINYEWD) == set(range(rec.V_CANONICO)):
        return dict(COORDS_TINYEWD)
    centro = np.array([4.30, 1.55, 0.0])
    raio = 1.55
    coords = {}
    for v in range(rec.V_CANONICO):
        ang = -PI / 2 + 2 * PI * v / max(1, rec.V_CANONICO)
        coords[v] = centro + np.array([raio * np.cos(ang), raio * np.sin(ang), 0.0])
    return coords


COORDS = coords_do_grafo()

ALTURA_CODIGO = 3.72
LARGURA_MAX_PAINEL = 6.1

ABAS_DIJKSTRA = (
    ("heap", "IndexMinPQ"),
    ("dt", "distTo"),
    ("et", "edgeTo"),
)


def _chave(u: int, v: int) -> tuple[int, int]:
    """Chave de aresta DIRIGIDA: (u, v), sem ordenar."""
    return (int(u), int(v))


def _fmt_dist(d: float) -> str:
    if d >= 999999.0 or d == float("inf"):
        return "∞"
    return f"{d:g}"


# ---------------------------------------------------------------------------
# DirectedGraphView
# ---------------------------------------------------------------------------


class DirectedGraphView:
    """Digrafo desenhável + tradução do destaque em animações.

    - setas: cada aresta dirigida tem ponta própria; pares recíprocos são
      deslocados perpendicularmente para as duas setas não se sobreporem;
    - pesos com fundo opaco, posicionados por busca de posição livre (nunca
      em cima de outro peso, de um nó ou de outra aresta);
    - o estado visual é acumulado e recalculado a cada passo a partir do
      `estado` real (SPT, edgeTo tentativa, aresta em análise).
    """

    RAIO_NO = 0.27
    OFFSET_RECIPROCA = 0.095

    def __init__(self, coords: dict | None = None):
        self.coords = coords or COORDS
        self.circulos: dict[int, Circle] = {}
        self.rotulos: dict[int, Text] = {}
        self.setas: dict[tuple[int, int], Arrow] = {}
        self.pesos: dict[tuple[int, int], Text] = {}
        self.peso_fundos: dict[tuple[int, int], RoundedRectangle] = {}
        self._status: dict[tuple[int, int], str] = {
            _chave(u, v): "fora" for u, v, _ in rec.ARESTAS_CANONICAS
        }
        self._no_status: dict[int, str] = {v: "fora" for v in self.coords}

        # Pares recíprocos: mesma aresta nos dois sentidos.
        self._reciprocas: set[tuple[int, int]] = {
            (u, v)
            for u, v, _ in rec.ARESTAS_CANONICAS
            if (v, u) in {_chave(a, b) for a, b, _ in rec.ARESTAS_CANONICAS}
        }

        elementos: list[Mobject] = []
        for u, v, w in rec.ARESTAS_CANONICAS:
            p1, p2 = self.coords[u], self.coords[v]
            desvio = ORIGIN
            if (u, v) in self._reciprocas:
                # A normal é calculada na direção canônica (menor -> maior),
                # não na direção da seta. Se fosse calculada na direção da
                # seta, normal e sinal inverteriam juntos e as duas setas
                # recíprocas ficariam exatamente sobrepostas.
                a, b = (u, v) if u < v else (v, u)
                vetor = self.coords[b] - self.coords[a]
                comprimento = np.linalg.norm(vetor)
                if comprimento > 0:
                    normal = np.array([-vetor[1], vetor[0], 0]) / comprimento
                    sinal = 1.0 if u < v else -1.0
                    desvio = normal * self.OFFSET_RECIPROCA * sinal

            seta = Arrow(
                p1 + desvio,
                p2 + desvio,
                buff=0.30,
                stroke_width=3.0,
                max_tip_length_to_length_ratio=0.22,
                tip_length=0.17,
                color=COR_ARESTA_FORA,
                z_index=1,
            )
            lbl = Text(f"{w:g}", font_size=14, color=GRAY_A).set_z_index(3)
            fundo = RoundedRectangle(
                corner_radius=0.05,
                width=lbl.width + 0.12,
                height=lbl.height + 0.06,
                stroke_width=0,
                fill_color=COR_FUNDO,
                fill_opacity=1.0,
            ).set_z_index(2)

            self.setas[_chave(u, v)] = seta
            self.pesos[_chave(u, v)] = lbl
            self.peso_fundos[_chave(u, v)] = fundo
            elementos += [seta, fundo, lbl]

        # Só depois de todos os pesos existirem é possível desviar de todos.
        self._posicionar_pesos()

        for i, pt in self.coords.items():
            circ = Circle(
                radius=self.RAIO_NO,
                color=COR_BORDA_NO,
                fill_color=COR_NO,
                fill_opacity=1.0,
                stroke_width=2.5,
                z_index=4,
            ).move_to(pt)
            lbl = Text(str(i), font_size=20, color=WHITE, weight=BOLD).move_to(pt).set_z_index(6)
            self.circulos[i] = circ
            self.rotulos[i] = lbl
            elementos += [circ, lbl]

        self.mobject = VGroup(*elementos)

    # -- posicionamento dos pesos ------------------------------------------

    def _posicionar_pesos(self) -> None:
        """Põe cada peso sobre a própria seta, sem cobrir outro elemento.

        Mesma busca determinística do `GraphView` do MST, adaptada para
        arestas dirigidas: o segmento considerado é o da seta (já deslocada
        no caso de par recíproco).
        """
        def segmento(u: int, v: int) -> tuple[np.ndarray, np.ndarray]:
            p1, p2 = self.coords[u], self.coords[v]
            if (u, v) in self._reciprocas:
                a, b = (u, v) if u < v else (v, u)
                vetor = self.coords[b] - self.coords[a]
                comp = np.linalg.norm(vetor)
                if comp > 0:
                    normal = np.array([-vetor[1], vetor[0], 0]) / comp
                    sinal = 1.0 if u < v else -1.0
                    desvio = normal * self.OFFSET_RECIPROCA * sinal
                    return p1 + desvio, p2 + desvio
            return p1, p2

        segmentos = {
            _chave(u, v): segmento(u, v)
            for u, v, _ in rec.ARESTAS_CANONICAS
        }
        chaves = [_chave(u, v) for u, v, _ in rec.ARESTAS_CANONICAS]

        caixas: list[tuple[float, float, float, float]] = [
            (pt[0] - 0.34, pt[0] + 0.34, pt[1] - 0.34, pt[1] + 0.34)
            for pt in self.coords.values()
        ]

        def cruza_segmento(p, q, caixa, margem: float) -> bool:
            """Liang–Barsky: o segmento p-q invade o retângulo expandido?"""
            xmin, xmax = caixa[0] - margem, caixa[1] + margem
            ymin, ymax = caixa[2] - margem, caixa[3] + margem
            dx, dy = q[0] - p[0], q[1] - p[1]
            t0, t1 = 0.0, 1.0
            for pk, qk in (
                (-dx, p[0] - xmin),
                (dx, xmax - p[0]),
                (-dy, p[1] - ymin),
                (dy, ymax - p[1]),
            ):
                if pk == 0:
                    if qk < 0:
                        return False
                else:
                    t = qk / pk
                    if pk < 0:
                        if t > t1:
                            return False
                        t0 = max(t0, t)
                    else:
                        if t < t0:
                            return False
                        t1 = min(t1, t)
            return t0 <= t1

        def colisoes(lbl: Text, propria: tuple[int, int]) -> int:
            caixa = (
                lbl.get_left()[0] - 0.02,
                lbl.get_right()[0] + 0.02,
                lbl.get_bottom()[1] - 0.02,
                lbl.get_top()[1] + 0.02,
            )
            total = sum(
                1
                for ce, cd, cb, ct in caixas
                if not (caixa[1] < ce or caixa[0] > cd or caixa[3] < cb or caixa[2] > ct)
            )
            # Fora da área útil (cabeçalho, moldura, painéis) também conta.
            if caixa[0] < 0.95 or caixa[1] > 7.02 or caixa[2] < 0.14 or caixa[3] > 3.42:
                total += 1
            for chave in chaves:
                if chave == propria:
                    continue
                p, q = segmentos[chave]
                if cruza_segmento(p, q, caixa, 0.05):
                    total += 1
            return total

        for chave in chaves:
            lbl = self.pesos[chave]
            p1, p2 = segmentos[chave]
            diretor = np.array([-(p2[1] - p1[1]), p2[0] - p1[0], 0.0])
            norma = np.linalg.norm(diretor)
            diretor = diretor / norma if norma else np.array([0.0, 1.0, 0.0])
            meio = (p1 + p2) / 2

            candidatos = [(t, 0.0) for t in (0.5, 0.44, 0.56, 0.38, 0.62, 0.32, 0.68, 0.26, 0.74)]
            candidatos += [
                (t, lado * d)
                for d in (0.14, 0.20, 0.27)
                for t in (0.5, 0.40, 0.60, 0.32, 0.68)
                for lado in (1.0, -1.0)
            ]

            livre = None
            melhor = (10 ** 9, None)
            for i, (t, desvio) in enumerate(candidatos):
                lbl.move_to(p1 + (p2 - p1) * t + diretor * desvio)
                n = colisoes(lbl, chave)
                nota = n * 1000 + i
                if n == 0:
                    livre = lbl.get_center()
                    break
                if nota < melhor[0]:
                    melhor = (nota, lbl.get_center())

            if livre is not None:
                lbl.move_to(livre)
            elif melhor[1] is not None:
                lbl.move_to(melhor[1])
            else:
                lbl.move_to(meio + diretor * 0.20)
            self.peso_fundos[chave].move_to(lbl.get_center())
            caixas.append(
                (
                    lbl.get_left()[0] - 0.05,
                    lbl.get_right()[0] + 0.05,
                    lbl.get_bottom()[1] - 0.05,
                    lbl.get_top()[1] + 0.05,
                )
            )

    # -- pintura -----------------------------------------------------------

    def _pintar_aresta(self, u: int, v: int, status: str) -> list[Animation]:
        chave = _chave(u, v)
        if chave not in self.setas:
            return []
        seta, peso = self.setas[chave], self.pesos[chave]
        self._status[chave] = status

        if status == "analise":
            return [
                seta.animate.set_color(COR_ANALISE).set_stroke(width=5.0),
                peso.animate.set_color(COR_DESTAQUE),
            ]
        if status == "aceita":
            return [
                seta.animate.set_color(COR_ACEITA).set_stroke(width=5.0),
                peso.animate.set_color(COR_PESO_ACEITO),
            ]
        if status == "tentativa":
            return [
                seta.animate.set_color(COR_TENTATIVA).set_stroke(width=4.0),
                peso.animate.set_color(COR_TENTATIVA),
            ]
        if status in ("rejeitada", "descarte"):
            return [
                seta.animate.set_color(COR_DESCARTE).set_stroke(width=3.0),
                peso.animate.set_color(COR_DESCARTE),
            ]
        return [
            seta.animate.set_color(COR_ARESTA_FORA).set_stroke(width=3.0),
            peso.animate.set_color(GRAY_A),
        ]

    def _pintar_no(self, u: int, status: str) -> list[Animation]:
        if u not in self.circulos:
            return []
        circ = self.circulos[u]
        self._no_status[u] = status

        if status == "origem":
            return [circ.animate.set_stroke(COR_TEXTO, width=3.6).set_fill("#182b3d")]
        if status == "finalizado":
            return [circ.animate.set_stroke(COR_NO_FINALIZADO, width=3.4).set_fill("#1a332a")]
        if status == "extraido":
            return [circ.animate.set_stroke(COR_EXTRACAO, width=4.2).set_fill("#382347")]
        if status == "analise":
            return [circ.animate.set_stroke(COR_DESTAQUE, width=3.6)]
        return []

    def _flash(self, u: int, cor: str = COR_DESTAQUE) -> Animation:
        return Flash(
            self.circulos[u],
            color=cor,
            line_length=0.16,
            num_lines=10,
            flash_radius=0.42,
        )

    def animar(self, destaque: tuple, estado: dict) -> list[Animation]:
        tipo, u, v, status = destaque
        anims: list[Animation] = []

        # 1. Nós: origem/finalizados são estado permanente.
        for vertice in self.coords:
            alvo = "origem" if vertice == estado.get("origem") else (
                "finalizado" if vertice in set(estado.get("marcados", [])) else "fora"
            )
            if self._no_status.get(vertice) != alvo:
                anims += self._pintar_no(vertice, alvo)

        # Extração: além de finalizado, ganha o destaque magenta por um passo.
        if tipo == "vertice" and status == "extraido" and u in self.circulos:
            if self._no_status.get(u) != "extraido":
                anims += self._pintar_no(u, "extraido")

        # 2. Arestas: recalcula o estado real do passo inteiro.
        destaque_chave = _chave(u, v) if tipo == "aresta" and u is not None and v is not None else None
        spt = {_chave(e[0], e[1]) for e in estado.get("spt", [])}
        marcados = set(estado.get("marcados", []))
        tentativa = set()
        for vert, e in enumerate(estado.get("edgeTo") or []):
            if e is not None and vert not in marcados:
                tentativa.add(_chave(e[0], e[1]))

        for chave in self.setas:
            if chave == destaque_chave and status in ("analise", "relaxada"):
                alvo = "analise"
            elif chave == destaque_chave and status == "aceita":
                # Registro em edgeTo: verde no instante do registro; a
                # confirmação definitiva só vem com a extração do vértice.
                alvo = "aceita"
            elif chave in spt:
                alvo = "aceita"
            elif chave in tentativa:
                alvo = "tentativa"
            else:
                alvo = "fora"
            if self._status.get(chave) != alvo:
                anims += self._pintar_aresta(chave[0], chave[1], alvo)

        # 3. Flash nos extremos da aresta analisada (sem duplicar nós que já
        #    mudaram de cor neste mesmo play).
        if tipo == "aresta" and u is not None and v is not None:
            for vertice in (u, v):
                if vertice in self.circulos:
                    anims.append(self._flash(vertice))
        elif tipo == "vertice" and u is not None and u in self.circulos:
            anims.append(self._flash(u, cor=COR_EXTRACAO))

        return anims


# ---------------------------------------------------------------------------
# CodePanel: uma view por função, troca fade-out/fade-in em dois plays
# ---------------------------------------------------------------------------


class CodePanel:
    """Painel fixo que mostra a função executada, na íntegra.

    Um `Code` por função (algoritmo e estruturas auxiliares), todos com a
    mesma escala; a moldura é dimensionada uma única vez; o indicador é por
    view e troca junto com o código. A troca usa dois plays (`FadeOut` e
    depois `FadeIn`) para nunca haver dois códigos no mesmo frame.
    """

    PADDING_ESQ = 0.30
    PADDING_DIR = 0.34
    PADDING_TOPO = 0.16
    PADDING_BASE = 0.16
    LARGURA_CODIGO = 6.40
    ALTURA_CABECALHO = 0.30
    TEMPO_FADE = 0.18

    def __init__(self, altura: float = ALTURA_CODIGO):
        self.funcoes = rec.funcoes_codigo()
        self._por_chave = {(f.modulo, f.nome): i for i, f in enumerate(self.funcoes)}

        self.codigos: list[Code] = []
        for f in self.funcoes:
            codigo = Code(
                code_string=f.texto,
                language="python",
                formatter_style="monokai",
                add_line_numbers=True,
                line_numbers_from=f.inicio,
                background="rectangle",
            )
            codigo.remove(codigo.background)
            self.codigos.append(codigo)

        escala = min(
            (altura - self.ALTURA_CABECALHO) / max(c.height for c in self.codigos),
            self.LARGURA_CODIGO / max(c.width for c in self.codigos),
        )
        for codigo in self.codigos:
            codigo.scale(escala)

        self.conteudos: list[VGroup] = []
        for f, codigo in zip(self.funcoes, self.codigos):
            cabecalho = Text(
                f"{f.nome}  ·  {f.arquivo}:{f.inicio}–{f.fim}",
                font_size=13,
                color=COR_TEXTO,
            )
            self.conteudos.append(
                VGroup(cabecalho, codigo).arrange(DOWN, aligned_edge=LEFT, buff=0.10)
            )

        largura = max(g.width for g in self.conteudos)
        altura_max = max(g.height for g in self.conteudos)

        # A moldura ocupa o quadrante superior esquerdo inteiro. Sem forçar
        # ALTURA_CODIGO, funções curtas do Dijkstra deixariam o painel baixo
        # e desalinhado em relação à faixa do painel de estrutura.
        self.moldura = RoundedRectangle(
            corner_radius=0.08,
            width=largura + self.PADDING_ESQ + self.PADDING_DIR,
            height=max(altura, altura_max + self.PADDING_TOPO + self.PADDING_BASE),
            color=GRAY_C,
            stroke_width=1.2,
            fill_color="#12141d",
            fill_opacity=0.85,
        )
        self.moldura.to_corner(UL, buff=0.55)

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
                color=COR_DESTAQUE,
                buff=0.04,
                stroke_width=2.5,
                fill_color=YELLOW,
                fill_opacity=0.15,
            )
            for codigo in self.codigos
        ]
        self._posicionar(self.indicadores[0], 0, self.funcoes[0].inicio)

        self.mobject = VGroup(self.moldura)
        self.ativo: int | None = None
        self.visivel: VGroup | None = None
        self.indicador: SurroundingRectangle | None = None

    def _view(self, passo: rec.Step) -> int:
        funcao = rec.funcao_da_linha(passo.linha, passo.modulo)
        return self._por_chave[(funcao.modulo, funcao.nome)]

    def _posicionar(self, indicador, indice: int, linha: int) -> None:
        codigo = self.codigos[indice]
        funcao = self.funcoes[indice]
        pos = max(0, min(linha - funcao.inicio, len(codigo.code_lines) - 1))
        alvo = codigo.code_lines[pos]
        indicador.move_to(alvo.get_center())
        indicador.stretch_to_fit_width(alvo.width + 0.25)
        indicador.stretch_to_fit_height(alvo.height + 0.12)

    def encaixar(self, passo: rec.Step) -> None:
        indice = self._view(passo)
        self.ativo = indice
        self.visivel = self.conteudos[indice]
        self.indicador = self.indicadores[indice]
        self._posicionar(self.indicador, indice, passo.linha)

    def mudou(self, passo: rec.Step) -> bool:
        return self._view(passo) != self.ativo

    def trocar(self, passo: rec.Step) -> tuple[list[Animation], list[Animation]]:
        indice = self._view(passo)
        if indice == self.ativo:
            return [], []

        antigo, antigo_ind = self.visivel, self.indicador
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
        codigo = self.codigos[indice]
        funcao = self.funcoes[indice]
        pos = max(0, min(passo.linha - funcao.inicio, len(codigo.code_lines) - 1))
        alvo = codigo.code_lines[pos]
        return (
            self.indicador.animate.move_to(alvo.get_center())
            .stretch_to_fit_width(alvo.width + 0.25)
            .stretch_to_fit_height(alvo.height + 0.12)
        )


# ---------------------------------------------------------------------------
# StatePanel: linhas fixas, troca sem Transform
# ---------------------------------------------------------------------------


class StatePanel:
    """Painel de N linhas fixas com crossfade curto por linha."""

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
                deslize = UP * 0.15 if i > 0 else ORIGIN
                anims.append(
                    AnimationGroup(
                        FadeOut(antigo, run_time=0.18, shift=deslize),
                        FadeIn(novo, run_time=0.18, shift=deslize),
                    )
                )
            self.linhas[i] = novo
            self.conteudos[i] = texto
            self.cores[i] = cor
            self.fontes[i] = fonte
        return anims


# ---------------------------------------------------------------------------
# Abas de estrutura de dados
# ---------------------------------------------------------------------------


class AbaBase:
    def __init__(self, painel: "EstruturaPanel"):
        self.p = painel
        self.mobjects: list[Mobject] = []

    def todos(self) -> list[Mobject]:
        return list(self.mobjects)

    def limpar(self) -> None:
        self.mobjects = []


class AbaHeap(AbaBase):
    """IndexMinPQ desenhada como árvore binária de slots fixos.

    Raiz = `pq[0]` (menor chave). O slot k tem filhos 2k+1 e 2k+2 e pai
    (k-1)//2. Os slots e as arestas da árvore são fixos; o que se move são as
    entradas do heap, então `swim` (sobe) e `sink` (desce) aparecem como
    movimento real na árvore.

    A chave de cada nó é `(vértice, ocorrência)` para tolerar repetição: com
    o `contains` antigo (baseado em `keys`), o mesmo vértice podia entrar duas
    vezes. Hoje ele lê `qp`, como no Java, e cada vértice aparece uma vez;
    o par (vértice, ocorrência) mantém o painel indexado por slot físico.
    """

    CAPTION = "IndexMinPQ · heap binário em slots · raiz = menor chave · ○ slot vazio"
    N_SLOTS = 15
    RAIO = 0.225
    Y0 = -1.90
    DY = 0.47

    def __init__(self, painel: "EstruturaPanel"):
        super().__init__(painel)
        self.nos: dict[tuple[int, int], Circle] = {}
        self.rotulos: dict[tuple[int, int], Text] = {}
        self.arestas_fixas: VGroup | None = None
        self.slots_vazios: VGroup | None = None
        self.tag_min: Text | None = None
        self.caption: Text | None = None

    def _slot(self, k: int) -> np.ndarray:
        if k <= 0:
            return np.array([self.p.cx, self.Y0, 0.0])
        nivel = (k + 1).bit_length() - 1
        dentro = k - (2 ** nivel - 1)
        largura_nivel = 2 ** nivel
        total = {1: 1.55, 2: 3.90, 3: 5.55}.get(nivel, 5.55)
        x = self.p.cx + (dentro - (largura_nivel - 1) / 2) * (total / largura_nivel)
        return np.array([x, self.Y0 - nivel * self.DY, 0.0])

    def _spec(self, passo: rec.Step) -> dict[tuple[int, int], dict]:
        est = passo.estado
        ordem = list(est.get("pq_ordem", []) or [])
        chaves = est.get("ipq_keys", {}) or {}
        marcados = set(est.get("marcados", []))

        contagem: dict[int, int] = {}
        for v in ordem:
            contagem[v] = contagem.get(v, 0) + 1

        itens: dict[tuple[int, int], dict] = {}
        ocorrencias: dict[int, int] = {}
        for k, v in enumerate(ordem):
            occ = ocorrencias.get(v, 0)
            ocorrencias[v] = occ + 1
            # Vértice já finalizado não pertence mais à IPQ; se ainda aparece
            # em `pq` é lixo do `del_min` (que não limpa keys/qp).
            if v in marcados or k >= self.N_SLOTS:
                continue
            chave = chaves.get(v)
            rotulo = f"{v}:{_fmt_dist(float(chave))}" if isinstance(chave, (int, float)) else f"{v}"
            itens[(v, occ)] = {
                "slot": k,
                "pos": self._slot(k),
                "rotulo": rotulo,
                "raiz": k == 0,
                "repetido": contagem.get(v, 0) > 1,
            }
        return itens

    @staticmethod
    def _cor_borda(item: dict) -> str:
        if item.get("repetido"):
            return COR_REPETIDO
        return WHITE if item["raiz"] else COR_BORDA_NO

    def _largura_borda(self, item: dict) -> float:
        if item.get("repetido"):
            return 2.8
        return 3.0 if item["raiz"] else 2.0

    def _montar_no(self, item: dict) -> tuple[Circle, Text]:
        circ = Circle(
            radius=self.RAIO,
            color=self._cor_borda(item),
            stroke_width=self._largura_borda(item),
            fill_color=COR_NO,
            fill_opacity=1.0,
        ).move_to(item["pos"]).set_z_index(3)
        rot = Text(item["rotulo"], font_size=9, color=WHITE).move_to(item["pos"]).set_z_index(4)
        return circ, rot

    def construir(self, passo: rec.Step) -> list[Mobject]:
        self.caption = Text(self.CAPTION, font_size=11, color=GRAY_A)
        self.caption.move_to([self.p.x0, self.p.y_caption, 0], aligned_edge=LEFT)

        self.arestas_fixas = VGroup(
            *[
                Line(
                    self._slot(k), self._slot(c),
                    color=COR_LINHA_HEAP, stroke_width=2.0,
                ).set_z_index(0)
                for k in range(self.N_SLOTS)
                for c in (2 * k + 1, 2 * k + 2)
                if c < self.N_SLOTS
            ]
        )
        self.slots_vazios = VGroup(
            *[
                Circle(
                    radius=self.RAIO,
                    color=COR_LINHA_HEAP,
                    stroke_width=1.2,
                    stroke_opacity=0.45,
                    fill_opacity=0.0,
                ).move_to(self._slot(k)).set_z_index(1)
                for k in range(self.N_SLOTS)
            ]
        )

        for chave, item in self._spec(passo).items():
            self.nos[chave], self.rotulos[chave] = self._montar_no(item)

        self.tag_min = Text("min", font_size=10, color=WHITE)
        raiz = self._slot(0)
        self.tag_min.move_to([raiz[0] + 0.44, raiz[1], 0])

        self.mobjects = [
            self.caption,
            self.arestas_fixas,
            self.slots_vazios,
            *self.nos.values(),
            *self.rotulos.values(),
            self.tag_min,
        ]
        return self.mobjects

    def sincronizar(self, passo: rec.Step) -> tuple[list[Animation], list[Mobject], list[Mobject]]:
        itens = self._spec(passo)
        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        alvos, atuais = set(itens), set(self.nos)
        for chave in alvos - atuais:
            circ, rot = self._montar_no(itens[chave])
            self.nos[chave], self.rotulos[chave] = circ, rot
            adicionar += [circ, rot]
            anims += [FadeIn(circ, run_time=0.20), FadeIn(rot, run_time=0.20)]
        for chave in atuais - alvos:
            circ, rot = self.nos.pop(chave), self.rotulos.pop(chave)
            remover += [circ, rot]
            anims += [FadeOut(circ, run_time=0.18), FadeOut(rot, run_time=0.18)]

        for chave in alvos & atuais:
            item = itens[chave]
            circ, rot = self.nos[chave], self.rotulos[chave]
            anims.append(circ.animate.move_to(item["pos"]))
            anims.append(rot.animate.move_to(item["pos"]))
            cor_borda = self._cor_borda(item)
            if circ.get_stroke_color() != ManimColor(cor_borda):
                anims.append(circ.animate.set_stroke(cor_borda, width=self._largura_borda(item)))
            if rot.text != item["rotulo"]:
                novo = Text(item["rotulo"], font_size=9, color=WHITE).move_to(item["pos"]).set_z_index(4)
                antigo = rot
                self.rotulos[chave] = novo
                remover.append(antigo)
                adicionar.append(novo)
                anims += [
                    FadeOut(antigo, run_time=0.15, target_position=item["pos"]),
                    FadeIn(novo, run_time=0.15),
                ]

        self.tag_min.move_to([self._slot(0)[0] + 0.44, self._slot(0)[1], 0])
        return anims, adicionar, remover

    def limpar(self) -> None:
        self.mobjects = []
        self.nos.clear()
        self.rotulos.clear()
        self.arestas_fixas = None
        self.slots_vazios = None
        self.tag_min = None
        self.caption = None

    def todos(self) -> list[Mobject]:
        partes = [self.caption] if self.caption is not None else []
        if self.arestas_fixas is not None:
            partes.append(self.arestas_fixas)
        if self.slots_vazios is not None:
            partes.append(self.slots_vazios)
        if self.tag_min is not None:
            partes.append(self.tag_min)
        return [*partes, *self.nos.values(), *self.rotulos.values()]


class AbaArray(AbaBase):
    """Vetor do Dijkstra (`distTo` ou `edgeTo`) como tabela indexada."""

    def __init__(self, painel: "EstruturaPanel", tipo: str):
        super().__init__(painel)
        self.tipo = tipo
        self.chips: dict[int, VGroup] = {}
        self.caption: Text | None = None
        self.nota: Text | None = None
        passo = (painel.x1 - painel.x0) / max(1, rec.V_CANONICO)
        self.chip_l = min(0.92, passo * 0.86)
        self.chip_h = 0.48

    @property
    def caption_texto(self) -> str:
        if self.tipo == "edgeTo":
            return "edgeTo[v] · aresta predecessora no caminho mínimo até v"
        return "distTo[v] · menor distância conhecida da origem até v"

    @property
    def nota_texto(self) -> str:
        if self.tipo == "edgeTo":
            return "verde = predecessor confirmado na SPT · branco = tentativa · cinza = null"
        return "verde = distância ótima · branco = tentativa · cinza = ∞ · borda magenta = vértice ativo"

    def _pos(self, v: int) -> np.ndarray:
        passo = (self.p.x1 - self.p.x0) / max(1, rec.V_CANONICO)
        return np.array(
            [self.p.x0 + (v + 0.5) * passo, self.p.y_topo - 0.52, 0.0]
        )

    def _spec(self, passo: rec.Step) -> dict[int, dict]:
        est = passo.estado
        marcados = set(est.get("marcados", []))
        ativo = est.get("ativo")
        itens: dict[int, dict] = {}
        for v in range(rec.V_CANONICO):
            if self.tipo == "edgeTo":
                edge_to = est.get("edgeTo") or []
                e = edge_to[v] if v < len(edge_to) else None
                if e is None:
                    valor, cor = "-", "#5e6579"
                else:
                    valor = f"{e[0]}→{e[1]}"
                    cor = COR_ACEITA if v in marcados else COR_TENTATIVA
            else:
                dist = est.get("distTo") or []
                d = dist[v] if v < len(dist) else 999999.0
                valor = _fmt_dist(d)
                if d >= 999999.0:
                    cor = "#5e6579"
                elif v in marcados:
                    cor = COR_ACEITA
                else:
                    cor = COR_TENTATIVA
            itens[v] = {
                "texto": valor,
                "cor": cor,
                "ativo": v == ativo,
            }
        return itens

    def _montar_chip(self, v: int, item: dict) -> VGroup:
        caixa = RoundedRectangle(
            corner_radius=0.09,
            width=self.chip_l,
            height=self.chip_h,
            color=COR_EXTRACAO if item["ativo"] else item["cor"],
            stroke_width=2.2 if item["ativo"] else 1.3,
            fill_color=item["cor"],
            fill_opacity=0.16,
        ).set_z_index(3)
        idx = Text(f"[{v}]", font_size=9, color=COR_TEXTO).set_z_index(4)
        val = Text(item["texto"], font_size=10, color=WHITE).set_z_index(4)
        idx.move_to([caixa.get_center()[0], caixa.get_center()[1] + 0.11, 0])
        val.move_to([caixa.get_center()[0], caixa.get_center()[1] - 0.10, 0])
        return VGroup(caixa, idx, val)

    def construir(self, passo: rec.Step) -> list[Mobject]:
        self.caption = Text(self.caption_texto, font_size=12, color=GRAY_A)
        self.caption.move_to([self.p.x0, self.p.y_caption, 0], aligned_edge=LEFT)

        for v, item in self._spec(passo).items():
            self.chips[v] = self._montar_chip(v, item)
            self.chips[v].move_to(self._pos(v))

        self.nota = Text(self.nota_texto, font_size=10, color="#5e6579")
        self.nota.move_to([self.p.x0, self.p.y_base + 0.18, 0], aligned_edge=LEFT)

        self.mobjects = [self.caption, *self.chips.values(), self.nota]
        return self.mobjects

    def sincronizar(self, passo: rec.Step) -> tuple[list[Animation], list[Mobject], list[Mobject]]:
        itens = self._spec(passo)
        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        for v, item in itens.items():
            grupo = self.chips[v]
            caixa, idx, val = grupo[0], grupo[1], grupo[2]
            cor = COR_EXTRACAO if item["ativo"] else item["cor"]
            if caixa.get_stroke_color() != ManimColor(cor):
                anims.append(
                    caixa.animate.set_stroke(
                        cor, width=2.2 if item["ativo"] else 1.3
                    ).set_fill(item["cor"], opacity=0.16)
                )
            if val.text != item["texto"]:
                novo = Text(item["texto"], font_size=10, color=WHITE).set_z_index(4)
                novo.move_to([caixa.get_center()[0], caixa.get_center()[1] - 0.10, 0])
                antigo = val
                grupo[2] = novo
                remover.append(antigo)
                adicionar.append(novo)
                anims += [FadeOut(antigo, run_time=0.15), FadeIn(novo, run_time=0.15)]

        return anims, adicionar, remover

    def limpar(self) -> None:
        self.mobjects = []
        self.chips.clear()
        self.caption = None
        self.nota = None

    def todos(self) -> list[Mobject]:
        partes = [self.caption] if self.caption is not None else []
        if self.nota is not None:
            partes.append(self.nota)
        return [*partes, *self.chips.values()]


class EstruturaPanel:
    """Painel com abas que desenha a estrutura REAL em execução.

    - IndexMinPQ: heap binário em slots fixos (raiz = menor chave);
    - distTo: tabela indexada por vértice;
    - edgeTo: tabela de predecessores (verde = confirmado, branco = tentativa).

    A aba ativa segue o módulo/linha executada. A troca é fade-out total e
    depois fade-in (dois plays), como no painel de código.
    """

    def __init__(self, centro: np.ndarray, largura: float, altura: float):
        self.centro = np.array(centro, dtype=float)

        self.fundo = RoundedRectangle(
            corner_radius=0.15,
            width=largura,
            height=altura,
            color=GRAY_D,
            stroke_width=1.5,
            fill_color=COR_PAINEL,
            fill_opacity=0.9,
        ).move_to(self.centro)

        self.x0 = self.fundo.get_left()[0] + 0.32
        self.x1 = self.fundo.get_right()[0] - 0.30
        self.cx = (self.x0 + self.x1) / 2

        self._aba_alto = 0.32
        self.y_abas_topo = self.fundo.get_top()[1] - 0.13
        self.y_abas_base = self.y_abas_topo - self._aba_alto
        self.y_caption = self.y_abas_base - 0.20
        self.y_topo = self.y_caption - 0.26
        self.y_base = self.fundo.get_bottom()[1] + 0.14

        self.abas_visuais: dict[str, tuple[RoundedRectangle, Text]] = {}
        self._montar_abas()

        self.conteudos = {
            "heap": AbaHeap(self),
            "dt": AbaArray(self, "distTo"),
            "et": AbaArray(self, "edgeTo"),
        }
        self.ativa: str | None = None
        self.mobject = VGroup(
            self.fundo,
            *[m for par in self.abas_visuais.values() for m in par],
        )

    def _montar_abas(self) -> None:
        x = self.x0
        y = self.y_abas_topo - self._aba_alto / 2
        for chave, rotulo in ABAS_DIJKSTRA:
            texto = Text(rotulo, font_size=13)
            largura = texto.width + 0.34
            caixa = RoundedRectangle(
                corner_radius=0.07,
                width=largura,
                height=self._aba_alto,
                color=GRAY_D,
                stroke_width=1.2,
                fill_color=COR_TAB_INATIVA,
                fill_opacity=1.0,
            ).move_to([x + largura / 2, y, 0])
            texto.move_to(caixa.get_center())
            self.abas_visuais[chave] = (caixa, texto)
            x += largura + 0.04

    def _estilo_abas(self, ativa: str, animar: bool) -> list[Animation]:
        anims: list[Animation] = []
        for chave, (caixa, texto) in self.abas_visuais.items():
            on = chave == ativa
            cor_borda = COR_TEXTO if on else GRAY_D
            preenchimento = COR_TAB_ATIVA if on else COR_TAB_INATIVA
            cor_texto = WHITE if on else GRAY_A
            if animar:
                anims += [
                    caixa.animate.set_stroke(cor_borda, width=1.6 if on else 1.2).set_fill(
                        preenchimento, opacity=1.0
                    ),
                    texto.animate.set_color(cor_texto),
                ]
            else:
                caixa.set_stroke(cor_borda, width=1.6 if on else 1.2)
                caixa.set_fill(preenchimento, opacity=1.0)
                texto.set_color(cor_texto)
        return anims

    def _alvo(self, passo: rec.Step) -> str:
        """Aba que corresponde à linha executada (fonte da verdade do trace)."""
        if passo.modulo == "algs4.index_min_pq":
            return "heap"
        if passo.modulo == "algs4.directed_edge":
            return "dt"
        if passo.modulo == "algs4.dijkstra_sp":
            linha = passo.linha
            if linha == 38:                     # edgeTo = [None] * V
                return "et"
            if linha in (39, 40, 41, 42):       # distTo = [inf] * V; distTo[s] = 0
                return "dt"
            if linha in (43, 44, 45, 46):       # cria a IPQ, insere s, while/del_min
                return "heap"
            if linha in (48, 49, 50, 51, 52):   # relax: lê distTo, testa e atualiza
                return "dt"
            if linha == 53:                     # edgeTo[w] = e
                return "et"
            if linha in (54, 55, 57):           # contains/change/insert
                return "heap"
        return self.ativa or "heap"

    def preparar(self, passo: rec.Step) -> list[Mobject]:
        alvo = self._alvo(passo)
        self.ativa = alvo
        self._estilo_abas(alvo, animar=False)
        conteudo = self.conteudos[alvo].construir(passo)
        return [self.mobject, *conteudo]

    def atualizar(self, passo: rec.Step):
        """Devolve (anims, adicionar, remover, troca).

        `troca` é `(sai, entra)`: a cena toca o fade-out, adiciona `entra` e
        só então toca o fade-in — dois plays, nunca duas estruturas no mesmo
        frame. O estilo das abas entra no primeiro play.
        """
        alvo = self._alvo(passo)

        if alvo != self.ativa:
            antigo = self.conteudos[self.ativa]
            sai = [FadeOut(m, run_time=0.18) for m in antigo.todos()]
            sai += self._estilo_abas(alvo, animar=True)
            antigo.limpar()
            self.ativa = alvo
            novos = self.conteudos[alvo].construir(passo)
            return [], [], [], (sai, novos)

        anims, adicionar, remover = self.conteudos[alvo].sincronizar(passo)
        return anims, adicionar, remover, None

    def encerrar(self) -> list[Mobject]:
        if self.ativa is None:
            return []
        return list(self.conteudos[self.ativa].todos())


# ---------------------------------------------------------------------------
# Formatação do painel
# ---------------------------------------------------------------------------


def cor_destaque(passo: rec.Step) -> str:
    status = passo.destaque[3]
    if status == "aceita":
        return COR_ACEITA
    if status in ("rejeitada", "descarte"):
        return COR_DESCARTE
    if status == "extraido":
        return COR_EXTRACAO
    if status in ("decrease_key", "insert", "consulta", "inicio"):
        return COR_DESTAQUE
    return COR_TEXTO


def fmt_spt(estado: dict) -> str:
    n = len(estado.get("spt", []))
    return f"SPT: {n} / {max(0, rec.V_CANONICO - 1)} arestas  |  Custo: {estado.get('custo', 0):g}"


def fmt_ipq(estado: dict) -> str:
    ipq = estado.get("ipq") or {}
    if not ipq:
        return "IndexMinPQ: {}"
    itens = sorted(ipq.items(), key=lambda kv: (kv[1], kv[0]))
    return "IndexMinPQ: {" + ", ".join(f"{v}:{_fmt_dist(k)}" for v, k in itens) + "}"


def fmt_edge_to(estado: dict) -> str:
    edge_to = estado.get("edgeTo") or []
    partes = ["-" if e is None else f"{e[0]}→{e[1]}" for e in edge_to]
    return "edgeTo: [" + ", ".join(partes) + "]"


def fmt_dist_to(estado: dict) -> str:
    dist = estado.get("distTo") or []
    return "distTo: [" + ", ".join(_fmt_dist(d) for d in dist) + "]"


def fmt_marcados(estado: dict) -> str:
    marcados = estado.get("marcados", [])
    conjunto = set(marcados)
    pendentes = [v for v in range(rec.V_CANONICO) if v not in conjunto]
    return (
        "Finalizados: " + (", ".join(map(str, marcados)) or "-")
        + "  |  Pendentes: " + (", ".join(map(str, pendentes)) or "-")
    )


# ---------------------------------------------------------------------------
# Cena base
# ---------------------------------------------------------------------------


class DijkstraExecucaoBase(Scene):
    titulo: str = "Algoritmo de Dijkstra: Execução com IndexMinPQ"
    subtitulo: str = "Single-Source Shortest Path (SSSP) · origem s = 0 · pesos não negativos"
    n_linhas_painel: int = 5
    por_linha: bool = True

    def configurar(self, modelo) -> None:
        self.titulo = modelo.titulo
        self.subtitulo = modelo.subtitulo
        self.n_linhas_painel = modelo.n_linhas_painel
        self.por_linha = modelo.por_linha

    def montar_estrutura(self, legenda: list[tuple[str, str] | tuple[str, str, str]]) -> None:
        self.camera.background_color = COR_FUNDO
        self.passos = rec.coletar_detalhado()

        # Cabeçalho: apenas o título, centralizado (sem subtítulo).
        titulo = Text(self.titulo, font_size=19, color=WHITE, weight=BOLD)
        cabecalho = titulo.move_to(np.array([0.0, 3.74, 0.0]))
        self.add(cabecalho)

        self.codigo = CodePanel()
        self.codigo.encaixar(self.passos[0])

        self.grafo = DirectedGraphView()

        self.painel = StatePanel(
            centro=np.array([3.55, -2.30, 0]),
            largura=6.5,
            altura=2.55,
            n_linhas=self.n_linhas_painel,
        )

        self.estrutura = EstruturaPanel(
            centro=np.array([-3.35, -2.30, 0]),
            largura=6.70,
            altura=2.90,
        )

        self.play(
            FadeIn(self.codigo.mobject, shift=RIGHT),
            FadeIn(self.codigo.visivel),
            FadeIn(self.codigo.indicador),
            run_time=0.8,
        )
        self.play(FadeIn(self.grafo.mobject), run_time=0.8)

        mobs_estrutura = self.estrutura.preparar(self.passos[0])
        self.add(*mobs_estrutura)
        self.play(
            *[FadeIn(m, run_time=0.6) for m in mobs_estrutura],
            run_time=0.6,
        )

        legenda_bloco = self._montar_legenda(legenda)
        self.add(legenda_bloco)

        self.add(*self.painel.iniciar(self.textos_painel(self.passos[0])))
        self.play(FadeIn(legenda_bloco), run_time=0.4)
        self.wait(0.6)

    def limpar(self, run_time: float = 0.5) -> None:
        if self.mobjects:
            self.play(FadeOut(Group(*self.mobjects)), run_time=run_time)
        self.clear()

    def _montar_legenda(self, itens) -> VGroup:
        """Guia visual com fonte única (15) e quebra por largura útil."""
        itens_visuais = []
        for item in itens:
            cor, texto = item[0], item[1]
            forma = item[2] if len(item) > 2 else "dot"
            if forma == "ring":
                marca = Circle(radius=0.075, color=cor, stroke_width=2.6, fill_opacity=0.0)
            else:
                marca = Dot(color=cor, radius=0.075)
            itens_visuais.append(
                VGroup(marca, Text(texto, font_size=15, color=WHITE)).arrange(RIGHT, buff=0.10)
            )

        LARGURA_MAX = 5.05
        BUFF_ITEM = 0.26
        n = len(itens_visuais)

        def largura(i: int, j: int) -> float:
            return sum(it.width for it in itens_visuais[i : j + 1]) + BUFF_ITEM * (j - i)

        melhor = None
        for mascara in range(1 << max(0, n - 1)):
            cortes = [0]
            for k in range(n - 1):
                if mascara & (1 << k):
                    cortes.append(k + 1)
            cortes.append(n)
            larguras = [largura(cortes[k], cortes[k + 1] - 1) for k in range(len(cortes) - 1)]
            if max(larguras) > LARGURA_MAX:
                continue
            chave = (len(larguras), max(larguras))
            if melhor is None or chave < (melhor[0], melhor[1]):
                melhor = (len(larguras), max(larguras), cortes)

        cortes = melhor[2] if melhor is not None else list(range(n + 1))
        linhas = [
            VGroup(*itens_visuais[cortes[k] : cortes[k + 1]]).arrange(RIGHT, buff=BUFF_ITEM)
            for k in range(len(cortes) - 1)
        ]
        bloco = VGroup(*linhas).arrange(DOWN, aligned_edge=LEFT, buff=0.10)
        bloco.next_to(self.grafo.mobject, DOWN, buff=0.14, aligned_edge=LEFT)

        limite = self.painel.fundo.get_top()[1] + 0.08
        if bloco.get_bottom()[1] < limite:
            bloco = VGroup(*linhas).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
            bloco.next_to(self.grafo.mobject, DOWN, buff=0.08, aligned_edge=LEFT)
            if bloco.get_bottom()[1] < limite:
                ancora = bloco.get_corner(UL)
                bloco.scale_to_fit_height(bloco.get_top()[1] - limite)
                bloco.move_to(ancora, aligned_edge=UL)
        return bloco

    def textos_painel(self, passo: rec.Step) -> list[tuple[str, str, int]]:
        est = passo.estado
        return [
            (passo.acao, cor_destaque(passo), 13),
            (fmt_spt(est), WHITE, 15),
            (fmt_ipq(est), "#8d99ae", 12),
            (fmt_edge_to(est), COR_TEXTO, 11),
            (fmt_dist_to(est), GRAY_A, 11),
        ]

    def fechar(self) -> None:
        est = self.passos[-1].estado
        spt = {_chave(e[0], e[1]) for e in est.get("spt", [])}

        # Frame final: só a SPT em verde; tentativas voltam ao cinza.
        # Guard: pode não sobrar nenhuma aresta a pintar (todas já em "fora").
        anims_fim = [
            anim
            for chave, status in self.grafo._status.items()
            if chave not in spt and status != "fora"
            for anim in self.grafo._pintar_aresta(chave[0], chave[1], "fora")
        ]
        if anims_fim:
            self.play(*anims_fim, run_time=0.7)

        textos = [
            (f"Dijkstra concluído: SPT com {len(spt)} arestas, custo {est.get('custo', 0):g}", COR_ACEITA, 15),
            (fmt_dist_to(est), WHITE, 12),
            ("Cada vértice é extraído uma única vez da IndexMinPQ", COR_TEXTO, 12),
            ("Pesos não negativos: a distância extraída é definitiva", GRAY_A, 12),
            (fmt_marcados(est), COR_DESTAQUE, 11),
        ]
        anims_painel = self.painel.atualizar(textos)
        if anims_painel:
            self.play(*anims_painel, run_time=0.6)
        self.wait(2.2)

    def play_step(self, passo: rec.Step) -> None:
        # Troca de função: fade-out total e depois fade-in (dois plays).
        if self.codigo.mudou(passo):
            sai, entra = self.codigo.trocar(passo)
            if sai:
                self.play(*sai)
            if entra:
                self.play(*entra)

        # Estrutura de dados: a aba segue a linha executada. Na troca, o
        # conteúdo antigo sai inteiro e o novo entra em DOIS plays.
        anims_estr, adicionar, remover, troca = self.estrutura.atualizar(passo)
        if troca:
            sai, novos = troca
            if sai:
                self.play(*sai)
            self.add(*novos)
            fade_in = [FadeIn(m, run_time=0.18) for m in novos]
            if fade_in:
                self.play(*fade_in)
            anims_estr = []
        if adicionar:
            self.add(*adicionar)

        anims: list[Animation] = [self.codigo.destacar(passo)]
        anims += self.grafo.animar(passo.destaque, passo.estado)
        anims += self.painel.atualizar(self.textos_painel(passo))
        anims += anims_estr
        if anims:
            self.play(*anims, run_time=0.45)
        if remover:
            self.remove(*remover)
        self.wait(passo.pausa)

    def executar_passos(self) -> list[rec.Step]:
        for passo in self.passos:
            self.play_step(passo)
        return self.passos
