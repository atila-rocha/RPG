import sys
from pathlib import Path

from PIL import Image

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
box = tuple(int(x) for x in sys.argv[3:7])  # left top right bottom
escala = float(sys.argv[7]) if len(sys.argv) > 7 else 2.0

img = Image.open(src).crop(box)
img = img.resize((int(img.width * escala), int(img.height * escala)), Image.LANCZOS)
img.save(dst)
print(dst, img.size)
