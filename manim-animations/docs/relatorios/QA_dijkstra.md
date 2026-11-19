# Dijkstra — correções e QA (480p)

## O que foi corrigido

### 1. Entrada real do algs4
- `src/dijkstra_record.py` lê o grafo do formato `EdgeWeightedDigraph`
  (`dataset/tinyEWD.txt` por padrão; `DIJKSTRA_GRAFO` sobrescreve).
- V, E e origem vêm do arquivo — nada de lista de arestas hardcoded.
- `tinyEWD`: V=8, E=15, origem 0. Resultado conferido com a saída oficial
  do algs4 (distTo, edgeTo, custo 2.56, ordem `[0,2,4,7,5,3,1,6]`).

### 2. Colisão do painel de código com o subtítulo
- Cabeçalho da execução virou **uma linha**: `título · subtítulo` em y=3.74
  (antes eram duas linhas empilhadas, e o subtítulo descia até y≈2.84).
- Painel de código usa as constantes do MST (`ALTURA_CODIGO=3.72`,
  `LARGURA_CODIGO=6.40`, `to_corner(UL, buff=0.55)`) → topo em y=3.45,
  folga de 0.15 sob o cabeçalho.
- Na intro, o grafo desceu 0.45: o topo estava em y=3.12 e o título
  (largura até x=4.93) encostava nele.

### 3. Estrutura de dados e abas
- `IndexMinPQ` é desenhada como **heap binário real de 15 slots** (4 níveis,
  raiz = mínimo), com `swim`/`sink` aparecendo como movimento de nós.
- `distTo` e `edgeTo` são tabelas indexadas por vértice (chips), com
  verde = confirmado, branco-osso = tentativa, cinza = vazio/∞.
- A aba ativa segue **a linha realmente executada**:
  - `DijkstraSP` 38 → edgeTo; 39–42 → distTo; 43–46 → heap;
    49–52 → distTo; 53 → edgeTo; 54/55/57 → heap;
  - qualquer linha de `IndexMinPQ` → heap;
  - qualquer linha de `DirectedEdge` → distTo.
- Troca de aba em **dois plays** (fade-out total e depois fade-in), nunca
  duas estruturas no mesmo frame — igual ao painel de código (padrão MST).

### 4. Padrão MST
- Uma view de código por função (derivada do `ast`, sem inventar funções).
- Indicador por view, nasce na primeira linha executada e desliza.
- Grafo dirigido com arestas recíprocas deslocadas (4↔5, 5↔7), pesos sem
  sobreposição, legenda com símbolo (anel = vértice, ponto = aresta).
- SPT do frame final derivada só do `edgeTo` dos vértices finalizados;
  tentativas voltam ao cinza no fechamento.

## Validação de estado (sem Manim)

`python validate_dijkstra_scenes.py` → 6/6:

| teste | resultado |
|---|---|
| golden (distTo, edgeTo, SPT, custo, ordem, IPQ vazia) | ok |
| invariantes (relaxação, monotonicidade, heap, SPT = edgeTo) | ok |
| determinismo (duas gravações idênticas) | ok |
| linha a linha (cobertura, views derivadas do fonte, linha dentro da view) | ok |
| abas (regra da cena == regra do validador, ≥ 6 trocas, 3 abas usadas) | ok |
| layout (pesos sem colisão com nós e entre si, recíprocas deslocadas) | ok |

## Validação de vídeo (pós-render)

`python validate_dijkstra_videos.py <video.mp4>` verifica:
último frame não-preto, texto dentro do quadro, cores declaradas presentes,
painel de estrutura populado, nada cortado na borda inferior.

## Render

- 480p15: `media_dev/videos/dijkstra_scene_new/480p15/`
- 1080p60: **somente depois da validação explícita do usuário**.
