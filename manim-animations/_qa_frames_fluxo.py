"""Extrai frames de um vídeo para inspeção visual do QA (streaming, sem OOM).

Uso:
    python _qa_frames_fluxo.py <video.mp4> <pasta_saida> [frac1 frac2 ...]

Sem frações, extrai 12 amostras uniformes (2%..98%) + o último frame.
Salva PNGs nomeados por índice de frame e fração, para inspeção manual
(fantasmas de aba, indicador fora da moldura, anel do corte).
"""

from __future__ import annotations

import os
import sys

import av


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    caminho, saida = sys.argv[1], sys.argv[2]
    fracs = [float(x) for x in sys.argv[3:]] or [i / 13 for i in range(1, 13)] + [0.995]
    os.makedirs(saida, exist_ok=True)

    container = av.open(caminho)
    stream = container.streams.video[0]
    fps = float(stream.average_rate)
    n = 0
    for _ in container.decode(video=0):
        n += 1
    container.close()
    if n == 0:
        print("vídeo sem frames")
        return 1

    alvos = {}
    for f in fracs:
        i = min(n - 1, max(0, int(f * n)))
        alvos.setdefault(i, f)

    salvos = 0
    container = av.open(caminho)
    for i, frame in enumerate(container.decode(video=0)):
        if i in alvos:
            nome = f"frame_{i:06d}_p{alvos[i]*100:05.1f}.png"
            frame.to_image().save(os.path.join(saida, nome))
            print("salvo", nome, f"t={i/fps:.1f}s")
            salvos += 1
            if salvos >= len(alvos):
                break
    container.close()
    print(f"total {salvos} frames de {n} (fps {fps:.1f}) em {saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
