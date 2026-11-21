# BRIEFING — `codificador` · implementar PLANO_VISUAL_FLUXO_V4

> **STATUS: LIBERADO.** O relatório `docs/relatorios/RELATORIO_ALGORITMO_ESTADO_POS.md` foi
> entregue (Gate 0 8/8, 153/135 passos com `escrita`, sha `c19ee524…a3a`). `src/flow_record.py`
> está **fechado** para esta fase. Leia `PLANO_VISUAL_FLUXO_V4.md` §A–§E antes de editar;
> em conflito entre este briefing e o plano, **o plano vence**.

Origem: fase VISUAL (revisão 4). Contrato: `PLANO_VISUAL_FLUXO_V4.md` (**medido**).
Entrega: `src/flow_common.py`, `validate_flow_layout.py`, `validate_flow_videos.py`.

Ambiente: `manim-animations/`, `.\.venv\Scripts\python.exe`, `$env:PYTHONIOENCODING='utf-8'`,
rodando de `src/` (ou com `sys.path` apontando para ele).

**Não tocar**: `src/flow_record.py`, `src/*_scene_new.py`, `RITMO`, `PALETA`,
`GUIA_SIMBOLOS`, `StatePanel`, `CodePanel`, `FlowGraphView`, `algs4-py/`. Nada de truncar
código, nada de render.

## 0. Antes de editar (obrigatório)

```
copy src\flow_common.py          src\_snapshot_v3\flow_common_v3.py
copy validate_flow_layout.py     src\_snapshot_v3\validate_flow_layout_v3.py
```

(`src/_snapshot_v3/` já tem `flow_record_v3.py` e `validate_flow_videos_pre_fix9.py` — **não**
sobrescrever.)

## 1. Colisão da `edgeTo` — `src/flow_common.py`

```python
class _AbaEdgeTo:                     # l.2223
    X_INFO    = X0_ESTRUTURA          # -5.00   (era X0_ESTRUTURA + 5.14)
    Y_CAMINHO = -2.74                 # era -2.02
    Y_GARGALO = -2.96                 # era -2.30
```

Nada mais muda na aba: fila (`X_FILA=-4.60`, `LARGURA=0.72`, `PASSO=0.86`, `Y_FILA=-2.10`),
`frente`, `fim`, setas, caption e `vazio` ficam iguais; os **textos** de `caminho`/`gargalo`
continuam os mesmos (`fmt_caminho`, `f"b = {fmt_num(...)}"`), `aligned_edge=LEFT`, fonte 10.

Prova esperada: 0 colisões nos **146** passos `edge_to` do EK e **141** do DFS (hoje: 90/120 no
EK, 180 eventos `chip5×caminho` + `chip5×gargalo`).

## 2. Aba = estrutura escrita pela linha

```python
def aba_do_passo(passo, aba_anterior: str) -> str:      # l.1690
    if passo.escrita is not None:      # NOVO, primeira regra
        return passo.escrita
    ...                                # resto igual
```

```python
def fundir_runs(abas, min_run: int = 2, protegidos: list[bool] | None = None):   # l.1710
    ...
        if (j - i) < min_run and i > 0:
            protegido = bool(protegidos) and any(protegidos[i:j])
            if not protegido:
                for k in range(i, j):
                    saida[k] = saida[i - 1]
```

`calcular_abas` (l.1725): `return fundir_runs(abas, 2, [p.escrita is not None for p in passos])`.

Sem `protegidos` o comportamento antigo tem de continuar idêntico (o autoteste do validador usa
`fundir_runs(["a","b","b","c"], 2)`).

## 3. Estado que a aba mostra (`estado`, não `estado_pos`)

Medido: `Step.estado` **já é** o pós-linha; `Step.estado_pos` é o pós-linha **da linha
seguinte** (antecipa). Exceção única: o push do `dfs` (81/97, linha "pré-chamada"), onde
`estado` ainda não tem `w` na pilha.

```python
def estado_da_busca(passo) -> dict:
    est = passo.estado
    if passo.escrita != "busca" or passo.estado_pos is None:
        return est
    if len(passo.estado_pos.get("pilha") or []) > len(est.get("pilha") or []):
        return {**est, "pilha": list(passo.estado_pos["pilha"])}
    return est
```

`_AbaEdgeTo` e `_AbaMarcados` usam `passo.estado` **sempre** (usar `estado_pos` pintaria o chip
de verde uma linha antes da 91). `_AbaBusca` usa `estado_da_busca(passo)` só para a lista;
`inspeções`/contadores vêm de `passo.estado`.

## 4. Aba `busca` sem `edgeTo`/`marcados`

