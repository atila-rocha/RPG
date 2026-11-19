# Relatório do codificador — Fluxo máximo (Edmonds-Karp e Ford-Fulkerson/DFS)

Escrita fiel do `PLANO_VISUAL_FLUXO.md` sobre o trace real de
`src/flow_record.py`. Nada de estado inventado: todo valor exibido vem de
`Step.estado`, `Step.destaque` ou `Step.acao`.

## 1. Arquivos

| Arquivo | Papel |
| --- | --- |
| `src/flow_common.py` | linguagem visual compartilhada: paleta, layout, `FlowGraphView`, `CodePanel`, `StatePanel`, `GuiaVisual`, `EstruturaPanel` (abas), `FlowExecucaoBase` |
| `src/edmonds_karp_scene_new.py` | `EdmondsKarpIntro_new`, `EdmondsKarpExecutionScene_new`, `FullEdmondsKarpVideo_new` |
| `src/ford_fulkerson_scene_new.py` | `FordFulkersonIntro_new`, `FordFulkersonExecutionScene_new`, `FullFordFulkersonVideo_new` |
| `validate_flow_layout.py` | portão de geometria (antes do render) |
| `validate_flow_videos.py` | portão de frames/paleta (depois do render) |

Nenhum arquivo pré-existente foi alterado (`flow_record.py`, `mst_common.py`,
`dijkstra_common.py`, cenas de MST/Dijkstra, `validate_flow_scenes.py`,
`media/`, `media_dev/`).

## 2. Fidelidade ao trace

| Medida | BFS | DFS |
| --- | --- | --- |
| passos animados (`por_linha=True`) | 1661 | 1218 |
| views de código usadas | 13/13 | 14/14 |
| trocas de view (dois `play` cada) | 596 | 418 |
| trocas de aba (dois `play` cada) | 10 | 10 |
| passos na aba `Busca` | 822 | 379 |
| inspeções no fecho | 69 | 27 |
| `\|f\|` / corte mínimo | 4 / 4 | 4 / 4 |

Rótulos finais `f/C` conferem com o golden em ambas as cenas:
`2/2, 2/3, 1/3, 1/1, 1/1, 1/1, 2/2, 2/3`; 8 arestas diretas e 8 reversas.

## 3. Painel de código (o ponto crítico)

- Código **na íntegra** de cada função real, derivado do `ast`
  (`funcoes_codigo`/`funcao_da_linha`), uma view por função.
- Moldura fixa 7,86 × 4,55 em `to_corner(UL, buff=0,55)`; o grupo estável é
  **só a moldura** (conteúdo e indicador são mobjects de cena).
- Troca de view em **dois `play` separados** (`FadeOut` total, depois
  `FadeIn`), com indicador por view.
- Fonte efetiva medida: **7,00 pt (BFS)** e **6,76 pt (DFS)**.

## 4. Desvios do plano (com a aritmética)

1. **Fonte do código abaixo dos 9 pt do §4.** A altura útil é
   `4,55 − 0,12 − 0,12 = 4,31`; menos o cabeçalho (0,28) sobram 4,03 para a
   maior view (37 linhas, 13,83 de altura nativa) → `0,2915` de escala
   (7,00 pt). Para 9 pt seria preciso `9/24 = 0,375`, ou seja, 5,18 de altura
   útil e **≈ 5,49 de moldura** — não cabe nos 4,96 disponíveis entre o topo
   do quadro e a estrutura. Preferi 7 pt legível a 9 pt cortando código.
   Paddings reais: `0,16 / 0,16 / 0,12 / 0,12` (plano: 0,30/0,34/0,16/0,16).
2. **13/14 views mantidas.** Descartar `is_feasible`/`check`/`validate`
   deixaria 204 passos sem view e ganharia só 7,38 pt de altura — não resolve
   o item 1 e quebra a regra "código na íntegra".
