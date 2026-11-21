# RELATÓRIO — fase `codificador` · PLANO_VISUAL_FLUXO_V4

Data: 2026-11-20. Contrato: `docs/planos/PLANO_VISUAL_FLUXO_V4.md` §A–§E (o plano vence sobre o
briefing em caso de conflito). Trace: `src/flow_record.py` **intocado** (fechado pela fase
`algoritmo`), `stages` sha `c19ee524057409482c65b7dbac8bbc89124e3e802a53566c0d9b59540f792a3a`.

Esta execução **retomou** o trabalho de duas runs anteriores que morreram por limite do provedor
depois de escrever no disco: auditou item por item, fechou duas invariantes geométricas do §A.4
que o validador só citava no texto, e rodou a aceitação completa. Nenhum render.

> **Delta da revisão 4.1 (2026-11-20) — §B.6 + §E.1-5 + §F.** O `Flash` do elemento novo passou
> a sair também no **ramo de troca de aba** de `EstruturaPanel.atualizar` (antes o realce local só
> existia nas 5/5 escritas que caíam em aba já ativa). Resultado medido: **70 (EK) / 55 (DFS)**
> adições com `Flash` de um elemento + **12/12** reconstruções (`reset`) só com `FadeIn` do corpo =
> **82 / 67** adições, com **0,0 s** de acréscimo (duração 1013,9 s / 864,3 s inalterada). Snapshot
> do código anterior em `src/_snapshot_v4/`. Detalhe no **§7**.

> **Bugfix de ritmo 4.2 (2026-11-21) — §8.** `EstruturaPanel._estilo_abas` devolvia
> `mobject.animate...` sem `run_time`; cada troca de aba custava **1,0 s** de fade-out em vez de
> `2/15 s` e o render 480p saiu **+85,8 s (EK) / +64,1 s (DFS)** acima do modelo. Agora o
> `run_time` é `RITMO["fade"]`; nenhuma animação da troca tem 1,0 s. Detalhe, prova e números
> antes/depois no **§8**.

## 1. Arquivos e linhas

| arquivo | diff vs. V3 (`src/_snapshot_v3/`) | conteúdo |
|---|---|---|
| `src/flow_common.py` | **+258 / −95** | `estado_da_busca` (187‑200), `aba_do_passo` (1706‑1725), `fundir_runs` (1728‑1753), `calcular_abas` (1756‑1764), `_AbaBusca` (1902‑2110), `_AbaMarcados.sincronizar` (2191‑2252), `_AbaEdgeTo` (2259‑2597) |
| `validate_flow_layout.py` | **+415 / −27** | §E.1 (a)–(f) + distribuição/trocas + `PARES_EDGE_TO` em todos os passos |
| `validate_flow_videos.py` | **+2 / −2** | `ALVO` (54‑55) |

Nesta run, o único delta de código foi em `validate_flow_layout.py` (l.912‑913, 973‑982,
1002‑1011): as invariantes 2 e 3 do §A.4 passaram a ser **medidas** (antes o rótulo do check
"bloco sempre abaixo da fila" só cobria `caixa_dentro`).

## 2. Geometria final do bloco da `edgeTo`

```
X_INFO    = X0_ESTRUTURA = -5.000      Y_CAMINHO = -2.740      Y_GARGALO = -2.960
fila      X_FILA = -4.600 · LARGURA 0.72 · PASSO 0.86 (6 chips: -4.60 … +0.42) · y -2.310…-1.890
bloco     medido nos 146+141 passos:  x -5.000…-4.317 · y -3.014…-2.687
folgas    fila×bloco 0.377 (topo -2.687 vs base do chip -2.310)
          guia×bloco 0.220 (base -3.014 vs topo do guia -3.234)
          caminho×gargalo 0.088 · bloco dentro de (-5.00…1.14 × -3.20…-1.30)
```

Textos inalterados (`fmt_caminho(estado)`, `f"b = {fmt_num(gargalo)}"`, fonte 10,
`aligned_edge=LEFT`); fila, `frente`, `fim`, setas, caption e `vazio` idênticos.

## 3. Transições de aba (medidas na sequência viva)

EK — **99**: `marcados→busca` 30 · `edge_to→marcados` 25 · `busca→edge_to` 24 ·
`busca→marcados` 5 · `edge_to→rede` 5 · `rede→edge_to` 5 · `rede→marcados` 2 · `adj→rede` 1 ·
`busca→rede` 1 · `marcados→edge_to` 1.

