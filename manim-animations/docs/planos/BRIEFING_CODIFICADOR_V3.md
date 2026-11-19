# BRIEFING — `codificador` · implementar PLANO_VISUAL_FLUXO_V3

Origem: fase VISUAL (revisão 3). Contrato: `PLANO_VISUAL_FLUXO_V3.md` (medido).
Entrega: `src/flow_common.py`, `validate_flow_layout.py`, `validate_flow_videos.py`.
**Não tocar** em `src/flow_record.py` (trace gated: sha `e9975393292db428e9570e010aa23868235f6c807da3ccc33f6224a1e3e1814f`,
1734/1281 passos, 14/15 views, 18/19 páginas), no `RITMO`, na `PALETA` nem em `FUNCOES_PAINEL`.
Nada de truncar código.

Ambiente: `C:\Users\atila\Documents\RPG\manim-animations`, `.\.venv\Scripts\python.exe`,
`$env:PYTHONIOENCODING='utf-8'`.

---

## 1. Cabeçalho do código em DUAS linhas — `src/flow_common.py`

**`CodePanel._rotulo` (l.1167-1190)** passa a devolver:

```
{nome} · {arquivo_curto}:{inicio}–{fim}
parte {k} de {n}[ · ▸ continuação da parte {k-1} de {n} | · ◂ volta da parte {k+1} de {n}]
```

- Sufixo só quando há troca adjacente na mesma função (`abs(origem.k - k) == 1`) e `n > 1`;
  página nunca alcançada por troca não ganha marcador.
- `Text` **único** com `"\n"` (Manim renderiza duas linhas; `original_text` continua string).
  `_atualizar_cabecalho` (l.1192-1202) segue com `move_to(antigo, aligned_edge=LEFT)`.
- Exatos: `FlowFulkersonDFS.is_feasible · ford_fulkerson_dfs.py:110–133` +
  `parte 2 de 2 · ▸ continuação da parte 1 de 2`; `FlowNetwork.validate_vertex ·
  flow_network.py:147–149` + `parte 1 de 1`.

**`escala_codigo` (l.1029-1030)**: `Text("x", ...)` → `Text("x\ny", ...)` (altura real de
2 linhas). A fonte deve continuar **11.06 pt** (largura manda: 7.54 / 16.36).

## 2. Guia de símbolos na base da aba — `src/flow_common.py`

**Novo `GUIA_SIMBOLOS`** (perto de `ABAS`, l.1422), texto EXATO:

```python
GUIA_SIMBOLOS = {
    "rede":      "C = C(u,v) nominal · f = f(u,v) · res→ = C_f(u,v) = C−f · res← = C_f(v,u) = f",
    "busca_bfs": "frente = próximo a sair · fim = último a entrar",
    "busca_dfs": "base = primeiro da pilha · topo = chamada atual",
    "marcados":  "marked[v] = alcançado pela residual · S* = lado da fonte",
    "edge_to":   "edgeTo[v] = aresta que descobriu v · s = fonte · t = sumidouro",
    "adj":       "▸ sai de v · ◂ entra de v · chip = w · f/C",
}
```

- `EstruturaPanel`: `self.guia = Text(..., font_size=10, color=COR_BORDA_NO)` em
  `(X0_ESTRUTURA, -3.30, 0)`, `aligned_edge=LEFT`; `busca_bfs`/`busca_dfs` pelo
  `self.algoritmo`.
- `preparar` (l.2366-2378) devolve `[..., self.guia]`.
- `atualizar` (l.2382-2401): na troca de aba, `FadeOut(self.guia)` em `sai` e o guia novo em
  `novos` (entra com o corpo). O guia **não** entra em `todos()` de aba.
- `_AbaAdj._texto_caption` (l.2146-2151): remover ` · w · f/C · ▸ sai de v · ◂ entra de v`
  (hoje 7.12 > 6.20). Fica `adj[] · Bag real (LIFO) · {n} entradas (2E=16)[ · em construção]`.

## 3. Bloco `f/C` + `→C−f ←f` no grafo — `src/flow_common.py`

- `posicao_rotulo` (l.293-327): grade `t ∈ {0.50,0.44,0.56,0.40,0.60,0.36,0.64,0.32,0.68,
  0.28,0.72,0.24,0.76,0.20,0.80}`, `desvio ∈ {0,±0.16,±0.24,±0.30,±0.36,±0.42}`; novo
  parâmetro `proprio` (amostras do arco reverso da própria aresta) **penalizado** — o
  `continue` de `chave == (u,v)` deixa de isentar a própria.
- `_calcular_rotulos` (l.444-459): dim do bloco pelo pior caso do arquivo — linha 1
  `f"{f:g}/{C:g}"` fonte 13, linha 2 `f"→{C-f:g} ←{f:g}"` fonte 11; largura = max + 0.12,
  altura = soma + 0.06. Bloco medido: **0.59 × 0.33**, **0 colisões**.
- `_criar_aresta` (l.461-494): `textos[(u,v)]` = `VGroup(linha1, linha2)` sobre o fundo
  opaco; guardar `fundo_atual`/`res_atual` para o diff.
- Cores: linha 1 `#f2f4f8`; `→{C−f}` `#06d6a0` se `0`, senão `#f2f4f8`; `←{f}` `#ef476f` se
  `f > 0`, senão `#8d99ae`. Nenhuma cor nova.
