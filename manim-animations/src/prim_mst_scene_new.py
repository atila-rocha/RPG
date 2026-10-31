"""
Prim Lazy e Prim Eager — animações novas (sufixo `_new`).

Estas cenas apenas desenham os `Step` gravados do `algs4-py`: a sequência
exibida vem da execução real, não é digitada à mão.
"""

from __future__ import annotations

from manim import *

import mst_record as rec
from mst_common import (
    COR_ACEITA,
    COR_ANALISE,
    COR_BORDA_NO,
    COR_DESCARTE,
    COR_DESTAQUE,
    COR_EXTRACAO,
    COR_FUNDO,
    COR_NO_ARVORE,
    COR_TEXTO,
    GraphView,
    MSTExecucaoBase,
)


# ---------------------------------------------------------------------------
# Introdução
# ---------------------------------------------------------------------------


class PrimIntroScene_new(Scene):
    def construct(self):
        self.camera.background_color = COR_FUNDO

        titulo = Text("Prim: crescer uma única árvore a partir da raiz", font_size=32, color=WHITE, weight=BOLD)
        subtitulo = Text(
            "Propriedade do corte — mesmo grafo de Kruskal",
            font_size=19,
            color=COR_TEXTO,
        )
        cabecalho = VGroup(titulo, subtitulo).arrange(DOWN, buff=0.14).to_edge(UP, buff=0.35)
        self.play(FadeIn(cabecalho, shift=DOWN))
        self.wait(0.4)

        painel = RoundedRectangle(
            corner_radius=0.15,
            width=6.2,
            height=4.9,
            color=GRAY_D,
            stroke_width=1.5,
            fill_color="#151824",
            fill_opacity=0.9,
        ).move_to(np.array([-3.5, -0.75, 0]))

        itens = [
            ("• Crescimento local", "Parte de uma raiz e nunca se divide", COR_TEXTO),
            ("• Propriedade do corte", "A menor aresta que cruza (S, V−S) entra na MST", WHITE),
            ("• Lazy (MinPQ de arestas)", "Insere todas as arestas do corte e descarta obsoletas", COR_DESTAQUE),
            ("• Eager (IndexMinPQ de vértices)", "Uma entrada por vértice, atualizada por decrease_key", COR_ACEITA),
        ]
        blocos = []
        for cabeca, detalhe, cor in itens:
            blocos.append(
                VGroup(
                    Text(cabeca, font_size=16, color=cor, weight=BOLD),
                    Text("  " + detalhe, font_size=12, color=GRAY_A),
                ).arrange(DOWN, aligned_edge=LEFT, buff=0.04)
            )
        lista = VGroup(*blocos).arrange(DOWN, aligned_edge=LEFT, buff=0.30).move_to(painel.get_center())
        self.play(FadeIn(painel), FadeIn(lista), run_time=0.8)

        grafo = GraphView()
        grafo.mobject.shift(DOWN * 0.3)
        edge_to = rec.coletar("eager")[-1].estado["edgeTo"]
        self.play(FadeIn(grafo.mobject), run_time=0.9)
        self.play(
            *[
                anim
                for e in edge_to
                if e is not None
                for anim in grafo._pintar((min(e[0], e[1]), max(e[0], e[1])), "aceita")
            ],
            run_time=1.0,
        )

        caixa = RoundedRectangle(
            corner_radius=0.15,
            width=6.0,
            height=1.55,
            color=GRAY_D,
            stroke_width=1.5,
            fill_color="#151824",
            fill_opacity=0.9,
        ).move_to(np.array([3.5, -2.5, 0]))
        resultado = VGroup(
            Text("Lazy: O(E log E) tempo · O(E) espaço", font_size=14, color=COR_DESTAQUE),
            Text("Eager: O(E log V) tempo · O(V) espaço", font_size=14, color=COR_ACEITA),
            Text("Ambos chegam ao mesmo custo 13", font_size=13, color=GRAY_A),
        ).arrange(DOWN, buff=0.10).move_to(caixa.get_center())
        self.play(FadeIn(caixa), FadeIn(resultado))
        self.wait(1.6)

        self.play(
            FadeOut(VGroup(cabecalho, painel, lista, grafo.mobject, caixa, resultado)),
            run_time=0.6,
        )
        self.wait(0.3)


# ---------------------------------------------------------------------------
# Execuções
# ---------------------------------------------------------------------------


class PrimLazyScene_new(MSTExecucaoBase):
    algoritmo = "lazy"
    titulo = "Prim Lazy: execução linha a linha (MinPQ de arestas)"
    modo_nos = "marcados"
    n_linhas_painel = 4

    def construct(self):
        self.configurar(PrimLazyScene_new)
        self.montar_estrutura(
            [
                (COR_ACEITA, "aresta aceita (liga um nó novo)"),
                (COR_DESCARTE, "obsoleta: ambos marcados → continue"),
                ("#8d99ae", "aresta ainda na MinPQ"),
                (COR_ANALISE, "aresta extraída da MinPQ (em análise)"),
                (COR_BORDA_NO, "vértice fora da árvore", "ring"),
                (COR_NO_ARVORE, "vértice já marcado (na árvore)", "ring"),
            ]
        )
        self.executar_passos()
        self.fechar()


class PrimEagerScene_new(MSTExecucaoBase):
    algoritmo = "eager"
    titulo = "Prim Eager: execução linha a linha (IndexMinPQ + decrease_key)"
    modo_nos = "marcados"
    n_linhas_painel = 5

    def construct(self):
        self.configurar(PrimEagerScene_new)
        self.montar_estrutura(
            [
                (COR_EXTRACAO, "vértice extraído da IPQ (flash magenta)", "ring"),
                (COR_NO_ARVORE, "vértice na árvore", "ring"),
                (COR_ANALISE, "aresta relaxada (insert / decrease_key)"),
                (COR_BORDA_NO, "vértice ainda fora da árvore", "ring"),
            ]
        )
        self.executar_passos()
        self.fechar()


class FullPrimVideo_new(MSTExecucaoBase):
    algoritmo = PrimLazyScene_new.algoritmo
    titulo = PrimLazyScene_new.titulo
    modo_nos = PrimLazyScene_new.modo_nos
    n_linhas_painel = PrimLazyScene_new.n_linhas_painel

    def construct(self):
        PrimIntroScene_new.construct(self)
        self.wait(0.5)
        self.limpar()
        PrimLazyScene_new.construct(self)
        self.wait(0.5)
        self.limpar()
        PrimEagerScene_new.construct(self)