DFS — **74**: `edge_to→marcados` 20 · `marcados→busca` 20 · `busca→edge_to` 19 ·
`edge_to→rede` 5 · `rede→edge_to` 5 · `rede→marcados` 2 · `adj→rede` 1 · `busca→rede` 1 ·
`marcados→edge_to` 1.

Distribuição: EK `99/572/144/146/549` · DFS `99/353/139/141/549` (adj/busca/marcados/edge_to/rede).

## 4. Contagem de animações (por objeto, `atualizar` real)

| | EK | DFS |
|---|---|---|
| adições estruturais (write) | **82** (26 `edge_to` + 31 `marcados` + 25 `busca`) | **67** (21 + 26 + 20) |
| adições com `Flash` (realce de 1 elemento) | **70** (20 `edge_to` + 25 `marcados` + 25 `busca`) | **55** (15 + 20 + 20) |
| … das quais no ramo de **troca** de aba (rev. 4.1) | 65 | 50 |
| … das quais na **mesma aba** (`sincronizar`) | 5 | 5 |
| `Indicate` (só `marcados`, sempre com `Flash`) | 25 | 20 |
| reconstruções (`reset`) só com `FadeIn` do corpo | **12** (6 `edge_to` + 6 `marcados`) | **12** (6 + 6) |
| pops (só `FadeOut`) | 18 | 20 |
| `FadeIn` / `FadeOut` totais no vídeo | 285 / 292 | 246 / 255 |

> **Nota da rev. 4.1 (fechada).** Como a aba é a estrutura escrita pela linha (§B.2), a linha que
> escreve é quase sempre a linha que troca de aba: **65/70 (EK) e 50/55 (DFS)** dos realces saem
> agora do ramo de troca. O `Flash` entra em `anims` (não no play do fade-in), então toca no play
> seguinte — o de indicador+grafo+estado — com o mesmo `run_time` (0,40 / 0,4667 s): **nenhum play
> nem segundo de acréscimo**. As 12/12 reconstruções continuam sem realce (não há elemento único a
> piscar) e aparecem pelo `FadeIn` do corpo da aba nova.

## 5. Verificações aprovadas

1. `python validate_flow_layout.py` → **PORTAO DE LAYOUT: VERDE (277 verificações, 0 falhas)**
   (137 EK + 140 DFS; eram 269 antes das duas invariantes do §A.4, 273 na V4 e 277 com os dois
   checks novos da rev. 4.1: `realce` e `total = reais + reconstruções`, +2 por algoritmo).
   - `edgeTo V4`: **0 colisões nos 146 (EK) e 141 (DFS)** em cada um dos 14 pares do §A.4.
   - `bloco 0,30 abaixo da fila`: 146/141 passos, 0 violações.
   - `caminho/gargalo com largura <= 6,20`: 146/141 passos, 0 violações.
   - `distribuicao das 5 abas confere` ✓ · `99/74 trocas` ✓ · `sem fantasma` 99/74 ✓.
   - `escrita manda na aba (sequencia crua)` ✓ · `fusao nao muda nenhuma posicao com escrita` ✓ ·
     `fundir_runs protege run de escrita` ✓.
   - `24 (EK) / 19 (DFS) edge_to nao antecipam marcados` ✓ · `reset de marcados nao acende chip` ✓.
   - `escrita visivel na propria linha`: 105 (EK) / 87 (DFS) passos ✓.
   - `82 / 67 adicoes estruturais` (26/31/25 e 21/26/20) ✓ · **`70 / 55 adicoes com Flash de UM
     elemento`** ✓ (`sem_realce` vazio) · **`12/12 reconstrucoes so com FadeIn do corpo`** ✓
     (`ruins` vazio: nenhum `Flash`/`Indicate` no reset e `troca is not None`) ·
     **`total 82 = 70 + 12` / `total 67 = 55 + 12`** ✓ ·
     `18 / 20 pops so com FadeOut` ✓ · `passo sem escrita e sem mudanca nao pisca` ✓ (110/110).
   - `aba Busca sem textos de edgeTo/marcados` ✓ (`conteudos == {"inspecoes"}`).
   - mantidos: fonte 11.06, páginas 18/19, views 14/15, passos 1510/1281, gutter, legenda 7/7,
     guia, selo, setas, dois plays, `todos()`.
