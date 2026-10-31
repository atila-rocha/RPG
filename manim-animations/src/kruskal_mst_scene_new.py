"""
Kruskal — animações novas (sufixo `_new`).

Estas cenas apenas desenham os `Step` gravados do `algs4-py`: a sequência
exibida vem da execução real, não é digitada à mão.
"""

from __future__ import annotations

from manim import *

import mst_record as rec
from mst_common import (
    COR_ACEITA,
    COR_ANALISE,
    COR_ARESTA_FORA,
    COR_DESCARTE,
    COR_DESTAQUE,
    COR_FUNDO,
    COR_NO_ARVORE,
    COR_TEXTO,
    GraphView,
    MSTExecucaoBase,
)


# ---------------------------------------------------------------------------
# Introdução
# ---------------------------------------------------------------------------


class MSTIntroScene_new(Scene):
    def construct(self):
        self.camera.background_color = COR_FUNDO

        titulo = Text("Árvore Geradora Mínima (MST)", font_size=38, color=WHITE, weight=BOLD)
        subtitulo = Text(
            "Conceitos e propriedades — grafo único dos três vídeos",
            font_size=20,
            color=COR_TEXTO,
        )
        cabecalho = VGroup(titulo, subtitulo).arrange(DOWN, buff=0.15).to_edge(UP, buff=0.4)
        self.play(FadeIn(cabecalho, shift=DOWN))
        self.wait(0.5)

        painel = RoundedRectangle(
            corner_radius=0.15,
            width=6.2,
            height=5.0,
            color=GRAY_D,
            stroke_width=1.5,
            fill_color="#151824",
            fill_opacity=0.9,
        ).move_to(np.array([-3.5, -0.7, 0]))

        itens = [
            ("• Conectividade total", "Conecta os 6 vértices em um só componente", COR_TEXTO),
            ("• Estrutura acíclica", "Nenhum ciclo fechado", WHITE),
            ("• |V| − 1 arestas", "Toda MST tem exatamente 5 arestas", COR_DESTAQUE),
            ("• Custo mínimo", "Soma dos pesos é a menor possível", COR_ACEITA),
        ]
        blocos = []
        for cabeca, detalhe, cor in itens:
            blocos.append(
                VGroup(
                    Text(cabeca, font_size=17, color=cor, weight=BOLD),
                    Text("  " + detalhe, font_size=14, color=GRAY_A),
                ).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
            )
        lista = VGroup(*blocos).arrange(DOWN, aligned_edge=LEFT, buff=0.35).move_to(painel.get_center())

        self.play(FadeIn(painel), FadeIn(lista), run_time=0.8)

        grafo = GraphView()
        grafo.mobject.shift(DOWN * 0.3)

        # A MST exibida vem da execução real do algs4, não é digitada.
        final = rec.coletar("kruskal")[-1].estado
        self.play(FadeIn(grafo.mobject), run_time=0.9)
        self.play(
            *[
                anim
                for u, v, _ in final["mst"]
                for anim in grafo._pintar((min(u, v), max(u, v)), "aceita")
            ],
            run_time=1.0,
        )

        caixa = RoundedRectangle(
            corner_radius=0.15,
            width=5.8,
            height=1.35,
            color=GRAY_D,
            stroke_width=1.5,
            fill_color="#151824",
            fill_opacity=0.9,
        ).move_to(np.array([3.6, -2.55, 0]))
        resultado = VGroup(
            Text(
                f"MST: {len(final['mst'])} arestas  |  Custo {final['custo']:g}",
                font_size=19,
                color=COR_ACEITA,
                weight=BOLD,
            ),
            Text("mesmo grafo em Kruskal, Prim Lazy e Prim Eager", font_size=13, color=GRAY_A),
        ).arrange(DOWN, buff=0.10).move_to(caixa.get_center())
        self.play(FadeIn(caixa), FadeIn(resultado))
        self.wait(2.0)

        self.play(
            FadeOut(VGroup(cabecalho, painel, lista, grafo.mobject, caixa, resultado)),
            run_time=0.6,
        )
        self.wait(0.3)


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


class KruskalExecutionScene_new(MSTExecucaoBase):
    algoritmo = "kruskal"
    titulo = "Kruskal: execução linha a linha (MinPQ + union-find)"
    modo_nos = "arvore"
    n_linhas_painel = 4

    def construct(self):
        self.configurar(KruskalExecutionScene_new)
        self.montar_estrutura(
            [
                (COR_ACEITA, "aresta aceita na MST (sem ciclo)"),
                (COR_DESCARTE, "aresta descartada (forma ciclo)"),
                (COR_ARESTA_FORA, "aresta fora da MST / ainda na MinPQ"),
                (COR_ANALISE, "aresta retirada da MinPQ (em análise)"),
                (COR_NO_ARVORE, "vértice já ligado pela árvore", "ring"),
            ]
        )
        self.executar_passos()
        self.fechar()


class FullMSTKruskalVideo_new(MSTExecucaoBase):
    algoritmo = KruskalExecutionScene_new.algoritmo
    titulo = KruskalExecutionScene_new.titulo
    modo_nos = KruskalExecutionScene_new.modo_nos
    n_linhas_painel = KruskalExecutionScene_new.n_linhas_painel

    def construct(self):
        MSTIntroScene_new.construct(self)
        self.wait(0.6)
        self.limpar()
        KruskalExecutionScene_new.construct(self)
