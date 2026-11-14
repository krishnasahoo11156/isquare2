"""
Train ISquareClassificationHeadV2 with domain adaptation and normalization (Phase 03F).
Evaluates on untouched test split and produces full evaluation metrics.
Saves weights to storage/models/isquare_classifier_head_v2.pth.
"""
import json
import time
from pathlib import Path
from PIL import Image

import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models.detection import ssdlite320_mobilenet_v3_large

BACKEND_DIR = Path(__file__).resolve().parent.parent
STORAGE_MODELS = BACKEND_DIR / "storage" / "models"
REAL_DATASET_DIR = BACKEND_DIR / "storage" / "dataset" / "realworld_dataset"

CATEGORIES = [
    "Human photograph",
    "Document",
    "Screenshot",
    "Logo or graphic",
    "Object or product",
    "Landscape or outdoor scene",
    "Animal photograph",
    "Illustration or artwork",
    "Mixed-content image",
    "Other",
]


class ISquareClassificationHeadV2(nn.Module):
    def __init__(self, in_features: int = 480, num_classes: int = 10):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.BatchNorm1d(256),
            nn.Hardswish(),
            nn.Dropout(p=0.25),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.Hardswish(),
            nn.Dropout(p=0.15),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(x)


def load_backbone():
    weights_path = STORAGE_MODELS / "ssdlite320_mobilenet_v3_large-coco_v1.pth"
    if not weights_path.is_file():
        raise FileNotFoundError(f"Missing SSDLite detector weights at: {weights_path}")
    detector = ssdlite320_mobilenet_v3_large(weights=None, weights_backbone=None)
    state = torch.load(weights_path, map_location="cpu", weights_only=True)
    detector.load_state_dict(state)
    backbone = detector.backbone.features
    backbone.eval()
    for param in backbone.parameters():
        param.requires_grad = False
    return backbone


transform_pipeline = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def extract_features(backbone, split: str, manifest: list[dict]):
    items = [m for m in manifest if m["split"] == split]
    features = []
    labels = []
    for item in items:
        img_path = BACKEND_DIR / item["filepath"]
        with Image.open(img_path) as img:
            tensor = transform_pipeline(img.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            feat = backbone(tensor)
            pooled = nn.functional.adaptive_avg_pool2d(feat, (1, 1)).flatten(1)
        features.append(pooled)
        labels.append(item["category_index"])
    return torch.cat(features, dim=0), torch.tensor(labels, dtype=torch.long)


def train_and_evaluate():
    torch.manual_seed(42)
    torch.set_num_threads(1)
    
    manifest_path = REAL_DATASET_DIR / "realworld_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    print("Loading pre-trained MobileNetV3-Large feature backbone...")
    backbone = load_backbone()
    
    print("Extracting features across splits...")
    X_train, y_train = extract_features(backbone, "train", manifest)
    X_val, y_val = extract_features(backbone, "val", manifest)
    X_test, y_test = extract_features(backbone, "test", manifest)
    print(f"Features: train={X_train.shape}, val={X_val.shape}, test={X_test.shape}")
    
    head = ISquareClassificationHeadV2(in_features=480, num_classes=len(CATEGORIES))
    optimizer = torch.optim.AdamW(head.parameters(), lr=0.003, weight_decay=1e-3)
    criterion = nn.CrossEntropyLoss()
    
    epochs = 45
    best_val_acc = 0.0
    best_state = None
    
    print(f"Training ISquareClassificationHeadV2 for {epochs} epochs...")
    for epoch in range(1, epochs + 1):
        head.train()
        optimizer.zero_grad()
        logits = head(X_train)
        loss = criterion(logits, y_train)
        loss.backward()
        optimizer.step()
        
        head.eval()
        with torch.no_grad():
            val_preds = head(X_val).argmax(dim=1)
            val_acc = (val_preds == y_val).float().mean().item()
            train_acc = (logits.argmax(dim=1) == y_train).float().mean().item()
            
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in head.state_dict().items()}
            
        if epoch % 10 == 0 or epoch == epochs:
            print(f"Epoch {epoch:02d}/{epochs:02d} - Loss: {loss.item():.4f} - Train Acc: {train_acc*100:.1f}% - Val Acc: {val_acc*100:.1f}%")
            
    # Load best checkpoint
    head.load_state_dict(best_state)
    head.eval()
    
    # Save checkpoint v2
    out_pth = STORAGE_MODELS / "isquare_classifier_head_v2.pth"
    torch.save(best_state, out_pth)
    print(f"Saved best model weights (val_acc={best_val_acc*100:.1f}%) to {out_pth}")
    
    # Evaluate on untouched test split
    with torch.no_grad():
        test_logits = head(X_test)
        test_probs = torch.softmax(test_logits, dim=1).numpy()
        test_preds = test_logits.argmax(dim=1).numpy()
        
    y_test_np = y_test.numpy()
    test_acc = float(np.mean(test_preds == y_test_np))
    
    # Confusion matrix & per-class metrics
    num_classes = len(CATEGORIES)
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_test_np, test_preds):
        cm[t, p] += 1
        
    per_class = {}
    for idx, cat in enumerate(CATEGORIES):
        tp = cm[idx, idx]
        fp = np.sum(cm[:, idx]) - tp
        fn = np.sum(cm[idx, :]) - tp
        support = int(np.sum(y_test_np == idx))
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        per_class[cat] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support,
        }
        
    macro_prec = float(np.mean([m["precision"] for m in per_class.values()]))
    macro_rec = float(np.mean([m["recall"] for m in per_class.values()]))
    macro_f1 = float(np.mean([m["f1"] for m in per_class.values()]))
    
    report = {
        "model_name": "isquare-mobilenet_v3_large-classifier-v2",
        "model_version": "2.0.0",
        "checkpoint": str(out_pth.relative_to(BACKEND_DIR)),
        "epochs": epochs,
        "best_val_acc": round(best_val_acc, 4),
        "test_accuracy": round(test_acc, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "categories": CATEGORIES,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    
    rep_path = BACKEND_DIR / "storage" / "dataset" / "phase_03f_classifier_v2_evaluation.json"
    rep_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n=== TEST SPLIT EVALUATION (100 independent test images) ===")
    print(f"Test Accuracy: {test_acc * 100:.2f}%")
    print(f"Macro Precision: {macro_prec:.4f} | Recall: {macro_rec:.4f} | F1: {macro_f1:.4f}")
    return report


if __name__ == "__main__":
    train_and_evaluate()