3. **Rótulos `f/C`** com posições calculadas (determinísticas, ordem do
   arquivo) diferentes da tabela do §2.3, porque a caixa do rótulo real é
   maior: zero colisões contra nós, rótulos, arestas alheias e arcos reversos
   alheios (verificado por `validate_flow_layout.py`).
4. **Área do grafo**: com os anéis, o bbox vai de x 1,47 a 6,90 (o plano
   previa 6,83). O portão usa margem de 0,18 no quadro (limite 6,93).
5. **Ordem dos slides da intro** (§8 pedia caminho antes dos conceitos):
   invertida para narrativa só-para-frente — conceitos → caminho/gargalo →
   residual → laço → fecho. Os números do slide do caminho são os do estado
   real da 1ª busca (residuais 3, 1, 3 → b = 1).
6. **Aba `Busca`** derivada por `calcular_abas()` (janela da busca), não pela
   regra ingênua de "iteração mudou": 10 trocas por vídeo em vez de 126.
7. **`("corte", u, v, "cruza")`** dispara para as 8 arestas; o âmbar só acende
   se a aresta realmente cruza o corte (`u ∈ S`, `v ∉ S`), senão fica magenta
   "em exame" — evita mentir sobre o corte.
8. **Aresta "insere"** chega 5 passos antes da aresta existir no estado: o
   desenho segue a presença no `estado`, e o passo vira no-op quando ausente.
9. **Rótulos da fronteira em palavra** (`frente`/`fim` no BFS, `base`/`topo`
   no DFS) em vez de `↓ frente`/`↑ fim`: em fonte 9 os glifos ↓/↑ saem como
   "l"/"1" no render.
10. **Duração real do BFS: 11,80 min** (alvo 10,6). A diferença é o
    arredondamento para frames de 15 fps: `play(0.18)` vira 3 frames (0,20),
    `fade(0.09)` vira 2 (0,133) — 596 trocas de view e 1661 passos somam
    ~1,2 min. Dentro da folga; encurtar exigiria mexer no ritmo do §8.

## 4.1 Bug encontrado no primeiro render (corrigido antes da entrega)

O primeiro render 480p do BFS (123 min, descartado) mostrou **fantasmas no
painel de estrutura**: ao trocar de aba, os números da tabela residual
continuavam na tela atrás da fila. Causa: `_AbaRede.todos()`/`_AbaBusca.todos()`
devolviam `self.mobjects`, um *snapshot* da montagem. `sincronizar` troca
textos (novos mobjects, dicts atualizados), então o `FadeOut` da troca de aba
acertava mobjects já fora de cena e os textos vivos ficavam para sempre.

Correção: `todos()` passou a devolver a lista **viva** (estáticos + chips +
textos/setas atuais). `validate_flow_layout.py` ganhou a verificação
"aba Rede/Busca: texto trocado sai da lista viva" para impedir a regressão.

## 5. Portões executados

- `validate_flow_scenes.py`: **6/6** (entrada, golden, invariantes,
  determinismo, linha a linha, funções de código);
  `stages_fluxo.json` sha256 `4428184b…c4d3d` (inalterado).
- `validate_flow_layout.py`: **VERDE** — 70 verificações (35 por algoritmo).
- `validate_flow_videos.py`: ver §6.

## 6. Renders 480p (`-ql`, `media_dev_fluxo`)

| Cena | Arquivo | Duração |
| --- | --- | --- |
| `EdmondsKarpExecutionScene_new` | _pendente_ | — |
| `FordFulkersonExecutionScene_new` | _pendente_ | — |

## 7. Para o QA

- O painel de código é o único ponto em que o plano não pôde ser cumprido
  literalmente: 7,00/6,76 pt em 1080p (≈ 3,1/3,0 px de altura de glifo em
  480p). Legível em 1080p, borrado em 480p — o 480p é portão de fumaça, não
  de leitura.
- Verificar no QA de frames: legenda (7 itens), indicador de view sempre
  dentro da moldura, e o fecho com o anel âmbar do corte.
