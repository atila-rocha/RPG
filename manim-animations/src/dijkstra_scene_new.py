"""
Cenas de animação do Algoritmo de Dijkstra (sufixo `_new`).

Cena 1: DijkstraIntroScene_new — Introdução teórica, conceitos de SSSP,
        relaxação, paradigma guloso e comparação Lazy vs Eager.
Cena 2: DijkstraExecutionScene_new — Execução linha a linha do algoritmo real
        do `algs4-py`, com grafo dirigido, painel dinâmico por função
        (fade-out/fade-in) e abas de estrutura de dados (IndexMinPQ, distTo,
        edgeTo) que acompanham a linha executada.
"""

from __future__ import annotations

import numpy as np
from manim import *

import dijkstra_record as rec
from dijkstra_common import (
    COR_ACEITA,
    COR_ANALISE,
    COR_ARESTA_FORA,
    COR_DESCARTE,
    COR_DESTAQUE,
    COR_EXTRACAO,
    COR_FUNDO,
    COR_NO_FINALIZADO,
    COR_PAINEL,
    COR_TENTATIVA,
    COR_TEXTO,
    DijkstraExecucaoBase,
    DirectedGraphView,
    coords_do_grafo,
    fmt_dist_to,
)


# ---------------------------------------------------------------------------
# Cena 1: Introdução ao Algoritmo de Dijkstra
# ---------------------------------------------------------------------------


class DijkstraIntroScene_new(Scene):
    """Introdução aos fundamentos teóricos do Algoritmo de Dijkstra."""

    def construct(self):
        self.camera.background_color = COR_FUNDO

        # Cabeçalho: apenas o título, centralizado (sem subtítulo).
        titulo = Text("O Algoritmo de Dijkstra: Caminho Mínimo", font_size=30, color=WHITE, weight=BOLD).to_edge(UP, buff=0.32)
        self.play(FadeIn(titulo, shift=DOWN))
        self.wait(0.4)

        # Painel esquerdo: princípios teóricos fundamentais
        painel_teoria = RoundedRectangle(
            corner_radius=0.15,
            width=6.20,
            height=5.00,
            color=GRAY_D,
            stroke_width=1.5,
            fill_color=COR_PAINEL,
            fill_opacity=0.92,
        ).move_to(np.array([-3.55, -0.80, 0]))

        itens = [
            (
                "• Problema SSSP (Single-Source Shortest Path)",
                "Menor distância acumulada de uma origem s a todos os nós v",
                COR_TEXTO,
            ),
            (
                "• Mecanismo de Relaxação de Arestas",
                "se distTo[v] + w(u,v) < distTo[w]  ⇒  atualiza distTo e edgeTo",
                COR_ANALISE,
            ),
            (
                "• Paradigma Guloso (Greedy Choice)",
                "Extrai sempre o nó não finalizado de menor distância acumulada",
                WHITE,
            ),
            (
                "• Restrição: Pesos Não Negativos (w ≥ 0)",
                "Garante monotonicidade. Para pesos negativos: Bellman-Ford",
                COR_DESCARTE,
            ),
        ]

        blocos = []
        for cabeca, detalhe, cor in itens:
            bloco = VGroup(
                Text(cabeca, font_size=15, color=cor, weight=BOLD),
                Text("  " + detalhe, font_size=12, color=GRAY_A),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
            # Nenhuma linha pode vazar a moldura de 6,20 de largura.
            for linha in bloco:
                if linha.width > painel_teoria.width - 0.50:
                    linha.scale_to_fit_width(painel_teoria.width - 0.50)
            blocos.append(bloco)

        lista = VGroup(*blocos).arrange(DOWN, aligned_edge=LEFT, buff=0.30)
        lista.move_to(painel_teoria.get_center())
        self.play(FadeIn(painel_teoria), FadeIn(lista), run_time=0.8)

        # Grafo real (lado direito), lido do tinyEWD.
        # Desce 0.45: o cabeçalho de duas linhas termina em y≈2.84 e o topo
        # do grafo em y≈3.12 encostava nele (x de 1.78 a 4.93 no título).
        grafo = DirectedGraphView(coords_do_grafo())
        grafo.mobject.shift(DOWN * 0.45)
        self.play(FadeIn(grafo.mobject), run_time=0.9)

        # Destaca a SPT calculada pela execução real do algs4
        passos = rec.coletar_detalhado()
        final = passos[-1].estado
        anims_spt = []
        for e in final.get("spt", []):
            anims_spt += grafo._pintar_aresta(e[0], e[1], "aceita")
        for v in range(rec.V_CANONICO):
            anims_spt += grafo._pintar_no(v, "origem" if v == rec.ORIGEM else "finalizado")
        self.play(*anims_spt, run_time=1.0)

        # Painel inferior direito: comparação Lazy vs Eager
        caixa_comp = RoundedRectangle(
            corner_radius=0.15,
            width=6.00,
            height=1.55,
            color=GRAY_D,
            stroke_width=1.5,
            fill_color=COR_PAINEL,
            fill_opacity=0.92,
        ).move_to(np.array([3.55, -2.60, 0]))

        resultado = VGroup(
            Text(f"SPT real: {len(final.get('spt', []))} arestas · custo {final.get('custo', 0):g}", font_size=14, color=COR_ACEITA, weight=BOLD),
            Text(f"distTo final: {fmt_dist_to(final).replace('distTo: ', '')}", font_size=12, color=WHITE),
            Text("Lazy: MinPQ com arestas obsoletas · O(E) espaço", font_size=12, color=COR_DESTAQUE),
            Text("Eager: IndexMinPQ + decreaseKey · O(V) espaço", font_size=12, color=COR_TEXTO),
        ).arrange(DOWN, buff=0.09).move_to(caixa_comp.get_center())
        for linha in resultado:
            if linha.width > caixa_comp.width - 0.40:
                linha.scale_to_fit_width(caixa_comp.width - 0.40)

        self.play(FadeIn(caixa_comp), FadeIn(resultado), run_time=0.8)
        self.wait(2.5)


# ---------------------------------------------------------------------------
# Cena 2: Execução Linha a Linha do Algoritmo de Dijkstra
# ---------------------------------------------------------------------------


class DijkstraExecutionScene_new(DijkstraExecucaoBase):
    """Execução linha a linha do DijkstraSP com IndexMinPQ e abas de dados."""

    def construct(self):
        self.montar_estrutura([
            (COR_TEXTO, "origem (s=0)", "ring"),
            (COR_NO_FINALIZADO, "finalizado (distância ótima)", "ring"),
            (COR_EXTRACAO, "extraído da IndexMinPQ", "ring"),
            (COR_ANALISE, "em análise", "dot"),
            (COR_TENTATIVA, "tentativa (edgeTo)", "dot"),
            (COR_ACEITA, "caminho mínimo (SPT)", "dot"),
        ])
        self.executar_passos()
        self.fechar()


class FullDijkstraVideo_new(DijkstraExecucaoBase):
    """Vídeo completo: introdução e depois a execução."""

    def construct(self):
        DijkstraIntroScene_new.construct(self)
        self.montar_estrutura([
            (COR_TEXTO, "origem (s=0)", "ring"),
            (COR_NO_FINALIZADO, "finalizado (distância ótima)", "ring"),
            (COR_EXTRACAO, "extraído da IndexMinPQ", "ring"),
            (COR_ANALISE, "em análise", "dot"),
            (COR_TENTATIVA, "tentativa (edgeTo)", "dot"),
            (COR_ACEITA, "caminho mínimo (SPT)", "dot"),
        ])
        self.executar_passos()
        self.fechar()
