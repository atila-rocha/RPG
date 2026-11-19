"""Portão de geometria da cena de fluxo — roda ANTES de qualquer render.

Não desenha nada: monta os mesmos mobjects da cena (`flow_common`) e mede.
Sai com código 1 se qualquer item do contrato do `PLANO_VISUAL_FLUXO_V2.md`
falhar (§1 layout, §2 grafo, §3 guia, §4 código/paginação, §5 estrutura/5
abas, §6 estado, §A ritmo).

Uso:
    python validate_flow_layout.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from manim import DOWN, LEFT, RIGHT, UP, Text, config

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import flow_common as fc  # noqa: E402
import flow_record as rec  # noqa: E402

MARGEM_QUADRO = 0.18
MARGEM_CALHA = 0.02
FONTE_MINIMA = 10.5
ALGORITMOS = ("edmonds_karp", "ford_fulkerson_dfs")
LARGURA_UTIL_CODIGO = fc.CODIGO["largura"] - fc.CodePanel.PADDING_ESQ - fc.CodePanel.PADDING_DIR


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


def cores_vivas(mobs) -> set[str]:
    """Cores de texto/borda E de preenchimento dos mobjects (recursivo)."""
    cores: set[str] = set()

    def visitar(m):
        try:
            cores.add(cor_de(m))
        except Exception:
            pass
        try:
            if getattr(m, "get_fill_opacity", lambda: 0)() > 0:
                fill = m.get_fill_color()
                cores.add(fill.lower() if isinstance(fill, str) else fill.to_hex().lower())
        except Exception:
            pass
        for filho in getattr(m, "submobjects", []):
            visitar(filho)

    for m in mobs:
        visitar(m)
    return cores


CORES_PERMITIDAS = (
    {hexa.lower() for hexa, _t, _s in fc.PALETA.values()}
    | {str(v).lower() for v in fc.ESTRUTURAIS.values()}
    | {fc.COR_ACENTO.lower(), fc.COR_TAB_ATIVA.lower(), fc.COR_TAB_INATIVA.lower()}
    | {fc.COR_CHIP.lower(), "#ffffff", "#12141d"}
    | {fc.COR_LINHA_TABELA.lower()}
)



def _mobjects_saindo(anims) -> set[int]:
    """Ids de todo mobject que um FadeOut (inclusive dentro de grupo) retira."""
    from manim import AnimationGroup, FadeOut

    ids: set[int] = set()
    pilha = list(anims)
    while pilha:
        anim = pilha.pop()
        if isinstance(anim, AnimationGroup):
            pilha.extend(anim.animations)
            continue
        if isinstance(anim, FadeOut) and getattr(anim, "mobject", None) is not None:
            ids.add(id(anim.mobject))
    return ids

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
            "calha codigo/estrutura >= 0.20",
            calha_v >= 0.20 - MARGEM_CALHA,
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

        pares = list(grafo.caixa_rotulo)
        colisoes = [
            (a, b)
            for i, a in enumerate(pares)
            for b in pares[i + 1:]
            if fc.caixas_colidem(grafo.caixa_rotulo[a], grafo.caixa_rotulo[b])
        ]
        self.check("rotulo x rotulo", not colisoes, str(colisoes))

        alvos = [fc.caixa(fc.COORDS[v], 2 * fc.RAIO_NO, 2 * fc.RAIO_NO)
                 for v in range(rec.V_REDE)]
        alvos += [box_de(e) for e in grafo.etiquetas_papel.values()]
        batidas = [
            (k, i) for k in pares for i, alvo in enumerate(alvos)
            if fc.caixas_colidem(grafo.caixa_rotulo[k], alvo, folga=0.04)
        ]
        self.check("rotulo x no/etiqueta s,t", not batidas, str(batidas[:4]))

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

    # -- F. painel de código: paginação, gutter, cabeçalho ----------------
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
        self.check("conteudo de toda pagina dentro da moldura", not fora, str(fora))

        # 1. limite de linhas e partição exata das funções
        grande = [
            (p.funcao.nome, p.k, len(p.linhas_fisicas))
            for p in codigo.paginas if len(p.linhas_fisicas) > fc.MAX_LINHAS_PAGINA
        ]
        self.check(
            f"toda pagina <= {fc.MAX_LINHAS_PAGINA} linhas fisicas",
            not grande, str(grande[:3]),
        )

        buracos = []
        sobrepostos = []
        for funcao, indices in zip(codigo.funcoes, codigo._paginas_da_funcao):
            vistos: dict[int, int] = {}
            for indice in indices:
                for lineno in codigo.paginas[indice].mapa_linha:
                    vistos[lineno] = vistos.get(lineno, 0) + 1
            esperado = set(range(funcao.inicio, funcao.fim + 1))
            if set(vistos) != esperado:
                buracos.append((funcao.nome, sorted(esperado - set(vistos))[:4]))
            repetidos = [l for l, n in vistos.items() if n > 1]
            if repetidos:
                sobrepostos.append((funcao.nome, repetidos[:4]))
        self.check("paginas particionam as linhas da funcao", not buracos, str(buracos[:3]))
        self.check(
            "linha-fonte pertence a exatamente uma pagina",
            not sobrepostos, str(sobrepostos[:3]),
        )

        # toda linha executada cai em exatamente uma página
        sem_pagina = []
        multiplas = []
        paginas_usadas = set()
        for p in passos:
            try:
                indice = codigo._view(p)
            except LookupError:
                sem_pagina.append((p.modulo, p.linha))
                continue
            paginas_usadas.add(indice)
            pagina = codigo.paginas[indice]
            ocorrencias = sum(
                1 for outro in codigo.paginas
                if outro.funcao is pagina.funcao and outro.contem(p.linha)
            )
            if ocorrencias != 1:
                multiplas.append((p.linha, ocorrencias))
        self.check("toda linha executada tem pagina", not sem_pagina, str(sem_pagina[:3]))
        self.check("toda linha executada em exatamente 1 pagina", not multiplas, str(multiplas[:3]))
        paginas_executaveis = {
            i
            for i, pagina in enumerate(codigo.paginas)
            if any(
                p.modulo == pagina.funcao.modulo
                and pagina.funcao.inicio <= p.linha <= pagina.funcao.fim
                and pagina.contem(p.linha)
                for p in passos
            )
        }
        self.check(
            "toda pagina com linha executada esta na sequencia",
            paginas_usadas == paginas_executaveis,
            f"{len(paginas_usadas)}/{len(paginas_executaveis)}",
        )
        funcoes_usadas = {codigo.paginas[i].funcao.nome for i in paginas_usadas}
        self.check(
            f"toda funcao e usada ({len(codigo.funcoes)}/{len(codigo.funcoes)})",
            funcoes_usadas == {f.nome for f in codigo.funcoes},
            str(sorted({f.nome for f in codigo.funcoes} - funcoes_usadas)),
        )

        # 2. cabeçalho: p.k/n sempre; sufixo SÓ quando a página é alcançada
        #    por uma troca adjacente na mesma função (entrada pela direção real).
        def rotulo_base(pagina):
            f = pagina.funcao
            return (
                f"{f.nome} · {Path(f.arquivo).name}:{f.inicio}–{f.fim}"
                f" · p.{pagina.k}/{pagina.n}"
            )

        def rotulo_esperado(pagina, origem):
            texto = rotulo_base(pagina)
            if pagina.n == 1 or origem is None:
                return texto
            adjacente = (
                origem.funcao is pagina.funcao
                and origem.n == pagina.n
                and abs(origem.k - pagina.k) == 1
            )
            if not adjacente:
                return texto
            if pagina.k == origem.k + 1:
                return texto + f" · ▸ continuação da p.{origem.k}/{pagina.n}"
            return texto + f" · ◂ volta da p.{origem.k}/{pagina.n}"

        cabecalhos_ruins = []
        largos = []
        for pagina, cabecalho in zip(codigo.paginas, codigo.cabecalhos):
            rotulo = cabecalho.original_text
            if rotulo != rotulo_base(pagina):
                cabecalhos_ruins.append((pagina.funcao.nome, pagina.k, rotulo))
            if cabecalho.width > LARGURA_UTIL_CODIGO:
                largos.append(
                    (pagina.funcao.nome, pagina.k, round(cabecalho.width, 2))
                )
        self.check(
            "cabecalho base: p.k/n sem marcador inventado",
            not cabecalhos_ruins, str(cabecalhos_ruins[:2]),
        )
        self.check(
            "cabecalho cabe na largura util (<= 7.54)",
            not largos, str(largos[:2]),
        )

        # 2b. a troca real reescreve o cabeçalho da página que entra
        codigo_trocas = fc.CodePanel(self.algoritmo)
        anterior = None
        alcancadas: set[int] = set()
        trocas_ruins = []
        check_p2 = None
        for passo in passos:
            if anterior is None:
                codigo_trocas.encaixar(passo)
            elif codigo_trocas.mudou(passo):
                origem = codigo_trocas.paginas[codigo_trocas.ativo]
                codigo_trocas.trocar(passo)
                alcancadas.add(codigo_trocas.ativo)
                atual = codigo_trocas.paginas[codigo_trocas.ativo]
                obtido = codigo_trocas.cabecalhos[codigo_trocas.ativo].original_text
                esperado = rotulo_esperado(atual, origem)
                if obtido != esperado:
                    trocas_ruins.append(
                        (atual.funcao.nome, atual.k, atual.n, obtido, esperado)
                    )
                if (
                    atual.funcao.nome.endswith(".check")
                    and atual.k == 2
                    and origem.funcao is atual.funcao
                    and origem.k == 1
                ):
                    check_p2 = obtido
            anterior = passo
        self.check(
            "troca de pagina atualiza cabecalho pela direcao",
            not trocas_ruins, str(trocas_ruins[:2]),
        )
        inventados = [
            (pagina.funcao.nome, pagina.k, codigo_trocas.cabecalhos[i].original_text)
            for i, pagina in enumerate(codigo_trocas.paginas)
            if i not in alcancadas
            and codigo_trocas.cabecalhos[i].original_text != rotulo_base(pagina)
        ]
        self.check(
            "pagina nunca trocada nao ganha marcador",
            not inventados, str(inventados[:2]),
        )
        fn_p1 = next(
            (
                i
                for i, pagina in enumerate(codigo_trocas.paginas)
                if pagina.funcao.nome == "FlowNetwork.__init__" and pagina.k == 1
            ),
            None,
        )
        self.check(
            "FlowNetwork.__init__ p.1 sem marcador",
            fn_p1 is not None
            and codigo_trocas.cabecalhos[fn_p1].original_text
            == rotulo_base(codigo_trocas.paginas[fn_p1])
            and "▸" not in codigo_trocas.cabecalhos[fn_p1].original_text
            and "◂" not in codigo_trocas.cabecalhos[fn_p1].original_text,
            "" if fn_p1 is None else codigo_trocas.cabecalhos[fn_p1].original_text,
        )
        self.check(
            "check p.2 diz continuacao da p.1/2",
            check_p2 is not None
            and check_p2.endswith("p.2/2 · ▸ continuação da p.1/2"),
            str(check_p2),
        )

        # 3. quebra de linha: nada removido e nenhuma linha fisica > 82
        quebras_ruins = []
        colunas = []
        for pagina in codigo.paginas:
            fonte = pagina.funcao.texto.splitlines()
            atual = None
            pedacos: list[str] = []
            for lineno, texto in pagina.linhas_fisicas:
                if atual is None:
                    atual, pedacos = lineno, [texto]
                elif lineno == atual:
                    pedacos.append(texto)
                else:
                    original = fonte[atual - pagina.funcao.inicio]
                    if "".join(pedacos).split() != original.split():
                        quebras_ruins.append((pagina.funcao.nome, atual))
                    atual, pedacos = lineno, [texto]
                if len(texto) > fc.COLUNAS_MAX:
                    colunas.append((pagina.funcao.nome, lineno, len(texto)))
            if atual is not None:
                original = fonte[atual - pagina.funcao.inicio]
                if "".join(pedacos).split() != original.split():
                    quebras_ruins.append((pagina.funcao.nome, atual))
        self.check("quebra de linha preserva todos os tokens", not quebras_ruins, str(quebras_ruins[:3]))
        self.check(
            f"nenhuma linha fisica > {fc.COLUNAS_MAX} colunas",
            not colunas, str(colunas[:3]),
        )

        # 4. gutter: números REAIS, um por linha-fonte, nenhum na continuação
        gutter_ruins = []
        for pagina, gutter in zip(codigo.paginas, codigo.gutters):
            numeros = [t.text for t in gutter.submobjects]
            esperado = [str(l) for l in pagina.mapa_linha]
            if numeros != esperado:
                gutter_ruins.append((pagina.funcao.nome, pagina.k, numeros[:4], esperado[:4]))
            continuacoes = len(pagina.linhas_fisicas) - len(pagina.mapa_linha)
            if len(numeros) != len(pagina.mapa_linha) or continuacoes < 0:
                gutter_ruins.append((pagina.funcao.nome, pagina.k, "continuacao numerada"))
        self.check("gutter com numero real por linha-fonte", not gutter_ruins, str(gutter_ruins[:2]))

        # uma view por vez: o grupo estável é só a moldura
        self.check(
            "grupo estavel = moldura (sem texto fantasma)",
            len(codigo.mobject.submobjects) == 1
            and codigo.moldura in codigo.mobject.submobjects,
            str(len(codigo.mobject.submobjects)),
        )

    # -- G. páginas: troca em dois plays ----------------------------------
    def troca_pagina(self, codigo: fc.CodePanel, passos) -> None:
        codigo.encaixar(passos[0])
        alvo = next((p for p in passos if codigo.mudou(p)), None)
        self.check("existe troca de pagina para auditar", alvo is not None)
        if alvo is None:
            return
        sai, entra = codigo.trocar(alvo)
        ids_sai = {id(a.mobject) for a in sai}
        ids_entra = {id(a.mobject) for a in entra}
        self.check(
            "troca de pagina devolve dois plays nao vazios",
            len(sai) > 0 and len(entra) > 0,
            f"{len(sai)} sai / {len(entra)} entra",
        )
        self.check(
            "troca de pagina sem mobject compartilhado",
            not (ids_sai & ids_entra),
            f"{len(ids_sai & ids_entra)} compartilhados",
        )

    # -- H. 5 abas ---------------------------------------------------------
    def abas(self, estrutura: fc.EstruturaPanel, passos) -> None:
        chaves = {chave for chave, _rotulo in fc.ABAS[self.algoritmo]}
        self.check(
            "5 abas do contrato",
            chaves == set(fc.ORDEM_ABAS) and len(fc.ORDEM_ABAS) == 5,
            str(chaves),
        )
        self.check(
            "uma aba por passo",
            len(estrutura.abas) == len(passos),
            f"{len(estrutura.abas)} vs {len(passos)}",
        )
        self.check(
            "aba ativa nunca vazia",
            all(isinstance(a, str) and a in fc.ORDEM_ABAS for a in estrutura.abas),
            str({a for a in estrutura.abas if a not in fc.ORDEM_ABAS}),
        )
        contagem = {chave: estrutura.abas.count(chave) for chave in fc.ORDEM_ABAS}
        self.check("cada aba tem >= 8 passos", all(n >= 8 for n in contagem.values()), str(contagem))

        esperado: list[str] = []
        anterior = "rede"
        for passo in passos:
            atual = fc.aba_do_passo(passo, anterior)
            esperado.append(atual)
            anterior = atual
        esperado = fc.fundir_runs(esperado, 2)
        self.check("sequencia de abas deterministica", esperado == estrutura.abas)
        self.check(
            "fundir_runs(min_run=2) usado",
            fc.fundir_runs(["a", "b", "b", "c"], 2) == ["a", "b", "b", "b"]
            and fc.fundir_runs(["a", "b", "c"], 3) == ["a", "a", "a"],
        )
        trocas = sum(1 for a, b in zip(estrutura.abas, estrutura.abas[1:]) if a != b)
        self.check("trocas de aba em dois plays (par)", trocas % 2 == 0, f"{trocas} trocas")

    def troca_aba(self, passos) -> None:
        painel = fc.EstruturaPanel(self.algoritmo, passos)
        painel.preparar(passos[0])
        troca = None
        for passo in passos[1:]:
            _anims, _add, _rem, troca = painel.atualizar(passo)
            if troca:
                break
        self.check("existe troca de aba para auditar", troca is not None)
        if troca is None:
            return
        sai, novos = troca
        ids_sai = {id(a.mobject) for a in sai}
        ids_novos = {id(m) for m in novos}
        self.check(
            "troca de aba devolve fade-out e fade-in",
            len(sai) > 0 and len(novos) > 0,
            f"{len(sai)} sai / {len(novos)} novos",
        )
        self.check(
            "troca de aba sem mobject compartilhado",
            not (ids_sai & ids_novos),
            f"{len(ids_sai & ids_novos)} compartilhados",
        )

    # -- I. conteúdo das abas (dados reais do trace) ----------------------
    def conteudo_abas(self, estrutura: fc.EstruturaPanel, passos) -> None:
        # adj: ordem REAL da Bag em 3 passos
        ordens_ruins = []
        candidatos = [
            passos[0],
            passos[len(passos) // 2],
            passos[-1],
        ]
        for passo in candidatos:
            aba = fc._AbaAdj(estrutura)
            aba.construir(passo)
            for v, chips in aba.chips.items():
                obtido = [
                    int(g[1].original_text.split()[0][1:]) for g in chips
                ]
                esperado = [int(e["w"]) for e in (passo.estado.get("adj") or {}).get(v, [])]
                if obtido != esperado:
                    ordens_ruins.append((v, obtido, esperado))
        self.check("adj na ordem real da Bag (3 passos)", not ordens_ruins, str(ordens_ruins[:2]))

        legendas = [
            fc._AbaAdj(estrutura)._texto_caption(p.estado) for p in candidatos
        ]
        self.check(
            "adj caption: Bag real/2E=16/construcao/chave completa",
            all(
                "Bag real (LIFO)" in t
                and "entradas (2E=16)" in t
                and "w · f/C" in t
                and "▸ sai de v" in t
                and "◂ entra de v" in t
                for t in legendas
            )
            and any("em construção" in t for t in legendas),
            str(legendas[:2]),
        )
        caption_larga = []
        chip_ruins = []
        for passo in candidatos:
            aba = fc._AbaAdj(estrutura)
            aba.construir(passo)
            if aba.caption.width > 6.20 + 1e-6:
                caption_larga.append(round(aba.caption.width, 3))
            for v, grupos in aba.chips.items():
                for i, grupo in enumerate(grupos):
                    texto = grupo[1]
                    if (
                        abs(texto.font_size - 11) > 1e-6
                        or texto.width > grupo[0].width - 0.02
                    ):
                        chip_ruins.append((v, i, texto.font_size, round(texto.width, 3)))
                for i in range(len(grupos)):
                    for j in range(i + 1, len(grupos)):
                        if fc.caixas_colidem(
                            box_de(grupos[i][0]), box_de(grupos[j][0]), folga=0.02
                        ):
                            chip_ruins.append((v, i, j, "colisao"))
        self.check(
            "adj caption cabe no corpo (<= 6,20)",
            not caption_larga, str(caption_larga),
        )
        self.check(
            "adj chips 11 pt cabem e nao colidem",
            not chip_ruins, str(chip_ruins[:2]),
        )

        # edgeTo: pai e nível (derivado) batem com o estado
        passos_edge = [p for p in passos if p.estado.get("edge_to")]
        self.check("existe passo com edgeTo", bool(passos_edge))
        if passos_edge:
            passo = passos_edge[len(passos_edge) // 2]
            aba = fc._AbaEdgeTo(estrutura)
            aba.construir(passo)
            erros = []
            for v in range(rec.V_REDE):
                aresta = (passo.estado.get("edge_to") or {}).get(v)
                pai = "—" if aresta is None else str(aresta[1] if aresta[0] == v else aresta[0])
                nivel = (passo.estado.get("nivel") or {}).get(v)
                nivel = "—" if nivel is None else str(nivel)
                if aba.pais[v].text != pai or aba.niveis[v].text != nivel:
                    erros.append((v, aba.pais[v].text, pai, aba.niveis[v].text, nivel))
            self.check("edgeTo pai/nivel derivado conferem", not erros, str(erros[:2]))
            self.check(
                "edgeTo caminho s->t confere",
                aba.caminho.text == fc.fmt_caminho(passo.estado.get("caminho")),
            )
            self.check(
                "edgeTo nivel rotulado derivado",
                any(
                    m.original_text == "nível (derivado)"
                    for m in aba.todos() if isinstance(m, Text)
                ),
            )

        # marked: k do caption e chips acesos
        passos_marcados = [p for p in passos if p.estado.get("marcados")]
        self.check("existe passo com marcados", bool(passos_marcados))
        if passos_marcados:
            passo = passos_marcados[len(passos_marcados) // 2]
            aba = fc._AbaMarcados(estrutura)
            aba.construir(passo)
            k = len(passo.estado["marcados"])
            acesos = {v for v, on in aba.acesos.items() if on}
            self.check(
                "marked: k do caption e chips acesos",
                f"{k}/6" in aba.caption.original_text
                and acesos == set(passo.estado["marcados"]),
                f"{k}/6 · {sorted(acesos)}",
            )
            ultimo = aba.chips[rec.V_REDE - 1]
            folga = aba.lado_s.get_left()[0] - ultimo.get_right()[0]
            abaixo = aba.lado_s.get_top()[1] <= ultimo.get_bottom()[1] - 0.12 + 1e-6
            dentro = aba.lado_s.get_right()[0] <= fc.X0_ESTRUTURA + 6.20 + 1e-6
            separado = not fc.caixas_colidem(
                box_de(aba.lado_s), box_de(ultimo), folga=0.12
            )
            self.check(
                "marked: S* com folga >= 0,12 e dentro do corpo",
                dentro
                and (folga >= 0.12 - 1e-6 or abaixo)
                and separado,
                f"folga={folga:.3f} abaixo={abaixo} dentro={dentro}",
            )

        # nenhuma cor nova nas 5 abas
        passos_amostra = [
            passos[0],
            passos[len(passos) // 4],
            passos[len(passos) // 2],
            passos[-1],
        ]
        cores = set()
        for chave in fc.ORDEM_ABAS:
            for passo in passos_amostra:
                aba = estrutura.conteudos[chave]
                mobs = aba.construir(passo)
                cores |= cores_vivas(mobs)
        self.check(
            "abas sem cor nova (PALETA + estruturais)",
            cores <= CORES_PERMITIDAS,
            str(sorted(cores - CORES_PERMITIDAS)[:4]),
        )

    # -- J. troca de aba sem fantasma -------------------------------------
    def fantasmas(self, estrutura, passos) -> None:
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

        passo_adj = next(p for p in passos if p.estado.get("adj"))
        adj = fc._AbaAdj(estrutura)
        adj.construir(passos[0])
        antes = list(adj.chips[0])
        adj.sincronizar(passo_adj)
        vivos_a = adj.todos()
        self.check(
            "aba adj: chips vivos cobrem a lista atual",
            all(g in vivos_a for grupos in adj.chips.values() for g in grupos),
            f"{len(vivos_a)} mobjects vivos",
        )


    # -- J2. troca de aba remove 100% da aba anterior (simulacao de cena) --
    def troca_sem_fantasma(self, estrutura, passos) -> None:
        """Reproduz a troca de aba como a cena faz e exige remocao total.

        O bug real: a caption e recriada em `sincronizar`, mas `todos()`
        devolvia o objeto antigo (via `estaticos`) e a caption VIVA nunca era
        removida na troca - ela ficava escrevendo por cima da nova. Aqui a
        cena e simulada passo a passo: no instante da troca, tudo o que estava
        em cena tem de estar nos FadeOut emitidos.
        """
        painel = fc.EstruturaPanel(estrutura.algoritmo, passos)
        # Invariante de base: `todos()` tem de cobrir TUDO o que `construir`
        # pos em cena. Se um mobject nasce em `construir` mas fica fora de
        # `todos()`, ele nao e alcancado pelo FadeOut da troca (foi o caso dos
        # rotulos de linha da aba edgeTo, que ficavam escritos por cima).
        abas = fc.calcular_abas(estrutura.algoritmo, passos)
        for chave in fc.ORDEM_ABAS:
            idx = abas.index(chave)
            aba = painel.conteudos[chave]
            construidos = aba.construir(passos[idx])
            vivos = {id(m) for m in aba.todos()}
            fora = [
                (type(m).__name__, str(getattr(m, "original_text", "") or "")[:30])
                for m in construidos
                if id(m) not in vivos
            ]
            self.check(
                f"aba {chave}: todos() cobre o que construir pos em cena",
                not fora,
                f"{len(fora)} fora: {fora[:3]}",
            )

        cena: dict[int, object] = {id(m): m for m in painel.preparar(passos[0])}
        # Painel + trilho sao moveis do proprio painel, nunca da aba: nao contam
        # como fantasma. Os CONTADORES ficam fora daqui de proposito - sao
        # recriados a cada passo e tratados pela identidade viva de
        # `painel.contadores` logo abaixo.
        base = {id(painel.mobject), id(painel.fundo)}
        base |= {id(m) for par in painel.abas_visuais.values() for m in par}

        sobras: list[tuple[int, str, str]] = []
        reusados: list[tuple[int, str]] = []
        trocas = 0
        for i, passo in enumerate(passos[1:], start=1):
            _anims, adicionar, remover, troca = painel.atualizar(passo)
            # FadeOut dentro de `anims` tambem tira o mobject da cena (e o que
            # acontece com texto trocado por _troca); ignorar isso no teste
            # gerava falso positivo.
            saindo = _mobjects_saindo(_anims)
            if troca is None:
                for m in remover:
                    cena.pop(id(m), None)
                for k in saindo:  # `saindo` ja e um conjunto de ids
                    cena.pop(k, None)
                for m in adicionar:
                    cena[id(m)] = m
                # o contador vivo sempre existe em cena (o antigo saiu acima
                # quando o FadeOut foi detectado)
                cena[id(painel.contadores)] = painel.contadores
                continue

            trocas += 1
            sai, novos = troca
            removidos = {id(a.mobject) for a in sai if getattr(a, "mobject", None) is not None}
            removidos |= saindo
            for chave, mob in cena.items():
                if chave in base or chave in removidos:
                    continue
                if chave == id(painel.contadores):  # contador vivo
                    continue
                texto = getattr(mob, "original_text", None) or getattr(mob, "text", "")
                sobras.append((i, painel.ativa, str(texto)[:40]))
            # na troca, a cena passa a ser exatamente a aba nova + contador
            cena = {id(m): m for m in novos}
            cena[id(painel.contadores)] = painel.contadores
            for k in base:
                cena.pop(k, None)
            for m in novos:
                if id(m) in removidos:
                    reusados.append((i, str(getattr(m, "text", ""))[:30]))

        self.check(
            "troca de aba remove tudo o que estava em cena",
            not sobras,
            f"{len(sobras)} sobras em {trocas} trocas: {sobras[:3]}",
        )
        self.check(
            "conteudo novo de aba nao reusa mobject removido",
            not reusados, str(reusados[:3]),
        )
        self.check(
            "houve trocas de aba para testar",
            trocas >= 5, f"{trocas} trocas",
        )

    # -- K. painel de estado ----------------------------------------------
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

    # -- L. ritmo (§A) -----------------------------------------------------
    def ritmo(self, codigo: fc.CodePanel, estrutura: fc.EstruturaPanel, passos) -> None:
        duracao = []
        for i, passo in enumerate(passos):
            troca_aba = i > 0 and estrutura.abas[i] != estrutura.abas[i - 1]
            troca_pag = codigo._view(passo) != (
                codigo._view(passos[i - 1]) if i > 0 else codigo._view(passos[0])
            )
            play = fc.RITMO["play_destaque"] if fc.FlowExecucaoBase._tem_flash(passo) else fc.RITMO["play"]
            pausa = fc.RITMO["pausa"].get(round(passo.pausa, 2), fc.RITMO["pausa"][0.55])
            extra = 2 * fc.RITMO["fade"] if (troca_aba or troca_pag) else 0.0
            duracao.append(play + extra + max(0.0, pausa - extra))
        minimo = min(duracao)
        maximo = max(duracao)
        self.check(
            "passo entre 0.60 e 1.00 s",
            0.60 - 1e-9 <= minimo and maximo <= 1.00 + 1e-9,
            f"{minimo:.3f}..{maximo:.3f}",
        )
        self.check("nenhum passo < 0.5 s", minimo >= 0.5, f"{minimo:.3f}")


def main() -> int:
    print(f"contrato: PLANO_VISUAL_FLUXO_V2.md · quadro {config.frame_width}x{config.frame_height}")
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
        portao.troca_pagina(codigo, passos)
        portao.abas(estrutura, passos)
        portao.troca_aba(passos)
        portao.conteudo_abas(estrutura, passos)
        portao.fantasmas(estrutura, passos)
        portao.troca_sem_fantasma(estrutura, passos)
        portao.estado(painel, passos, estrutura.max_iteracao)
        portao.ritmo(codigo, estrutura, passos)

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
