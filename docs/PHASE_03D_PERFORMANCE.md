# Phase 03D Hardware Benchmark & Performance Report

## 1. Test Environment

All benchmarks were measured directly on the developer's local host workstation:

- **Host Processor**: AMD Ryzen 7 (`AMD64 Family 25 Model 68 Stepping 1, AuthenticAMD`)
- **Logical CPU Cores**: 16 cores (8 physical cores / 16 threads)
- **Host Memory**: 16.0 GB Total Physical RAM (~13.31 GB usable after GPU hardware reservation)
- **Operating System**: Windows 10 Home (Build 26200 / 25H2, 64-bit)
- **Inference Hardware**: CPU-only execution (PyTorch `2.15.0+cpu`, Torchvision `0.29.2+cpu`)
- **Process Architecture**: 64-bit CPython 3.13.14

---

## 2. Memory Footprint & Resource Consumption

Measurements recorded via Win32 `GetProcessMemoryInfo` (Process Working Set):

| Stage | Process Working Set (MB) | Delta from Baseline (MB) |
| :--- | :---: | :---: |
| **Python Process Baseline** | 197.21 MB | — |
| **After Loading Classifier (Head + MobileNetV3 Trunk)** | 328.12 MB | +130.91 MB |
| **After Loading SSDLite320 Object Detector** | 335.25 MB | +7.13 MB |
| **Peak Memory during Concurrent Stress Inference** | **375.52 MB** | **+178.31 MB** |

> **Note**: Both MobileNetV3-Large classification and SSDLite320 object detection share the same underlying architecture. Because the detector weights file (`ssdlite320_mobilenet_v3_large-coco_v1.pth`) supplies the feature trunk for both models, memory overhead remains well below 400 MB.

---

## 3. Cold Model Load Latencies

Measured from initial import and disk read to model instantiation in CPU RAM:

| Engine / Component | Model Checkpoint Path | File Size | Cold Load Latency |
| :--- | :--- | :---: | :---: |
| **iSquare Classifier** | `storage/models/isquare_classifier_head_v1.pth` | 248.1 KB | **2,898.48 ms** |
| **SSDLite320 Detector** | `storage/models/ssdlite320_mobilenet_v3_large-coco_v1.pth` | 13.42 MB | **174.97 ms** |

> **Analysis**: Classifier cold load includes constructing the full MobileNetV3 architecture, loading state dictionaries, extracting the backbone feature trunk, and instantiating Torchvision transforms. Once loaded, models remain cached in process memory across all subsequent requests via thread locks (`_classifier_lock`, `_detector_lock`).

---

## 4. Warm Inference Latency Benchmarks (Ryzen 7)

Evaluated across 25 iterations for classification and 15 iterations for detection across standard resolution profiles.

### 4.1 Single-Thread Execution (`torch.set_num_threads(1)`) — Default Production Setting

| Engine | Image Resolution | Mean Latency | Min Latency | Median (p50) | 95th Percentile (p95) | Max Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Classifier** | 320 $\times$ 320 | **15.22 ms** | 13.84 ms | 14.76 ms | 17.98 ms | 19.65 ms |
| **Classifier** | 640 $\times$ 640 | **17.02 ms** | 15.45 ms | 16.87 ms | 19.46 ms | 19.97 ms |
| **Classifier** | 1024 $\times$ 1024 | **19.75 ms** | 18.50 ms | 19.56 ms | 21.76 ms | 21.85 ms |
| **Detector** | 320 $\times$ 320 | **67.36 ms** | 57.37 ms | 63.56 ms | 102.54 ms | 102.54 ms |
| **Detector** | 640 $\times$ 640 | **73.37 ms** | 67.25 ms | 72.17 ms | 86.38 ms | 86.38 ms |
| **Detector** | 1024 $\times$ 1024 | **100.04 ms** | 95.82 ms | 99.02 ms | 112.89 ms | 112.89 ms |

---

## 5. Thread Scaling Analysis (1 vs. 4 vs. 8 CPU Threads)

To evaluate multi-threaded CPU parallelization in PyTorch, latency was measured at 1, 4, and 8 worker threads on 1024 $\times$ 1024 inputs:

| Thread Count | Classifier Mean Latency (1024x1024) | Detector Mean Latency (1024x1024) | Notes |
| :---: | :---: | :---: | :--- |
| **1 Thread** | **19.75 ms** | 100.04 ms | Optimal for classifier; minimal context switching |
| **4 Threads** | 18.82 ms | **73.18 ms** | 27% speedup on detection; best overall balance |
| **8 Threads** | 21.82 ms | 77.74 ms | Inter-thread synchronization overhead increases latency |

### Recommended Configuration
- For background worker inference on Ryzen 7, setting `torch.set_num_threads(4)` offers the fastest object detection throughput (73.18 ms) without thread contention.
- Classifier inference remains sub-20 ms regardless of thread count.
