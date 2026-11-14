"""Detector and preprocessor benchmark — run from backend/ directory."""
import time, sys, os
sys.path.insert(0, '.')
os.environ.setdefault('MODEL_CACHE_DIR', './storage/models')

from pathlib import Path
from app.services.analysis.preprocessing import prepare_image

FIXTURES = Path('tests/fixtures')

print('=== DETECTOR BENCHMARK ===')
print('Cold load (includes model initialization from disk):')
t0 = time.perf_counter()
from app.services.analysis.engines import run_detector, _load_detector
_load_detector()
cold_ms = round((time.perf_counter() - t0) * 1000)
print(f'  Model load time: {cold_ms} ms')

fixtures = [
    'fixture_printed_document.png',
    'fixture_geometric_shapes.png',
    'fixture_multi_column_poster.png',
    'fixture_blank_document.png',
    'fixture_low_resolution.png',
]

print()
print('Warm inference per fixture:')
for name in fixtures:
    p = prepare_image(FIXTURES / name)
    t1 = time.perf_counter()
    detections = run_detector(p)
    warm_ms = round((time.perf_counter() - t1) * 1000)
    print(f'  {name}')
    print(f'    Dims: {p.width}x{p.height}  Detections: {len(detections)}  Time: {warm_ms} ms')
    for d in detections:
        box = d.box
        print(f'    -> {d.label}: conf={d.confidence:.2f}  box=x{box["x"]},y{box["y"]},w{box["width"]},h{box["height"]}')
    p.close()

import torchvision, torch
print()
print(f'Model: torchvision-ssdlite320-mobilenet_v3_large-coco, version {torchvision.__version__}')
print(f'PyTorch: {torch.__version__}, threads: {torch.get_num_threads()}, CUDA: {torch.cuda.is_available()}')

