"""Cena temporária de inspeção de layout (não entra no vídeo).

Uso:
    ALG=kruskal IDX=123 manim render src/_layout_check.py LayoutCheck -s -ql

Monta o frame completo (título, código, grafo, legenda, painel de estado e
painel de estrutura) no passo `IDX`, sem animar — serve para conferir
margens, colisões e o conteúdo das abas.
"""

from __future__ import annotations

import os

import numpy as np
from manim import *

import mst_record as rec
from mst_common import (
    COR_ACEITA, COR_ANALISE, COR_ARESTA_FORA, COR_BORDA_NO, COR_DESCARTE,
    COR_DESTAQUE, COR_EXTRACAO, COR_FUNDO, COR_NO_ARVORE, COR_TEXTO,
    CodePanel, EstruturaPanel, GraphView, StatePanel,
)

LEGENDAS = {
    "kruskal": [
        (COR_ACEITA, "aceita (MST)"),
        (COR_DESCARTE, "descartada (ciclo)"),
        (COR_ARESTA_FORA, "fora / na MinPQ"),
        (COR_ANALISE, "em análise"),
        (COR_NO_ARVORE, "na árvore", "ring"),
    ],
    "lazy": [
        (COR_ACEITA, "aceita (nó novo)"),
        (COR_DESCARTE, "obsoleta → continue"),
        ("#8d99ae", "na MinPQ"),
        (COR_ANALISE, "em análise"),
        (COR_BORDA_NO, "fora da árvore", "ring"),
        (COR_NO_ARVORE, "na árvore", "ring"),
    ],
    "eager": [
        (COR_EXTRACAO, "extraído da IPQ", "ring"),
        (COR_NO_ARVORE, "na árvore", "ring"),
        (COR_ANALISE, "relaxada (insert / decrease)"),
        (COR_BORDA_NO, "fora da árvore", "ring"),
    ],
}

TITULOS = {
    "kruskal": "Kruskal: execução linha a linha (MinPQ + union-find)",
    "lazy": "Prim Lazy: execução linha a linha (MinPQ de arestas)",
    "eager": "Prim Eager: execução linha a linha (IndexMinPQ + decrease_key)",
}


class LayoutCheck(Scene):
    def construct(self):
        alg = os.environ.get("ALG", "kruskal")
        idx = int(os.environ.get("IDX", "0"))
        self.camera.background_color = COR_FUNDO

        passos = rec.coletar_detalhado(alg)
        passo = passos[idx]

        titulo = Text(TITULOS[alg], font_size=20, color=WHITE, weight=BOLD)
        titulo.to_edge(UP, buff=0.08)
        self.add(titulo)

        codigo = CodePanel(alg)
        codigo.encaixar(passo)
        self.add(codigo.mobject, codigo.visivel, codigo.indicador)

        grafo = GraphView()
        self.add(grafo.mobject)

        painel = StatePanel(
            centro=np.array([3.55, -2.30, 0]),
            largura=6.5,
            altura=2.55,
            n_linhas=5 if alg == "eager" else 4,
        )
        self.add(*painel.iniciar(self._textos(alg, passo)))

        estrutura = EstruturaPanel(
            alg, centro=np.array([-3.35, -2.30, 0]), largura=6.70, altura=2.90
        )
        mobs = estrutura.preparar(passo)
        self.add(*mobs)
        self.add(self._legenda(alg, grafo))
        self.wait(0.1)

    @staticmethod
    def _legenda(alg, grafo):
        itens = []
        for item in LEGENDAS[alg]:
            cor, texto = item[0], item[1]
            forma = item[2] if len(item) > 2 else "dot"
            marca = (
                Circle(radius=0.075, color=cor, stroke_width=2.6, fill_opacity=0.0)
                if forma == "ring"
                else Dot(color=cor, radius=0.075)
            )
            itens.append(
                VGroup(marca, Text(texto, font_size=15, color=WHITE)).arrange(
                    RIGHT, buff=0.10
                )
            )
        meia = (len(itens) + 1) // 2
        l1 = VGroup(*itens[:meia]).arrange(RIGHT, buff=0.26)
        l2 = VGroup(*itens[meia:]).arrange(RIGHT, buff=0.26)
        for linha in (l1, l2):
            if linha.width > 5.2:
                linha.scale_to_fit_width(5.2)
        bloco = VGroup(l1, l2).arrange(DOWN, aligned_edge=LEFT, buff=0.10)
        bloco.next_to(grafo.mobject, DOWN, buff=0.14, aligned_edge=LEFT)
        return bloco

    @staticmethod
    def _textos(alg, passo):
        from mst_common import (
            fmt_componentes, fmt_dist_to, fmt_edge_to, fmt_fila, fmt_fila_lazy,
            fmt_ipq, fmt_marcados, fmt_mst_prim, cor_destaque,
        )

        est = passo.estado
        cor = cor_destaque(passo)
        if alg == "kruskal":
            return [
                (passo.acao, cor, 14),
                (f"MST: {len(est['mst'])} / 5 arestas  |  Custo: {est['custo']:g}", WHITE, 15),
                (fmt_fila(est), "#8d99ae", 12),
                (fmt_componentes(est), GRAY_A, 12),
            ]
        if alg == "lazy":
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
