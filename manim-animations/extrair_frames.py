"""Extrai frames de um video para inspecao visual rapida.

Uso:
    python extrair_frames.py <video.mp4> <saida_dir> [t1 t2 ...]

Sem tempos: extrai 8 frames distribuidos ao longo do video.
Faz streaming (guarda so os indices pedidos), para nao estourar a memoria
em videos longos de 1080p60.
"""

from __future__ import annotations

import sys
from pathlib import Path

import av
from PIL import Image


def extrair(video: str, saida: Path, tempos: list[float] | None = None) -> list[Path]:
    saida.mkdir(parents=True, exist_ok=True)

    with av.open(video) as container:
        stream = container.streams.video[0]
        fps = float(stream.average_rate)
        total = stream.frames or 0

        if not tempos:
            n = total or 1
            tempos = [t * n / 8 / fps for t in range(8)]

        pedidos = {min(total - 1, max(0, int(round(t * fps)))) for t in tempos} if total else None
        alvos: dict[int, Image.Image] = {}
        contador = 0
        for frame in container.decode(video=0):
            if pedidos is None:
                # Sem metadados de duracao: guarda 1 de cada N (decide depois).
                alvos[contador] = Image.fromarray(frame.to_ndarray(format="rgb24"))
            elif contador in pedidos:
                alvos[contador] = Image.fromarray(frame.to_ndarray(format="rgb24"))
            contador += 1

    caminhos = []
    if pedidos is None:
        total = contador
        passo = max(1, total // 8)
        escolhidos = sorted(alvos)[::passo][:8]
    else:
        escolhidos = sorted(pedidos)

    for i, idx in enumerate(escolhidos):
        if idx not in alvos:
            continue
        p = saida / f"frame_{i:02d}_{idx:06d}.png"
        alvos[idx].save(p)
        caminhos.append(p)
        print(f"{p.name}  ({idx}/{contador})")
    return caminhos


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    video = sys.argv[1]
    destino = Path(sys.argv[2])
    ts = [float(x) for x in sys.argv[3:]] or None
    extrair(video, destino, ts)