2. `python validate_flow_scenes.py` → 8/8 ok, sha `c19ee524057409482c65b7dbac8bbc89124e3e802a53566c0d9b59540f792a3a`.
3. Duração do modelo (`build/_medir_duracao_v4.py`): EK **1013,9 s = 16,90 min**, passo 433 em
   **287,0 s**; DFS **864,3 s = 14,40 min**. Passo individual entre 0,600 e 1,000 s.

## 6. Desvios do plano (todos justificados, nenhum muda o contrato visual)

| # | plano | código | por quê |
|---|---|---|---|
| 1 | `Flash(..., stroke_width=2)` | `line_stroke_width=2` | assinatura real do Manim 0.22 (`Flash.__init__` não tem `stroke_width`) |
| 2 | §B.5.4 chips que mudam de índice → `animate.move_to` | `chip.move_to(pos)` imediato | `animate.move_to` no grupo + `animate` no filho no mesmo `play` se anulam; e a descoberta sempre **acrescenta** no fim (não há mudança de índice fora do reset, que reconstrói a aba) |
| 3 | §B.2 `fundir_runs` com only `any(protegidos[i:j])` | + `protegido or= protegidos[i-1]` | exigido pelo teste (b) do §E.1: `["b","b","e","b"]` tem de ficar `["b","b","e","b"]` |
| 4 | §B.5 `Indicate(chip, color=..., scale_factor=1.12)` | idem, com `_aplicar_estilo` antes | o alvo do `Indicate` precisa ser a cópia viva do chip |

Nenhum item ficou impossível; nenhum número do plano foi contrariado.

## 7. Delta da revisão 4.1 (só o realce na troca de aba)

### 7.1 O que mudou

Snapshot do código V4 anterior em `src/_snapshot_v4/` (`flow_common_v4.py`,
`validate_flow_layout_v4.py`), conforme a regra de preservação.

| arquivo | diff vs. `src/_snapshot_v4/` | mudança |
|---|---|---|
| `src/flow_common.py` | **+40 / −1** | `EstruturaPanel.estado_anterior` (2806, `None` no `__init__`), gravado em `preparar` (2885) e **nos dois ramos** de `atualizar` (2924, 2929); **novo** `_realce` (2932‑2960); ramo de troca: `anims = self._realce(passo) + self._atualizar_contadores(passo)` (2921) |
| `validate_flow_layout.py` | **+32 / −12** | §E.1-5 (l.1190‑1277): saiu `entrada = True` por `troca`, entraram as duas classes explícitas (`reset` × `Flash`/`Indicate`) e quatro checks no lugar de dois |

O helper de contadores é **`_atualizar_contadores`** (nome já existente, preservado) — o plano
citou `<helper de contadores já usado nesse ramo>`, que é exatamente ele.

`play_step`, `RITMO`, `PALETA`, `GUIA_SIMBOLOS`, `CodePanel`, `StatePanel`, `FlowGraphView`,
`_AbaBusca`/`_AbaMarcados`/`_AbaEdgeTo`, `flow_record.py`, `*_scene_new.py` e
`validate_flow_scenes.py`: **não tocados**.

### 7.2 Por que o `Flash` não vira tempo

```
ramo de troca  (play_step):  play(sai, 2/15) → add(novos) → play(FadeIn corpo, 2/15)
                             → play(indicador + grafo + estado + [Flash, Indicate], run_time)
                             → wait(max(0, pausa − 2·fade))
```

O `_realce` devolve animações e elas entram em `anims` — o **mesmo** play que já existia (0,40 s
ou 0,4667 s). Nada de play extra, nada de `wait` extra: a duração do modelo não muda.

### 7.3 Números medidos da 4.1

| medida | EK | DFS |
|---|---|---|
| adições com `Flash` de elemento único | **70** | **55** |
| … no ramo de troca / na mesma aba | 65 / 5 | 50 / 5 |
| `Indicate` (`marcados`) | 25 | 20 |
| reconstruções `reset` (só `FadeIn` do corpo, `troca is not None`) | **12** | **12** |
| total de adições | **82** | **67** |
| adições sem realce (`sem_realce`) | **0** | **0** |
| `edge_to` sem colisão (14 pares do §A.4) | 146 | 141 |
| duração do modelo | **1013,9 s** (16,90 min) | **864,3 s** (14,40 min) |
| passo 433 | **287,0 s** | 287,5 s |

