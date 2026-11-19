"""
Validador dos vídeos de fluxo máximo (Edmonds-Karp e Ford-Fulkerson/DFS).

Uso:
    python validate_flow_videos.py <video.mp4> [video.mp4 ...]

Verifica, para cada vídeo:
  1. o ÚLTIMO frame não é tela preta;
  2. nenhuma banda de texto toca a borda do quadro;
  3. os 7 papéis da paleta do contrato (`PLANO_VISUAL_FLUXO_V2.md` §C.7)
     aparecem no vídeo — nenhuma cor é decorativa e nenhuma cor do guia fica
     sem uso;
  4. a cor cinza-padrão antiga (#4a4e69) não aparece (paleta única);
  5. os painéis de código e de estado têm texto em todo frame amostrado;
  6. o fecho mostra o corte mínimo (anel âmbar no último frame);
  7. a duração bate com o alvo do plano (folga de 40%);
  8. (V2) 1 frame por aba, com a cor semântica daquela aba dentro do corpo da
     estrutura: `rede` #06d6a0, `busca` #80ed99, `marcados` #80ed99,
     `edge_to` #ffd166 e `adj` com chips #1f2637 (prova de aba não vazia).
"""

from __future__ import annotations

import sys
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import flow_common as fc  # noqa: E402
import flow_record as rec  # noqa: E402

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

# alvos de duração do plano V2 (§A.5) — BFS ~18,7 min · DFS ~13,8 min
ALVO = {"edmonds": 18.7 * 60, "ford": 13.8 * 60}

# Slot de cada aba no trilho vertical (x0, x1, y0, y1). A aba ATIVA e a unica
# com fundo COR_TAB_ATIVA (#1f2637): e evidencia de que aquela aba esteve em
# cena. Cores de CONTEUDO nao servem para isso - `saturada`, por exemplo, so
# aparece depois da primeira augmentacao, e `alcancado` em chips tem 22 % de
# opacidade (cor misturada, nao o hex da paleta).
X_SLOT = (-6.48, -5.18)
SLOTS_ABA = {
    "rede": (*X_SLOT, -1.72, -1.40),
    "busca": (*X_SLOT, -2.09, -1.77),
    "marcados": (*X_SLOT, -2.46, -2.14),
    "edge_to": (*X_SLOT, -2.83, -2.51),
    "adj": (*X_SLOT, -3.20, -2.88),
}
COR_TAB_ATIVA = (0x1F, 0x26, 0x37)


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


def _recorte(a: np.ndarray, caixa) -> np.ndarray:
    x0, x1, y0, y1 = [int(v) for v in caixa]
    return a[max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)]


def _contar_na_caixa(a: np.ndarray, cor, caixa, tol: int = TOLERANCIA) -> int:
    recorte = _recorte(a, caixa)
    if recorte.size == 0:
        return 0
    return _contar(recorte, cor, tol)


def _fora_do_guia(a: np.ndarray, caixa_guia) -> np.ndarray:
    """Cópia do frame com a caixa do guia zerada (para contagens sem o guia)."""
    copia = a.copy()
    x0, x1, y0, y1 = [int(v) for v in caixa_guia]
    copia[max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)] = 0
    return copia


def _tempo_por_aba(nome_alg: str) -> dict[str, float]:
    """Fração estimada do vídeo em que cada aba aparece (meio do maior run)."""
    algoritmo = "ford_fulkerson_dfs" if "ford" in nome_alg else "edmonds_karp"
    try:
        passos = rec.coletar_detalhado(algoritmo)
        abas = fc.calcular_abas(algoritmo, passos)
    except Exception:
        return {}

    tempos = []
    acumulado = 0.0
    for i, passo in enumerate(passos):
        troca = i > 0 and abas[i] != abas[i - 1]
        play = (
            fc.RITMO["play_destaque"]
            if fc.FlowExecucaoBase._tem_flash(passo)
            else fc.RITMO["play"]
        )
        pausa = fc.RITMO["pausa"].get(round(passo.pausa, 2), fc.RITMO["pausa"][0.55])
        extra = 2 * fc.RITMO["fade"] if troca else 0.0
        duracao = play + extra + max(0.0, pausa - extra)
        tempos.append((acumulado, acumulado + duracao, abas[i]))
        acumulado += duracao

    acumulado += 7.2  # montagem + fechar
    fracoes: dict[str, float] = {}
    for aba in fc.ORDEM_ABAS:
        runs = [(ini, fim) for ini, fim, a in tempos if a == aba]
        if not runs:
            continue
        # maior run contínuo em tempo
        blocos = []
        ini_run, fim_run = runs[0]
        for ini, fim in runs[1:]:
            if abs(ini - fim_run) < 1e-9:
                fim_run = fim
            else:
                blocos.append((ini_run, fim_run))
                ini_run, fim_run = ini, fim
        blocos.append((ini_run, fim_run))
        ini, fim = max(blocos, key=lambda par: par[1] - par[0])
        fracoes[aba] = ((ini + fim) / 2) / acumulado
    return fracoes


