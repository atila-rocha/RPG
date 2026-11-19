# RELATÓRIO ROTEIRO — Fluxo Máximo sobre `tinyFN`

Fase: **roteiro** (entrada + guia → briefing executável). Não grava trace, não escreve cena.
Data: 2026-11-11. Plano: `manim-animations/PLANO_FLUXO.md`.

## 0. Veredito

Entrada **válida** e didaticamente boa. Golden de registro (ordem `Bag` do algs4):
**fluxo máximo = 4**, corte mínimo **S\* = {0, 2}**, capacidade **4**, em **4 augmentações de gargalo 1**
— e, nesta ordem de adjacência, **Edmonds-Karp e Ford-Fulkerson produzem exatamente a MESMA
sequência de caminhos**. A diferença observável fica na *busca* (fila × pilha, ordem de descoberta,
69 × 27 inspeções de aresta), não nos caminhos. Ver §4 e §6 (decisão pendente).

---

## 1. Entrada — `C:\Users\atila\Documents\RPG\dataset\tinyFN.txt`

Formato declarado: **`FlowNetwork` do algs4** (`V`, `E`, depois `E` linhas `u v capacidade`) —
mesma forma do `ewg`, semântica de **capacidade** (não é MST, não é distância).

| item | valor medido |
|---|---|
| bytes | 78 |
| SHA-256 | `40c3b78a29605f8f8f8edb0c77e861ab8552ff822d0e5a928ddef11845bd1cf2` |
| BOM | **ausente** (1º byte `0x36` = `'6'`) |
| fim de linha | **CRLF** em 10/10 linhas, 0 LF solto |
| linhas físicas / úteis / vazias | 10 / 10 / 0 |
| comentários `#` | 0 |
| tabs / espaço à direita / não-ASCII | 0 / 0 / 0 |
| V | **6** (vértices 0..5) |
| E | **8** (8 linhas de corpo — bate) |
| s / t | **s = 0**, **t = V−1 = 5** (main do `FordFulkerson`: `s=0, t=G.V()-1`) |
| capacidades | {1.0, 2.0, 3.0}; tokens sempre com `.0` (`"2.0"`, `"3.0"`, `"1.0"`) |
| soma cap. saída de s | 5.0 (grau 2) — **≠ fluxo máximo** |
| soma cap. entrada em t | 5.0 (grau 2) |
| arestas entrando em s / saindo de t | **nenhuma** (rede "limpa") |
| duplicadas / antiparalelas / self-loops | nenhuma / nenhuma / nenhum |
| soma de todas as capacidades | 16.0 |

### 1.1 Tabela de arestas (índice = ordem do arquivo = ordem de inserção)

| # | u → v | capacidade | token | observação |
|---|---|---|---|---|
| 0 | 0 → 1 | 2 | `2.0` | sai de s |
| 1 | 0 → 2 | 3 | `3.0` | sai de s; **nunca satura** (fica 2/3) |
| 2 | 1 → 3 | 3 | `3.0` | única entrada de 3 vinda de 1 |
| 3 | 1 → 4 | 1 | `1.0` | **unitária** |
| 4 | 2 → 3 | 1 | `1.0` | **unitária** |
| 5 | 2 → 4 | 1 | `1.0` | **unitária** |
| 6 | 3 → 5 | 2 | `2.0` | entra em t |
| 7 | 4 → 5 | 3 | `3.0` | entra em t |

### 1.2 Validação (executada de verdade)

Scripts temporários: `%TEMP%\opencode\validar_tinyFN.py`, `golden_flow_tinyFN.py`,
`evidencias_flow_tinyFN.py`, `verifica_fluxo_tinyFN.py` (rodados com
`manim-animations\.venv\Scripts\python.exe`).

Regras checadas, todas **OK**: `V>0`, `E>=0`, `len(corpo)==E`, `0<=u,v<V`, `u!=v`, `capacidade>=0`
e finita, campos `u v cap` (3 por linha). **Nenhum erro.** Leitura com `utf-8-sig` +
`splitlines()` + `strip()`/`split()` aceita este arquivo sem caso especial.

### 1.3 Armadilhas didáticas (medidas, não supostas)

