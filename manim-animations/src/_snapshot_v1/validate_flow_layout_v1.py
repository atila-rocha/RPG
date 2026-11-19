"""Portão de geometria da cena de fluxo — roda ANTES de qualquer render.

Não desenha nada: monta os mesmos mobjects da cena (`flow_common`) e mede.
Sai com código 1 se qualquer item do contrato do `PLANO_VISUAL_FLUXO.md`
falhar (§1 layout, §2 grafo, §3 guia, §4 código, §5 estrutura, §6 estado).

Uso:
    python validate_flow_layout.py
"""

from __future__ import annotations

import sys

from manim import DOWN, LEFT, RIGHT, UP, Text, config

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent / "src"))

import flow_common as fc  # noqa: E402
import flow_record as rec  # noqa: E402

MARGEM_QUADRO = 0.18
MARGEM_CALHA = 0.02
FONTE_MINIMA = 6.5
ALGORITMOS = ("edmonds_karp", "ford_fulkerson_dfs")


def box_de(mob) -> tuple[float, float, float, float]:
    return (
        float(mob.get_left()[0]),
        float(mob.get_bottom()[1]),
        float(mob.get_right()[0]),
        float(mob.get_top()[1]),
    )


def cor_de(mob) -> str:
    c = mob.get_color()
    if isinstance(c, str):
        return c.lower()
    return c.to_hex().lower()


