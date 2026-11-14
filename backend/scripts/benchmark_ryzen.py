"""
Hardware benchmark script for iSquare running on AMD Ryzen 7 (Windows 10, CPU-only).
Measures:
- Cold load latency (models + weights)
- Warm inference latency (classifier & detector)
- Latency across different image resolutions
- Impact of PyTorch thread count (1, 4, 8)
- Memory usage (working set)
"""
import ctypes
from ctypes import wintypes
import gc
import json
import os
import platform
import time
from pathlib import Path
from PIL import Image

import torch
from app.core.config import settings
from app.services.analysis.engines import _load_classifier, _load_detector, run_classifier, run_detector
from app.services.analysis.preprocessing import PreparedImage


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def get_working_set_mb() -> float:
    kernel32 = ctypes.windll.kernel32
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.windll.psapi
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    pmc = PROCESS_MEMORY_COUNTERS()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return round(pmc.WorkingSetSize / (1024 * 1024), 2)


def benchmark():
    results = {}
    
    # 1. System Info
    cpu_model = os.environ.get("PROCESSOR_IDENTIFIER", platform.processor())
    results["hardware"] = {
        "os": f"Windows 10 ({platform.version()})",
        "cpu": cpu_model,
        "logical_cores": os.cpu_count(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "torch": torch.__version__,
    }
    
    initial_ram = get_working_set_mb()
    results["memory_baseline_mb"] = initial_ram
    
    # 2. Classifier Cold Load
    import app.services.analysis.engines as engines
    engines._classifier = None
    engines._classifier_meta = None
    
    t0 = time.perf_counter()
    _load_classifier()
    cold_load_classifier_ms = round((time.perf_counter() - t0) * 1000, 2)
    ram_after_classifier = get_working_set_mb()
    
    # 3. Detector Cold Load
    engines._detector = None
    engines._detector_meta = None
    
    t0 = time.perf_counter()
    _load_detector()
    cold_load_detector_ms = round((time.perf_counter() - t0) * 1000, 2)
    ram_after_detector = get_working_set_mb()
    
    results["cold_load_ms"] = {
        "classifier": cold_load_classifier_ms,
        "detector": cold_load_detector_ms,
    }
    results["memory_footprint_mb"] = {
        "baseline": initial_ram,
        "after_classifier": ram_after_classifier,
        "classifier_delta": round(ram_after_classifier - initial_ram, 2),
        "after_detector": ram_after_detector,
        "detector_delta": round(ram_after_detector - ram_after_classifier, 2),
    }
    
    # Test images across resolutions
    resolutions = [
        ("320x320", 320, 320),
        ("640x640", 640, 640),
        ("1024x1024", 1024, 1024),
    ]
    
    # Warm inference benchmark (1 thread vs 4 threads vs 8 threads)
    thread_benchmarks = {}
    for num_threads in [1, 4, 8]:
        torch.set_num_threads(num_threads)
        thread_results = {"classifier": {}, "detector": {}}
        
        for name, w, h in resolutions:
            img = Image.new("RGB", (w, h), (120, 150, 180))
            prepared = PreparedImage(img, w, h, w, h, [])
            
            # Warm up
            run_classifier(prepared)
            run_detector(prepared)
            
            # Benchmark classifier (25 iterations)
            c_times = []
            for _ in range(25):
                t0 = time.perf_counter()
                run_classifier(prepared)
                c_times.append((time.perf_counter() - t0) * 1000)
                
            # Benchmark detector (15 iterations)
            d_times = []
            for _ in range(15):
                t0 = time.perf_counter()
                run_detector(prepared)
                d_times.append((time.perf_counter() - t0) * 1000)
                
            prepared.close()
            
            c_times.sort()
            d_times.sort()
            
            thread_results["classifier"][name] = {
                "mean_ms": round(sum(c_times) / len(c_times), 2),
                "min_ms": round(min(c_times), 2),
                "p50_ms": round(c_times[len(c_times) // 2], 2),
                "p95_ms": round(c_times[int(len(c_times) * 0.95)], 2),
                "max_ms": round(max(c_times), 2),
            }
            thread_results["detector"][name] = {
                "mean_ms": round(sum(d_times) / len(d_times), 2),
                "min_ms": round(min(d_times), 2),
                "p50_ms": round(d_times[len(d_times) // 2], 2),
                "p95_ms": round(d_times[int(len(d_times) * 0.95)], 2),
                "max_ms": round(max(d_times), 2),
            }
        thread_benchmarks[f"threads_{num_threads}"] = thread_results
        
    results["inference_benchmarks"] = thread_benchmarks
    results["peak_ram_mb"] = get_working_set_mb()
    
    # Reset thread count to default
    torch.set_num_threads(1)
    
    out_path = Path("storage/dataset/ryzen_hardware_benchmark.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    benchmark()