Fonte do realce por ramo: `build/_medir_realce_v41e.py` (descartável, só mede classes de
animação de `atualizar`). Duração: `build/_medir_duracao_v4.py` (inalterado, mesmo modelo).

### 7.4 Comportamento do teste novo

```python
realce = bool(tipos.get("Flash") or tipos.get("Indicate"))
if tipo == "reset":                 # 12/12: só FadeIn do corpo
    reconstrucoes += 1
    if realce or not troca:
        ruins.append((i, passo.escrita, tipo))
elif realce:                        # 70/55: exige Flash
    reais += 1
else:
    sem_realce.append((i, passo.escrita, tipo))
```

O `troca[1] is not None → entrada = True` (atalho desonesto: aceitava o `FadeIn` do corpo inteiro
como se fosse realce) foi removido. Agora o reset é cobrado pelo lado oposto — **não pode** ter
`Flash`/`Indicate` **e precisa** de `troca` —, e a adição pontual exige a classe de realce, nos
dois ramos. O check `passo sem escrita e sem mudanca nao pisca` continua ao lado, cobrindo o
"nada pisca à toa". Nenhum outro check foi relaxado.

### 7.5 Aceitação da 4.1 (rodada final)

```
python validate_flow_layout.py  → VERDE (277 verificações, 0 falhas)   [exit 0]
    EK  137 OK · 70 + 12 = 82 · 146 edge_to sem colisão
    DFS 140 OK · 55 + 12 = 67 · 141 edge_to sem colisão
python validate_flow_scenes.py  → 8/8 ok · sha c19ee524057409482c65b7dbac8bbc89124e3e802a53566c0d9b59540f792a3a  [exit 0]
duração do modelo               → EK 1013,9 s (passo 433 em 287,0 s) · DFS 864,3 s
```

Nenhum render executado.

## 8. Bugfix de ritmo da rev. 4.2 — `_estilo_abas` fora do `RITMO`

### 8.1 Diagnóstico (fechado pela fase `pipeline`, refeito aqui para registro)

Conta do desvio entre render e modelo, sem sobra:

| peça | EK | DFS |
|---|---|---|
| render 480p medido | **1106,532 s** | **935,199 s** |
| modelo (`build/_medir_duracao_v4.py`) | 1013,9 s | 864,3 s |
| os 2.976 `play` somados (modelo) | 900,533 s | — |
| excesso por troca: `1,0 − 2/15` = **0,8667 s** × trocas | 99 → **+85,8 s** | 74 → **+64,1 s** |
| pré-roll `montar()` + fecho `fechar()` | 6,7 s | 6,7 s |
| `modelo + excesso + pré-roll` | **1106,40** | **935,13** |

Causa: `EstruturaPanel._estilo_abas` devolvia `caixa.animate.set_stroke(...).set_fill(...)` e
`texto.animate.set_color(...)` — `_AnimationBuilder` que o `prepare_animation` converte em
`_MethodAnimation`, e cujo `__init__` cai em `MoveToTarget` → `Animation` com `run_time` default
**1,0 s**. As 10 animações (5 abas × caixa + texto) entram em `sai` (`atualizar`, l.2924) e são
tocadas no `play(*sai_aba)` de `play_step` (l.3085), que **não** passa `run_time`: o play vale
`max(run_time) = 1,0 s` em vez do `2/15` dos `FadeOut` que dividem o mesmo play.

### 8.2 Correção (um arquivo, uma função)

`src/flow_common.py`, `EstruturaPanel._estilo_abas` (2836‑2855):

```python
caixa.animate(run_time=RITMO["fade"]).set_stroke(...).set_fill(...)
texto.animate(run_time=RITMO["fade"]).set_color(...)
```

Chave usada: **`RITMO["fade"]` = `2/15` = 0,133333 s** — a mesma de `CodePanel.TEMPO_FADE`
(troca de página, 1431‑1440), a dos `FadeOut` do conteúdo antigo (2911, 2914) e a do `FadeIn` do
corpo novo (`play_step`, 3087). O valor vai no **construtor** do builder
(`animate(run_time=...)`): no Manim 0.22 o `_AnimationBuilder.__call__` guarda `anim_args`
("Animation arguments must be passed before accessing methods") e `build()` aplica por `setattr`
na animação pronta.

