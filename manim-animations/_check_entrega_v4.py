"""Verificacao de entrega (somente leitura, decodificacao real com PyAV, streaming).

Para cada MP4:
  - duracao do container e por frames decodificados, contagem de frames,
    resolucao, fps, codec/profile/pix_fmt, sar, time_base;
  - monotonicidade de pts (nenhum frame fora de ordem ou negativo);
  - ultimo frame nao vazio (tinta > LIMIAR).

Para os integrais:
  - frames(integral) == frames(intro) + frames(exec);
  - duracao(integral) == soma das duracoes dos containers (tolerancia 1 frame);
  - frame #frames(intro)-1 do integral identico ao ultimo da intro e
    frame #frames(intro) identico ao frame 0 da execucao (inicio da execucao
    comeca exatamente depois da intro).

Uso:
  python _check_entrega_v4.py arquivo.mp4 [arquivo.mp4 ...]
  python _check_entrega_v4.py --integral INTEGRAL INTRO EXEC [INTEGRAL INTRO EXEC ...]
"""
from __future__ import annotations

import sys
from contextlib import closing

import av
import numpy as np

LIMIAR_TINTA = 1500
FPS = 15.0


def tinta(a):
    return int((a.max(axis=2) > 40).sum())


def varrer(caminho, indices=()):
    """Decodifica em streaming; guarda apenas os frames de `indices`."""
    guardados = {}
    alvo = set(indices)
    n = 0
    primeiro_pts = None
    pts_anterior = None
    pts_ordem = True
    pts_negativo = False
    ultimo = None
    primeiro_arr = None
    with closing(av.open(caminho)) as c:
        vs = c.streams.video[0]
        info = {
            "w": vs.codec_context.width,
            "h": vs.codec_context.height,
            "fps": float(vs.average_rate),
            "codec": vs.codec_context.name,
            "profile": vs.codec_context.profile,
            "pix": vs.codec_context.pix_fmt,
            "sar": str(vs.codec_context.sample_aspect_ratio),
            "tb": str(vs.time_base),
            "dur_container": (c.duration / float(av.time_base)) if c.duration else None,
            "dur_stream": (float(vs.duration * vs.time_base) if vs.duration else None),
        }
        for f in c.decode(vs):
            if n == 0:
                primeiro_pts = f.pts
            if f.pts is not None and pts_anterior is not None and f.pts <= pts_anterior:
                pts_ordem = False
            if f.pts is not None and f.pts < 0:
                pts_negativo = True
            pts_anterior = f.pts
            if n in alvo:
                guardados[n] = f.to_ndarray(format="rgb24")
            arr = f.to_ndarray(format="rgb24")
            if primeiro_arr is None:
                primeiro_arr = arr
            ultimo = arr
            n += 1
    return {
        "info": info,
        "n": n,
        "primeiro_arr": primeiro_arr,
        "ultimo_arr": ultimo,
        "primeiro": tinta(primeiro_arr) if primeiro_arr is not None else None,
        "ultimo": tinta(ultimo) if ultimo is not None else 0,
        "pts0": primeiro_pts,
        "pts_ordem": pts_ordem,
        "pts_negativo": pts_negativo,
        "guardados": guardados,
    }


def imprimir(caminho, r):
    i = r["info"]
    print(f"== {caminho}")
    print(
        f"   dur_container={i['dur_container']:.3f}s dur_stream={i['dur_stream']:.3f}s "
        f"frames={r['n']} dur_frames={r['n'] / FPS:.3f}s"
    )
    print(
        f"   {i['w']}x{i['h']} fps={i['fps']:.3f} {i['codec']}/{i['profile']}/{i['pix']} "
        f"sar={i['sar']} tb={i['tb']}"
    )
    print(
        f"   pts0={r['pts0']} pts_monotonico={r['pts_ordem']} pts_negativo={r['pts_negativo']} "
        f"tinta_primeiro={r['primeiro']}px tinta_ultimo={r['ultimo']}px"
    )


def conf_integral(integral, intro, execucao):
    if not (intro["info"]["dur_container"] and execucao["info"]["dur_container"]):
        print("   !! duracao ausente em uma das fontes")
        return
    n_i = intro["n"]
    esperado = intro["n"] + execucao["n"]
    soma_s = intro["info"]["dur_container"] + execucao["info"]["dur_container"]
    print("   -- conferencia do integral --")
    print(
        f"   frames: {integral['n']} vs {intro['n']} + {execucao['n']} = {esperado} -> "
        f"{'OK' if integral['n'] == esperado else 'FALHA'}"
    )
    dif = integral["n"] / FPS - soma_s
    print(
        f"   duracao: frames/15 = {integral['n'] / FPS:.3f}s vs soma containers = {soma_s:.3f}s "
        f"(dif {dif:+.3f}s = {dif * FPS:+.2f} frame) -> "
        f"{'OK' if abs(dif) <= 1.0 / FPS + 1e-9 else 'FALHA'}"
    )
    g = integral["guardados"]
    for rotulo, idx, b in (
        ("ultimo da intro", n_i - 1, intro["ultimo_arr"]),
        ("frame 0 da execucao", n_i, execucao["primeiro_arr"]),
    ):
        a = g[idx].astype(np.int16)
        d = float(np.abs(a - b.astype(np.int16)).mean())
        print(
            f"   frame {idx} do integral == {rotulo}: diff_medio={d:.6f} "
            f"{'IDENTICO' if d == 0.0 else 'DIFERENTE'} (tinta {tinta(g[idx])}px)"
        )


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--integral":
        resto = args[1:]
        trios = [resto[k : k + 3] for k in range(0, len(resto), 3)]
        cache = {}
        for integral, intro_p, exec_p in trios:
            for p in (intro_p, exec_p):
                if p not in cache:
                    cache[p] = varrer(p)
                    imprimir(p, cache[p])
            intro, execucao = cache[intro_p], cache[exec_p]
            n_i = intro["n"]
            # 0 = inicio da intro; n-1/n = fronteira intro/execucao
            r = varrer(integral, indices=(0, n_i - 1, n_i))
            imprimir(integral, r)
            conf_integral(r, intro, execucao)
            a = r["guardados"][0].astype(np.int16)
            b = intro["primeiro_arr"]
            if b is not None:
                d = float(np.abs(a - b.astype(np.int16)).mean())
                print(
                    f"   frame 0 do integral == frame 0 da intro: diff_medio={d:.6f} "
                    f"{'IDENTICO' if d == 0.0 else 'DIFERENTE'}"
                )
    else:
        for p in args:
            imprimir(p, varrer(p, indices=(0,)))