1. **`soma das capacidades que saem de s = 5`, mas o fluxo máximo é 4.** Quem olha só as bordas
   de s/t erra. O gargalo está *dentro*: o vértice 2 só consegue empurrar 1+1 = 2 (arcos `2→3` e
   `2→4`, ambos cap. 1). O vídeo precisa explicitar isso — é o argumento do corte mínimo.
2. **O corte mínimo não é `{s}`.** `{0}` tem capacidade 5; o mínimo é `{0,2}` com 4. E o arco
   `0→2` (o único não saturado saindo de s) **não** cruza o corte, porque 2 está do lado de s.
3. **Três arcos unitários** (`1→4`, `2→3`, `2→4`) ⇒ todo caminho aumentante desta rede tem gargalo
   ≤ 1; no golden `Bag` **todas as 4 augmentações são b = 1**. Não espere gargalo "grande".
4. **Capacidades iguais/pequenas** (1, 2, 3) fazem vários caminhos empatarem em comprimento (3
   arestas): a vantagem "BFS pega o mais curto" não se materializa aqui. Ver §4.
5. **O exemplo do guia (§5/§6) NÃO é esta rede.** O guia resolve uma rede de 5 vértices com valor
   **20** e corte `S*={s}`. Nenhum número do guia (`20`, `10`, `2`, `8`) pode aparecer no vídeo; os
   números vêm de `tinyFN` (valor **4**, corte `{0,2}`). Só os *conceitos* vêm do guia.
6. **Aresta que nunca recebe fluxo:** não existe (todas as 8 têm f > 0 no final). Mas `0→2` fica
   **2/3** — útil para mostrar que "não saturada" ≠ "fora do corte".
7. `t = 5` é o **último vértice**, não "o vértice 5 por acaso": deriva de `V−1`. Trocar o arquivo
   muda `t` sem editar código.

---

## 2. Guia de estudo — o que a animação precisa cobrir, em ordem

Fonte: `…\faculdade\grafos\Guia de Estudo Completo Fluxo Máximo em Redes.md` (440 linhas, 9 seções).

| ordem | seção do guia | conteúdo | papel no vídeo |
|---|---|---|---|
| 1 | §1 Definição | grafo **direcionado** com capacidade `C(u,v) ≥ 0`, origem `s`, sumidouro `t` | **obrigatório** (intro) |
| 2 | §1 Restrições | `0 ≤ f ≤ C` e **conservação** nos intermediários | **obrigatório** |
| 3 | §1 Valor do fluxo | `|f| = Σf(s,v) = Σf(u,t)` | **obrigatório** (contador na tela) |
| 4 | §1 Rede residual | `C_f(u,v) = C−f` (direta) e `C_f(v,u) = f` (reversa, simetria oblíqua) | **obrigatório** (núcleo) |
| 5 | §1 Caminho aumentante + gargalo | caminho simples em `G_f` com `C_f > 0`; `b = min C_f` | **obrigatório** |
| 6 | §3 Loop Ford-Fulkerson | inicializa 0 → busca → gargalo → augmenta → repete até não haver caminho | **obrigatório** |
| 7 | §2 Teorema Max-Flow Min-Cut | `max|f| = min C(S,T)`; `S*` = alcançáveis de s no residual final | **obrigatório** (fecho) |
| 8 | §4 Edmonds-Karp | BFS ⇒ caminho de **menor nº de arestas**; `O(V·E²)`; fortemente polinomial | **obrigatório** |
| 9 | §3 Ford-Fulkerson/DFS | DFS; `O(E·|f|)`; pseudo-polinomial, depende das capacidades | **obrigatório** |
| 10 | §8 Erros 1,2,3,5 | residual ≠ original; atualizar reversa; residual ≠ fluxo; aresta saturada bloqueia | **obrigatório** (como checagens na tela) |
| 11 | §7 Tabela comparativa | DFS × BFS (busca, complexidade, garantia de término, comprimento) | **opcional** (slide de fecho) |
| 12 | §2 Aplicações | água, tráfego, corrente, matching bipartido | **opcional** (1 frase na intro) |
| 13 | §3 Visited token | otimização O(1) por iteração | **opcional** (nota, não é conceito de fluxo) |
| 14 | §3 Pior caso 1000/1/1000 e não-terminação irracional | 2000 iterações × 2 | **opcional** e **rotulado como outra rede** |
| 15 | §4 Ecossistema (scaling, Dinic, push-relabel) | complexidades | **opcional** |
| 16 | §5/§6 exemplo de 5 vértices (valor 20) | execução manual | **proibido como dado** (não é `tinyFN`) |
| 17 | §9 cheat sheet | resumo | **opcional** |

