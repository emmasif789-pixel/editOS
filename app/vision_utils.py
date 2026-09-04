import cv2
import numpy as np

def analyze_reference_rhythm(path: str, sample_fps: float = 3.0) -> dict:
    """Real scene-cut detection via frame-difference histogram comparison."""
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = frame_count / fps if fps else 0
    step = max(1, int(round(fps / sample_fps)))

    prev_hist = None
    cuts = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            small = cv2.resize(frame, (64, 36))
            hist = cv2.calcHist([small], [0, 1, 2], None, [8, 8, 8], [0, 256]*3)
            cv2.normalize(hist, hist)
            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                if diff > 0.35:
                    cuts.append(round(idx / fps, 2))
            prev_hist = hist
        idx += 1
    cap.release()

    cuts_per_min = round((len(cuts) / (duration / 60)), 1) if duration > 0 else 0
    avg_shot_len = round(duration / (len(cuts) + 1), 1) if duration > 0 else 0
    return {"duration": duration, "cuts": cuts, "cuts_per_min": cuts_per_min, "avg_shot_len": avg_shot_len}