class Portao:
    def __init__(self, algoritmo: str):
        self.algoritmo = algoritmo
        self.falhas: list[str] = []
        self.ok = 0

    def check(self, nome: str, condicao: bool, detalhe: str = "") -> None:
        if condicao:
            self.ok += 1
            print(f"  OK   {nome}" + (f"  [{detalhe}]" if detalhe else ""))
        else:
            self.falhas.append(nome)
            print(f"  FALHA {nome}  {detalhe}")

    # -- A. painéis no quadro seguro --------------------------------------
    def paineis(self, codigo, estrutura, painel, guia, cabecalho) -> None:
        quadro = (-config.frame_width / 2, -config.frame_height / 2,
                  config.frame_width / 2, config.frame_height / 2)
        for nome, mob in (
            ("cabecalho", cabecalho),
            ("moldura do codigo", codigo.moldura),
            ("estrutura", estrutura.fundo),
            ("estado", painel.fundo),
            ("guia", guia.mobject),
        ):
            self.check(
                f"dentro do quadro seguro: {nome}",
                fc.caixa_dentro(box_de(mob), quadro, MARGEM_QUADRO),
                f"bbox={tuple(round(x, 2) for x in box_de(mob))}",
            )

        # B. calhas entre os quadrantes (§1.2)
        cod = box_de(codigo.moldura)
        est = box_de(estrutura.fundo)
        sta = box_de(painel.fundo)
        self.cod, self.sta = cod, sta
        calha_v = cod[1] - est[3]
        self.check(
            "calha codigo/estrutura >= 0.34",
            calha_v >= 0.34 - MARGEM_CALHA,
            f"{calha_v:.2f}",
        )
        calha_h1 = sta[0] - cod[2]
        calha_h2 = sta[0] - est[2]
        self.check(
            "calha codigo/estado >= 0.20",
            calha_h1 >= 0.20 - MARGEM_CALHA,
            f"{calha_h1:.2f}",
        )
        self.check(
            "calha estrutura/estado >= 0.20",
            calha_h2 >= 0.20 - MARGEM_CALHA,
            f"{calha_h2:.2f}",
        )
        self.check(
            "estrutura e estado na mesma faixa inferior",
            abs(est[1] - sta[1]) <= 0.35,
            f"{est[1]:.2f} vs {sta[1]:.2f}",
        )

    # -- C/D. grafo: nós, rótulos f/C e colisões --------------------------
    def grafo(self, grafo: fc.FlowGraphView) -> None:
        nos_ok = 0
        for v in range(rec.V_REDE):
            circulo = grafo.circulos[v]
            rotulo = grafo.rotulos_no[v]
            dentro = fc.caixa_dentro(box_de(rotulo), box_de(circulo))
            nos_ok += int(rotulo.text == str(v) and dentro)
        self.check("rotulo em todo no (6/6)", nos_ok == rec.V_REDE, f"{nos_ok}/6")

        self.check(
            "toda aresta do arquivo tem rotulo f/C (8/8)",
            all((u, v) in grafo.caixa_rotulo for u, v, _c in rec.ARESTAS_REDE),
            f"{len(grafo.caixa_rotulo)}/8",
        )

        piores = {k: n for k, n in grafo.colisoes_rotulo.items() if n}
        self.check("rotulo f/C sem colisao propria", not piores, str(piores))

        # rótulo × rótulo
        pares = list(grafo.caixa_rotulo)
        colisoes = [
            (a, b)
            for i, a in enumerate(pares)
            for b in pares[i + 1:]
            if fc.caixas_colidem(grafo.caixa_rotulo[a], grafo.caixa_rotulo[b])
        ]
        self.check("rotulo x rotulo", not colisoes, str(colisoes))

        # rótulo × nó (com folga) e × etiqueta s/t
        alvos = [fc.caixa(fc.COORDS[v], 2 * fc.RAIO_NO, 2 * fc.RAIO_NO)
                 for v in range(rec.V_REDE)]
        alvos += [box_de(e) for e in grafo.etiquetas_papel.values()]
        batidas = [
            (k, i) for k in pares for i, alvo in enumerate(alvos)
            if fc.caixas_colidem(grafo.caixa_rotulo[k], alvo, folga=0.04)
        ]
        self.check("rotulo x no/etiqueta s,t", not batidas, str(batidas[:4]))

        # rótulo × aresta alheia (direta) e × arco reverso alheio
        cruza = []
        for u, v, _c in rec.ARESTAS_REDE:
            p0 = fc.ponto_na_aresta(u, v, 0.0)
            p1 = fc.ponto_na_aresta(u, v, 1.0)
            for k, box in grafo.caixa_rotulo.items():
                if k == (u, v):
                    continue
                if fc.segmento_cruza_caixa(p0, p1, box, margem=0.02):
                    cruza.append((k, (u, v)))
        self.check("rotulo x aresta alheia", not cruza, str(cruza[:4]))

        cruza_rev = []
        proprio = []
        for u, v, _c in rec.ARESTAS_REDE:
            amostras = fc.amostras_reversa(u, v)
            for k, box in grafo.caixa_rotulo.items():
                if not any(fc.segmento_cruza_caixa(a, b, box, margem=0.02)
                           for a, b in zip(amostras, amostras[1:])):
                    continue
                if k == (u, v):
                    proprio.append(k)
                else:
                    cruza_rev.append((k, (v, u)))
        self.check("rotulo x arco reverso alheio", not cruza_rev, str(cruza_rev[:4]))
        # o arco reverso do próprio par passa sob o rótulo: só é aceitável
        # porque o fundo do rótulo é opaco e cobre a caixa inteira (§2.3)
        mascarados = [
            k for k in proprio
            if grafo.fundos[k].get_fill_opacity() >= 0.99
            and fc.caixa_dentro(grafo.caixa_rotulo[k], box_de(grafo.fundos[k]))
        ]
        self.check(
            "arco reverso proprio mascarado pelo fundo do rotulo",
            len(mascarados) == len(proprio),
            f"{len(mascarados)}/{len(proprio)}",
        )

        # área útil do grafo: à direita do código e acima do estado
        self.check(
            "grafo a direita do codigo e acima do estado",
            float(grafo.mobject.get_left()[0]) >= self.cod[2] + 0.10
            and float(grafo.mobject.get_right()[0]) <= 6.93
            and float(grafo.mobject.get_bottom()[1]) >= self.sta[3] + 0.10,
            f"x={float(grafo.mobject.get_left()[0]):.2f}.."
            f"{float(grafo.mobject.get_right()[0]):.2f}",
        )

    # -- E. guia fiel (7 papéis, usados e listados) -----------------------
    def guia(self, guia: fc.GuiaVisual, passos) -> None:
        papeis = list(fc.ORDEM_GUIA)
        self.check("guia lista os 7 papeis", len(papeis) == 7 == len(fc.PALETA), str(papeis))

        itens = [m for linha in guia.mobject.submobjects for m in linha.submobjects]
        marcas = [(cor_de(it[0]), it[1].text) for it in itens]
        fiel = [
            papeis[i]
            for i, (cor, texto) in enumerate(marcas)
            if cor == fc.PALETA[papeis[i]][0].lower()
            and texto.replace(" ", "") == fc.PALETA[papeis[i]][1].replace(" ", "")
        ]
        self.check("marca e texto de cada papel conferem", len(fiel) == 7, f"{len(fiel)}/7")

        usados = set()
        for p in passos:
            est = p.estado
            tipo, _u, _v, status = p.destaque
            usados.add("fora")
            if any(v > 0 for v in est["fluxos"].values()):
                usados.update({"fluxo", "reversa"})
            if any(v > 0 for v in est["residual_reversa"].values()):
                usados.add("reversa")
            if any(
                est["fluxos"][(u, v)] > 0 and est["residual_direta"][(u, v)] == 0
                for u, v in est["fluxos"]
            ):
                usados.add("saturada")
            if est.get("marcados"):
                usados.add("alcancado")
            if tipo == "busca" and status in ("olhando", "examina"):
                usados.add("exame")
            if tipo == "caminho":
                usados.add("caminho")
        self.check("todo papel da guia aparece no trace", set(papeis) <= usados,
                   str(sorted(set(papeis) - usados)))
        self.check("nenhuma cor fora da guia", usados <= set(papeis), str(usados - set(papeis)))

    # -- F. painel de código ----------------------------------------------
    def codigo(self, codigo: fc.CodePanel, passos) -> None:
        self.check(
            f"fonte efetiva >= {FONTE_MINIMA} pt",
            codigo.fonte_efetiva >= FONTE_MINIMA,
            f"{codigo.fonte_efetiva:.2f} pt (escala {codigo.escala:.4f})",
        )
        moldura = box_de(codigo.moldura)
        fora = [
            i for i, c in enumerate(codigo.conteudos)
            if not fc.caixa_dentro(box_de(c), moldura, 0.02)
        ]
        self.check("conteudo de toda view dentro da moldura", not fora, str(fora))

        # toda linha executada cai numa view; toda view é usada
        indices = set()
        sem_view = []
        for p in passos:
            try:
                indices.add(codigo._view(p))
            except KeyError:
                sem_view.append((p.modulo, p.linha))
        self.check("toda linha executada tem view", not sem_view, str(sem_view[:3]))
        self.check(
            f"toda view e usada ({len(codigo.funcoes)}/{len(codigo.funcoes)})",
            indices == set(range(len(codigo.funcoes))),
            f"{len(indices)}/{len(codigo.funcoes)}",
        )
        # uma view por vez: o grupo estável é só a moldura
        self.check(
            "grupo estavel = moldura (sem texto fantasma)",
            len(codigo.mobject.submobjects) == 1
            and codigo.moldura in codigo.mobject.submobjects,
            str(len(codigo.mobject.submobjects)),
        )

    # -- G. abas -----------------------------------------------------------
    def abas(self, estrutura: fc.EstruturaPanel, passos) -> None:
        self.check(
            "uma aba por passo",
            len(estrutura.abas) == len(passos),
            f"{len(estrutura.abas)} vs {len(passos)}",
        )
        self.check(
            "so as duas abas do contrato",
            set(estrutura.abas) <= {"rede", "busca"},
            str(set(estrutura.abas)),
        )
        self.check(
            "aba busca realmente usada",
            estrutura.abas.count("busca") > 0,
            f"{estrutura.abas.count('busca')} passos",
        )
        trocas = sum(1 for a, b in zip(estrutura.abas, estrutura.abas[1:]) if a != b)
        self.check("trocas de aba em dois plays (par)", trocas % 2 == 0, f"{trocas} trocas")

    # -- H. troca de aba sem fantasma -------------------------------------
    def fantasmas(self, estrutura, passos) -> None:
        """`todos()` precisa ser a lista VIVA: a troca de aba faz FadeOut nela.

        Se devolver o snapshot da montagem, o FadeOut acerta mobjects que já
        saíram e os textos atuais ficam na tela para sempre.
        """
        rede = fc._AbaRede(estrutura)
        rede.construir(passos[0])
        velho = rede.textos[(0, 2, 3)]
        rede.sincronizar(passos[-1])
        novo = rede.textos[(0, 2, 3)]
        vivos = rede.todos()
        self.check(
            "aba Rede: texto trocado sai da lista viva",
            novo is not velho and novo in vivos and velho not in vivos,
            f"{len(vivos)} mobjects vivos",
        )
        self.check(
            "aba Rede: lista viva cobre chips e textos atuais",
            all(c in vivos for c in rede.chips.values())
            and all(t in vivos for t in rede.textos.values()),
        )

        busca = fc._AbaBusca(estrutura)
        busca.construir(passos[0])
        velho_e = busca.edge_to
        busca.sincronizar(passos[-1])
        vivos_b = busca.todos()
        self.check(
            "aba Busca: texto trocado sai da lista viva",
            busca.edge_to is not velho_e
            and busca.edge_to in vivos_b
            and velho_e not in vivos_b,
            f"{len(vivos_b)} mobjects vivos",
        )

    # -- I. painel de estado ----------------------------------------------
    def estado(self, painel: fc.StatePanel, passos, max_iteracao: int) -> None:
        fundo = box_de(painel.fundo)
        piores = max(passos, key=lambda p: len(p.acao))
        textos = painel.textos_do_passo(piores, max_iteracao)
        painel.iniciar(textos)
        linhas = [l for l in painel.linhas if l is not None]
        self.check("5 slots fixos", len(painel.linhas) == painel.N_SLOTS, str(len(painel.linhas)))
        fora = [i for i, l in enumerate(linhas) if not fc.caixa_dentro(box_de(l), fundo, 0.10)]
        self.check("slot dentro do painel", not fora, str(fora))
        sobre = [
            (i, j)
            for i in range(len(linhas))
            for j in range(i + 1, len(linhas))
            if fc.caixas_colidem(box_de(linhas[i]), box_de(linhas[j]))
        ]
        self.check("slots sem sobreposicao", not sobre, str(sobre))
        largura = max(len(fc.dividir_acao(p.acao)[0]) for p in passos)
        self.check(
            "acao mais longa cabe em duas linhas",
            max(l.width for l in linhas[:2]) <= fundo[2] - fundo[0] - 0.40,
            f"maior 1a linha {largura} ch",
        )


