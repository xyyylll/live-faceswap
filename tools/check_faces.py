"""QC candidate source faces for single-image face swap, and build a contact sheet.

Run from the repo root with the Deep-Live-Cam venv (has insightface + buffalo_l):
    Deep-Live-Cam/venv/bin/python tools/check_faces.py faces [--sheet sheet.jpg]

Checks per image: exactly one face, face width >= MIN_FACE_PX, |yaw|/|pitch|/|roll| within limits,
detection score. Prints a table and writes a labeled contact sheet.
"""
import argparse
import glob
import os

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image, ImageDraw, ImageFont

MIN_FACE_PX = 256
MAX_YAW = 15.0
MAX_PITCH = 15.0
MAX_ROLL = 10.0
MIN_SCORE = 0.7


def check(fa: FaceAnalysis, path: str) -> dict:
    img = cv2.imread(path)
    faces = fa.get(img)
    r = {"file": os.path.basename(path), "n_faces": len(faces)}
    if len(faces) != 1:
        r.update(ok=False, reason=f"{len(faces)} faces")
        return r
    f = faces[0]
    x1, y1, x2, y2 = f.bbox
    pitch, yaw, roll = (float(v) for v in f.pose)
    r.update(face_px=int(x2 - x1), score=float(f.det_score), yaw=yaw, pitch=pitch, roll=roll)
    reasons = []
    if r["face_px"] < MIN_FACE_PX:
        reasons.append("face too small")
    if abs(yaw) > MAX_YAW:
        reasons.append("yaw")
    if abs(pitch) > MAX_PITCH:
        reasons.append("pitch")
    if abs(roll) > MAX_ROLL:
        reasons.append("roll")
    if r["score"] < MIN_SCORE:
        reasons.append("low det score")
    r.update(ok=not reasons, reason=",".join(reasons) or "-")
    return r


def contact_sheet(rows: list, img_dir: str, out: str, thumb: int = 384, cols: int = 4) -> None:
    n = len(rows)
    nrows = (n + cols - 1) // cols
    label_h = 44
    sheet = Image.new("RGB", (cols * thumb, nrows * (thumb + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except OSError:
        font = ImageFont.load_default()
    for i, r in enumerate(rows):
        im = Image.open(os.path.join(img_dir, r["file"])).convert("RGB").resize((thumb, thumb))
        x, y = (i % cols) * thumb, (i // cols) * (thumb + label_h)
        sheet.paste(im, (x, y))
        tag = "PASS" if r.get("ok") else "FAIL"
        color = (20, 120, 40) if r.get("ok") else (190, 30, 30)
        line1 = f"{r['file'].rsplit('.', 1)[0]}  {tag}"
        line2 = (f"face {r.get('face_px', 0)}px  yaw {r.get('yaw', 0):.1f}  pitch {r.get('pitch', 0):.1f}"
                 if r.get("n_faces") == 1 else r.get("reason", ""))
        draw.text((x + 6, y + thumb + 3), line1, fill=color, font=font)
        draw.text((x + 6, y + thumb + 23), line2, fill=(60, 60, 60), font=font)
    sheet.save(out, quality=90)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("img_dir")
    ap.add_argument("--sheet", default=None)
    args = ap.parse_args()

    fa = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"],
                      allowed_modules=["detection", "landmark_3d_68"])
    fa.prepare(ctx_id=-1, det_size=(640, 640))

    paths = sorted(p for p in glob.glob(os.path.join(args.img_dir, "*"))
                   if p.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))
    rows = [check(fa, p) for p in paths]
    print(f"{'file':<28}{'ok':<6}{'faces':<7}{'face_px':<9}{'yaw':<8}{'pitch':<8}{'roll':<8}reason")
    for r in rows:
        print(f"{r['file']:<28}{str(r['ok']):<6}{r['n_faces']:<7}{r.get('face_px', '-')!s:<9}"
              f"{r.get('yaw', float('nan')):<8.3g}{r.get('pitch', float('nan')):<8.3g}"
              f"{r.get('roll', float('nan')):<8.3g}{r['reason']}")
    print(f"pass {sum(r['ok'] for r in rows)}/{len(rows)}")
    if args.sheet and rows:
        contact_sheet(rows, args.img_dir, args.sheet)
        print("sheet:", args.sheet)


if __name__ == "__main__":
    main()
