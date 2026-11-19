"""
Ford-Fulkerson (DFS) — animações novas (sufixo `_new`).

Mesma espinha visual do Edmonds-Karp (contrato `PLANO_VISUAL_FLUXO.md`),
mas o slide 4 fala do que muda de fato: a busca é DFS (pilha), o custo é
O(E · |f|) e o número de inspeções cai — tudo lido do trace real.
"""

from __future__ import annotations

from manim import *

import flow_record as rec
from flow_common import (
    COR_ACENTO,
    COR_BORDA_NO,
    COR_FUNDO,
    COR_PAINEL,
    COR_TEXTO,
    PALETA,
    FlowExecucaoBase,
    FlowGraphView,
)

SUBTITULO = (
    f"tinyFN · V={rec.V_REDE} · E={len(rec.ARESTAS_REDE)}"
    f" · s={rec.S_FONTE} · t={rec.T_SUMIDOURO}"
)


def _bloco(cabeca: str, detalhe: str, cor: str) -> VGroup:
    """Par título/detalhe da lista de conceitos (mesma tipografia do BFS)."""
    return VGroup(
        Text(cabeca, font_size=16, color=cor, weight=BOLD),
        Text("  " + detalhe, font_size=12, color=GRAY_A),
    ).arrange(DOWN, aligned_edge=LEFT, buff=0.04)


# ---------------------------------------------------------------------------
# Introdução (~50 s)
# ---------------------------------------------------------------------------


