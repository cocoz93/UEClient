"""Tile a run's screenshots (in step order of file time) into one labelled grid.png. Usage: python shot_grid.py <run folder> [columns]"""
from pathlib import Path
import sys

from PIL import Image, ImageDraw

run = Path(sys.argv[1])
columns = int(sys.argv[2]) if len(sys.argv) > 2 else 4
shots = sorted((run / 'screenshots').glob('*.png'), key=lambda p: p.stat().st_mtime)
tile_width = 480
tiles = []
for shot in shots:
    image = Image.open(shot).convert('RGB')
    image = image.resize((tile_width, int(image.height * tile_width / image.width)))
    canvas = Image.new('RGB', (image.width, image.height + 22), 'white')
    canvas.paste(image, (0, 22))
    ImageDraw.Draw(canvas).text((6, 4), shot.stem, fill='black')
    tiles.append(canvas)
rows = (len(tiles) + columns - 1) // columns
tile_height = max(t.height for t in tiles)
grid = Image.new('RGB', (tile_width * columns, tile_height * rows), 'white')
for index, tile in enumerate(tiles):
    grid.paste(tile, ((index % columns) * tile_width, (index // columns) * tile_height))
grid.save(run / 'grid.png')
print(run / 'grid.png', len(tiles))