**Regra de ouro:** o guia dá o *roteiro conceitual*; `tinyFN` dá *todos os números*.

---

## 3. Mapeamento conceito → dado (qual região do trace sustenta qual conceito)

| conceito do guia | dado de `tinyFN` que o evidencia | onde aparece no trace |
|---|---|---|
| rede direcionada, s, t | 6 vértices, 8 arcos, s=0, t=5 | cabeçalho + setas do grafo |
| capacidade | 8 valores (1, 2, 3) | coluna `cap` da tabela |
| conservação | vértices 1, 2, 3, 4 | soma in/out por vértice (balanço 0) |
| rede residual direta | `0→2` passa 3→2→1 de residual | coluna `res. direta` |
| rede residual reversa | após it. 1: `2→0` res 1, `4→2` res 1, `5→4` res 1 | coluna `res. reversa` |
| caminho aumentante | 4 caminhos de 3 arcos (§4) | destaque no grafo, iteração a iteração |
| gargalo | sempre **1** (arcos unitários `1→4`,`2→3`,`2→4`) | mínimo das residuais do caminho |
| augmentação | 4 × b=1 ⇒ valor 1,2,3,4 | contador `|f|` |
| aresta reversa | `2→0` res 2 e `4→2` res 1 inspecionadas e rejeitadas na busca | painel + passo de busca |
| término | busca final alcança só `{0,2}` | último passo (sem caminho) |
| corte mínimo | `S*={0,2}`, corte `0→1`(2) + `2→3`(1) + `2→4`(1) = **4** | destaque do corte + soma |
| "saturada ⇒ bloqueia" | `1→4`, `2→3`, `2→4`, `3→5` terminam com res 0 | coluna `res. direta` = 0 |
| "não saturada ≠ fora do corte" | `0→2` termina 2/3 e **não** cruza o corte | realce no fecho |

---

## 4. Goldens (calculados, não estimados)

### 4.1 Modelo usado — e por que a ordem importa

Simulação fiel a algs4:

- `FlowEdge(from,to,cap,flow)` com `residual_capacity_to` / `add_residual_flow_to` (ε = 1e-10);
- `FlowNetwork.add_edge` insere a aresta em `adj[from]` **e** `adj[to]`;
- **`Bag` do algs4 insere no início** (`bag.py` confirmado: `Node(item, oldfirst)`) ⇒ iterar `adj[v]`
  devolve a **ordem reversa de inserção**;
- BFS: fila FIFO, `edgeTo[w]` no primeiro descobrimento, **sem early exit** (como o Java: 16
  inspeções por busca);
- DFS: **recursiva**, `edgeTo[w]` no primeiro descobrimento, retorna ao chegar em `t`.

Listas de adjacência na ordem de iteração (`Bag`, reversa):

```
0: 0→2[3]  0→1[2]
1: 1→4[1]  1→3[3]  0→1[2]
2: 2→4[1]  2→3[1]  0→2[3]
3: 3→5[2]  2→3[1]  1→3[3]
4: 4→5[3]  2→4[1]  1→4[1]
5: 4→5[3]  3→5[2]
```

**Sim, o resultado depende da ordem** — mas só a *sequência*, não o valor:

| variante de ordem | valor | corte | caminhos | iterações | inspeções |
|---|---|---|---|---|---|
| `Bag` algs4 (LIFO/reversa) — **plano** | 4 | {0,2} | 4 caminhos, idênticos nos 2 algoritmos | 4 + 1 busca final | BFS 69 / DFS 27 |
| lista `append` (ordem de inserção) | 4 | {0,2} | 3 caminhos, **diferentes** entre si | 3 + 1 busca final | BFS 53 / DFS 36 |