class FordFulkersonIntro_new(Scene):
    def construct(self):
        self.camera.background_color = COR_FUNDO

        titulo = Text(
            "Fluxo Máximo — Ford-Fulkerson (DFS)", font_size=28, color=WHITE, weight=BOLD
        )
        subtitulo = Text(SUBTITULO, font_size=14, color=COR_ACENTO)
        cabecalho = VGroup(titulo, subtitulo).arrange(DOWN, buff=0.10)
        cabecalho.to_edge(UP, buff=0.24)
        self.play(FadeIn(cabecalho, shift=DOWN), run_time=0.8)
        self.wait(0.4)

        painel = RoundedRectangle(
            corner_radius=0.15,
            width=6.0,
            height=4.5,
            color=COR_BORDA_NO,
            stroke_width=1.5,
            fill_color=COR_PAINEL,
            fill_opacity=0.9,
        ).move_to(np.array([-3.50, -0.55, 0.0]))

        itens = [
            _bloco("• Capacidade", "cada arco tem C(u,v) ≥ 0", COR_TEXTO),
            _bloco("• Conservação", "0 ≤ f ≤ C; nos internos, entra = sai", WHITE),
            _bloco("• Valor", "|f| = Σ f(s,·) = Σ f(·,t)", PALETA["caminho"][0]),
            _bloco(
                "• Rede residual",
                "C_f(u,v) = C−f (direta) · C_f(v,u) = f (reversa)",
                PALETA["reversa"][0],
            ),
        ]
        lista = VGroup(*itens).arrange(DOWN, aligned_edge=LEFT, buff=0.30)
        lista.move_to(painel.get_center())
        self.play(FadeIn(painel), FadeIn(lista), run_time=0.8)

        final = rec.coletar("ford_fulkerson_dfs")[-1].estado
        inicial = rec.coletar_detalhado("ford_fulkerson_dfs")[0].estado
        grafo = FlowGraphView(mostrar_rede=True, estado_inicial=inicial)
        self.play(FadeIn(grafo.mobject), run_time=0.9)
        self.wait(1.2)

        # -- slide 2: caminho aumentante e gargalo (1ª busca, estado real) ---
        passo_nova = next(
            p
            for p in rec.coletar_detalhado("ford_fulkerson_dfs")
            if p.destaque[0] == "busca" and p.destaque[3] == "nova"
        )
        est = passo_nova.estado
        caminho = est["caminho"]
        residuais = [est["residual_direta"][par] for par in caminho]
        gargalo = min(residuais)
        extenso = "→".join(str(caminho[0][0])) + "".join(
            f"→{v}" for _u, v in caminho
        )

        self.play(FadeOut(lista), run_time=0.3)
        texto2 = VGroup(
            Text("Caminho aumentante", font_size=16, color=PALETA["caminho"][0], weight=BOLD),
            Text(extenso, font_size=14, color=COR_TEXTO),
            Text(
                "residuais " + " · ".join(f"{r:g}" for r in residuais),
                font_size=12,
                color=COR_TEXTO,
            ),
            Text(
                f"b = min = {gargalo:g}  →  |f| += b",
                font_size=13,
                color=PALETA["caminho"][0],
            ),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        texto2.move_to(painel.get_center())
        anims = [grafo.pintar(a, b, PALETA["caminho"][0], 5.5) for a, b in caminho]
        self.play(
            FadeIn(texto2),
            *[a for a in anims if a is not None],
            *[grafo.flash(a, b) for a, b in caminho],
            run_time=0.9,
        )
        self.wait(1.8)

        # -- slide 3: rede residual (estado FINAL: 0→2 com f = 2) -----------
        self.play(FadeOut(texto2), *grafo.aplicar(final), run_time=0.9)
        cap = final["capacidades"][(0, 2)]
        fluxo = final["fluxos"][(0, 2)]
        texto3 = VGroup(
            Text("Rede residual", font_size=16, color=PALETA["reversa"][0], weight=BOLD),
            Text(
                f"C_f(0,2) = C − f = {cap:g} − {fluxo:g} = {final['residual_direta'][(0, 2)]:g}",
                font_size=13,
                color=COR_TEXTO,
            ),
            Text(
                f"C_f(2,0) = f = {final['residual_reversa'][(0, 2)]:g}",
                font_size=13,
                color=PALETA["reversa"][0],
            ),
            Text("a reversa desfaz fluxo", font_size=12, color=GRAY_A),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        texto3.move_to(painel.get_center())
        rotulo_rev = grafo.rotulo_residual(
            (0, 2), f"res = {final['residual_reversa'][(0, 2)]:g}"
        )
        self.play(
            FadeIn(texto3),
            grafo.pintar(0, 2, PALETA["reversa"][0], 5.5),
            FadeIn(rotulo_rev),
            run_time=0.8,
        )
        self.wait(2.0)

        # -- slide 4: DFS — pilha, custo e inspeções reais ------------------
        inspecoes_bfs = rec.coletar("edmonds_karp")[-1].estado["inspecoes"]
        self.play(FadeOut(texto3), FadeOut(rotulo_rev), run_time=0.3)
        texto4 = VGroup(
            Text("O laço com DFS", font_size=16, color=COR_ACENTO, weight=BOLD),
            Text("pilha: desce até t, sem garantia de caminho curto", font_size=13, color=COR_TEXTO),
            Text(
                f"{int(final['inspecoes'])} inspeções (DFS) vs {int(inspecoes_bfs)} (BFS)",
                font_size=13,
                color=PALETA["caminho"][0],
            ),
            Text("O(E · |f|) — pseudo-polinomial", font_size=14, color=COR_TEXTO),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        texto4.move_to(painel.get_center())
        self.play(FadeIn(texto4), run_time=0.6)
        self.wait(1.8)

        # -- fecho: |f| e corte mínimo --------------------------------------
        # o painel da esquerda já cumpriu o papel: sai com o último texto
        self.play(FadeOut(texto4), FadeOut(painel), run_time=0.3)
        self.play(*grafo.destacar_corte(final), run_time=1.0)
        lado = set(final["corte"])
        cortadas = [c for u, v, c in rec.ARESTAS_REDE if u in lado and v not in lado]
        caixa = RoundedRectangle(
            corner_radius=0.15,
            width=5.2,
            height=1.25,
            color=COR_BORDA_NO,
            stroke_width=1.5,
            fill_color=COR_PAINEL,
            fill_opacity=0.95,
        ).move_to(np.array([4.15, -2.95, 0.0]))
        veredito = VGroup(
            Text(
                f"|f| = {final['valor']:g}  ·  corte mínimo = {final['corte_capacidade']:g}",
                font_size=17,
                color=PALETA["caminho"][0],
                weight=BOLD,
            ),
            Text(
                "S* = {" + ", ".join(map(str, final["corte"])) + "}  ·  C(S,T) = "
                + " + ".join(f"{c:g}" for c in cortadas),
                font_size=12,
                color=COR_TEXTO,
            ),
        ).arrange(DOWN, buff=0.08).move_to(caixa.get_center())
        self.play(FadeIn(caixa), FadeIn(veredito), run_time=0.7)
        self.wait(2.4)


# ---------------------------------------------------------------------------
# Execução linha a linha
# ---------------------------------------------------------------------------


class FordFulkersonExecutionScene_new(FlowExecucaoBase):
    algoritmo = "ford_fulkerson_dfs"
    titulo = "Ford-Fulkerson (DFS) — linha a linha"
    subtitulo = SUBTITULO

    def construct(self):
        self.montar()
        self.executar_passos()
        self.fechar()


class FullFordFulkersonVideo_new(FlowExecucaoBase):
    algoritmo = FordFulkersonExecutionScene_new.algoritmo
    titulo = FordFulkersonExecutionScene_new.titulo
    subtitulo = FordFulkersonExecutionScene_new.subtitulo

    def construct(self):
        FordFulkersonIntro_new.construct(self)
        self.wait(0.4)
        self.limpar()
        FordFulkersonExecutionScene_new.construct(self)
