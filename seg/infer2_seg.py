# infer_seg.py
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import argparse

import cv2
import numpy as np
import torch
import segmentation_models_pytorch as smp

# Normalización igual a la del entrenamiento (Imagenet)
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# Colores BGR para OpenCV
BGR_BLACK = (0, 0, 0)
BGR_RED   = (0, 0, 255)
BGR_GREEN = (0, 255, 0)
BGR_BLUE  = (255, 0, 0)

def _norm_label_to_name(label_to_name):
    """Admite dict con claves str/int o lista; devuelve dict {int:name} con 1..K."""
    if label_to_name is None:
        return None
    if isinstance(label_to_name, list):
        # asume índice 1..K (algunos checkpoints guardan lista)
        return {i+1: n for i, n in enumerate(label_to_name)}
    # dict
    out = {}
    for k, v in label_to_name.items():
        try:
            out[int(k)] = v
        except Exception:
            continue
    return out

def build_palette(num_classes, label_to_name=None):
    """
    Paleta BGR:
      0=fondo negro, cabeza rojo, cuerpo verde, aleta/cola azul.
    Intenta mapear por nombre ('cabeza','cuerpo','cola','aleta','head','body','tail','fin').
    Si no hay nombres, fallback por índice: 1=cuerpo, 2=aleta/cola, 3=cabeza.
    """
    pal = {0: BGR_BLACK}
    label_to_name = _norm_label_to_name(label_to_name)

    def is_head(name):
        n = name.lower()
        return any(t in n for t in ["cabe", "head", "cara", "rostro"])

    def is_body(name):
        n = name.lower()
        return any(t in n for t in ["cuerpo", "body", "tronco"])

    def is_tail_or_fin(name):
        n = name.lower()
        return any(t in n for t in ["cola", "tail", "aleta", "aletas", "fin", "fins"])

    if label_to_name:
        for i in range(1, num_classes + 1):
            name = str(label_to_name.get(i, ""))
            if is_head(name):
                pal[i] = BGR_RED
            elif is_body(name):
                pal[i] = BGR_GREEN
            elif is_tail_or_fin(name):
                pal[i] = BGR_BLUE
            else:
                # Fallback determinista si apareciera otra clase
                pal[i] = (128, 128, 128)
        return pal

    # Fallback por índice (1..K): 1=cuerpo, 2=aleta/cola, 3=cabeza
    mapping = {1: BGR_GREEN, 2: BGR_BLUE, 3: BGR_RED}
    for i in range(1, num_classes + 1):
        pal[i] = mapping.get(i, (128, 128, 128))
    return pal

def colorize_mask(mask_np, palette):
    h, w = mask_np.shape
    out = np.zeros((h, w, 3), dtype=np.uint8)
    # Pintar sólo los IDs presentes para evitar bucles innecesarios
    for k in np.unique(mask_np):
        out[mask_np == k] = palette.get(int(k), BGR_BLACK)
    return out

def load_model_and_meta(ckpt_path, device):
    ckpt = torch.load(ckpt_path, map_location=device)
    cfg  = ckpt.get("config", {})
    label_to_name = _norm_label_to_name(ckpt.get("label_to_name", None))

    num_classes_no_bg = len(label_to_name) if label_to_name is not None else 3
    classes_total = num_classes_no_bg + 1  # + fondo

    encoder_name = cfg.get("ENCODER_NAME", "resnet50")
    image_size   = tuple(cfg.get("IMAGE_SIZE", (256, 256)))

    model = smp.DeepLabV3Plus(
        encoder_name=encoder_name,
        encoder_weights=None,
        in_channels=3,
        classes=classes_total
    )
    model.load_state_dict(ckpt["state_dict"], strict=True)
    model.to(device).eval()
    return model, image_size, label_to_name, classes_total

def preprocess_image(img_rgb, size):
    ih, iw = img_rgb.shape[:2]
    img_resized = cv2.resize(img_rgb, size, interpolation=cv2.INTER_LINEAR)
    img = img_resized.astype(np.float32) / 255.0
    img = (img - MEAN) / STD
    img = img.transpose(2, 0, 1)  # [C,H,W]
    ten = torch.from_numpy(img).unsqueeze(0)
    return ten, (ih, iw)

