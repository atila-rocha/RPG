"""
Componentes visuais compartilhados pelas animações MST (revisão 2).

Todo o estado exibido vem de `mst_record.Step`. Nenhuma cena calcula
Kruskal/Prim: ela só desenha o que o gravador observou no `algs4`.

Regras de desenho:
- `play_step` altera código, grafo e painel no MESMO `self.play`, e depois
  faz um hold, para não existir frame com estado misturado.
- O painel mostra UMA função por vez (a que contém a linha executada). Na
  troca de função: `Succession(FadeOut, FadeIn)` — o código antigo sai
  inteiro antes de o novo entrar; nunca os dois no mesmo frame.
- Nunca `Transform` entre dois `Text` de conteúdo diferente — era isso que
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

# Entrada repetida no `pq` da IndexMinPQ. Com o `contains` atual (baseado em
# `qp`, como no Java) o mesmo vértice entra uma única vez; a cor fica como
# marcação de slot repetido caso o heap alguma vez mostre duas cópias.
# Laranja fica longe do magenta da extração e do amarelo "em análise".
COR_REPETIDO = "#f9844a"

# Cor própria dos vértices que já estão na árvore. É um verde distinto do
# `COR_ACEITA` das arestas para o guia visual não ter dois itens iguais.
# (Vértices usam marcador em anel; arestas usam ponto cheio.)
COR_NO_ARVORE = "#80ed99"

# Cores de componente do union-find. Ficam no eixo azul/roxo/teal, longe do
# verde "aceita", do vermelho "descartada", do amarelo "em análise" e do
# magenta "extraída" do guia visual — o aluno não confunde componente com
# status de aresta.
PALETA_COMPONENTES = [
    "#4b7bec",  # azul royal
    "#9b59b6",  # roxo
    "#16a085",  # teal
    "#2e86de",  # azul claro
    "#6c5ce7",  # índigo
    "#00a8a8",  # ciano escuro
]

# Layout do grafo de 6 vértices (fallback / rodadas anteriores). Estes são os
# traços de referência; `_escalar_coords` aplica o zoom final e o
# recentraliza na área liberada pela redução do painel de código.
COORDS_6 = {
    0: np.array([1.90, 2.15, 0]),
    1: np.array([4.30, 2.45, 0]),
    2: np.array([3.00, 0.95, 0]),
    3: np.array([6.30, 2.15, 0]),
    4: np.array([5.10, 0.75, 0]),
    5: np.array([6.60, 0.75, 0]),
}

# Layout tuned do tinyEWG (8 vértices), em anel na ordem 0-7-1-5-4-6-3-2.
COORDS_TINYEWG = {
    0: np.array([4.30, 2.85, 0]),
    7: np.array([5.89, 2.47, 0]),
    1: np.array([6.55, 1.55, 0]),
    5: np.array([5.89, 0.63, 0]),
    4: np.array([4.30, 0.25, 0]),
    6: np.array([2.71, 0.63, 0]),
    3: np.array([2.05, 1.55, 0]),
    2: np.array([2.71, 2.47, 0]),
}

_TINYEWG_KEYS = frozenset(
    (min(u, v), max(u, v))
    for u, v in (
        (4, 5), (4, 7), (5, 7), (0, 7), (1, 5), (0, 4), (2, 3), (1, 7),
        (0, 2), (1, 2), (1, 3), (2, 7), (6, 2), (3, 6), (6, 0), (6, 4),
    )
)

# Área útil do grafo: começa onde o painel de código termina (com
# LARGURA_CODIGO = 6,4 a borda direita fica em ~0,48) e vai até a margem
# direita do quadro. Antes o painel ia até 1,38 e o grafo ocupava ~4,8 de
# largura; agora ocupa ~5,6, o que dá espaço para o peso de cada aresta
# ficar na própria aresta sem cobrir as outras.
GRAFO_CENTRO = np.array([3.95, 1.66, 0.0])
GRAFO_ESCALA = 1.20


def _escalar_coords(
    coords: dict[int, np.ndarray],
    escala: float = GRAFO_ESCALA,
    centro: np.ndarray | None = None,
) -> dict[int, np.ndarray]:
    """Amplia o traço de referência em torno do seu centro e recentraliza."""
    pontos = np.array([p[:2] for p in coords.values()])
    centro_antigo = (pontos.min(axis=0) + pontos.max(axis=0)) / 2
    alvo = GRAFO_CENTRO if centro is None else centro
    return {
        i: np.array(
            [
                alvo[0] + (p[0] - centro_antigo[0]) * escala,
                alvo[1] + (p[1] - centro_antigo[1]) * escala,
                0.0,
            ]
        )
        for i, p in coords.items()
    }


def _coords_anel(v: int) -> dict[int, np.ndarray]:
    """Layout genérico (anel) para um grafo de `v` vértices qualquer."""
    rx, ry = 2.80, 1.55
    return {
        i: GRAFO_CENTRO + np.array(
            [rx * np.cos(PI / 2 - 2 * PI * i / v),
             ry * np.sin(PI / 2 - 2 * PI * i / v), 0.0]
        )
        for i in range(v)
    }


def coords_do_grafo() -> dict[int, np.ndarray]:
    """Coordenadas do grafo ativo (tuned p/ 6 e tinyEWG; anel p/ o resto)."""
    v = rec.V_CANONICO
    chaves = frozenset((min(a, b), max(a, b)) for a, b, _ in rec.ARESTAS_CANONICAS)
    if v == len(COORDS_6):
        # 6 vértices: um pouco menor e à esquerda do centro padrão, porque o
        # desenho é mais largo (os 6 nós ocupam 5,64 de largura) e o nó da
        # ponta direita ficaria a 0,07 da borda do quadro.
        return _escalar_coords(COORDS_6, escala=1.15, centro=np.array([3.90, 1.66, 0.0]))
    if v == 8 and chaves == _TINYEWG_KEYS:
        return _escalar_coords(COORDS_TINYEWG)
    return _coords_anel(v)


COORDS = coords_do_grafo()

# Altura total do bloco de código (cabeçalho + código). 3,72 em vez de 3,9
# porque a moldura precisa terminar acima do painel de estado (topo em
# y=-1,025); a diferença é o respiro vertical do QA visual.
ALTURA_CODIGO = 3.72
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
        self.peso_fundos: dict[tuple[int, int], RoundedRectangle] = {}
        self._status: dict[tuple[int, int], str] = {
            _chave(u, v): "fora" for u, v, _ in rec.ARESTAS_CANONICAS
        }

        elementos: list[Mobject] = []

        for u, v, w in rec.ARESTAS_CANONICAS:
            p1, p2 = self.coords[u], self.coords[v]
            linha = Line(p1, p2, color=COR_ARESTA_FORA, stroke_width=3.5, z_index=0)
            lbl = Text(f"{w:g}", font_size=15, color=GRAY_A).set_z_index(3)
            # Fundo opaco: o peso pode ficar sobre uma linha sem ser riscado
            # (com 16 arestas no tinyEWG não há espaço para todos ao lado).
            fundo = RoundedRectangle(
                corner_radius=0.05,
                width=lbl.width + 0.12,
                height=lbl.height + 0.06,
                stroke_width=0,
                fill_color=COR_FUNDO,
                fill_opacity=1.0,
            ).set_z_index(2)
            self.linhas[_chave(u, v)] = linha
            self.pesos[_chave(u, v)] = lbl
            self.peso_fundos[_chave(u, v)] = fundo
            elementos += [linha, fundo, lbl]

        # Os pesos só ganham posição depois de existirem todos: arestas que
        # se cruzam (o anel do tinyEWG tem várias) empilhariam três rótulos
        # no mesmo ponto se cada um usasse um offset fixo.
        self._posicionar_pesos()

        for i, pt in self.coords.items():
            circ = Circle(radius=0.27, color=COR_BORDA_NO, fill_color=COR_NO, fill_opacity=1.0)
            circ.move_to(pt)
            lbl = Text(str(i), font_size=17, color=WHITE).move_to(pt)
            self.circulos[i] = circ
            self._cor_atual[i] = COR_NO
            self.rotulos[i] = lbl
            elementos += [circ, lbl]

        self.mobject = VGroup(*elementos)

    def _posicionar_pesos(self) -> None:
        """Põe cada peso EM CIMA da própria aresta, sem cobrir as outras.

        O peso tem fundo opaco: em cima da própria aresta ele abre um vão no
        traço, que é a convenção de figura de grafo e deixa a associação
        número↔aresta óbvia. O que NÃO pode acontecer é a caixa do número
        encostar em outra aresta (era essa a colisão visível: um `0.38` com a
        linha de outra aresta atravessando o fundo).

        Ordem de preferência para cada aresta (na ordem do arquivo, então o
        resultado é determinístico):
        1. centro da aresta, em cima dela;
        2. deslocando ao longo dela (em direção às pontas);
        3. ao lado dela (perpendicular), com afastamento crescente;
        4. se nada estiver livre, a posição com menos colisões.
        """
        # Retângulo (esq, dir, base, topo) de cada obstáculo.
        caixas: list[tuple[float, float, float, float]] = [
            (pt[0] - 0.34, pt[0] + 0.34, pt[1] - 0.34, pt[1] + 0.34)
            for pt in self.coords.values()
        ]
        segmentos = {
            _chave(u, v): (self.coords[u], self.coords[v])
            for u, v, _w in rec.ARESTAS_CANONICAS
        }
        chaves = [_chave(u, v) for u, v, _w in rec.ARESTAS_CANONICAS]

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
            """Quantos obstáculos a caixa do peso toca (0 = posição livre).

            A aresta do próprio peso não conta: ficar em cima dela é o
            comportamento desejado.
            """
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
            # Fora da área útil (moldura/título/painéis) também é colisão.
            if caixa[0] < 0.90 or caixa[1] > 7.02 or caixa[2] < 0.16 or caixa[3] > 3.42:
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

            # (t ao longo da aresta, afastamento perpendicular com sinal)
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
                # Ordem da lista já é a preferência; `i` só desempata o
                # fallback (menos colisões primeiro, depois o candidato mais
                # próximo do ideal).
                nota = n * 1000 + i
                if n == 0:
                    livre = lbl.get_center()
                    break
                if nota < melhor[0]:
                    melhor = (nota, lbl.get_center())

            if livre is not None:
                lbl.move_to(livre)
            else:  # nenhuma posição limpa: usa a menos ruim
                lbl.move_to(
                    melhor[1] if melhor[1] is not None else meio + diretor * 0.20
                )
            self.peso_fundos[chave].move_to(lbl.get_center())

            caixas.append(
                (
                    lbl.get_left()[0] - 0.05,
                    lbl.get_right()[0] + 0.05,
                    lbl.get_bottom()[1] - 0.05,
                    lbl.get_top()[1] + 0.05,
                )
            )

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
# Painel de código: uma view por função, troca sequencial fade-out/fade-in
# ---------------------------------------------------------------------------


class CodePanel:
    """Painel fixo que mostra a função executada, na íntegra.

    - um `Code` por função executada (algoritmo **e** estruturas auxiliares:
      MinPQ, IndexMinPQ, Edge, UF, EdgeWeightedGraph), todos com a **mesma
      escala**;
    - a moldura é dimensionada uma única vez pela maior view;
    - o indicador é por view: sai junto com o código antigo e entra com o
      novo já posicionado, então nunca existe indicador órfão;
    - troca de função: dois plays (`FadeOut` e depois `FadeIn`) — nunca os
      dois códigos no mesmo frame e nunca `Transform` entre strings
      diferentes. Um `Succession` único não serve: o `Scene.play` adiciona o
      mobject do `FadeIn` à cena no início, com opacidade cheia.
    """

    PADDING_ESQ = 0.30
    PADDING_DIR = 0.34
    PADDING_TOPO = 0.16
    PADDING_BASE = 0.16
    LARGURA_CODIGO = 6.40
    ALTURA_CABECALHO = 0.30
    TEMPO_FADE = 0.18

    def __init__(self, algoritmo: str, altura: float = ALTURA_CODIGO):
        self.algoritmo = algoritmo
        self.funcoes = rec.funcoes_codigo(algoritmo)
        self._por_chave = {(f.modulo, f.nome): i for i, f in enumerate(self.funcoes)}

        # Um `Code` por função, com numeração real do arquivo.
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
            # A moldura nativa do `Code` não acompanha o texto (cortava a
            # última linha e ficava duplicada). Desenhamos a nossa.
            codigo.remove(codigo.background)
            self.codigos.append(codigo)

        # UMA escala por vídeo: fonte constante para não haver zoom na troca.
        escala = min(
            (altura - self.ALTURA_CABECALHO) / max(c.height for c in self.codigos),
            self.LARGURA_CODIGO / max(c.width for c in self.codigos),
        )
        for codigo in self.codigos:
            codigo.scale(escala)

        # Cabeçalho + código, alinhados pelo topo-esquerda.
        self.conteudos: list[VGroup] = []
        for f, codigo in zip(self.funcoes, self.codigos):
            cabecalho = Text(self._rotulo(f), font_size=13, color=COR_TEXTO)
            self.conteudos.append(
                VGroup(cabecalho, codigo).arrange(DOWN, aligned_edge=LEFT, buff=0.10)
            )

        largura = max(g.width for g in self.conteudos)
        altura_max = max(g.height for g in self.conteudos)

        # Moldura calculada UMA vez, pela maior view; nunca é reconstruída.
        self.moldura = RoundedRectangle(
            corner_radius=0.08,
            width=largura + self.PADDING_ESQ + self.PADDING_DIR,
            height=altura_max + self.PADDING_TOPO + self.PADDING_BASE,
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

        # Um indicador por view. Só o da view ativa fica na cena.
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

        # Grupo ESTÁVEL só com a moldura. O conteúdo NÃO entra nele: o
        # `FadeOut` remove de verdade mobjects de cena e, se o código antigo
        # fosse filho do grupo, o cleanup restauraria a opacidade dele
        # (`interpolate(0)`) e deixaria texto fantasma durante o fade-in.
        self.mobject = VGroup(self.moldura)
        self.ativo: int | None = None
        self.visivel: VGroup | None = None
        self.indicador: SurroundingRectangle | None = None

    # -- rótulos -----------------------------------------------------------

    def _rotulo(self, funcao: rec.FuncaoCodigo) -> str:
        return f"{funcao.nome}  ·  {funcao.arquivo}:{funcao.inicio}–{funcao.fim}"

    # -- índice da view ----------------------------------------------------

    def _view(self, passo: rec.Step) -> int:
        funcao = rec.funcao_da_linha(self.algoritmo, passo.linha, passo.modulo)
        return self._por_chave[(funcao.modulo, funcao.nome)]

    def _posicionar(self, indicador, indice: int, linha: int) -> None:
        codigo = self.codigos[indice]
        funcao = self.funcoes[indice]
        pos = max(0, min(linha - funcao.inicio, len(codigo.code_lines) - 1))
        alvo = codigo.code_lines[pos]
        indicador.move_to(alvo.get_center())
        # `set_width`/`set_height` escalam proporcionalmente; para a caixa
        # acompanhar a linha real (inclusive as longas) é preciso esticar
        # cada eixo de forma independente.
        indicador.stretch_to_fit_width(alvo.width + 0.25)
        indicador.stretch_to_fit_height(alvo.height + 0.12)

    # -- montagem / troca --------------------------------------------------

    def encaixar(self, passo: rec.Step) -> None:
        """Primeira montagem: escolhe a view do primeiro passo, sem animação."""
        indice = self._view(passo)
        self.ativo = indice
        self.visivel = self.conteudos[indice]
        self.indicador = self.indicadores[indice]
        self._posicionar(self.indicador, indice, passo.linha)

    def mudou(self, passo: rec.Step) -> bool:
        return self._view(passo) != self.ativo

    def trocar(self, passo: rec.Step) -> tuple[list[Animation], list[Animation]]:
        """Troca de função: fade-out completo **e depois** fade-in.

        Devolve `(sai, entra)` para a cena tocar em DOIS `play` separados.
        Não cabe `Succession` aqui: o `Scene.play` adiciona o mobject do
        `FadeIn` à cena no início do play, com opacidade cheia, e ele
        apareceria durante o fade-out do antigo. Com dois plays, o novo só
        entra na cena quando o antigo já saiu.

        A moldura não participa: fica parada o tempo todo. O código antigo é
        um mobject de cena (não filho da moldura), então o `FadeOut` o retira
        da cena antes do fade-in — sem fantasma e sem dissolver a moldura.
        """
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
        linha = passo.linha
        pos = max(0, min(linha - funcao.inicio, len(codigo.code_lines) - 1))
        alvo = codigo.code_lines[pos]
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
                # linha invisível entre o FadeOut e o FadeIn). O deslize
                # vertical é só nas linhas internas: na primeira (a ação), ele
                # empurrava o texto antigo para fora da moldura do painel.
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
# Painel de estrutura de dados interna (abas, derivadas do trace real)
# ---------------------------------------------------------------------------
#
# O painel mostra UMA estrutura por vez, em abas fixas ("Union-Find",
# "MinPQ", "IndexMinPQ", "edgeTo", "distTo"). A aba ativa acompanha o módulo
# do algs4 que está executando e as linhas que escrevem cada vetor no Prim.
# Na troca de aba o conteúdo antigo sai inteiro e o novo entra em dois plays,
# o mesmo padrão do painel de código — nunca os dois no mesmo frame.

ABAS = {
    "kruskal": (
        ("uf", "Union-Find"),
        ("pq", "MinPQ fila"),
        ("heap", "MinPQ heap"),
    ),
    "lazy": (
        ("pq", "MinPQ fila"),
        ("heap", "MinPQ heap"),
    ),
    "eager": (("heap", "IndexMinPQ"), ("et", "edgeTo"), ("dt", "distTo")),
}

COR_TAB_ATIVA = "#1f2637"
COR_TAB_INATIVA = "#0f111a"
COR_LINHA_HEAP = "#2a2f45"


class AbaUF:
    """Floresta do union-find com layout de árvore.

    A posição de cada vértice é derivada dos pais reais (`uf_id`) a cada
    passo: raízes no topo, filhos abaixo, irmãos lado a lado. Quando uma
    união muda o pai, a subárvore inteira desliza para a nova posição (os
    dois lados "trocam de lugar") em vez de sumir e reaparecer.
    """

    CAPTION = "Union-Find · cor do nó = componente · seta aponta para o pai"
    RAIO = 0.22

    def __init__(self, painel):
        self.p = painel
        self.mobjects: list[Mobject] = []
        self.nos: dict[int, Circle] = {}
        self.rotulos: dict[int, Text] = {}
        self.setas: dict[tuple[int, int], Arrow] = {}
        self.caption: Text | None = None

    # -- layout ------------------------------------------------------------

    def _layout(self, ids: list[int]) -> dict[int, np.ndarray]:
        n = len(ids)
        filhos: dict[int, list[int]] = {v: [] for v in range(n)}
        raizes: list[int] = []
        for v, pai in enumerate(ids):
            if pai == v or not (0 <= pai < n):
                raizes.append(v)
            else:
                filhos[pai].append(v)
        for v in filhos:
            filhos[v].sort()

        folhas: list[int] = []

        def coletar(v: int) -> None:
            if not filhos[v]:
                folhas.append(v)
            else:
                for c in filhos[v]:
                    coletar(c)

        for r in raizes:
            coletar(r)

        passo = (self.p.x1 - self.p.x0) / max(1, len(folhas))
        x_de: dict[int, float] = {}

        def calcular_x(v: int) -> float:
            if v in x_de:
                return x_de[v]
            if not filhos[v]:
                x = self.p.x0 + (folhas.index(v) + 0.5) * passo
            else:
                xs = [calcular_x(c) for c in filhos[v]]
                x = sum(xs) / len(xs)
            x_de[v] = x
            return x

        profundidade: dict[int, int] = {}

        def medir(v: int, d: int) -> None:
            profundidade[v] = d
            for c in filhos[v]:
                medir(c, d + 1)

        for r in raizes:
            medir(r, 0)

        y0 = self.p.y_topo - 0.26
        dy = 0.70
        return {
            v: np.array([calcular_x(v), y0 - profundidade[v] * dy, 0.0])
            for v in range(n)
        }

    # -- construção / sincronização ---------------------------------------

    def _spec(self, passo) -> tuple[dict, dict]:
        est = passo.estado
        ids = list(est.get("uf_id") or [])
        if not ids:
            ids = list(range(rec.V_CANONICO))
        pos = self._layout(ids)

        nos = {
            v: {"pos": pos[v], "cor": self.p._cor_componente(est, v)}
            for v in range(len(ids))
        }
        setas: dict[tuple[int, int], dict] = {}
        for v, pai in enumerate(ids):
            if pai != v and 0 <= pai < len(ids):
                setas[(v, pai)] = {
                    "de": pos[v],
                    "para": pos[pai],
                    "cor": nos[v]["cor"],
                }
        return nos, setas

    def construir(self, passo) -> list[Mobject]:
        nos, setas = self._spec(passo)
        self.caption = Text(self.CAPTION, font_size=12, color=GRAY_A)
        self.caption.move_to([self.p.x0, self.p.y_caption, 0], aligned_edge=LEFT)

        for v, a in nos.items():
            circ = Circle(
                radius=self.RAIO, color=COR_BORDA_NO,
                fill_color=a["cor"], fill_opacity=1.0,
            ).move_to(a["pos"]).set_z_index(3)
            rot = Text(str(v), font_size=14, color=WHITE).move_to(a["pos"]).set_z_index(4)
            self.nos[v] = circ
            self.rotulos[v] = rot

        for (v, pai), s in setas.items():
            self.setas[(v, pai)] = self._seta(s)

        self.mobjects = [
            self.caption,
            *self.setas.values(),
            *self.nos.values(),
            *self.rotulos.values(),
        ]
        return self.mobjects

    @staticmethod
    def _seta(s: dict) -> Arrow:
        # Ponta com tamanho fixo: em nós empilhados na vertical a seta é
        # curta e, com a ponta proporcional ao comprimento, ela sumia.
        seta = Arrow(
            s["de"], s["para"], buff=0.22, color=s["cor"],
            stroke_width=2.6, tip_length=0.13,
            max_tip_length_to_length_ratio=0.90,
        )
        seta.set_z_index(1)
        return seta

    def sincronizar(self, passo) -> tuple[list[Animation], list[Mobject], list[Mobject]]:
        nos, setas = self._spec(passo)
        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        alvos, atuais = set(nos), set(self.nos)
        for v in alvos - atuais:
            a = nos[v]
            circ = Circle(
                radius=self.RAIO, color=COR_BORDA_NO,
                fill_color=a["cor"], fill_opacity=1.0,
            ).move_to(a["pos"]).set_z_index(3)
            rot = Text(str(v), font_size=14, color=WHITE).move_to(a["pos"]).set_z_index(4)
            self.nos[v], self.rotulos[v] = circ, rot
            adicionar += [circ, rot]
            anims += [FadeIn(circ, run_time=0.20), FadeIn(rot, run_time=0.20)]
        for v in atuais - alvos:
            circ, rot = self.nos.pop(v), self.rotulos.pop(v)
            remover += [circ, rot]
            anims += [FadeOut(circ, run_time=0.18), FadeOut(rot, run_time=0.18)]
        for v in alvos & atuais:
            circ, rot = self.nos[v], self.rotulos[v]
            a = nos[v]
            anims.append(circ.animate.move_to(a["pos"]).set_fill(a["cor"], opacity=1.0))
            anims.append(rot.animate.move_to(a["pos"]))

        chaves, existentes = set(setas), set(self.setas)
        for chave in chaves - existentes:
            s = setas[chave]
            seta = self._seta(s)
            self.setas[chave] = seta
            adicionar.append(seta)
            anims.append(FadeIn(seta, run_time=0.20))
        for chave in existentes - chaves:
            seta = self.setas.pop(chave)
            remover.append(seta)
            anims.append(FadeOut(seta, run_time=0.18))
        for chave in chaves & existentes:
            s = setas[chave]
            seta = self.setas[chave]
            anims.append(
                seta.animate.put_start_and_end_on(s["de"], s["para"]).set_color(s["cor"])
            )

        return anims, adicionar, remover

    def limpar(self) -> None:
        self.mobjects = []
        self.nos.clear()
        self.rotulos.clear()
        self.setas.clear()

    def todos(self) -> list[Mobject]:
        partes = [self.caption] if self.caption is not None else []
        return [
            *partes,
            *self.setas.values(),
            *self.nos.values(),
            *self.rotulos.values(),
        ]


class AbaFila:
    """MinPQ de arestas como o VETOR FÍSICO `pq.pq` (heap binário real).

    Mostra a ordem **física** do heap — os índices `pq[0..N-1]` como o
    `algs4` guarda — e não a ordem lógica. `↓ início` fica SEMPRE acima do
    primeiro chip e `↑ fim` SEMPRE abaixo do último.

    É esta visão que mostra `swim`/`sink`: a aresta entra no FIM do vetor e
    sobe (arco para cima) até o pai; quando o mínimo sai, o último assume a
    raiz e desce (arco para baixo). Em lazy, arestas obsoletas ganham risco.
    """

    CHIP_L = 0.70
    CHIP_H = 0.28
    COLS = 8
    TAG_GAP = 0.20
    FONTE = 10

    def __init__(self, painel):
        self.p = painel
        self.mobjects: list[Mobject] = []
        self.chips: dict[tuple[int, int], VGroup] = {}
        self.slots: dict[tuple[int, int], int] = {}
        self.tag_ini: Text | None = None
        self.tag_fim: Text | None = None
        self.caption: Text | None = None
        # O vetor cresce até E (Kruskal guarda TODAS as arestas: 16 no
        # tinyEWG). Numa linha só, 16 chips ficariam com 0,38 de passo e o
        # texto não caberia; então a linha quebra a cada 8 slots, mantendo a
        # MESMA sequência física (índice i -> coluna i % 8, linha i // 8).
        maximo = max(
            (len(p.estado.get("pq_fisico") or []) for p in rec.coletar_detalhado(painel.algoritmo)),
            default=0,
        )
        self.n_linhas = max(1, -(-maximo // self.COLS))

    def _y_linha(self, linha: int) -> float:
        """Centro vertical da linha `linha` dentro da área útil do painel."""
        topo, base = self.p.y_topo, self.p.y_base
        if self.n_linhas == 1:
            return (topo + base) / 2
        # 0,55 de respiro no topo e na base para as tags `↓ início`/`↑ fim`.
        primeira = topo - 0.55
        ultima = base + 0.55
        return primeira + (ultima - primeira) * linha / (self.n_linhas - 1)

    def _caption_texto(self) -> str:
        if self.p.algoritmo == "kruskal":
            return "MinPQ · vetor pq (heap binário) · swim sobe / sink desce"
        return "MinPQ (lazy) · vetor pq (heap binário) · risco = obsoleta"

    def _pos(self, i: int) -> np.ndarray:
        passo = (self.p.x1 - self.p.x0 - self.CHIP_L) / (self.COLS - 1)
        coluna = i % self.COLS
        return np.array(
            [
                self.p.x0 + self.CHIP_L / 2 + coluna * passo,
                self._y_linha(i // self.COLS),
                0.0,
            ]
        )


    def _destacada(self, passo) -> set[int]:
        destaque = passo.destaque
        return (
            set(destaque[1:3])
            if destaque and destaque[0] == "aresta" and len(destaque) >= 3
            else set()
        )

    def _item(self, aresta: tuple[int, int, float], destacada: set[int], marcados: set[int]) -> dict:
        u, v, w = aresta
        obsoleta = (
            self.p.algoritmo != "kruskal"
            and u in marcados and v in marcados
        )
        ativa = {u, v} == destacada
        cor = COR_DESCARTE if obsoleta else (
            COR_ANALISE if ativa else "#b9c0c9"
        )
        return {
            "chave": (u, v),
            "texto": f"{u}-{v} {w:g}",
            "cor": cor,
            "riscada": obsoleta,
        }

    def _spec(self, passo) -> list[dict]:
        """Ordem FÍSICA do vetor `pq.pq` (o heap binário), não a ordenada."""
        est = passo.estado
        fisica = est.get("pq_fisico", [])
        marcados = set(est.get("marcados", []))
        destacada = self._destacada(passo)
        return [self._item(a, destacada, marcados) for a in fisica]

    def _montar_chip(self, texto: str, cor: str) -> VGroup:
        caixa = RoundedRectangle(
            corner_radius=0.09, width=self.CHIP_L, height=self.CHIP_H,
            color=cor, stroke_width=1.8, fill_color=cor, fill_opacity=0.22,
        )
        rotulo = Text(texto, font_size=self.FONTE, color=WHITE).move_to(caixa.get_center())
        risco = Line(
            caixa.get_corner(UL) + RIGHT * 0.09,
            caixa.get_corner(UR) + LEFT * 0.09,
            color="#5e6579", stroke_width=1.8,
        )
        risco.set_stroke(opacity=0.0)
        return VGroup(caixa, rotulo, risco)

    def construir(self, passo) -> list[Mobject]:
        self.caption = Text(self._caption_texto(), font_size=11, color=GRAY_A)
        self.caption.move_to([self.p.x0, self.p.y_caption, 0], aligned_edge=LEFT)

        itens = self._spec(passo)
        for i, item in enumerate(itens):
            item["pos"] = self._pos(i)
            grupo = self._montar_chip(item["texto"], item["cor"])
            grupo.move_to(item["pos"])
            if item["riscada"]:
                grupo[2].set_stroke(opacity=1.0)
            self.chips[item["chave"]] = grupo
            self.slots[item["chave"]] = i

        self.tag_ini = Text("↓ início", font_size=12, color=COR_DESTAQUE)
        self.tag_fim = Text("↑ fim", font_size=12, color=GRAY_A)
        self._posicionar_tags(itens)
        self.tag_ini.set_opacity(1.0 if itens else 0.0)
        self.tag_fim.set_opacity(1.0 if itens else 0.0)

        self.mobjects = [
            self.caption,
            *self.chips.values(),
            self.tag_ini,
            self.tag_fim,
        ]
        return self.mobjects

    def _alvos_tags(self, itens: list[dict]) -> tuple[np.ndarray, np.ndarray]:
        """Posição das tags `início`/`fim`.

        `início` fica SEMPRE acima do primeiro chip, com a seta `↓` apontando
        para ele; `fim` fica SEMPRE abaixo do último chip, com `↑`. Assim as
        duas nunca disputam o mesmo ponto — inclusive com **um** item só.
        """
        if not itens:
            return (
                np.array(
                    [self.p.x0 + self.CHIP_L / 2, self._y_linha(0) + 0.30, 0.0]
                ),
                np.array(
                    [
                        self.p.x1 - self.CHIP_L / 2,
                        self._y_linha(self.n_linhas - 1) - 0.30,
                        0.0,
                    ]
                ),
            )
        y_ini = itens[0]["pos"][1] + self.CHIP_H / 2 + self.TAG_GAP
        y_fim = itens[-1]["pos"][1] - self.CHIP_H / 2 - self.TAG_GAP
        return (
            np.array([itens[0]["pos"][0], y_ini, 0.0]),
            np.array([itens[-1]["pos"][0], y_fim, 0.0]),
        )

    def _posicionar_tags(self, itens: list[dict]) -> None:
        ini, fim = self._alvos_tags(itens)
        self.tag_ini.move_to(ini)
        self.tag_fim.move_to(fim)

    def sincronizar(self, passo) -> tuple[list[Animation], list[Mobject], list[Mobject]]:
        itens = self._spec(passo)
        for i, item in enumerate(itens):
            item["pos"] = self._pos(i)

        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        antigos = dict(self.slots)
        alvos = {item["chave"] for item in itens}
        atuais = set(self.chips)
        for item in itens:
            chave = item["chave"]
            if chave not in self.chips:
                grupo = self._montar_chip(item["texto"], item["cor"])
                grupo.move_to(item["pos"])
                self.chips[chave] = grupo
                adicionar.append(grupo)
                anims.append(FadeIn(grupo, run_time=0.20))
        for chave in atuais - alvos:
            grupo = self.chips.pop(chave)
            self.slots.pop(chave, None)
            remover.append(grupo)
            anims.append(FadeOut(grupo, run_time=0.18))

        for i, item in enumerate(itens):
            chave = item["chave"]
            grupo = self.chips[chave]
            caixa, risco = grupo[0], grupo[2]
            velho = antigos.get(chave)
            if velho is not None and velho != i:
                # índice menor = o nó SUBIU no heap (swim); maior = DESCEU
                # (sink). O arco deixa a direção visível no vídeo.
                arco = -PI / 2 if i < velho else PI / 2
                anims.append(grupo.animate(path_arc=arco).move_to(item["pos"]))
            self.slots[chave] = i
            if caixa.get_stroke_color() != ManimColor(item["cor"]):
                anims.append(
                    caixa.animate.set_stroke(color=item["cor"]).set_fill(
                        item["cor"], opacity=0.22
                    )
                )
            alvo = 1.0 if item["riscada"] else 0.0
            if abs(risco.get_stroke_opacity() - alvo) > 1e-3:
                anims.append(risco.animate.set_stroke(opacity=alvo))

        ini_pos, fim_pos = self._alvos_tags(itens)
        if itens:
            anims += [
                self.tag_ini.animate.move_to(ini_pos).set_opacity(1.0),
                self.tag_fim.animate.move_to(fim_pos).set_opacity(1.0),
            ]
        else:
            anims += [
                self.tag_ini.animate.set_opacity(0.0),
                self.tag_fim.animate.set_opacity(0.0),
            ]

        return anims, adicionar, remover

    def limpar(self) -> None:
        self.mobjects = []
        self.chips.clear()
        self.slots.clear()

    def todos(self) -> list[Mobject]:
        partes = [self.caption] if self.caption is not None else []
        tags = [self.tag_ini, self.tag_fim] if self.tag_ini is not None else []
        return [*partes, *self.chips.values(), *tags]


class AbaHeap:
    """IndexMinPQ desenhada como árvore binária de slots fixos.

    As arestas da árvore são estáticas (o slot k tem filhos 2k+1 e 2k+2);
    o que se move são os vértices entre os slots. Assim `del_min` e
    `decrease_key` aparecem como um heap de verdade: o nó sobe ou desce
    pela árvore, sem "sumir aqui e aparecer ali".
    """

    CAPTION = "IndexMinPQ · heap em slots (○ vazio · ● vértice:chave · laranja = repetido)"
    N_SLOTS = 7
    RAIO = 0.30
    Y0 = -1.98
    DY = 0.62

    def __init__(self, painel):
        self.p = painel
        self.mobjects: list[Mobject] = []
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
        total = {1: 1.55, 2: 4.40}.get(nivel, 5.60)
        x = self.p.cx + (dentro - (largura_nivel - 1) / 2) * (total / largura_nivel)
        return np.array([x, self.Y0 - nivel * self.DY, 0.0])

    def _spec(self, passo) -> dict[tuple[int, int], dict]:
        """Entradas físicas do heap, uma por SLOT (não por vértice).

        A chave é `(vértice, ocorrência)`, não só o vértice: o `contains` do
        `algs4` pode deixar o mesmo vértice entrar duas vezes (bug real da
        biblioteca). Com chave por vértice, a segunda entrada sobrescrevia a
        primeira e a raiz "sumia" do painel. Agora as duas aparecem em slots
        diferentes, como estão de fato em `pq.pq`.
        """
        est = passo.estado
        ordem = est.get("pq_ordem", [])
        chaves = est.get("ipq_keys", {})
        marcados = set(est.get("marcados", []))
        # Uma entrada por SLOT: o painel reflete a posição física em `pq.pq`.
        # Com o `contains` atual cada vértice aparece uma vez; se o mesmo
        # vértice surgir duas vezes, as cópias são marcadas para o aluno ver
        # que a repetição é do estado real, não do desenho.
        contagem: dict[int, int] = {}
        for v in ordem:
            contagem[v] = contagem.get(v, 0) + 1
        nos: dict[tuple[int, int], dict] = {}
        ocorrencias: dict[int, int] = {}
        for k, v in enumerate(ordem):
            occ = ocorrencias.get(v, 0)
            ocorrencias[v] = occ + 1
            if v in marcados or k >= self.N_SLOTS:
                continue
            chave = chaves.get(v)
            if isinstance(chave, (int, float)):
                rotulo = f"{v}:{chave:g}"
            else:
                rotulo = f"{v}"
            nos[(v, occ)] = {
                "slot": k,
                "pos": self._slot(k),
                "rotulo": rotulo,
                "raiz": k == 0,
                "repetido": contagem.get(v, 0) > 1,
            }
        return nos

    @staticmethod
    def _cor_borda(item: dict) -> str:
        """Borda laranja = entrada repetida; branca = raiz; senão padrão."""
        if item.get("repetido"):
            return COR_REPETIDO
        return WHITE if item["raiz"] else COR_BORDA_NO

    @staticmethod
    def _largura_borda(item: dict) -> float:
        if item.get("repetido"):
            return 2.8
        return 3.0 if item["raiz"] else 2.0

    def construir(self, passo) -> list[Mobject]:
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

        # Slots vazios: posições do heap, NÃO entradas da IPQ. Ficam como
        # círculos apagados para o aluno ver que a árvore é o "endereço" do
        # heap (pai em (k-1)//2, filhos em 2k+1/2k+2), e não arestas criadas.
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

        nos = self._spec(passo)
        for chave, a in nos.items():
            circ = Circle(
                radius=self.RAIO,
                color=self._cor_borda(a),
                stroke_width=self._largura_borda(a),
                fill_color=COR_NO,
                fill_opacity=1.0,
            ).move_to(a["pos"]).set_z_index(3)
            rot = Text(a["rotulo"], font_size=11, color=WHITE).move_to(a["pos"]).set_z_index(4)
            self.nos[chave], self.rotulos[chave] = circ, rot

        self.tag_min = Text("min", font_size=11, color=WHITE)
        raiz = self._slot(0)
        self.tag_min.move_to([raiz[0] + 0.50, raiz[1], 0])

        self.mobjects = [
            self.caption,
            self.arestas_fixas,
            self.slots_vazios,
            *self.nos.values(),
            *self.rotulos.values(),
            self.tag_min,
        ]
        return self.mobjects

    def sincronizar(self, passo) -> tuple[list[Animation], list[Mobject], list[Mobject]]:
        nos = self._spec(passo)
        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        alvos, atuais = set(nos), set(self.nos)
        for v in alvos - atuais:
            a = nos[v]
            circ = Circle(
                radius=self.RAIO,
                color=self._cor_borda(a),
                stroke_width=self._largura_borda(a),
                fill_color=COR_NO,
                fill_opacity=1.0,
            ).move_to(a["pos"]).set_z_index(3)
            rot = Text(a["rotulo"], font_size=11, color=WHITE).move_to(a["pos"]).set_z_index(4)
            self.nos[v], self.rotulos[v] = circ, rot
            adicionar += [circ, rot]
            anims += [FadeIn(circ, run_time=0.20), FadeIn(rot, run_time=0.20)]
        for v in atuais - alvos:
            circ, rot = self.nos.pop(v), self.rotulos.pop(v)
            remover += [circ, rot]
            anims += [FadeOut(circ, run_time=0.18), FadeOut(rot, run_time=0.18)]
        for v in alvos & atuais:
            a = nos[v]
            circ, rot = self.nos[v], self.rotulos[v]
            anims.append(circ.animate.move_to(a["pos"]))
            anims.append(rot.animate.move_to(a["pos"]))
            cor_borda = self._cor_borda(a)
            if circ.get_stroke_color() != ManimColor(cor_borda):
                anims.append(
                    circ.animate.set_stroke(cor_borda, width=self._largura_borda(a))
                )
            if rot.text != a["rotulo"]:
                # Valor mudou (decrease_key): troca só o rótulo, no mesmo
                # lugar, para não parecer que o nó foi para outro slot.
                novo = Text(a["rotulo"], font_size=11, color=WHITE).move_to(a["pos"]).set_z_index(4)
                antigo = rot
                self.rotulos[v] = novo
                remover.append(antigo)
                adicionar.append(novo)
                anims += [
                    FadeOut(antigo, run_time=0.15, target_position=a["pos"]),
                    FadeIn(novo, run_time=0.15),
                ]

        self.tag_min.move_to([self._slot(0)[0] + 0.50, self._slot(0)[1], 0])
        return anims, adicionar, remover

    def limpar(self) -> None:
        self.mobjects = []
        self.nos.clear()
        self.rotulos.clear()
        self.arestas_fixas = None
        self.slots_vazios = None

    def todos(self) -> list[Mobject]:
        partes = [self.caption] if self.caption is not None else []
        if self.arestas_fixas is not None:
            partes.append(self.arestas_fixas)
        if self.slots_vazios is not None:
            partes.append(self.slots_vazios)
        if self.tag_min is not None:
            partes.append(self.tag_min)
        return [
            *partes,
            *self.nos.values(),
            *self.rotulos.values(),
        ]


class AbaHeapArvore:
    """MinPQ de arestas desenhada como ÁRVORE binária (heap) em slots fixos.

    Raiz é `pq[0]` (índice 0, como no `algs4-py`); o slot k tem filhos
    2k+1 e 2k+2 e pai (k-1)//2. Fixar os slots e as arestas da árvore faz o
    `swim` (a aresta SOBE em direção à raiz) e o `sink` (a aresta DESCE)
    aparecerem como movimento real na árvore, e não como "some aqui e
    aparece ali".

    Serve para Kruskal e Prim Lazy (MinPQ de arestas); o IndexMinPQ do
    Eager segue usando `AbaHeap`.
    """

    N_SLOTS = 15
    RAIO = 0.26
    Y0 = -2.00
    DY = 0.42

    def __init__(self, painel):
        self.p = painel
        self.mobjects: list[Mobject] = []
        self.chips: dict[tuple[int, int], VGroup] = {}
        self.slots: dict[tuple[int, int], int] = {}
        self.arestas_fixas: VGroup | None = None
        self.slots_vazios: VGroup | None = None
        self.tag_min: Text | None = None
        self.caption: Text | None = None

    @property
    def _caption_texto(self) -> str:
        return "MinPQ · árvore binária: raiz = menor · pai ≤ filhos"

    def _slot(self, k: int) -> np.ndarray:
        """Posição do slot k (índice 0). Nível g = quantidade de bis no índice."""
        if k <= 0:
            return np.array([self.p.cx, self.Y0, 0.0])
        nivel = (k + 1).bit_length() - 1
        dentro = k - (2 ** nivel - 1)
        largura_nivel = 2 ** nivel
        total = {0: 0.0, 1: 1.8, 2: 3.6, 3: 5.6}.get(nivel, 5.6)
        x = self.p.cx + (dentro - (largura_nivel - 1) / 2) * (total / largura_nivel)
        return np.array([x, self.Y0 - nivel * self.DY, 0.0])

    def _destacada(self, passo) -> set[int]:
        d = passo.destaque
        return (
            set(d[1:3])
            if d and d[0] == "aresta" and len(d) >= 3
            else set()
        )

    def _spec(self, passo) -> dict[tuple[int, int], dict]:
        est = passo.estado
        fis = list(est.get("pq_fisico", []) or [])
        marcados = set(est.get("marcados", []))
        destacada = self._destacada(passo)
        itens: dict[tuple[int, int], dict] = {}
        for k, a in enumerate(fis):
            if k >= self.N_SLOTS:
                break
            u, v, w = a
            obsoleta = (
                self.p.algoritmo != "kruskal"
                and u in marcados and v in marcados
            )
            ativa = {u, v} == destacada
            cor = COR_DESCARTE if obsoleta else (
                COR_ANALISE if ativa else "#b9c0c9"
            )
            chave = _chave(u, v)
            itens[chave] = {
                "slot": k,
                "pos": self._slot(k),
                "texto": f"{u}-{v} {w:g}",
                "cor": cor,
                "riscada": obsoleta,
                "raiz": k == 0,
            }
        return itens

    def _montar_chip(self, item: dict) -> VGroup:
        caixa = RoundedRectangle(
            corner_radius=0.09, width=0.70, height=0.28,
            color=item["cor"], stroke_width=2.2 if item["raiz"] else 1.5,
            fill_color=item["cor"], fill_opacity=0.22,
        ).set_z_index(4)
        rotulo = Text(item["texto"], font_size=10, color=WHITE)
        rotulo.move_to(caixa.get_center()).set_z_index(5)
        risco = Line(
            caixa.get_corner(UL) + RIGHT * 0.08,
            caixa.get_corner(UR) + LEFT * 0.08,
            color="#5e6579", stroke_width=1.6,
        )
        risco.set_stroke(opacity=0.0)
        return VGroup(caixa, rotulo, risco)

    def construir(self, passo) -> list[Mobject]:
        self.caption = Text(self._caption_texto, font_size=11, color=GRAY_A)
        self.caption.move_to([self.p.x0, self.p.y_caption, 0], aligned_edge=LEFT)

        # Arestas fixas da árvore (slot k -> filhos 2k+1/2k+2).
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

        # Slots vazios: posições do heap (endereço), não arestas criadas.
        self.slots_vazios = VGroup(
            *[
                Circle(
                    radius=self.RAIO, color=COR_LINHA_HEAP,
                    stroke_width=1.2, stroke_opacity=0.45, fill_opacity=0.0,
                ).move_to(self._slot(k)).set_z_index(1)
                for k in range(self.N_SLOTS)
            ]
        )

        itens = self._spec(passo)
        for chave, item in itens.items():
            grupo = self._montar_chip(item)
            grupo.move_to(item["pos"])
            if item["riscada"]:
                grupo[2].set_stroke(opacity=1.0)
            self.chips[chave] = grupo
            self.slots[chave] = item["slot"]

        self.tag_min = Text("min", font_size=11, color=WHITE)
        raiz = self._slot(0)
        self.tag_min.move_to([raiz[0] + 0.56, raiz[1], 0])

        self.mobjects = [
            self.caption,
            self.arestas_fixas,
            self.slots_vazios,
            *self.chips.values(),
            self.tag_min,
        ]
        return self.mobjects

    def sincronizar(self, passo) -> tuple[list[Animation], list[Mobject], list[Mobject]]:
        itens = self._spec(passo)
        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        alvos, atuais = set(itens), set(self.chips)
        for chave in alvos - atuais:
            grupo = self._montar_chip(itens[chave])
            grupo.move_to(itens[chave]["pos"])
            self.chips[chave] = grupo
            self.slots[chave] = itens[chave]["slot"]
            adicionar.append(grupo)
            anims.append(FadeIn(grupo, run_time=0.20))
        for chave in atuais - alvos:
            grupo = self.chips.pop(chave)
            self.slots.pop(chave, None)
            remover.append(grupo)
            anims.append(FadeOut(grupo, run_time=0.18))

        for chave, item in itens.items():
            grupo = self.chips[chave]
            velho = self.slots.get(chave)
            novo = item["slot"]
            if velho is not None and velho != novo:
                # índice menor = aresta SUBIU (swim); maior = DESCEU (sink).
                arco = -PI / 2 if novo < velho else PI / 2
                anims.append(grupo.animate(path_arc=arco).move_to(item["pos"]))
            self.slots[chave] = novo
            caixa, rotulo, risco = grupo
            if caixa.get_stroke_color() != ManimColor(item["cor"]):
                anims.append(
                    caixa.animate.set_stroke(
                        item["cor"], width=2.2 if item["raiz"] else 1.5
                    ).set_fill(item["cor"], opacity=0.22)
                )
            if rotulo.text != item["texto"]:
                novo_t = Text(item["texto"], font_size=10, color=WHITE)
                novo_t.move_to(caixa.get_center()).set_z_index(5)
                remover.append(rotulo)
                adicionar.append(novo_t)
                grupo[1] = novo_t
                anims += [
                    FadeOut(rotulo, run_time=0.15, target_position=caixa.get_center()),
                    FadeIn(novo_t, run_time=0.15),
                ]
            alvo = 1.0 if item["riscada"] else 0.0
            if abs(risco.get_stroke_opacity() - alvo) > 1e-3:
                anims.append(risco.animate.set_stroke(opacity=alvo))

        self.tag_min.move_to([self._slot(0)[0] + 0.56, self._slot(0)[1], 0])
        return anims, adicionar, remover

    def limpar(self) -> None:
        self.mobjects = []
        self.chips.clear()
        self.slots.clear()
        self.arestas_fixas = None
        self.slots_vazios = None
        self.tag_min = None

    def todos(self) -> list[Mobject]:
        partes = [self.caption] if self.caption is not None else []
        if self.arestas_fixas is not None:
            partes.append(self.arestas_fixas)
        if self.slots_vazios is not None:
            partes.append(self.slots_vazios)
        if self.tag_min is not None:
            partes.append(self.tag_min)
        return [*partes, *self.chips.values()]


class AbaArray:
    """Vetor do Prim (`edgeTo` ou `distTo`) como tabela indexada por vértice."""

    CHIP_L = 0.90
    CHIP_H = 0.38

    def __init__(self, painel, tipo: str):
        self.p = painel
        self.tipo = tipo
        self.mobjects: list[Mobject] = []
        self.chips: dict[int, VGroup] = {}
        self.caption: Text | None = None
        # Em V grande (8 no tinyEWG) o chip de 0,90 sobreporia o vizinho.
        passo = (painel.x1 - painel.x0) / rec.V_CANONICO
        self.chip_l = min(self.CHIP_L, passo * 0.88)

    @property
    def caption_texto(self) -> str:
        if self.tipo == "edgeTo":
            return "edgeTo[v] · aresta que liga v à árvore"
        return "distTo[v] · menor peso conhecido até v"

    def _pos(self, v: int) -> np.ndarray:
        passo = (self.p.x1 - self.p.x0) / rec.V_CANONICO
        return np.array(
            [
                self.p.x0 + (v + 0.5) * passo,
                self.p.y_topo - 0.72,
                0.0,
            ]
        )

    def _spec(self, passo) -> dict[int, dict]:
        est = passo.estado
        itens: dict[int, dict] = {}
        for v in range(rec.V_CANONICO):
            if self.tipo == "edgeTo":
                edge_to = est.get("edgeTo") or []
                e = edge_to[v] if v < len(edge_to) else None
                valor = "-" if e is None else f"{e[0]}-{e[1]}"
                cor = COR_ACEITA if e is not None else "#5e6579"
            else:
                dist = est.get("distTo") or []
                d = dist[v] if v < len(dist) else INF
                valor = "inf" if d == INF else f"{d:g}"
                cor = COR_TEXTO if d != INF else "#5e6579"
            itens[v] = {"texto": f"{v}: {valor}", "cor": cor}
        return itens

    def _montar_chip(self, texto: str, cor: str) -> VGroup:
        caixa = RoundedRectangle(
            corner_radius=0.10, width=self.chip_l, height=self.CHIP_H,
            color=cor, stroke_width=1.8, fill_color=cor, fill_opacity=0.18,
        )
        rotulo = Text(texto, font_size=11, color=WHITE).move_to(caixa.get_center())
        return VGroup(caixa, rotulo)

    def construir(self, passo) -> list[Mobject]:
        self.caption = Text(self.caption_texto, font_size=12, color=GRAY_A)
        self.caption.move_to([self.p.x0, self.p.y_caption, 0], aligned_edge=LEFT)
        for v, item in self._spec(passo).items():
            grupo = self._montar_chip(item["texto"], item["cor"])
            grupo.move_to(self._pos(v))
            self.chips[v] = grupo
        self.mobjects = [self.caption, *self.chips.values()]
        return self.mobjects

    def sincronizar(self, passo) -> tuple[list[Animation], list[Mobject], list[Mobject]]:
        itens = self._spec(passo)
        anims: list[Animation] = []
        adicionar: list[Mobject] = []
        remover: list[Mobject] = []

        for v, item in itens.items():
            grupo = self.chips[v]
            caixa, rotulo = grupo[0], grupo[1]
            if caixa.get_stroke_color() != ManimColor(item["cor"]):
                anims.append(
                    caixa.animate.set_stroke(item["cor"]).set_fill(
                        item["cor"], opacity=0.18
                    )
                )
            if rotulo.text != item["texto"]:
                novo = Text(item["texto"], font_size=12, color=WHITE)
                novo.move_to(caixa.get_center())
                remover.append(rotulo)
                adicionar.append(novo)
                grupo[1] = novo
                anims += [FadeOut(rotulo, run_time=0.15), FadeIn(novo, run_time=0.15)]

        return anims, adicionar, remover

    def limpar(self) -> None:
        self.mobjects = []
        self.chips.clear()

    def todos(self) -> list[Mobject]:
        partes = [self.caption] if self.caption is not None else []
        return [*partes, *self.chips.values()]


class EstruturaPanel:
    """Painel com abas que desenha a estrutura REAL em execução.

    Todo o conteúdo vem de `Step.estado` (nunca fabricado):

    - kruskal: floresta union-find (layout de árvore; nós deslizam quando o
      pai muda) e MinPQ em fila ordenada, com início/fim marcados;
    - lazy: MinPQ em fila ordenada, com obsoletas riscadas;
    - eager: IndexMinPQ como heap binário em slots fixos, `edgeTo` e
      `distTo` como tabelas indexadas por vértice.

    A aba ativa segue o módulo/linha executada; a troca é fade-out total e
    depois fade-in (dois plays), como no painel de código.
    """

    def __init__(
        self,
        algoritmo: str,
        centro: np.ndarray,
        largura: float,
        altura: float,
    ):
        self.algoritmo = algoritmo
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

        heap_cls = AbaHeap if self.algoritmo == "eager" else AbaHeapArvore
        self.conteudos = {
            "uf": AbaUF(self),
            "pq": AbaFila(self),
            "heap": heap_cls(self),
            "et": AbaArray(self, "edgeTo"),
            "dt": AbaArray(self, "distTo"),
        }
        self.ativa: str | None = None
        self.mobject = VGroup(
            self.fundo,
            *[m for par in self.abas_visuais.values() for m in par],
        )

    # ------------------------------------------------------------- abas

    def _cor_componente(self, estado: dict, v: int) -> str:
        for grupo in estado.get("componentes", []):
            if v in grupo:
                return PALETA_COMPONENTES[min(grupo) % len(PALETA_COMPONENTES)]
        return COR_BORDA_NO

    def _montar_abas(self) -> None:
        x = self.x0
        y = self.y_abas_topo - self._aba_alto / 2
        for chave, rotulo in ABAS[self.algoritmo]:
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
                    caixa.animate.set_stroke(
                        cor_borda, width=1.6 if on else 1.2
                    ).set_fill(preenchimento, opacity=1.0),
                    texto.animate.set_color(cor_texto),
                ]
            else:
                caixa.set_stroke(cor_borda, width=1.6 if on else 1.2)
                caixa.set_fill(preenchimento, opacity=1.0)
                texto.set_color(cor_texto)
        return anims

    # ------------------------------------------------------- seleção de aba

    def _alvo(self, passo) -> str:
        # Kruskal e Prim Lazy compartilham a MinPQ de arestas: enquanto a
        # função interna do heap mexe na ordem (swim/sink) mostramos a aba
        # "heap" (árvore); insert/del_min/is_empty mostram a fila ("pq").
        if self.algoritmo in ("kruskal", "lazy"):
            if passo.modulo == "algs4.min_pq":
                # MinPQ.swim: 26-31 · MinPQ.sink: 32-fim
                if passo.linha >= 26:
                    return "heap"
                return "pq"
        if self.algoritmo == "lazy":
            return "pq"

        if self.algoritmo == "eager":
            if passo.modulo == "algs4.index_min_pq":
                return "heap"
            if passo.modulo == "algs4.prim_mst":
                if passo.linha in (67, 68):
                    return "dt"
                if passo.linha == 69:
                    return "et"
                if passo.linha in (55, 56, 58, 70, 71, 73):
                    return "heap"
            return self.ativa or "heap"

        # kruskal
        if passo.modulo == "algs4.uf":
            return "uf"
        if passo.modulo == "algs4.min_pq":
            return "pq"
        if passo.modulo == "algs4.kruskal_mst":
            if passo.linha in (55, 56):
                return "pq"
            if passo.linha in (59, 60, 61):
                return "uf"
        return self.ativa or "uf"

    # --------------------------------------------------------- primeiro frame

    def preparar(self, passo) -> list[Mobject]:
        alvo = self._alvo(passo)
        self.ativa = alvo
        self._estilo_abas(alvo, animar=False)
        conteudo = self.conteudos[alvo].construir(passo)
        return [self.mobject, *conteudo]

    # --------------------------------------------------------- atualização

    def atualizar(self, passo):
        """Devolve (anims, adicionar, remover, troca).

        `troca`, quando não é None, é `(sai, entra)`: a cena deve tocar o
        fade-out, adicionar `entra` e só então tocar o fade-in — em dois
        plays, para nunca haver duas estruturas no mesmo frame.
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
        """Todos os mobjects do conteúdo da aba ativa (para limpar a cena)."""
        if self.ativa is None:
            return []
        return list(self.conteudos[self.ativa].todos())



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
    return f"MST: {n} / {rec.V_CANONICO - 1} arestas  |  Custo: {estado['custo']:g}"


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

        titulo = Text(self.titulo, font_size=20, color=WHITE, weight=BOLD)
        titulo.to_edge(UP, buff=0.08)
        self.add(titulo)

        self.codigo = CodePanel(self.algoritmo)
        # O indicador nasce na primeira linha exibida; sem isso a cena abre
        # destacando `class KruskalMST:` (linha 46), que nunca executa.
        self.codigo.encaixar(self.passos[0])

        self.grafo = GraphView()

        self.painel = StatePanel(
            centro=np.array([3.55, -2.30, 0]),
            largura=6.5,
            altura=2.55,
            n_linhas=self.n_linhas_painel,
        )

        # Painel de estrutura de dados (abas UF/MinPQ/Heap/edgeTo/distTo) na
        # faixa embaixo do código. A folga entre os dois é o que impede o
        # balão de código de encostar no painel (ver `CodePanel`/`altura`).
        self.estrutura = EstruturaPanel(
            self.algoritmo,
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

        # Estado inicial da estrutura, desenhado sem animar transições.
        mobs_estrutura = self.estrutura.preparar(self.passos[0])
        self.add(*mobs_estrutura)
        self.play(
            *[FadeIn(m, run_time=0.6) for m in mobs_estrutura],
            run_time=0.6,
        )

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
        """Monta o guia visual com fonte única e legível.

        Cada item é `(cor, texto)` ou `(cor, texto, forma)`. Todos usam a
        MESMA fonte (15) e o mesmo tamanho de marca. As linhas são quebradas
        por largura útil: nenhuma linha é escalada, então nenhum item fica com
        fonte menor que os outros (era o defeito do `scale_to_fit_width`).
        """
        itens_visuais = []
        for item in itens:
            cor, texto = item[0], item[1]
            forma = item[2] if len(item) > 2 else "dot"
            if forma == "ring":
                marca = Circle(
                    radius=0.075,
                    color=cor,
                    stroke_width=2.6,
                    fill_opacity=0.0,
                )
            else:
                marca = Dot(color=cor, radius=0.075)
            itens_visuais.append(
                VGroup(marca, Text(texto, font_size=15, color=WHITE)).arrange(
                    RIGHT, buff=0.10
                )
            )

        # Distribuição em linhas por partição ótima: todas as linhas cabem em
        # LARGURA_MAX (a faixa útil embaixo do grafo tem ~5,2, x 1,63..6,9) e,
        # entre as opções com o menor número de linhas, escolhe a de menor
        # largura máxima. Nenhuma linha é escalada — a fonte é 15 em todas.
        LARGURA_MAX = 5.05
        BUFF_ITEM = 0.26
        n = len(itens_visuais)

        def largura(i: int, j: int) -> float:
            return sum(it.width for it in itens_visuais[i : j + 1]) + BUFF_ITEM * (j - i)

        melhor: tuple[int, float, list[int]] | None = None
        # n <= 6: 2^(n-1) partições, sem custo.
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

        if melhor is None:
            # Rótulos longos demais para a faixa: mantém uma linha por item
            # (ainda sem reduzir a fonte) e deixa o chamador encurtar o texto.
            cortes = list(range(n + 1))
        else:
            cortes = melhor[2]

        linhas = [
            VGroup(*itens_visuais[cortes[k] : cortes[k + 1]]).arrange(
                RIGHT, buff=BUFF_ITEM
            )
            for k in range(len(cortes) - 1)
        ]

        # O Prim Lazy tem 6 itens → 3 linhas, e com o espaçamento padrão
        # (0,10) a última linha cruzava a borda do painel de estado. Só nesse
        # caso o bloco é recomprimido (linhas mais juntas e mais perto do
        # grafo); as legendas de 2 linhas ficam exatamente como estavam.
        bloco = VGroup(*linhas).arrange(DOWN, aligned_edge=LEFT, buff=0.10)
        bloco.next_to(self.grafo.mobject, DOWN, buff=0.14, aligned_edge=LEFT)

        limite = self.painel.fundo.get_top()[1] + 0.08
        if bloco.get_bottom()[1] < limite:
            bloco = VGroup(*linhas).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
            bloco.next_to(self.grafo.mobject, DOWN, buff=0.08, aligned_edge=LEFT)
            if bloco.get_bottom()[1] < limite:
                # Rede de segurança para legendas ainda maiores: reduz o
                # bloco inteiro, mantendo todos os itens com a mesma fonte.
                ancora = bloco.get_corner(UL)
                bloco.scale_to_fit_height(bloco.get_top()[1] - limite)
                bloco.move_to(ancora, aligned_edge=UL)
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
                (f"MST: {len(est['mst'])} / {rec.V_CANONICO - 1} arestas  |  Custo: {est['custo']:g}", WHITE, 15),
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
                (f"MST concluída: {len(est['mst'])} arestas, custo {est['custo']:g}", COR_ACEITA, 15),
                (fmt_fila(est), "#8d99ae", 12),
                (fmt_componentes(est), GRAY_A, 12),
                ("Um único componente: a árvore conecta todos os vértices", COR_TEXTO, 13),
            ]
        elif self.algoritmo == "lazy":
            textos = [
                (f"MST concluída: {len(est['mst'])} arestas, custo {est['custo']:g}", COR_ACEITA, 15),
                ("A MinPQ foi drenada: nenhuma aresta sobrou", WHITE, 13),
                ("Arestas obsoletas foram descartadas por continue", COR_DESCARTE, 12),
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
            n_arvore = sum(1 for e in est["edgeTo"] if e is not None)
            textos = [
                (f"MST concluída: {n_arvore} arestas, custo {est['custo']:g}", COR_ACEITA, 15),
                ("Um item por vértice na IPQ; nenhuma aresta obsoleta guardada", WHITE, 12),
                (fmt_edge_to(est), COR_TEXTO, 11),
                (fmt_dist_to(est), GRAY_A, 11),
                (f"Árvore confirmada em edgeTo: {n_arvore} arestas", COR_DESTAQUE, 12),
            ]

        self.play(*self.painel.atualizar(textos), run_time=0.6)
        self.wait(2.2)

    # -- o único ponto de atualização --------------------------------------

    def play_step(self, passo: rec.Step) -> None:
        # Troca de função: sai a antiga, entra a nova, e SÓ DEPOIS o passo
        # é destacado. Assim o indicador nunca troca de bloco "no meio".
        if self.codigo.mudou(passo):
            sai, entra = self.codigo.trocar(passo)
            # Dois plays: o código novo só entra na cena depois que o antigo
            # saiu (dentro de um único play o FadeIn seria adicionado cheio).
            self.play(*sai)
            self.play(*entra)

        # Estrutura de dados: atualiza com o estado deste passo. Quando a aba
        # muda (UF <-> MinPQ <-> heap <-> edgeTo <-> distTo), o conteúdo antigo
        # sai inteiro e o novo entra em DOIS plays, como no painel de código.
        anims_estr, adicionar, remover, troca = self.estrutura.atualizar(passo)
        if troca:
            sai, novos = troca
            self.play(*sai)
            self.add(*novos)
            self.play(*[FadeIn(m, run_time=0.18) for m in novos])
            anims_estr = []
        if adicionar:
            self.add(*adicionar)

        anims: list[Animation] = [self.codigo.destacar(passo)]
        anims += self.grafo.animar(passo.destaque, passo.estado, modo=self.modo_nos)
        anims += self.painel.atualizar(self.textos_painel(passo))
        anims += anims_estr
        self.play(*anims, run_time=0.45)
        if remover:
            self.remove(*remover)
        # O ritmo vem do gravador: decisões ficam mais tempo na tela,
        # linhas de bookkeeping (for/while/if) passam mais rápido.
        self.wait(passo.pausa)

    def executar_passos(self) -> list[rec.Step]:
        for passo in self.passos:
            self.play_step(passo)
        return self.passos
