"""Concatena MP4s (mesmo codec/resolucao) por remux, sem re-encode.

Uso:
    python _concat_mp4.py saida.mp4 entrada1.mp4 entrada2.mp4 ...
"""
import sys
import av


def concatenar(saida, entradas):
    saida_container = av.open(saida, mode="w")
    out_stream = None
    out_tb = None
    offset_s = 0.0

    for caminho in entradas:
        entrada = av.open(caminho)
        in_stream = entrada.streams.video[0]
        tb = in_stream.time_base

        if out_stream is None:
            out_stream = saida_container.add_stream_from_template(in_stream)
            out_tb = in_stream.time_base

        inicio_s = offset_s
        for packet in entrada.demux(in_stream):
            if packet.dts is None:
                continue
            packet.stream = out_stream
            if packet.pts is not None:
                packet.pts = int((inicio_s + float(packet.pts * tb)) / float(out_tb))
            packet.dts = int((inicio_s + float(packet.dts * tb)) / float(out_tb))
            packet.time_base = out_tb
            saida_container.mux(packet)

        if in_stream.duration is not None:
            offset_s += float(in_stream.duration * tb)
        elif entrada.duration is not None:
            offset_s += entrada.duration / float(av.time_base)
        entrada.close()

    saida_container.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    concatenar(sys.argv[1], sys.argv[2:])
    print("OK:", sys.argv[1])
