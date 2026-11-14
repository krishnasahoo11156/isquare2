"""
Train the custom iSquare image classification head using transfer learning over
the MobileNetV3-Large feature backbone from the local SSDLite weights.

Taxonomy (10 concrete categories + Uncertain):
  0: Human photograph
  1: Document
  2: Screenshot
  3: Logo or graphic
  4: Object or product
  5: Landscape or outdoor scene
  6: Animal photograph
  7: Illustration or artwork
  8: Mixed-content image
  9: Other
"""
import json
import time
from pathlib import Path
from PIL import Image

import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models.detection import ssdlite320_mobilenet_v3_large

BACKEND_DIR = Path(__file__).resolve().parent.parent
STORAGE_MODELS = BACKEND_DIR / "storage" / "models"
DATASET_DIR = BACKEND_DIR / "storage" / "dataset"

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


class ISquareClassificationHead(nn.Module):
    def __init__(self, in_features: int = 480, num_classes: int = 10):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(in_features, 128),
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


def train():
    torch.manual_seed(42)
    torch.set_num_threads(1)
    
    manifest_path = DATASET_DIR / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Run create_dataset.py first: {manifest_path} not found")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    print("Loading pretrained MobileNetV3-Large backbone...")
    backbone = load_backbone()
    
    print("Extracting features for train, val, test splits...")
    X_train, y_train = extract_features(backbone, "train", manifest)
    X_val, y_val = extract_features(backbone, "val", manifest)
    X_test, y_test = extract_features(backbone, "test", manifest)
    print(f"Extracted features: train={X_train.shape}, val={X_val.shape}, test={X_test.shape}")
    
    head = ISquareClassificationHead(in_features=480, num_classes=len(CATEGORIES))
    optimizer = torch.optim.Adam(head.parameters(), lr=0.005, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()
    
    epochs = 40
    print(f"\nTraining custom classification head for {epochs} epochs...")
    head.train()
    best_val_acc = 0.0
    best_state = None
    
    for epoch in range(1, epochs + 1):
        optimizer.zero_grad()
        logits = head(X_train)
        loss = criterion(logits, y_train)
        loss.backward()
        optimizer.step()
        
        # Validation
        head.eval()
        with torch.no_grad():
            val_logits = head(X_val)
            val_preds = val_logits.argmax(dim=1)
            val_acc = (val_preds == y_val).float().mean().item()
            train_acc = (logits.argmax(dim=1) == y_train).float().mean().item()
        head.train()
        
        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in head.state_dict().items()}
            
        if epoch % 10 == 0 or epoch == epochs:
            print(f"  Epoch {epoch:02d}/{epochs:02d}: loss={loss.item():.4f}, train_acc={train_acc*100:.1f}%, val_acc={val_acc*100:.1f}%")
            
    # Save best head weights
    out_weights = STORAGE_MODELS / "isquare_classifier_head_v1.pth"
    head.load_state_dict(best_state)
    torch.save(best_state, out_weights)
    print(f"\nSaved trained classifier head to: {out_weights} ({out_weights.stat().st_size / 1024:.1f} KB)")
    
    # Evaluate on held-out test split
    head.eval()
    with torch.no_grad():
        test_logits = head(X_test)
        probs = torch.softmax(test_logits, dim=1)
        test_preds = probs.argmax(dim=1)
        test_acc = (test_preds == y_test).float().mean().item()
        
    print(f"\n--- HELD-OUT TEST EVALUATION ---")
    print(f"Overall Test Accuracy: {test_acc * 100:.2f}% ({int(test_acc * len(y_test))}/{len(y_test)} correct)")
    
    # Confusion matrix
    num_classes = len(CATEGORIES)
    cm = [[0] * num_classes for _ in range(num_classes)]
    for true_l, pred_l in zip(y_test.tolist(), test_preds.tolist()):
        cm[true_l][pred_l] += 1
        
    per_class_metrics = {}
    for i, cat in enumerate(CATEGORIES):
        tp = cm[i][i]
        fp = sum(cm[r][i] for r in range(num_classes) if r != i)
        fn = sum(cm[i][c] for c in range(num_classes) if c != i)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        per_class_metrics[cat] = {
            "precision": round(prec, 3),
            "recall": round(rec, 3),
            "f1": round(f1, 3),
            "support": sum(cm[i]),
        }
        print(f"  {cat:<28} | Prec: {prec:.2f} | Rec: {rec:.2f} | F1: {f1:.2f}")
        
    evaluation_record = {
        "model_name": "isquare-mobilenet_v3_large-custom",
        "model_version": "1.0.0",
        "backbone": "torchvision.models.mobilenet_v3_large (features)",
        "head_architecture": "Sequential(Linear(480, 128), Hardswish(), Dropout(0.15), Linear(128, 10))",
        "test_accuracy": round(test_acc, 4),
        "per_class": per_class_metrics,
        "confusion_matrix": cm,
        "categories": CATEGORIES,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
    }
    eval_path = DATASET_DIR / "classifier_evaluation.json"
    eval_path.write_text(json.dumps(evaluation_record, indent=2), encoding="utf-8")
    print(f"Evaluation report written to: {eval_path}")
    return evaluation_record


if __name__ == "__main__":
    train()

