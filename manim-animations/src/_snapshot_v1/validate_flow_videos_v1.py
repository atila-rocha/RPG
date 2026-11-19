"""
Validador dos vídeos de fluxo máximo (Edmonds-Karp e Ford-Fulkerson/DFS).

Uso:
    python validate_flow_videos.py <video.mp4> [video.mp4 ...]

Verifica, para cada vídeo:
  1. o ÚLTIMO frame não é tela preta;
  2. nenhuma banda de texto toca a borda do quadro;
  3. os 7 papéis da paleta do contrato (`PLANO_VISUAL_FLUXO.md` §3) aparecem
     no vídeo — nenhuma cor é decorativa e nenhuma cor do guia fica sem uso;
  4. a cor cinza-padrão antiga (#4a4e69) não aparece (paleta única);
  5. os painéis de código e de estado têm texto em todo frame amostrado
     (painel vazio = bug de montagem, não de conteúdo);
  6. o fecho mostra o corte mínimo (anel âmbar no último frame);
  7. a duração bate com o alvo do plano (folga de 40%).
"""

from __future__ import annotations

import sys

import av
import numpy as np

# Papéis do guia (§3): cor, nome, alvo esperado
PALETA = {
    "fora": (0x8D, 0x99, 0xAE),
    "fluxo": (0x4C, 0xC9, 0xF0),
    "saturada": (0x06, 0xD6, 0xA0),
    "exame": (0xE8, 0x79, 0xF9),
    "caminho": (0xFF, 0xD1, 0x66),
    "reversa": (0xEF, 0x47, 0x6F),
    "alcancado": (0x80, 0xED, 0x99),
}
COR_CINZA_ANTIGA = (0x4A, 0x4E, 0x69)
COR_FUNDO = (0x0F, 0x11, 0x1A)

TOLERANCIA = 22
N_AMOSTRAS = 24

# alvos de duração do plano (§8) — BFS ~10,6 min · DFS ~8,0 min
ALVO = {"edmonds": 10.6 * 60, "ford": 8.0 * 60}


def _contar(a: np.ndarray, cor, tol: int = TOLERANCIA) -> int:
    d = np.abs(a.astype(int) - np.array(cor)).sum(axis=2)
    return int((d <= tol).sum())


def _bandas_texto(a: np.ndarray, limiar: int = 300):
    lum = a.sum(axis=2)
    bright = (lum > limiar) & (
        np.abs(a.astype(int) - np.array(COR_FUNDO)).sum(axis=2) > 60
    )
    rows = bright.sum(axis=1)
    bandas, dentro, ini = [], False, 0
    for y in range(len(rows)):
        if rows[y] > 3 and not dentro:
            dentro, ini = True, y
        elif rows[y] <= 3 and dentro:
            dentro = False
            bandas.append((ini, y - 1))
    if dentro:
        bandas.append((ini, len(rows) - 1))
    return bandas


def _tem_texto(a: np.ndarray, box, limiar: int = 6) -> bool:
    """A região (x0, x1, y0, y1) em coordenadas de tela tem pixels claros?"""
    x0, x1, y0, y1 = [int(v) for v in box]
    recorte = a[y0:y1, x0:x1]
    if recorte.size == 0:
        return False
    lum = recorte.sum(axis=2)
    return bool((lum > 300).sum() > limiar)


def _caixa_tela(box, largura: int, altura: int, inset: float = 0.10):
    """Converte (x0, x1, y0, y1) de cena para pixels de tela (origem no topo)."""
    x0, x1, y0, y1 = box
    x0, x1 = x0 + inset, x1 - inset
    y0, y1 = y0 + inset, y1 - inset

    def px(x):
        return (x + 7.1111) / 14.2222 * largura

    def py(y):
        return (4.0 - y) / 8.0 * altura

    return (px(x0), px(x1), py(y1), py(y0))


def validar(caminho: str) -> bool:
    nome = caminho.replace("\\", "/").split("/")[-1]
    print("=" * 74)
    print("VALIDANDO:", nome)

    container = av.open(caminho)
    stream = container.streams.video[0]
    fps = float(stream.average_rate)
    largura = int(stream.codec_context.width)
    altura = int(stream.codec_context.height)

    frames = []
    n = 0
    for frame in container.decode(video=0):
        n += 1
        frames.append(frame.to_ndarray(format="rgb24"))
    container.close()

    if n == 0:
        print("  FALHA: vídeo sem frames")
        return False

    passo = max(1, n // N_AMOSTRAS)
    # o primeiro frame é o fade-in da montagem: amostramos 2%..98%
    inicio = int(0.02 * n)
    amostras = frames[inicio::passo][:N_AMOSTRAS]
    ultimo = frames[-1]
    duracao = n / fps
    print(f"  frames={n}  fps={fps:.1f}  dur={duracao/60:.2f} min  {largura}x{altura}")

    ok = True

    # --- 1. último frame não-preto -------------------------------------
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
    # tolerância apertada de propósito: com 22 o antialias da borda #8d99ae
    # sobre o fundo #0f111a cai em cima do #4a4e69 e dá falso positivo.
    # Sobram ~10 px isolados por frame (ruído de AA), nunca uma região.
    cinza = max(_contar(f, COR_CINZA_ANTIGA, tol=8) for f in amostras)
    print(f"  [4] cinza antigo #4a4e69 (tol 8): {cinza} px/frame"
          f" -> {'OK' if cinza <= 30 else 'FALHA'} (ruído de antialias ≤ 30)")
    ok &= cinza <= 30

    # --- 5. painéis preenchidos (código, guia, estado) -------------------
    caixas = {
        # a troca de view é FadeOut total e DEPOIS FadeIn (dois plays): há
        # frame sem código por contrato — 596 trocas × ~3 frames ≈ 17% do
        # vídeo. Por isso o piso do código é 75%; guia e estado não piscam.
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
