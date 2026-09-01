"""Entrena un clasificador REAL vs AI_EDITED con separación por pares.

No activa el checkpoint automáticamente. El artefacto se escribe en
training_data/models/candidate_ai_edited.pt para evaluación posterior.
"""
import argparse
import io
import json
import random
from pathlib import Path

import torch
from PIL import Image, ImageFilter
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0


MINIMUM_PAIRS = 30


class PairDataset(Dataset):
    def __init__(self, root: Path, entries: list[dict], training: bool):
        self.root = root
        self.training = training
        self.samples = [
            (root / entry[path_key], label)
            for entry in entries
            for path_key, label in (("original_path", 0), ("edited_path", 1))
        ]
        self.tensor = transforms.Compose([
            transforms.Resize((288, 288)),
            transforms.RandomCrop(256) if training else transforms.CenterCrop(256),
            transforms.RandomHorizontalFlip() if training else nn.Identity(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, label = self.samples[index]
        image = Image.open(path).convert("RGB")
        if self.training:
            # Simula reescalado, desenfoque y recompresión habituales al compartir.
            scale = random.uniform(0.55, 1.0)
            image = image.resize((max(128, int(image.width * scale)), max(128, int(image.height * scale))))
            if random.random() < 0.35:
                image = image.filter(ImageFilter.GaussianBlur(random.uniform(0.1, 1.2)))
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=random.randint(35, 92), optimize=True)
            buffer.seek(0)
            image = Image.open(buffer).convert("RGB")
        return self.tensor(image), label


def load_entries(root: Path) -> list[dict]:
    manifest = root / "manifest.jsonl"
    if not manifest.exists():
        return []
    return [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("training_data"))
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--allow-small-smoke-test", action="store_true")
    args = parser.parse_args()
    entries = load_entries(args.data_dir)
    reviewed = [item for item in entries if item.get("review_status") == "approved"]
    print(json.dumps({
        "pairs_total": len(entries),
        "pairs_approved": len(reviewed),
        "pairs_minimum": MINIMUM_PAIRS,
        "ready": len(reviewed) >= MINIMUM_PAIRS,
    }, indent=2))
    if args.audit_only:
        return
    if len(reviewed) < MINIMUM_PAIRS and not args.allow_small_smoke_test:
        raise SystemExit(
            f"Se requieren al menos {MINIMUM_PAIRS} pares aprobados; hay {len(reviewed)}. "
            "Use --allow-small-smoke-test solo para verificar el pipeline."
        )
    if len(reviewed) < 2:
        raise SystemExit("Se necesitan al menos dos pares aprobados para separar entrenamiento y validación.")

    random.Random(20260831).shuffle(reviewed)
    validation_count = max(1, round(len(reviewed) * 0.2))
    validation_entries = reviewed[:validation_count]
    training_entries = reviewed[validation_count:]
    train_loader = DataLoader(PairDataset(args.data_dir, training_entries, True), batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(PairDataset(args.data_dir, validation_entries, False), batch_size=args.batch_size)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = efficientnet_b0(weights=EfficientNet_B0_Weights.DEFAULT)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 2)
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.05)
    best_accuracy = 0.0
    output_dir = args.data_dir / "models"
    output_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(args.epochs):
        model.train()
        for images, labels in train_loader:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(images.to(device)), labels.to(device))
            loss.backward()
            optimizer.step()
        model.eval()
        correct = total = 0
        with torch.inference_mode():
            for images, labels in val_loader:
                predictions = model(images.to(device)).argmax(dim=1).cpu()
                correct += int((predictions == labels).sum())
                total += len(labels)
        accuracy = correct / max(1, total)
        print(f"epoch={epoch + 1} validation_accuracy={accuracy:.4f}")
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            torch.save({
                "state_dict": model.state_dict(),
                "classes": {0: "REAL", 1: "AI_EDITED"},
                "validation_accuracy": accuracy,
                "training_pairs": len(training_entries),
                "validation_pairs": len(validation_entries),
            }, output_dir / "candidate_ai_edited.pt")


if __name__ == "__main__":
    main()
