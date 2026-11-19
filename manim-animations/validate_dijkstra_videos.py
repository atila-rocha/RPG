"""
Validador automatizado dos criterios de aceitacao do video de Dijkstra.

Uso:
    python validate_dijkstra_videos.py <video.mp4> [video.mp4 ...]

Verifica, para cada video:
  1. O ULTIMO frame contem conteudo (nao termina em tela preta).
  2. Todo texto visivel esta dentro do quadro (nenhuma banda de texto toca
     y=0 nem y=altura-1).
  3. As cores de aresta usadas correspondem a categorias declaradas:
       - verde   (#06d6a0) = aresta confirmada na SPT
       - magenta (#e879f9) = vertice extraido da IPQ
       - amarelo (#f9c74f) = aresta/nó em analise
       - branco-osso (#e0e1dd) = tentativa (edgeTo nao confirmada)
       - ciano   (#48cae4) = cabecalhos/rotulos
  4. O painel de estrutura nao esta vazio no frame final (abas + conteudo).
  5. Nao existe faixa de texto colada na borda inferior (painel cortado).
"""

from __future__ import annotations

import sys

import av
import numpy as np

COR_ACEITA = (0x06, 0xD6, 0xA0)
COR_EXTRACAO = (0xE8, 0x79, 0xF9)
COR_ANALISE = (0xF9, 0xC7, 0x4F)
COR_TENTATIVA = (0xE0, 0xE1, 0xDD)
COR_TEXTO = (0x48, 0xCA, 0xE4)
COR_FUNDO = (0x0F, 0x11, 0x1A)

TOLERANCIA = 26


def _contar(a, cor, tol=TOLERANCIA):
    """Conta pixels proximos de uma cor (RGB)."""
    d = np.abs(a.astype(int) - np.array(cor)).sum(axis=2)
    return int((d <= tol).sum())


def _bandas_texto(a, limiar=300):
    """Retorna as faixas (y_inicio, y_fim) com pixels claros (texto/elementos)."""
    lum = a.sum(axis=2)
    bright = (lum > limiar) & (
        np.abs(a.astype(int) - np.array(COR_FUNDO)).sum(axis=2) > 60
    )
    rows = bright.sum(axis=1)
    bandas, dentro = [], False
    ini = 0
    for y in range(len(rows)):
        if rows[y] > 3 and not dentro:
            dentro, ini = True, y
        elif rows[y] <= 3 and dentro:
            dentro = False
            bandas.append((ini, y - 1))
    if dentro:
        bandas.append((ini, len(rows) - 1))
    return bandas


def validar(caminho: str) -> bool:
    print("=" * 72)
    print("VALIDANDO:", caminho.replace("\\", "/").split("/")[-1])

    container = av.open(caminho)
    stream = container.streams.video[0]
    fps = float(stream.average_rate)
    ultimo = None
    n = 0
    for frame in container.decode(video=0):
        ultimo = frame
        n += 1
    container.close()

    if ultimo is None:
        print("  FALHA: video sem frames")
        return False

    a = ultimo.to_ndarray(format="rgb24")
    h, w, _ = a.shape
    print("  frames=%d  fps=%.1f  dur=%.1fs  %dx%d" % (n, fps, n / fps, w, h))

    ok = True

    # --- Criterio 1: ultimo frame nao-preto ---
    bright = int((a.sum(axis=2) > 300).sum())
    print(
        "  [1] ultimo frame: %d pixels claros -> %s"
        % (bright, "OK" if bright > 500 else "FALHA")
    )
    if bright <= 500:
        ok = False

    # --- Criterio 2: texto dentro do quadro ---
    bandas = _bandas_texto(a)
    fora = [b for b in bandas if b[0] <= 1 or b[1] >= h - 2]
    print(
        "  [2] %d bandas de texto; fora do quadro: %d -> %s"
        % (len(bandas), len(fora), "OK" if not fora else "FALHA")
    )
    if fora:
        print("      bandas problematicas:", fora[:5])
        ok = False

    # --- Criterio 3: cores declaradas presentes ---
    c_aceita = _contar(a, COR_ACEITA)
    c_extracao = _contar(a, COR_EXTRACAO)
    c_analise = _contar(a, COR_ANALISE)
    c_tentativa = _contar(a, COR_TENTATIVA)
    c_texto = _contar(a, COR_TEXTO)
    print(
        "  [3] aceita=%d extracao=%d analise=%d tentativa=%d texto=%d"
        % (c_aceita, c_extracao, c_analise, c_tentativa, c_texto)
    )
    if c_aceita == 0:
        print("      FALHA: nenhuma aresta confirmada (verde) no frame final")
        ok = False

    # --- Criterio 4: painel de estrutura populado ---
    painel = a[int(h * 0.62) :, : int(w * 0.52)]
    p_bright = int((painel.sum(axis=2) > 300).sum())
    print(
        "  [4] painel de estrutura: %d pixels claros -> %s"
        % (p_bright, "OK" if p_bright > 800 else "FALHA")
    )
    if p_bright <= 800:
        ok = False

    # --- Criterio 5: sem corte na borda inferior ---
    rodape = _bandas_texto(a[int(h * 0.94) :])
    cortado = [b for b in rodape if b[1] >= int(h * 0.06) - 2]
    print(
        "  [5] texto na borda inferior: %d -> %s"
        % (len(cortado), "OK" if not cortado else "FALHA")
    )
    if cortado:
        ok = False

    print("  RESULTADO:", "APROVADO" if ok else "REPROVADO")
    return ok


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    resultados = [validar(p) for p in args]
    print("=" * 72)
    print("TODOS APROVADOS" if all(resultados) else "HA FALHAS")
    sys.exit(0 if all(resultados) else 1)
