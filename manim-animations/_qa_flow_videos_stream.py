"""QA de frames em STREAMING para os vídeos de fluxo máximo.

`validate_flow_videos.py` decodifica TODOS os frames para uma lista em RAM
(~13 GB para o BFS de 11,8 min em 480p15, com 7,8 GB de RAM na máquina).
Esta variante aplica as MESMAS 7 verificações, com as mesmas constantes e
helpers importados do validador oficial, mas guarda só as 24 amostras + o
último frame.

Uso:
    python _qa_flow_videos_stream.py <video.mp4> [video.mp4 ...]

Não substitui o validador oficial: é o mesmo critério, medido sem OOM.
"""

from __future__ import annotations

import sys

import av
import numpy as np

from validate_flow_videos import (
    ALVO,
    COR_CINZA_ANTIGA,
    N_AMOSTRAS,
    PALETA,
    _bandas_texto,
    _caixa_tela,
    _contar,
    _tem_texto,
)


def validar(caminho: str) -> bool:
    nome = caminho.replace("\\", "/").split("/")[-1]
    print("=" * 74)
    print("VALIDANDO (streaming):", nome)

    # --- passe 1: metadados exatos + último frame -----------------------
    container = av.open(caminho)
    stream = container.streams.video[0]
    fps = float(stream.average_rate)
    largura = int(stream.codec_context.width)
    altura = int(stream.codec_context.height)
    n = 0
    ultimo = None
    for frame in container.decode(video=0):
        n += 1
        if ultimo is not None:
            del ultimo
        ultimo = frame.to_ndarray(format="rgb24")
    container.close()

    if n == 0:
        print("  FALHA: vídeo sem frames")
        return False

    passo = max(1, n // N_AMOSTRAS)
    inicio = int(0.02 * n)
    indices = list(range(inicio, n, passo))[:N_AMOSTRAS]

    # --- passe 2: só as amostras ----------------------------------------
    amostras = []
    container = av.open(caminho)
    for i, frame in enumerate(container.decode(video=0)):
        if i in set(indices):
            amostras.append(frame.to_ndarray(format="rgb24"))
            if len(amostras) >= len(indices):
                break
    container.close()

    duracao = n / fps
    print(f"  frames={n}  fps={fps:.1f}  dur={duracao/60:.2f} min  {largura}x{altura}")
    print(f"  amostras={len(amostras)} (passo {passo}, inicio {inicio})")

    ok = True

    # --- 1. último frame não-preto --------------------------------------
    claros = int((ultimo.sum(axis=2) > 300).sum())
    print(f"  [1] último frame: {claros} pixels claros -> {'OK' if claros > 500 else 'FALHA'}")
    ok &= claros > 500

    # --- 2. texto dentro do quadro --------------------------------------
    fora = [b for b in _bandas_texto(ultimo) if b[0] <= 1 or b[1] >= altura - 2]
    print(f"  [2] bandas de texto fora do quadro: {len(fora)} -> {'OK' if not fora else 'FALHA'}")
    if fora:
        print("      bandas:", fora[:5])
    ok &= not fora

    # --- 3. os 7 papéis da paleta aparecem ------------------------------
    faltando = []
    contagem = {}
    for papel, cor in PALETA.items():
        total = max(_contar(f, cor) for f in amostras)
        contagem[papel] = total
        if total == 0:
            faltando.append(papel)
    print("  [3] papéis: " + " ".join(f"{p}={contagem[p]}" for p in PALETA))
    print(f"      papéis sem uso: {faltando or 'nenhum'} -> {'OK' if not faltando else 'FALHA'}")
    ok &= not faltando

    # --- 4. cinza antigo ausente ----------------------------------------
    cinza = max(_contar(f, COR_CINZA_ANTIGA, tol=8) for f in amostras)
    print(f"  [4] cinza antigo #4a4e69 (tol 8): {cinza} px/frame"
          f" -> {'OK' if cinza <= 30 else 'FALHA'} (ruído de antialias ≤ 30)")
    ok &= cinza <= 30

    # --- 5. painéis preenchidos -----------------------------------------
    caixas = {
        "codigo": (_caixa_tela((-6.56, 1.30, -1.10, 3.45), largura, altura), 0.75),
        "guia": (_caixa_tela((1.55, 6.49, -0.85, -0.44), largura, altura), 0.90),
        "estado": (_caixa_tela((1.50, 6.83, -3.72, -1.60), largura, altura), 0.90),
    }
    for nome_caixa, (caixa, piso) in caixas.items():
        cheias = sum(1 for f in amostras if _tem_texto(f, caixa))
        fracao = cheias / len(amostras)
        print(f"  [5] {nome_caixa} preenchido em {cheias}/{len(amostras)} amostras"
              f" ({fracao:.0%}, piso {piso:.0%}) -> {'OK' if fracao >= piso else 'FALHA'}")
        ok &= fracao >= piso

    # --- 6. fecho: anel do corte (âmbar) no último frame -----------------
    aneis = _contar(ultimo, PALETA["caminho"])
    print(f"  [6] anel do corte no último frame: {aneis} px -> {'OK' if aneis > 200 else 'FALHA'}")
    ok &= aneis > 200

    # --- 7. duração contra o alvo ---------------------------------------
    alvo = ALVO["ford"] if "ford" in nome.lower() else ALVO["edmonds"]
    razao = duracao / alvo
    print(f"  [7] duração {duracao/60:.2f} min vs alvo {alvo/60:.2f} min"
          f" ({razao:.0%}) -> {'OK' if 0.6 <= razao <= 1.4 else 'AVISO'}")
    if not (0.6 <= razao <= 1.4):
        print("      fora da folga de 40%: revise o ritmo de pausa")

    print("  RESULTADO:", "APROVADO" if ok else "REPROVADO")
    return ok


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    resultados = [validar(p) for p in args]
    print("=" * 74)
    print("TODOS APROVADOS" if all(resultados) else "HÁ FALHAS")
    return 0 if all(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