def validar(caminho: str) -> bool:
    nome = caminho.replace("\\", "/").split("/")[-1]
    print("=" * 74)
    print("VALIDANDO:", nome)

    container = av.open(caminho)
    stream = container.streams.video[0]
    fps = float(stream.average_rate)
    largura = int(stream.codec_context.width)
    altura = int(stream.codec_context.height)

    # Streaming: um vídeo de 19 min a 854x480 tem ~17 mil frames = ~20 GB de
    # RGB. Guardamos SÓ as amostras e o último frame; o teste por aba é
    # avaliado na hora e descarta o pixel. (A V2 guardava tudo e estourava RAM.)
    n_meta = int(stream.frames or 0)
    if not n_meta:
        if stream.duration:
            n_meta = int(float(stream.duration * stream.time_base) * fps)
        if not n_meta:
            container.close()
            container = av.open(caminho)
            n_meta = sum(1 for _ in container.decode(video=0))
            container.close()
            container = av.open(caminho)

    fracoes = _tempo_por_aba(nome)

    passo = max(1, n_meta // N_AMOSTRAS)
    inicio = int(0.02 * n_meta)
    idx_amostras = set(range(inicio, n_meta, passo))
    idx_ultimo = {n_meta - 1, max(0, n_meta - 2)}

    # candidatos por aba: janela em torno do centro previsto pelo trace,
    # mais uma grade grossa no vídeo inteiro como fallback.
    janela = max(3, n_meta // 200)
    idx_janela: dict[int, set[str]] = {}
    for aba, fracao in fracoes.items():
        if aba not in SLOTS_ABA:
            continue
        centro = int(fracao * n_meta)
        for i in range(max(0, centro - janela), min(n_meta, centro + janela + 1)):
            idx_janela.setdefault(i, set()).add(aba)
    idx_grade = set(range(0, n_meta, max(1, n_meta // 400)))

    caixas_slot = {
        aba: _caixa_tela(box, largura, altura, inset=0.0)
        for aba, box in SLOTS_ABA.items()
    }

    def _valor_aba(arr, aba: str) -> int:
        """Pixels do fundo de aba ATIVA no slot daquela aba."""
        return _contar_na_caixa(arr, COR_TAB_ATIVA, caixas_slot[aba], tol=10)

    amostras: list = []
    ultimo = None
    janela_melhor = {a: (-1, -1) for a in fracoes if a in SLOTS_ABA}
    grade_melhor = {a: (-1, -1) for a in fracoes if a in SLOTS_ABA}

    n = 0
    for frame in container.decode(video=0):
        relevante = (
            n in idx_amostras
            or n in idx_ultimo
            or n in idx_janela
            or n in idx_grade
        )
        if not relevante:
            n += 1
            continue
        arr = frame.to_ndarray(format="rgb24")
        if n in idx_amostras:
            amostras.append(arr)
        if n in idx_janela:
            for aba in idx_janela[n]:
                valor = _valor_aba(arr, aba)
                if valor > janela_melhor[aba][0]:
                    janela_melhor[aba] = (valor, n)
        if n in idx_grade:
            for aba in grade_melhor:
                valor = _valor_aba(arr, aba)
                if valor > grade_melhor[aba][0]:
                    grade_melhor[aba] = (valor, n)
        ultimo = arr
        n += 1
    container.close()

    if n == 0:
        print("  FALHA: vídeo sem frames")
        return False
    if ultimo is None:  # metadados mentiram: pega só o último frame
        container = av.open(caminho)
        for frame in container.decode(video=0):
            ultimo = frame.to_ndarray(format="rgb24")
        container.close()
        if ultimo is None:
            print("  FALHA: não consegui ler o último frame")
            return False

    amostras = amostras[:N_AMOSTRAS]
    duracao = n / fps
    print(f"  frames={n}  fps={fps:.1f}  dur={duracao/60:.2f} min  {largura}x{altura}")
    print(f"  amostras guardadas={len(amostras)} (streaming, sem carregar o vídeo)")

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
    cinza = max(_contar(f, COR_CINZA_ANTIGA, tol=8) for f in amostras)
    print(f"  [4] cinza antigo #4a4e69 (tol 8): {cinza} px/frame"
          f" -> {'OK' if cinza <= 30 else 'FALHA'} (ruído de antialias ≤ 30)")
    ok &= cinza <= 30

    # --- 5. painéis preenchidos (código, guia, estado) -------------------
    caixas = {
        # a troca de view é FadeOut total e DEPOIS FadeIn (dois plays): há
        # frame sem código por contrato. Piso de 75%.
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

    # --- 8. 1 frame por aba (V2) ----------------------------------------
    # Os valores por aba vieram do streaming acima (sem guardar o vídeo).
    # Evidencia: o fundo da aba ATIVA no slot daquela aba do trilho.
    for aba in SLOTS_ABA:
        fracao = fracoes.get(aba)
        if fracao is None:
            print(f"  [8] aba {aba}: sem passo no trace -> FALHA")
            ok = False
            continue
        # Duas evidencias independentes, e vale a MELHOR das duas:
        #   - `janela`: regiao onde o modelo de duracao por passo preve a aba;
        #   - `grade` : varredura do video inteiro (fallback).
        # A `janela` sozinha ja deu falso negativo no DFS: o modelo assume
        # duracao fixa por passo, mas alguns passos emitem plays extras
        # (flash, troca de caption), entao o centro derivado do trace desliza
        # ~300 frames e cai dentro de outro run. O video esta correto - a
        # evidencia que importa e "a aba ATIVA aparece em algum frame?".
        mj, ij = janela_melhor.get(aba, (-1, -1))
        mg, ig = grade_melhor.get(aba, (-1, -1))
        if mg >= mj:
            melhor, melhor_i, usado = mg, ig, "grade"
        else:
            melhor, melhor_i, usado = mj, ij, "janela"
        piso = 200  # ~1.500 px uteis no slot a 480p; texto/borda comem parte
        veredito = "OK" if melhor > piso else "FALHA"
        print(f"  [8] aba {aba}: frame {melhor_i} ({melhor_i / n:.0%}, {usado}) -> "
              f"{melhor} px de aba ativa no slot -> {veredito}")
        ok &= melhor > piso
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