def main() -> int:
    print(f"contrato: PLANO_VISUAL_FLUXO.md · quadro {config.frame_width}x{config.frame_height}")
    total = 0
    falhas = 0
    for alg in ALGORITMOS:
        print("=" * 72)
        print(f"{alg}")
        passos = rec.coletar_detalhado(alg)
        print(f"  {len(passos)} passos")
        portao = Portao(alg)

        codigo = fc.CodePanel(alg)
        grafo = fc.FlowGraphView(mostrar_rede=True, estado_inicial=passos[-1].estado)
        estrutura = fc.EstruturaPanel(alg, passos)
        painel = fc.StatePanel(alg)
        guia = fc.GuiaVisual()

        titulo = Text("x", font_size=15, color=fc.COR_TEXTO)
        titulo.move_to([fc.TITULO_X, 3.62, 0.0], aligned_edge=LEFT)
        cabecalho = titulo

        portao.paineis(codigo, estrutura, painel, guia, cabecalho)
        portao.grafo(grafo)
        portao.guia(guia, passos)
        portao.codigo(codigo, passos)
        portao.abas(estrutura, passos)
        portao.fantasmas(estrutura, passos)
        portao.estado(painel, passos, estrutura.max_iteracao)

        print(f"  -> {portao.ok} verificacoes OK, {len(portao.falhas)} falhas")
        total += portao.ok
        falhas += len(portao.falhas)

    print("=" * 72)
    if falhas:
        print(f"PORTAO DE LAYOUT: VERMELHO ({falhas} falhas)")
        return 1
    print(f"PORTAO DE LAYOUT: VERDE ({total} verificacoes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
