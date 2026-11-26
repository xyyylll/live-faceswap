"""Offline speed check for the live pipeline (no webcam, nothing saved).

Uses Deep-Live-Cam's own CoreML-optimized loaders and a single-face 720p test frame
cropped from InsightFace's bundled sample image. Reports per-stage latency and fps.

    Deep-Live-Cam/venv/bin/python tools/bench_live.py --source faces/source_01.jpg [--det 320] [--gpen256]
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DLC = os.path.join(ROOT, "Deep-Live-Cam")
sys.path.insert(0, DLC)

import cv2  # noqa: E402
import numpy as np  # noqa: E402


def test_frame(fa) -> np.ndarray:
    from insightface.data import get_image

    img = get_image("t1")
    x1, y1, x2, y2 = fa.get(img)[0].bbox.astype(int)
    fw = x2 - x1
    cw, ch = int(fw * 3.0), int(fw * 3.0 * 9 / 16)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2 + int(0.3 * fw)
    pad = max(cw, ch)
    padded = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    crop = padded[cy - ch // 2 + pad: cy + ch // 2 + pad, cx - cw // 2 + pad: cx + cw // 2 + pad]
    return cv2.resize(crop, (1280, 720))


def median_ms(xs) -> float:
    return 1000 * float(np.median(xs))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="source face image")
    ap.add_argument("--det", type=int, default=320, choices=[160, 320, 640])
    ap.add_argument("--gpen256", action="store_true", help="also time the GPEN-256 enhancer")
    ap.add_argument("--n", type=int, default=80)
    args = ap.parse_args()

    import modules.globals as G

    G.execution_providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
    G.det_size = args.det

    from modules.face_analyser import get_face_analyser
    from modules.processors.frame.face_swapper import get_face_swapper, _fast_paste_back

    fa = get_face_analyser()
    swap = get_face_swapper()
    src_img = cv2.imread(os.path.abspath(args.source))
    assert src_img is not None, f"cannot read {args.source}"
    src_faces = fa.get(src_img)
    assert src_faces, "no face in source image"
    src = src_faces[0]

    frame = test_frame(fa)
    tgt = fa.get(frame)[0]
    n_in = swap.input_size[0]
    aimg_dummy = np.empty((n_in, n_in, 3), dtype=np.uint8)

    enh = None
    if args.gpen256:
        from modules.processors.frame import face_enhancer_gpen256 as gpen
        from modules.processors.frame._onnx_enhancer import enhance_face_onnx

        enh = gpen.get_enhancer()

    t_det, t_swap, t_enh = [], [], []
    for i in range(args.n + 8):  # first 8 iterations are warm-up
        f = frame.copy()
        t0 = time.perf_counter()
        fa.get(f)
        t1 = time.perf_counter()
        bgr_fake, M = swap.get(f, tgt, src, paste_back=False)
        f = _fast_paste_back(f, bgr_fake, aimg_dummy, M)
        t2 = time.perf_counter()
        if enh is not None:
            f = enhance_face_onnx(f, tgt, enh, gpen.INPUT_SIZE)
        t3 = time.perf_counter()
        if i >= 8:
            t_det.append(t1 - t0)
            t_swap.append(t2 - t1)
            t_enh.append(t3 - t2)

    det, sw, en = median_ms(t_det), median_ms(t_swap), median_ms(t_enh)
    print(f"det(DET={args.det})={det:.4g}ms  swap+paste={sw:.4g}ms" + (f"  gpen256={en:.4g}ms" if enh else ""))
    print(f"swap only : ~{1000 / sw:.4g} fps (detection amortized; the UI detects every 1-2 frames)")
    if enh is not None:
        print(f"swap+gpen : ~{1000 / (sw + en):.4g} fps (enhancer runs synchronously in the live loop)")


if __name__ == "__main__":
    main()