@torch.no_grad()
def predict_mask(model, image_tensor, orig_hw, device, use_tta=False):
    image_tensor = image_tensor.to(device, non_blocking=True)
    if device.type == "cuda":
        ctx = torch.autocast("cuda", dtype=torch.float16)
    else:
        ctx = torch.autocast("cpu", dtype=torch.bfloat16)

    with ctx:
        logits = model(image_tensor)
        if use_tta:
            logits_f = model(torch.flip(image_tensor, dims=[3]))
            logits_f = torch.flip(logits_f, dims=[3])
            logits = (logits + logits_f) / 2

    pred = torch.argmax(logits, dim=1)[0].detach().cpu().numpy().astype(np.uint8)
    ih, iw = orig_hw
    pred = cv2.resize(pred, (iw, ih), interpolation=cv2.INTER_NEAREST)
    return pred

def is_image_file(p: Path):
    return p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

def run_inference(ckpt_path, input_path, out_dir, device_str="cuda", use_tta=False):
    device = torch.device(device_str if torch.cuda.is_available() and device_str == "cuda" else "cpu")
    assert not (device.type == "cpu" and device_str == "cuda"), "CUDA no disponible. Verificá tu instalación de torch CUDA."

    model, net_size, label_to_name, classes_total = load_model_and_meta(ckpt_path, device)
    palette = build_palette(classes_total - 1, label_to_name)
    os.makedirs(out_dir, exist_ok=True)

    in_path = Path(input_path)
    if in_path.is_dir():
        files = [p for p in in_path.iterdir() if is_image_file(p)]
    elif in_path.is_file():
        assert is_image_file(in_path), f"Archivo no soportado: {in_path}"
        files = [in_path]
    else:
        raise FileNotFoundError(f"No existe: {input_path}")

    print(f"[INFO] Dispositivo: {device} | Imágenes: {len(files)} | NetSize: {net_size}")

    for p in files:
        bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if bgr is None:
            print(f"[WARN] No se pudo leer: {p}")
            continue
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        ten, orig_hw = preprocess_image(rgb, net_size)
        pred = predict_mask(model, ten, orig_hw, device, use_tta=use_tta)

        # 1) Máscara coloreada (fondo negro)
        mask_bgr = colorize_mask(pred, palette)

        # 2) Overlay (opcional)
        overlay = cv2.addWeighted(bgr, 0.6, mask_bgr, 0.4, 0)

        # 3) IDs crudos (uint16) y 4) versión visible en grises
        pred_ids_u16 = pred.astype(np.uint16)  # útil para métricas/post-proceso
        if (classes_total - 1) > 0:
            scale = 255 // (classes_total - 1)
        else:
            scale = 255
        pred_vis = (pred * scale).astype(np.uint8)

        out_mask_color = Path(out_dir) / f"{p.stem}_mask.png"
        out_overlay    = Path(out_dir) / f"{p.stem}_overlay.png"
        out_mask_ids   = Path(out_dir) / f"{p.stem}_mask_ids.png"
        out_mask_vis   = Path(out_dir) / f"{p.stem}_mask_index_vis.png"

        cv2.imwrite(str(out_mask_color), mask_bgr)    # coloreada (fondo negro)
        cv2.imwrite(str(out_overlay), overlay)        # overlay
        cv2.imwrite(str(out_mask_ids), pred_ids_u16)  # IDs reales (0..K) - 16 bits
        cv2.imwrite(str(out_mask_vis), pred_vis)      # sólo para ver en escala de grises

        print(f"[OK] {p.name} -> {out_mask_color.name}, {out_overlay.name}, {out_mask_ids.name}, {out_mask_vis.name}")

    if label_to_name:
        legend_path = Path(out_dir) / "legend.txt"
        with open(legend_path, "w", encoding="utf-8") as f:
            f.write("ID\tNombre\tColor(B,G,R)\n")
            f.write("0\tFondo\t(0,0,0)\n")
            for i in range(1, classes_total):
                f.write(f"{i}\t{label_to_name.get(i, f'class_{i}')}\t{palette[i]}\n")
        print(f"[INFO] Leyenda guardada en {legend_path}")

def main():
    ap = argparse.ArgumentParser(description="Inferencia DeepLabV3+ (SMP) con checkpoint")
    ap.add_argument("--ckpt", required=True, help="Ruta al checkpoint .pth (best_miou.pth)")
    ap.add_argument("--input", required=True, help="Imagen o carpeta de imágenes")
    ap.add_argument("--out", default="preds", help="Carpeta de salida")
    ap.add_argument("--device", default="cuda", choices=["cuda", "cpu"], help="Forzar dispositivo")
    ap.add_argument("--tta", action="store_true", help="Test-time augmentation (flip horizontal)")
    args = ap.parse_args()
    run_inference(args.ckpt, args.input, args.out, device_str=args.device, use_tta=args.tta)

if __name__ == "__main__":
    main()