- `_troca_texto` (l.583-592) vira `_troca_bloco` (um `AnimationGroup`); `animar` (l.750-752)
  e `aplicar`/`_aplicar_imediato` (l.596-675) usam `_montar_bloco`.
- Remover o rótulo temporário `res = f` de `animar` (l.775-792) e `rotulo_rev*`.

## 4. Seta da pilha no DFS — `src/flow_common.py` (`_AbaBusca`)

- Bug: `_seta(a,b)` (l.1673-1683) usa `_x(a)`/`_x(b)` com **vértices**, mas `_x` espera
  **índice**. Passa a receber `indice`:
  `x0 = _x(i-1) + 0.21 + 0.02`, `x1 = _x(i) - 0.21 - 0.02`, `y=-2.30`, `buff=0`,
  `tip_length=0.07`, `stroke_width=1.6`.
- `construir` (l.1703-1711) e `sincronizar` (l.1773-1785): `setas` por índice `1..len-1`;
  sobras `FadeOut`+`remove`; novas `FadeIn`; `put_start_and_end_on(...)` em todas a cada
  sincronização. Pilha de 1 ⇒ sem setas.

## 5. `validate_vertex`: aba herdada + selo (sem filtrar passo)

- `aba_do_passo` (l.1451-1464), l.1456:
  ```python
  if fn in ("FlowNetwork.adj", "FlowNetwork.validate_vertex") or fn.startswith("FlowEdge."):
      return aba_anterior
  ```
  Obrigatório (80 → 16 trocas no BFS; 60 → 16 no DFS).
- **Todos** os 73/63 passos entram (nenhum filtro).
- Selo no slot 5 do `StatePanel` (vazio durante a execução): em `FlowExecucaoBase.play_step`,
  `self._vv_vistos` (zera em `montar`) conta os passos de `FlowNetwork.validate_vertex` já
  executados; `self._vv_violacoes` é calculado do trace em `montar` (passos com linha 149).
  Depois de `textos = self.painel.textos_do_passo(...)`:
  ```python
  if self._vv_vistos:
      plural = "violação" if self._vv_violacoes == 1 else "violações"
      textos[4] = (f"validate_vertex {self._vv_vistos}× · {self._vv_violacoes} {plural}",
                   COR_BORDA_NO, 10)
  ```
  Posição vem do `StatePanel` (`posicoes[4]`), sem hardcode.
- Realce único no 1º passo de `validate_vertex`: `Flash(self.codigo.indicador.get_center(),
  color=COR_ACENTO, line_length=0.16, num_lines=10, flash_radius=0.30)` nos `anims` (o
  `run_time` do play já limita; sem tempo extra).

## 6. Validadores

`validate_flow_layout.py`
- `rotulo_base`/`rotulo_esperado` (l.362-382) com as duas linhas e a nova redação; medir
  cada linha (`split("\n")`) ≤ 7.54.
- Abas: `validate_vertex` herda; 16 trocas em ambas; BFS `adj` 99 / `rede` 551 / `busca` 851
  / `edge_to` 120 / `marcados` 113; DFS `busca` 398.
- Novo: guia (texto == `GUIA_SIMBOLOS[aba_ativa]` em 5 passos; ≤ 6.20; dentro do painel;
  folga ≥ 0.05 até o conteúdo e até os contadores).
- Novo: bloco (`len(textos[(u,v)]) == 2`; caixa não cruza o arco da própria aresta (0.02)
  nem o de outra; linha 1 = fluxo; linha 2 = (C−f, f)).
- Novo: setas (`start.x ≥ x(i-1)+0.21`, `end.x ≤ x(i)-0.21`, sem cruzar chip com 0.02, sem
  índice ≥ len).
- Novo: `adj` caption ≤ 6.20.
- Novo: selo (1º passo `validate_vertex 1× · 0 violações`; no fim `n` = total do trace e
  `k` = passos na linha 149).
- Esperado: páginas 18/19, views 14/15, passos 1734/1281.

`validate_flow_videos.py`
- l.52: `ALVO = {"edmonds": 19.44 * 60, "ford": 14.45 * 60}`.
- Novo frame: aba `rede` com `f > 0` e `#ef476f` fora da caixa do guia; `#06d6a0` em algum
  frame.

## 7. Aceitação (devolver com números)

1. `.\\.venv\\Scripts\\python.exe validate_flow_layout.py` (dois algoritmos) sem falhas:
   fonte **11.06**, páginas **18/19**, views **14/15**, trocas **16/16**, guia ≤ **5.27**,
   **0 colisões**, setas sem cruzamento, `adj` caption ≤ **3.02**, selo no slot 5.
2. `.\\.venv\\Scripts\\python.exe validate_flow_scenes.py`: sha do `stages` continua
   `e9975393…` (o `flow_record` não é tocado).
3. **Não** rodar render longo; se precisar de frame, `-s` ou `src/_layout_check.py`.
4. Relatório: arquivos:linhas, texto exato do cabeçalho de `FlowNetwork.validate_vertex`,
   posições dos 8 blocos, largura do guia por aba, checagens aprovadas.

Se algo for impossível, devolver o motivo com a medida — não improvisar.