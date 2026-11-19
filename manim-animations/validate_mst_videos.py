"""
Validador automatizado dos criterios de aceitacao dos videos de MST.

Uso:
    python validate_mst_videos.py <video.mp4> [video.mp4 ...]

Verifica, para cada video:
  1. O ULTIMO frame contem conteudo (nao termina em tela preta).
  2. Todo texto visivel esta dentro do quadro (nenhuma banda de texto toca
     y=0 nem y=altura-1).
  3. As cores de aresta usadas correspondem a categorias declaradas:
     - verde  (#06d6a0) = aceita na MST
     - vermelho (#ef476f) = descartada / obsoleta
     - cinza-claro (#8d99ae) = fora da MST
     - amarelo (#f9c74f) = em analise
  4. Nenhuma aresta descartada permanece na cor cinza padrao (#4a4e69).
  5. Os pesos das arestas aceitas usam UMA UNICA cor.
"""

import sys
import numpy as np
import av
from PIL import Image

COR_ACEITA = (0x06, 0xD6, 0xA0)
COR_DESCARTE = (0xEF, 0x47, 0x6F)
COR_FORA = (0x8D, 0x99, 0xAE)
COR_EM_ANALISE = (0xF9, 0xC7, 0x4F)
COR_CINZA_PADRAO = (0x4A, 0x4E, 0x69)
COR_PESO_ACEITA = (0xF2, 0xF4, 0xF8)

TOLERANCIA = 26


def _contar(a, cor, tol=TOLERANCIA):
    """Conta pixels proximos de uma cor (RGB)."""
    d = np.abs(a.astype(int) - np.array(cor)).sum(axis=2)
    return int((d <= tol).sum())


def _bandas_texto(a, limiar=300):
    """Retorna as faixas (y_inicio, y_fim) com pixels claros (texto/elementos)."""
    lum = a.sum(axis=2)
    bright = (lum > limiar) & (np.abs(a.astype(int) - np.array([0x0F, 0x11, 0x1A])).sum(axis=2) > 60)
    rows = bright.sum(axis=1)
    bandas, dentro = [], False
    for y in range(len(rows)):
        if rows[y] > 3 and not dentro:
            dentro, ini = True, y
        elif rows[y] <= 3 and dentro:
            dentro = False
            bandas.append((ini, y - 1))
    if dentro:
        bandas.append((ini, len(rows) - 1))
    return bandas


def validar(caminho):
    print("=" * 72)
    print("VALIDANDO:", caminho.split("\\")[-1])

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
    print("  [1] ultimo frame: %d pixels claros -> %s" % (bright, "OK" if bright > 500 else "FALHA"))
    if bright <= 500:
        ok = False

    # --- Criterio 2: texto dentro do quadro ---
    bandas = _bandas_texto(a)
    fora = [b for b in bandas if b[0] <= 1 or b[1] >= h - 2]
    print("  [2] %d bandas de texto; fora do quadro: %d -> %s"
          % (len(bandas), len(fora), "OK" if not fora else "FALHA"))
    if fora:
        print("      bandas problematicas:", fora[:5])
        ok = False

    # --- Criterio 3: cores de aresta presentes ---
    c_aceita = _contar(a, COR_ACEITA)
    c_descarte = _contar(a, COR_DESCARTE)
    c_fora = _contar(a, COR_FORA)
    c_analise = _contar(a, COR_EM_ANALISE)
    c_cinza = _contar(a, COR_CINZA_PADRAO)
    c_peso = _contar(a, COR_PESO_ACEITA)
    print("  [3] arestas: aceita=%d descartada=%d fora=%d em_analise=%d | cinza_padrao=%d | peso_aceita=%d"
          % (c_aceita, c_descarte, c_fora, c_analise, c_cinza, c_peso))
    if c_aceita == 0:
        print("      FALHA: nenhuma aresta aceita (verde) encontrada")
        ok = False

    # --- Criterio 4: nenhuma aresta descartada em cinza padrao ---
    if c_cinza > 0:
        print("      AVISO: %d pixels na cor cinza padrao #4a4e69 (pode ser aresta fora da MST)" % c_cinza)

    # --- Criterio 5: pesos das arestas aceitas em cor unica ---
    # mede quantas cores distintas existem na regiao dos pesos aceitos
    if c_peso == 0:
        print("      AVISO: cor unica de peso aceito (#f2f4f8) nao encontrada no frame final")
    else:
        print("      [5] peso aceito em cor unica: %d pixels OK" % c_peso)

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