Em `_AbaBusca` (l.1871-2085): apagar `self.edge_to`, `self.marcados`, os dois `Text` de
`construir` (l.1973-1982), o bloco `"edgeTo"`/`"marcados"` de `sincronizar` (l.2054-2069), as
duas entradas de `todos()`; `self.conteudos` fica só `{"inspecoes": ""}`.
**Fica**: caption, chips, setas por índice, `frente`/`fim` (BFS) / `base`/`topo` (DFS),
`inspeções {n}` em `(X0_ESTRUTURA+3.60, −2.58)`.

## 5. Adição animada (incremental)

`_AbaEdgeTo.sincronizar` deixa de reconstruir a fila: `chips: dict[int, VGroup]` por **vértice**,
`estilos: dict[int, tuple]`, `setas: dict[int, Arrow]` por **índice**. Por passo: sai
`FadeOut`+`remover`, entra `FadeIn` + `Flash(centro, color=COR_ACENTO, line_length=0.14,
num_lines=8, flash_radius=0.26, stroke_width=2)` + `adicionar`, muda de índice com `move_to`,
estilo com `set_stroke`/`set_fill`, setas com `put_start_and_end_on` em todas, `caminho`/
`gargalo` só por `_troca_texto` quando o texto muda.

`_AbaMarcados.sincronizar`: `Flash(chip, color=PALETA["alcancado"][0], line_length=0.12,
num_lines=8, flash_radius=0.30)` + `Indicate(chip, scale_factor=1.12)` para
`marcados - self.acesos`.

`_AbaBusca.sincronizar`: o `FadeIn` do chip novo ganha o mesmo `Flash` em `COR_ACENTO`; o pop
continua só `FadeOut`.

Tudo dentro do `play` do passo (sem tempo extra). Troca de aba continua **dois** `self.play`
(`play_step` não muda).

## 6. Validadores

`validate_flow_layout.py`
- l.648-655: `EK {rede 549, busca 572, marcados 144, edge_to 146, adj 99}`;
  `DFS {rede 549, busca 353, marcados 139, edge_to 141, adj 99}`.
- l.678 e l.1218: `trocas == 99` (EK) / `74` (DFS).
- l.1100-1111 (`fantasmas`): trocar `busca.edge_to` por `busca.inspecoes`.
- l.784-842: substituir a amostra única por **todos** os passos `edge_to` da sequência nova
  com `PARES_EDGE_TO` (plano §A.4), `caixa_dentro` do bloco, `bloco abaixo da fila` e
  `largura ≤ 6.20`.
- novos: (a) a sequência **crua** é `passo.escrita or aba_do_passo(...)` e, depois da fusão,
  **nenhuma posição com `escrita` muda de aba**; (b) `fundir_runs` com `protegidos`
  (`fundir_runs(["b","e"], 2, [False,True]) == ["b","e"]`); (c) sem antecipação nos **24/19**
  passos com `estado_pos["marcados"] != estado["marcados"]`; (d) escrita visível na própria
  linha por tipo (`edge_to`/`marcados`/`busca`, incl. push e `popleft`); (e) adição animada
  (`FadeIn`/`Flash`) nos passos de escrita e lista vazia quando o estado não muda;
  (f) `_AbaBusca` sem `edge_to`/`marcados`.
- manter tudo o resto (fonte 11.06, páginas 18/19, views 14/15, passos 1510/1281, gutter,
  legenda, guia, selo, setas, dois plays, `todos()`).

`validate_flow_videos.py`
- l.55: `ALVO = {"edmonds": 16.90 * 60, "ford": 14.40 * 60}` (cena de execução; o vídeo
  completo soma a intro, que não muda — comparar sempre o mesmo tipo de arquivo).

`validate_flow_scenes.py`
- **não tocar**; rodar e conferir `SHA_STAGES_ESPERADO` = `c19ee524…a3a`.

## 7. Aceitação (devolver com números)

1. `.\\.venv\\Scripts\\python.exe validate_flow_layout.py` sem falhas, com: 0 colisões nos
   **146/141** passos `edge_to`, distribuição **99/572/144/146/549** e **99/353/139/141/549**,
   trocas **99/74**, `busca` sem `edge_to`/`marcados`, escrita visível e sem antecipação.
2. `.\\.venv\\Scripts\\python.exe validate_flow_scenes.py` com o sha do `stages` inalterado.
3. Duração do modelo: **16.90 min** (EK, 1013,9 s) e **14.40 min** (DFS) — o passo 433 em
   **287,0 s** (V3: 285,9 s).
4. Nenhum render. Se precisar de frame: `-s` ou `src/_layout_check.py` (saída em `build/media`).
5. Relatório: arquivos:linhas, geometria final do bloco da `edgeTo`, a lista das 99/74
   transições de aba, contagem de `FadeIn`+`Flash`, e as verificações aprovadas.

Se algo for impossível, devolver o motivo com a medida — não improvisar.