**Invariantes nas quatro combinações:** valor **4**, corte **{0,2}**, capacidade **4**, fluxos finais
idênticos, viabilidade OK (capacidade + conservação + `|f| = Σ saída de s = Σ entrada em t`).

### 4.2 GOLDEN DE REGISTRO — ordem `Bag` (plano: "adj com Bag")

**Edmonds-Karp (BFS)** e **Ford-Fulkerson (DFS)** dão a **mesma** sequência:

| it | caminho aumentante | gargalo | `|f|` acumulado | descoberta BFS | descoberta DFS |
|---|---|---|---|---|---|
| 1 | `0→2→4→5` | 1 | 1 | 0, 2, 1, 4, 3, 5 | 0, 2, 4, 5 |
| 2 | `0→2→3→5` | 1 | 2 | 0, 2, 1, 3, 4, 5 | 0, 2, 3, 5 |
| 3 | `0→1→4→5` | 1 | 3 | 0, 2, 1, 4, 3, 5 | 0, 2, 1, 4, 5 |
| 4 | `0→1→3→5` | 1 | **4** | 0, 2, 1, 3, 5, 4 | 0, 2, 1, 3, 5 |
| 5 | — (sem caminho) | — | 4 | marcados `{0,2}` | marcados `{0,2}` |

**Nenhuma augmentação usa aresta reversa** nesta ordem (todas as diretas). A reversa só é
*inspecionada e rejeitada* (ex.: DFS it. 3 percorre `2→0` com res 2 e volta por `0` já marcado).

Fluxos finais (idênticos nos dois algoritmos):

| aresta | cap | fluxo | res. direta | res. reversa |
|---|---|---|---|---|
| 0→1 | 2 | **2** | 0 | 2 |
| 0→2 | 3 | 2 | **1** | 2 |
| 1→3 | 3 | 1 | 2 | 1 |
| 1→4 | 1 | **1** | 0 | 1 |
| 2→3 | 1 | **1** | 0 | 1 |
| 2→4 | 1 | **1** | 0 | 1 |
| 3→5 | 2 | **2** | 0 | 2 |
| 4→5 | 3 | 2 | 1 | 2 |

Corte: `S* = {0,2}`, `T* = {1,3,4,5}`; arestas cruzando `0→1`(2), `2→3`(1), `2→4`(1) — **todas
saturadas**; soma **4 = valor**. ✓

### 4.3 GOLDEN ALTERNATIVO — ordem de inserção (`append`)

| it | Edmonds-Karp (BFS) | b | Ford-Fulkerson (DFS) | b |
|---|---|---|---|---|
| 1 | `0→1→3→5` | **2** | `0→1→3→5` | **2** |
| 2 | `0→2→4→5` | 1 | `0→2→3→1→4→5` *(usa reversa `3→1`)* | 1 |
| 3 | `0→2→3→1→4→5` *(usa reversa `3→1`)* | 1 | `0→2→4→5` | 1 |
| 4 | — | — | — | — |

Mesmo valor **4**, mesmo corte **{0,2}**, mesmos fluxos finais; **3 iterações** e um caminho com
**aresta reversa** (`3→1`, res 2) — o que a ordem `Bag` não oferece.

### 4.4 Como o vídeo evidencia a diferença (caso `Bag`, sequências iguais)

1. **Fronteira:** painel mostra **fila BFS** (0 | 2,1 | 4,3 | 5) × **pilha/recursão DFS** (0→2→4→5
   direto). Mesma resposta, caminhada oposta.
2. **Contador de inspeções de aresta:** BFS **69** × DFS **27** acumuladas (por iteração:
   BFS 16/16/16/16/5; DFS 3/4/7/8/5). É a diferença *medida* — e é consequência direta do early
   exit da DFS × varredura completa da BFS.
3. **Ordem de descoberta** na mesma iteração (tabela §4.2, colunas 5 e 6): BFS descobre por nível,
   DFS desce.
4. **Comprimento do caminho:** declarar na tela que BFS **garante** mínimo em arestas e DFS **não**;
   em `tinyFN` todos os caminhos têm 3 arcos, então a garantia não se *manifesta* — dizer isso é
   mais honesto (e mais instrutivo) que forçar uma diferença.