Diff da função: **+12 / −3** (comentário de ritmo + as duas cadeias de estilo). O arquivo inteiro
contra `src/_snapshot_v4/flow_common_v4.py` dá **+52 / −4**: os outros +40 / −1 são o delta da
rev. 4.1 já registrado no §7 (o congelamento é de antes do `_realce`), nada de novo.

**Nenhum outro ponto** do caminho de troca de aba tem `_MethodAnimation` implícita:
`CodePanel.trocar` (1432‑1440) já fixa `run_time=t` nos quatro `FadeOut`/`FadeIn`; `_troca_texto`
(2454) e `_animar_estilo` (2382) devolvem animações que caem no play principal, que recebe
`run_time=` explícito (3112) — e `compile_animations` aplica os kwargs a **todas** as animações do
play, sobrescrevendo o default. Não havia mais nada a corrigir.

### 8.3 Instrumentação (sem render)

`build/_medir_ritmo_aba_v4.py` reproduz a sequência viva de `EstruturaPanel.atualizar` e mede cada
animação do play de saída pelo caminho do próprio Manim: `prepare_animation` (resolve o builder)
+ `Scene.get_run_time` (o `max(run_time)` que vira `scene.duration`). O modo `--antes` rebindiza a
`_estilo_abas` 4.1 (mesmo código, só o bug) e re-mede:

| | antes (4.1) | agora (4.2) |
|---|---|---|
| EK · 99 trocas — `play(sai)` | **1,0 s** ×99 | **0,133333 s** ×99 |
| EK · `play(entra)` | 0,133333 s ×99 | 0,133333 s ×99 |
| EK · `run_time` por animação do `sai` | `FadeOut` 0,133333 ×1677 · `_MethodAnimation` **1,0** ×990 | `FadeOut` 0,133333 ×1677 · `_MethodAnimation` **0,133333** ×990 |
| EK · soma dos 2 plays | 112,20 s (excesso **+85,80**) | 26,40 s (excesso **0,00**) |
| DFS · 74 trocas — `play(sai)` | **1,0 s** ×74 | **0,133333 s** ×74 |
| DFS · `run_time` por animação do `sai` | `FadeOut` 0,133333 ×1407 · `_MethodAnimation` **1,0** ×740 | `FadeOut` 0,133333 ×1407 · `_MethodAnimation` **0,133333** ×740 |
| DFS · soma dos 2 plays | 83,87 s (excesso **+64,13**) | 19,73 s (excesso **0,00**) |

Os 10 `_MethodAnimation` por troca — 5 abas × 2 (caixa + texto) — estão todos em **0,133333 s**;
nenhum play de saída com duração ≥ 1,0 s em 99/74 trocas. Saída crua: `build/_saida_ritmo_aba.txt`.

### 8.4 Aceitação

```
python validate_flow_layout.py   → VERDE (277 verificações, 0 falhas)   [EK 137 · DFS 140 · exit 0]
python validate_flow_scenes.py   → 8/8 ok · sha c19ee524057409482c65b7dbac8bbc89124e3e802a53566c0d9b59540f792a3a
duração do modelo (inalterada)   → EK 1013,9 s (16,90 min) · DFS 864,3 s (14,40 min)
pré-roll + fecho (montar+fechar) → 2,9 + 3,8 = 6,7 s
total previsto para o 480p       → EK 1020,6 s · DFS 871,0 s
```

O modelo **não mudou** — ele nunca contou o bug: já orçava `2·fade` por troca
(`_medir_duracao_v4.py`, l.39‑44). O que muda é o render, que agora fecha com ele:
1013,9 + 6,7 = **1020,6 s** e 864,3 + 6,7 = **871,0 s**, contra 1106,532 / 935,199 s medidos antes.

Congelamento: `src/_snapshot_v4/flow_common_v4.py` (4.1) **intocado**; a versão corrigida foi
congelada em `src/_snapshot_v4/flow_common_v4_r2.py`. `play_step`, `RITMO`, `PALETA`,
`GUIA_SIMBOLOS`, cenas, `flow_record.py`, `validate_flow_scenes.py` e `algs4-py/`: **não
tocados**. Nenhum render; nada em `entregas/`.