5. Se o orquestrador quiser diferença **visível na sequência** e o uso da reversa, trocar para a
   ordem de inserção (§4.3) — decisão de uma linha no `FlowNetwork`, mas **muda o golden**.

---

## 5. Narrativa em etapas (o que a animação precisa cobrir)

Mesma espinha para as duas cenas; muda só o painel de busca (fila × pilha) e a legenda de complexidade.

| # | etapa | conteúdo | dado de `tinyFN` |
|---|---|---|---|
| 1 | Intro | rede dirigida, `s=0`, `t=5`, 6 vértices / 8 arcos; "peso = capacidade" | cabeçalho `V E` |
| 2 | Estado inicial | `f=0` em todas; residual direta = capacidade; valor 0 | 8 arestas |
| 3 | Busca no residual | BFS: enfileira, marca, rejeita `res=0` e "já marcado"; DFS: mergulha e volta | ordem de adjacência declarada |
| 4 | Caminho aumentante | destaque do caminho `s→…→t` com `res>0` | caminho da iteração |
| 5 | Gargalo | `b = min res` ao longo do caminho (aqui **1**) | arcos unitários |
| 6 | Augmentação | `f += b` na direta, `res. direta -= b`, `res. reversa += b`, `|f| += b` | tabela do painel |
| 7 | Aresta reversa | mostrar a reversa criada (ex. `2→0` res 1) e explicar "desfazer"; se não for usada, **dizer que não foi** | coluna `res. reversa` |
| 8 | Repetição | iterações 1..4 (§4.2) | 4 caminhos |
| 9 | Término | busca não alcança `t`; só `{0,2}` marcados | último passo |
| 10 | Corte mínimo | `S*={0,2}` × `T*`; arestas `0→1`,`2→3`,`2→4`; `2+1+1 = 4` | corte |
| 11 | Fecho | `max|f| = min C(S,T) = 4`; nota: "saída de s vale 5, o gargalo interno limita a 4" | — |

Complexidade por cena: EK `O(V·E²)` (fortemente polinomial); FF/DFS `O(E·|f|)` (pseudo-polinomial).

---

## 6. Pendências / decisões antes das próximas fases

1. **[BLOQUEANTE — decide o golden] Ordem de iteração de `adj`.** `Bag` (plano, fiel ao
   `FlowNetwork.java`; sequências iguais, sem reversa usada) **ou** lista `append` (sequências
   diferentes + caminho com reversa). Precisa estar escrita no docstring de `flow_network.py` e no
   golden. Recomendação: **`Bag`** (fidelidade ao algs4 e ao plano); se a prioridade for mostrar a
   divergência EK×FF, adotar `append` e usar o golden §4.3.
2. **Semântica da DFS a declarar** (senão o golden não reproduz): recursiva, `edgeTo` no primeiro
   descobrimento, **retorno antecipado ao tocar `t`**, iterando `adj[v]` na ordem declarada. Uma DFS
   iterativa com pilha "empurra todos e desempilha" inverte a ordem e **muda o golden**.
3. **`algs4-py` ainda não tem o capítulo de fluxo** (confirmado: não existe `flow_edge.py`,
   `flow_network.py`, `ford_fulkerson*.py`). O golden acima é uma simulação fiel; o **Gate 0** deve
   reconfirmá-lo rodando o port real (valor 4, corte {0,2}, sequência §4.2).
4. **Early exit da BFS:** o Java varre o grafo residual inteiro (16 inspeções/busca). Se o port
   antecipar a saída, os *caminhos* não mudam, mas o contador de inspeções muda — então o número
   "69 × 27" só vale com a BFS sem early exit.
5. **Guia não cobre exibição** de residual reverso nem a leitura do corte no painel: a forma de
   mostrar é decisão da fase visual (o dado já existe no trace: `f`, `cap`, residuais, valor).
6. **Nada do exemplo §5/§6 do guia** (5 vértices, valor 20, corte `{s}`) pode entrar como dado —
   serve só como contraste conceitual, rotulado como outra rede.
7. Guia sem menção a `tinyFN`: todos os textos/contadores devem derivar de `V`, `E`, `s=V-1` e dos
   valores lidos (nada de `4`, `5`, `6` hardcoded na cena).
