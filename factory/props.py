"""Channel 'props' drawn by code (identical in every episode): case file, mugshot, roulette wheel,
casino maze under a magnifier, and the newsreel film look."""
from __future__ import annotations

import math
from collections import deque

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .config import hex_to_rgb, resolve_font
from .shots import MARGIN, Shot, add_grain, cover, ease, mark_strokes
from .text import blend, fit_font, font, text_block
from .i18n import ui


def _pal(cfg):
    return {k: hex_to_rgb(v) for k, v in cfg["style"]["palette"].items()}


def _darker(c, f):
    return tuple(int(x * f) for x in c)


def _push(base: np.ndarray, size, z: float) -> np.ndarray:
    """Centre crop-zoom of a (MARGIN-sized) canvas down to the frame size."""
    W, H = size
    BH, BW = base.shape[:2]
    win_w = BW / z
    s = W / win_w
    M = np.float32([[s, 0, W / 2 - s * BW / 2], [0, s, H / 2 - s * BH / 2]])
    return cv2.warpAffine(base, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def _draw_marker(frame: np.ndarray, strokes, p: float, color, thick: int) -> None:
    total = sum(len(s) for s in strokes)
    budget = int(total * min(1.0, max(0.0, p)))
    for s in strokes:
        if budget <= 1:
            break
        seg = s[: min(len(s), budget)]
        budget -= len(seg)
        cv2.polylines(frame, [seg.astype(np.int32).reshape(-1, 1, 2)], False, color, thick, cv2.LINE_AA)


# ------------------------------------------------------------------ newsreel look

def newsreel(frame: np.ndarray, t: float, seed: int, label: str | None, cfg: dict) -> np.ndarray:
    """1950s newsreel: sepia, flicker, scratches, dust, heavy vignette, small 'reconstruction' label."""
    H, W = frame.shape[:2]
    pal = _pal(cfg)
    k = int(t * 12)  # film flickers at 12 fps
    rnd = np.random.default_rng(seed * 1000 + k)
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    gray = np.clip((gray - 0.5) * 1.25 + 0.5, 0, 1)
    flicker = 0.93 + 0.07 * rnd.random()
    gray *= flicker
    dark = np.array(pal["ink"], np.float32) / 255.0
    light = np.array([0.95, 0.88, 0.72], np.float32)
    out = (dark[None, None, :] * (1 - gray[..., None]) + light[None, None, :] * gray[..., None]) * 255
    out = out.astype(np.uint8)
    for _ in range(rnd.integers(0, 3)):  # vertical scratches
        x = int(rnd.uniform(0.05, 0.95) * W)
        cv2.line(out, (x, 0), (x + int(rnd.uniform(-8, 8)), H), (235, 225, 200), 1 + int(rnd.random() * 2), cv2.LINE_AA)
    for _ in range(rnd.integers(4, 12)):  # dust
        cx, cy = int(rnd.random() * W), int(rnd.random() * H)
        r = int(1 + rnd.random() * 3)
        cv2.circle(out, (cx, cy), r, (25, 20, 15) if rnd.random() < 0.5 else (240, 232, 210), -1, cv2.LINE_AA)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = np.clip(1.15 - 0.55 * rr ** 2.5, 0, 1)[..., None]
    out = (out.astype(np.float32) * vig).astype(np.uint8)
    if label:
        fnt = font(resolve_font(cfg["fonts"]["body"]), max(14, int(H * 0.026)))
        blk = text_block([label.upper()], fnt, fill=pal["paper"], box_fill=pal["ink"] + (210,), pad=int(fnt.size * 0.4))
        blend(out, blk, W - blk.shape[1] - int(W * 0.03), H - blk.shape[0] - int(H * 0.04))
    return out


def projector_sfx_times(start: float, duration: float) -> list[float]:
    return [start + i * 2.9 for i in range(max(1, int(duration // 2.9) + 1))]


# ------------------------------------------------------------------ case file

class CaseFileShot(Shot):
    """mode 'open': manila folder opens on a desk. mode 'closed': folder + a stamp slams down + verdict lines.

    spec: number, title, stamp, lines[], stamp_at (s after narration start)
    """

    def __init__(self, start, duration, spec: dict, cfg: dict, size, lead_in: float = 0.0):
        super().__init__(start, duration)
        self.W, self.H = size
        self.cfg, self.spec = cfg, spec
        self.pal = pal = _pal(cfg)
        self.mode = spec.get("mode", "open")
        self.lead_in = lead_in
        BW, BH = int(self.W * MARGIN), int(self.H * MARGIN)
        self.BW, self.BH = BW, BH
        desk = np.full((BH, BW, 3), _darker(pal["green"], 0.55), np.uint8)
        # simple wood-ish desk stripes
        rnd = np.random.default_rng(4)
        for y in range(0, BH, 6):
            desk[y : y + 3] = np.clip(desk[y : y + 3].astype(int) + int(rnd.integers(-6, 6)), 0, 255)
        self.desk = add_grain(desk, 0.05, 2)
        portrait = self.H > self.W
        # an opening folder becomes a two-page spread, so it starts smaller to fit the frame when open
        fh = int(BH * (0.62 if portrait else (0.62 if self.mode == "open" else 0.74)))
        fw = int(fh / 1.28)
        self.fw, self.fh = fw, fh
        self.fx, self.fy = (BW - fw) // 2, (BH - fh) // 2 + int(fh * 0.03)
        manila = (222, 186, 120)
        self.manila = manila
        head = resolve_font(cfg["fonts"]["headline"])
        typew = resolve_font(cfg["fonts"]["serif"])
        marker = resolve_font(cfg["fonts"]["marker"])
        # cover
        cover_img = Image.new("RGBA", (fw, fh), manila + (255,))
        d = ImageDraw.Draw(cover_img)
        d.rectangle((0, 0, fw - 1, fh - 1), outline=_darker(manila, 0.7) + (255,), width=4)
        lab_w, lab_h = int(fw * 0.7), int(fh * 0.2)
        lx, ly = (fw - lab_w) // 2, int(fh * 0.12)
        d.rectangle((lx, ly, lx + lab_w, ly + lab_h), fill=(250, 246, 236, 255), outline=pal["ink"] + (255,), width=3)
        f1 = font(typew, int(lab_h * 0.2))
        d.text((lx + lab_w / 2, ly + lab_h * 0.28), f"{ui('CASE FILE #')}{spec.get('number', '001')}", font=f1, fill=pal["ink"], anchor="mm")
        f2, l2 = fit_font(str(spec.get("title", "")).upper(), head, int(lab_w * 0.9), int(lab_h * 0.5), start=int(lab_h * 0.42))
        d.text((lx + lab_w / 2, ly + lab_h * 0.68), " ".join(l2), font=f2, fill=pal["ink"], anchor="mm")
        d.text((int(fw * 0.08), int(fh * 0.9)), ui("CONFIDENTIAL"), font=font(typew, int(fh * 0.03)), fill=_darker(manila, 0.55), anchor="lm")
        self.cover = cover_img
        # inside page
        page = Image.new("RGBA", (fw, fh), (250, 246, 236, 255))
        d = ImageDraw.Draw(page)
        fs = int(fh * 0.05)
        ft = font(typew, fs)
        y = int(fh * 0.1)
        lines = spec.get("inside") or [f"CASE: {spec.get('title', '')}", "SUSPECTS: see attached", "STATUS: under investigation"]
        self.inside_lines = []
        from .text import wrap as _wrap
        for ln in lines:  # long lines wrap inside the page instead of running off its edge
            for k, part in enumerate(_wrap(str(ln), ft, int(fw * 0.8)) or [""]):
                self.inside_lines.append((int(fw * (0.1 if k == 0 else 0.14)), y, part))
                y += int(fs * 1.35)
            y += int(fs * 0.55)
        self.page = page
        self.ft = ft
        self.writes = []
        if spec.get("writes"):
            from .endscreen import Writing
            wf = font(marker, int(fs * 1.05))
            from .draw import stamp_window
            busy = stamp_window(float(spec["open_stamp_at"]) + lead_in)[1] if spec.get("open_stamp_at") is not None else -1e9
            for w_ in sorted(spec["writes"], key=lambda w: float(w.get("at", 2.5))):
                lx, ly, txt = self.inside_lines[int(w_["line"])]
                gap = int(fs * 0.5) if txt.strip() else 0
                col = pal.get(w_.get("color", "ink"), pal["ink"])
                dur = float(w_.get("dur", max(0.6, 0.075 * len(str(w_["text"])))))
                w0 = max(float(w_.get("at", 2.5)) + lead_in, busy + 0.2 + 0.28)  # one hand at a time, line by line
                wx_ = lx + int(ft.getlength(txt)) + gap
                wfo = wf
                while wfo.size > int(fs * 0.6) and wfo.getlength(str(w_["text"])) > fw * 0.95 - wx_:
                    wfo = font(marker, wfo.size - 2)  # a longer (translated) note shrinks to stay on the page
                self.writes.append((Writing(str(w_["text"]), wfo, col), wx_, ly - int(fs * 0.12) + (wf.size - wfo.size) // 2,
                                    w0, dur, w_.get("color", "ink")))
                busy = w0 + dur + 0.32
        # stamp
        self.stamp = None
        if spec.get("stamp"):
            sf, sl = fit_font(str(spec["stamp"]).upper(), head, int(fw * 0.8), int(fh * 0.2), start=int(fh * 0.12))
            red = pal["red"] if self.mode == "closed" else pal["green"]
            blk = text_block(sl, sf, fill=red, pad=int(sf.size * 0.25))
            img = Image.fromarray(blk)
            frame = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(frame).rectangle((2, 2, img.width - 3, img.height - 3), outline=red + (255,), width=max(6, sf.size // 10))
            frame.alpha_composite(img)
            # worn ink: punch random holes
            arr = np.array(frame)
            holes = np.random.default_rng(9).random(arr.shape[:2]) < 0.07
            arr[..., 3] = np.where(holes, (arr[..., 3] * 0.35).astype(np.uint8), arr[..., 3])
            self.stamp = np.array(Image.fromarray(arr).rotate(-12, resample=Image.BICUBIC, expand=True))
        self.verdict = None
        if spec.get("lines"):
            vf = font(marker, int(fh * 0.055))
            self.verdict = [text_block([str(l)], vf, fill=pal["red"], stroke=3, stroke_fill=(250, 246, 236)) for l in spec["lines"]]
        self.stamp_at = float(spec.get("stamp_at", 0.6)) + lead_in
        self._cache = {}

    def _inner(self) -> Image.Image:
        """Inside of the cover; with "clip_image" (e.g. the case's hero ticket) that picture is paper-clipped to it, so the
        left page of the open file is never an empty rectangle (Klot r84 item 25)."""
        if getattr(self, "_inner_img", None) is not None:
            return self._inner_img
        fw, fh = self.fw, self.fh
        inner = Image.new("RGBA", (fw, fh), _darker(self.manila, 0.96) + (255,))
        d = ImageDraw.Draw(inner)
        d.rectangle((0, 0, fw - 1, fh - 1), outline=_darker(self.manila, 0.75) + (255,), width=4)
        ci = self.spec.get("_clip_img")
        if ci:
            try:
                ph = Image.open(ci).convert("RGB")
                box = self.spec.get("clip_box")  # crop of the picture (fractions), e.g. just the ticket
                if box:
                    W0, H0 = ph.size
                    ph = ph.crop((int(box[0] * W0), int(box[1] * H0), int(box[2] * W0), int(box[3] * H0)))
                tw = int(fw * 0.84)
                th = int(ph.height * tw / ph.width)
                ph = ph.resize((tw, th), Image.LANCZOS).convert("RGBA")
                ph = ph.rotate(-3, resample=Image.BICUBIC, expand=True)
                x, y = (fw - ph.width) // 2, int(fh * 0.30) - ph.height // 2 + int(fh * 0.08)
                sh = Image.new("RGBA", ph.size, (0, 0, 0, 0))
                sh.putalpha(Image.fromarray((np.array(ph)[..., 3] * 0.35).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5)))
                inner.alpha_composite(sh, (x + 6, y + 8))
                inner.alpha_composite(ph, (x, y))
                cx_, cy_ = x + int(ph.width * 0.22), y + 6  # a steel paper clip over the top edge
                for k, (w_, h_) in enumerate(((22, 70), (14, 52))):
                    d2 = ImageDraw.Draw(inner)
                    d2.rounded_rectangle((cx_ - w_ // 2, cy_ - h_ // 2, cx_ + w_ // 2, cy_ + h_ // 2), radius=w_ // 2,
                                         outline=(120, 120, 124, 255), width=5)
            except Exception:  # noqa: BLE001 - a missing picture leaves the plain cover
                pass
        self._inner_img = inner
        return inner

    def _scene(self, open_p: float, type_chars: int) -> np.ndarray:
        """The cover swings open on its spine like a real folder (perspective flip), revealing the typed page;
        the whole folder glides so the open spread ends up centred."""
        key = (round(open_p, 3), type_chars)
        if key in self._cache:
            return self._cache[key]
        base = Image.fromarray(self.desk.copy()).convert("RGBA")
        fw, fh, fy = self.fw, self.fh, self.fy
        spine = self.fx + int((self.BW // 2 - self.fx) * open_p) if self.mode == "open" else self.fx
        # shadow under the folder (and under the opened cover)
        shadow = Image.new("RGBA", (fw + 40, fh + 40), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rectangle((20, 20, fw + 20, fh + 20), fill=(0, 0, 0, 110))
        shadow = shadow.filter(ImageFilter.GaussianBlur(16))
        base.alpha_composite(shadow, (spine - 4, fy + 10))
        # back of folder + tab
        back = Image.new("RGBA", (fw, fh), _darker(self.manila, 0.9) + (255,))
        ImageDraw.Draw(back).rectangle((int(fw * 0.62), 0, int(fw * 0.95), int(fh * 0.05)), fill=_darker(self.manila, 0.9) + (255,))
        base.alpha_composite(back, (spine, fy - int(fh * 0.04)))
        if open_p > 0:
            page = self.page.copy()
            d = ImageDraw.Draw(page)
            remaining = type_chars
            for x, y, txt in self.inside_lines:
                if remaining <= 0:
                    break
                d.text((x, y), txt[:remaining], font=self.ft, fill=self.pal["ink"])
                remaining -= len(txt)
            base.alpha_composite(page, (spine, fy))
        out = np.array(base.convert("RGB"))
        if True:  # cover: closed, mid-swing, or lying open on the left
            theta = math.pi * open_p
            c, sn = math.cos(theta), math.sin(theta)
            w = fw * abs(c)
            if w >= 2:
                if c > 0:  # front of the cover, still over the page
                    tex = np.array(self.cover)
                    shade = 1 - 0.3 * sn
                else:  # inside of the cover, now lying to the left of the spine
                    tex = np.array(self._inner())
                    shade = 1 - 0.25 * sn
                tex = tex.copy()
                tex[..., :3] = (tex[..., :3] * shade).astype(np.uint8)
                lift = fh * 0.08 * sn  # the free edge comes towards the camera
                fx_edge = spine + (w if c > 0 else -w)
                if c > 0:
                    src = np.float32([[0, 0], [fw, 0], [fw, fh], [0, fh]])
                    dst = np.float32([[spine, fy], [fx_edge, fy - lift], [fx_edge, fy + fh + lift], [spine, fy + fh]])
                else:
                    src = np.float32([[fw, 0], [0, 0], [0, fh], [fw, fh]])
                    dst = np.float32([[spine, fy], [fx_edge, fy - lift], [fx_edge, fy + fh + lift], [spine, fy + fh]])
                M = cv2.getPerspectiveTransform(src, dst)
                warped = cv2.warpPerspective(tex, M, (out.shape[1], out.shape[0]), flags=cv2.INTER_LINEAR,
                                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
                blend(out, warped, 0, 0)
        if len(self._cache) > 64:
            self._cache.clear()
        self._cache[key] = out
        return out

    def frame(self, t: float) -> np.ndarray:
        if self.mode == "open":
            op = ease((t - self.lead_in - 0.8) / 1.1)
            total_chars = sum(len(x[2]) for x in self.inside_lines)
            chars = int(total_chars * min(1.0, max(0.0, (t - self.lead_in - 1.7) / 1.6)))
            if self.spec.get("typed") is False:  # pre-written file: the page is already filled in when it opens
                chars = total_chars if op > 0.2 else 0
        else:
            op, chars = 0.0, 0
        canvas = self._scene(op, chars).copy()
        osa = self.spec.get("open_stamp_at")
        if self.mode == "open" and osa is not None and self.inside_lines:  # the hand stamps "OPEN" next to STATUS
            osa = float(osa) + self.lead_in
            if not hasattr(self, "_ostamp"):
                from .endscreen import _stamp
                self._ostamp = _stamp(self.spec.get("open_stamp", ui("Open")), self.cfg, int(self.fw * 0.42), self.pal["red"], -9, 3)
            lx, ly, txt = self.inside_lines[-1]
            sx = int(self.BW // 2 + lx + self.ft.getlength(txt) + self.fw * 0.26)
            sy = int(self.fy + ly + self.ft.size * 0.5)
            from .draw import stamp_press
            stamp_press(canvas, self._ostamp, sx, sy, t, osa, plate=(self.BW // 2, self.fy, self.BW // 2 + self.fw, self.fy + self.fh))
        if self.mode == "open" and self.writes and op >= 0.999:
            from .draw import hand_path, paste_hand
            px0 = self.BW // 2
            for wr, wx, wy, w0, wd, wc in self.writes:
                q = (t - w0) / wd
                if q <= 0:
                    continue
                X, Y = px0 + wx, self.fy + wy
                blend(canvas, wr.at(min(1.0, q)), X, Y)
                if q < 1.25:
                    tip = hand_path(lambda qq, wr=wr, X=X, Y=Y, w0=w0, wd=wd: (X + wr.tip((qq - w0) / wd)[0], Y + wr.tip((qq - w0) / wd)[1]),
                                    w0, w0 + wd, t, canvas.shape[1], canvas.shape[0], False, from_below=True)
                    if tip:
                        paste_hand(canvas, "marker_under" if wc == "red" else "ink_under", tip[0], tip[1], False)
        if self.mode == "closed" and self.stamp is not None and t >= self.stamp_at:
            age = t - self.stamp_at
            p = min(1.0, age / 0.14)
            scale = 2.6 - 1.6 * p
            st = cv2.resize(self.stamp, (max(1, int(self.stamp.shape[1] * scale)), max(1, int(self.stamp.shape[0] * scale))))
            cx, cy = self.fx + self.fw // 2, self.fy + int(self.fh * 0.5)
            blend(canvas, st, cx - st.shape[1] // 2, cy - st.shape[0] // 2, opacity=min(1.0, 0.3 + p))
            if self.verdict:
                y = cy + self.stamp.shape[0] // 2 + int(self.fh * 0.03)
                for i, v in enumerate(self.verdict):
                    op2 = min(1.0, max(0.0, (age - 0.6 - i * 0.7) / 0.25))
                    if op2 > 0:
                        blend(canvas, v, cx - v.shape[1] // 2, y, opacity=op2)
                    y += v.shape[0] + int(self.fh * 0.01)
        z = 1.0 + 0.1 * ease(t / max(self.duration, 1e-6))
        if self.mode == "closed" and t >= self.stamp_at and t - self.stamp_at < 0.25:  # impact shake
            z += 0.015 * math.sin((t - self.stamp_at) * 90)
        return _push(canvas, (self.W, self.H), z)

    def sfx(self, start_abs: float) -> list[tuple[float, str]]:
        if self.mode == "open":
            out = [(start_abs + self.lead_in + 0.95, "whoosh")]
            if self.spec.get("typed") is not False:
                out.append((start_abs + self.lead_in + 1.7, "type"))
            if self.spec.get("open_stamp_at") is not None:
                osa = start_abs + self.lead_in + float(self.spec["open_stamp_at"])
                out += [(osa, "kachunk")]
            for w_ in self.writes:
                out.append((start_abs + w_[3], f"scribble:{w_[4]:.3f}"))
            return out
        return [(start_abs + self.stamp_at, "thud"), (start_abs + self.stamp_at + 0.01, "hit")]


# ------------------------------------------------------------------ mugshot

class MugshotShot(Shot):
    """Police mugshot for a 'suspect' (any object or idea): height chart, booking photo, index card.

    spec: number, name, alias, last_seen, notes(optional)
    """

    def __init__(self, start, duration, image: Image.Image, spec: dict, cfg: dict, size, lead_in: float = 0.0, seed: int = 0):
        super().__init__(start, duration)
        self.W, self.H = size
        self.spec, self.cfg, self.lead_in = spec, cfg, lead_in
        pal = self.pal = _pal(cfg)
        BW, BH = int(self.W * MARGIN), int(self.H * MARGIN)
        portrait = self.H > self.W
        wall = Image.new("RGB", (BW, BH), (214, 210, 196))
        d = ImageDraw.Draw(wall)
        body = resolve_font(cfg["fonts"]["body"])
        head = resolve_font(cfg["fonts"]["headline"])
        typew = resolve_font(cfg["fonts"]["serif"])
        marker = resolve_font(cfg["fonts"]["marker"])
        step = BH / 14
        nf = font(body, int(step * 0.32))
        for i in range(15):  # height chart
            y = int(BH - i * step)
            d.line((0, y, BW, y), fill=_darker((214, 210, 196), 0.7), width=3 if i % 2 == 0 else 1)
            if i % 2 == 0:
                d.text((int(BW * 0.02), y - 4), f"{3 + i // 2}'0\"", font=nf, fill=pal["ink"], anchor="lb")
        # photo
        ph = int(BH * (0.24 if portrait else 0.5))  # Shorts: photo + card stay above the caption line
        pw = int(ph * 0.8)
        px = int(BW * (0.5 if portrait else 0.31)) - pw // 2
        py = int(BH * (0.12 if portrait else 0.17))
        photo = Image.fromarray(cover(image, pw, ph))
        border = max(8, pw // 40)
        framed = Image.new("RGB", (pw + 2 * border, ph + 2 * border), (250, 246, 236))
        framed.paste(photo, (border, border))
        wall.paste(framed, (px - border, py - border))
        self.photo_box = (px, py, pw, ph)
        self.photo_marks = [dict(m) for m in (spec.get("photo_marks") or [])]
        # booking plate under the photo
        plate_w, plate_h = pw, int(ph * 0.16)
        pyp = py + ph + border * 2
        d.rectangle((px, pyp, px + plate_w, pyp + plate_h), fill=pal["ink"])
        pf, pl = fit_font(f"{ui('SUSPECT No.')} {spec.get('number', 1)}", head, int(plate_w * 0.9), int(plate_h * 0.8), start=int(plate_h * 0.7))
        d.text((px + plate_w / 2, pyp + plate_h / 2), " ".join(pl), font=pf, fill=pal["paper"], anchor="mm")
        self.base = add_grain(np.array(wall), 0.035, seed)
        # index card (typed lines appear one by one)
        cw = int(BW * (0.78 if portrait else 0.38))
        cx = int(BW * (0.5 if portrait else 0.73)) - cw // 2
        cy = int(BH * (0.43 if portrait else 0.2))
        # Klot r89: "ALIASES" when more than one alias is listed (narration: "Aliases")
        al_key = "ALIASES" if any(sep in str(spec.get("alias", "")) for sep in ("·", ",", " / ")) else "ALIAS"
        rows = [(ui(k), v) for k, v in (("NAME", spec.get("name", "")), (al_key, spec.get("alias", "")),
                                        ("LAST SEEN", spec.get("last_seen", ""))) if str(v).strip()]
        if spec.get("notes"):
            rows.append((ui("NOTES"), spec["notes"]))
        lf = font(typew, int(BH * (0.017 if portrait else 0.03)))
        vf_path = head
        self.text_dx = int(cw * 0.06) + max(26, int(BW * 0.018))  # rule 30: typed text starts right of the red margin line
        self.rows = []
        y = 0
        row_imgs = []
        self.row_type = []
        for label, value in rows:
            lab = text_block([label + ":"], lf, fill=pal["red"], align="left")
            vfnt, vlines = fit_font(str(value).upper(), vf_path, int(cw - self.text_dx - cw * 0.06), int(BH * (0.09 if portrait else 0.16)), start=int(BH * (0.032 if portrait else 0.055)))
            val = text_block(vlines, vfnt, fill=pal["ink"], align="left")
            row_imgs.append((lab, val))
            self.row_type.append((vfnt, vlines))
            y += lab.shape[0] + val.shape[0] + int(BH * 0.015)
        self._typed = {}
        card_h = y + int(BH * (0.03 if portrait else 0.06))
        card = Image.new("RGBA", (cw, card_h), (250, 246, 236, 255))
        cd = ImageDraw.Draw(card)
        for ly in range(int(BH * 0.05), card_h, int(BH * 0.045)):
            cd.line((0, ly, cw, ly), fill=(170, 200, 220, 255), width=1)
        cd.line((int(cw * 0.06), 0, int(cw * 0.06), card_h), fill=pal["red"] + (160,), width=2)
        self.card = np.array(card.rotate(1.5, resample=Image.BICUBIC, expand=True))
        self.card_xy = (cx, cy)
        self.row_imgs = row_imgs
        self.BW, self.BH = BW, BH
        # marker word 'GUILTY?' scribble near the photo
        from .endscreen import _stamp
        # rule 29: the SUSPECT stamp lands across the middle of the booking photo, about -10 deg, ~70 % of its width
        self.tag = _stamp(spec.get("tag", "WANTED"), cfg, int(pw * float(spec.get("stamp_w", 0.70))), pal["red"],
                          float(spec.get("stamp_angle", -10)), seed + 5)  # a rubber stamp, dropped in (angle: + = rising, - = falling)
        sp = spec.get("stamp_pos") or (0.5, 0.5)  # (fx, fy) in photo fractions: where the SUSPECT stamp lands
        self.tag_xy = (px + int(pw * sp[0]), py + int(ph * sp[1]))
        # typing: each field types in letter by letter, in sync with the narration of that field
        n = len(row_imgs)
        ta = list(spec.get("_type_at") or [lead_in + 0.35 + i * 0.9 for i in range(n)])
        while len(ta) < n:
            ta.append(ta[-1] + 0.9 if ta else lead_in + 0.35)
        self.type_at, self.type_dur = [], []
        for i in range(n):
            chars = sum(len(l) for l in self.row_type[i][1])
            nxt = ta[i + 1] - 0.15 if i + 1 < n else self.duration - 0.6
            self.type_at.append(ta[i])
            self.type_dur.append(max(0.3, min(0.065 * chars, nxt - ta[i])))
        from .draw import STAMP_IN
        pm_end = max((float(m.get("at", 0)) + float(m.get("dur", 0.45)) + 0.32 for m in self.photo_marks if m.get("hand")), default=-1e9)
        self.tag_at = float(spec.get("_tag_at", max(max((a + d for a, d in zip(self.type_at, self.type_dur)), default=lead_in) + 0.25,
                                                     pm_end + 0.2 + STAMP_IN)))
        self._static = None

    def frame(self, t: float) -> np.ndarray:
        canvas = self.base.copy()
        tl = t - self.lead_in
        cx, cy = self.card_xy
        blend(canvas, self.card, cx, cy, opacity=min(1.0, max(0.0, tl / 0.25)))
        y = cy + int(self.BH * 0.03)
        for i, (lab, val) in enumerate(self.row_imgs):
            ta, td = self.type_at[i], self.type_dur[i]
            if t >= ta:
                blend(canvas, lab, cx + self.text_dx, y)
                vfnt, vlines = self.row_type[i]
                total = sum(len(l) for l in vlines)
                nch = total if t >= ta + td else int(total * (t - ta) / td)
                if nch >= total:
                    img = val
                else:
                    img = self._typed.get((i, nch))
                    if img is None:
                        left, cut = nch, []
                        for l in vlines:
                            cut.append(l[:max(0, left)])
                            left -= len(l)
                        full = Image.fromarray(val)
                        part = Image.new("RGBA", full.size, (0, 0, 0, 0))
                        blk = text_block([c if c else " " for c in cut], vfnt, fill=self.pal["ink"], align="left")
                        part.alpha_composite(Image.fromarray(blk).crop((0, 0, min(blk.shape[1], full.width), min(blk.shape[0], full.height))))
                        img = np.array(part)
                        self._typed[(i, nch)] = img
                if nch > 0:
                    blend(canvas, img, cx + self.text_dx, y + lab.shape[0])
            y += lab.shape[0] + val.shape[0] + int(self.BH * 0.015)
        if self.photo_marks:  # the hand writes / strikes on the booking photo (marks in photo fractions)
            from .shots import draw_marks
            from .draw import mark_pen, hand_path, paste_hand
            px, py, pw, ph = self.photo_box
            reg = np.ascontiguousarray(canvas[py:py + ph, px:px + pw])
            canvas[py:py + ph, px:px + pw] = draw_marks(reg, self.photo_marks, t, tuple(int(c) for c in self.pal["red"]), self.cfg)
            pen = mark_pen(self.photo_marks, t, pw, ph)
            if pen:
                ftip, t0, t1, kind = pen
                pos = hand_path(lambda tt: (px + ftip(tt)[0], py + ftip(tt)[1]), t0, t1, t, self.BW, self.BH, False)
                if pos:
                    paste_hand(canvas, kind, pos[0], pos[1], False)
        from .draw import stamp_press  # SUSPECT is pressed on by the stamp hand
        px, py, pw, ph = self.photo_box
        stamp_press(canvas, self.tag, self.tag_xy[0], self.tag_xy[1], t, self.tag_at, plate=(px, py, px + pw, py + ph))
        out = _push(canvas, (self.W, self.H), 1.02 + 0.08 * ease(t / max(self.duration, 1e-6)))
        if 0 <= tl < 0.18:  # camera flash
            a = 1 - tl / 0.18
            out = (out.astype(np.float32) * (1 - a) + 255 * a).astype(np.uint8)
        return out

    def sfx(self, start_abs: float) -> list[tuple[float, str]]:
        ev = [(start_abs + self.lead_in, "shutter")]
        for ta, td in zip(self.type_at, self.type_dur):
            k = 0.0
            while k < td:  # typewriter clicks while the field types
                ev.append((start_abs + ta + k, "type"))
                k += 0.42
        ev += [(start_abs + self.tag_at, "kachunk")]
        return ev


# ------------------------------------------------------------------ roulette wheel

AMERICAN_WHEEL = ["0", "28", "9", "26", "30", "11", "7", "20", "32", "17", "5", "22", "34", "15", "3", "24", "36", "13", "1",
                  "00", "27", "10", "25", "29", "12", "8", "19", "31", "18", "6", "21", "33", "16", "4", "23", "35", "14", "2"]
REDS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


class RouletteShot(Shot):
    """American roulette wheel spins, stops with 0 at the top and 00 at the bottom, red marker circles both greens.

    spec: spin (s), mark_at (s after narration start), note
    """

    def __init__(self, start, duration, spec: dict, cfg: dict, size, lead_in: float = 0.0):
        super().__init__(start, duration)
        self.W, self.H = size
        self.cfg, self.spec, self.lead_in = cfg, spec, lead_in
        pal = self.pal = _pal(cfg)
        D = int(min(self.W, self.H) * (0.8 if self.H > self.W else 0.7))
        self.D = D
        img = Image.new("RGBA", (D, D), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        c = D / 2
        n = len(AMERICAN_WHEEL)
        r_out, r_in = D * 0.49, D * 0.34
        d.ellipse((c - r_out - 6, c - r_out - 6, c + r_out + 6, c + r_out + 6), fill=(120, 72, 38, 255))
        num_font = font(resolve_font(cfg["fonts"]["headline"]), int(D * 0.032))
        self.pocket_angles = {}
        for i, num in enumerate(AMERICAN_WHEEL):
            a0 = -90 - 360 / n / 2 + i * 360 / n
            a1 = a0 + 360 / n
            if num in ("0", "00"):
                col = pal["green"]
            elif int(num) in REDS:
                col = pal["red"]
            else:
                col = pal["ink"]
            d.pieslice((c - r_out, c - r_out, c + r_out, c + r_out), a0, a1, fill=col + (255,), outline=(220, 190, 120, 255), width=2)
            self.pocket_angles[num] = math.radians((a0 + a1) / 2)
        d.ellipse((c - r_in, c - r_in, c + r_in, c + r_in), fill=(150, 92, 48, 255), outline=(220, 190, 120, 255), width=4)
        for k in range(8):  # turret spokes
            a = k * math.pi / 4
            d.line((c, c, c + r_in * 0.85 * math.cos(a), c + r_in * 0.85 * math.sin(a)), fill=(220, 190, 120, 255), width=max(4, D // 120))
        d.ellipse((c - D * 0.05, c - D * 0.05, c + D * 0.05, c + D * 0.05), fill=(220, 190, 120, 255))
        for i, num in enumerate(AMERICAN_WHEEL):  # numbers, rotated to face outwards
            ang = self.pocket_angles[num]
            tb = text_block([num], num_font, fill=(250, 246, 236))
            rot = Image.fromarray(tb).rotate(-math.degrees(ang) - 90, resample=Image.BICUBIC, expand=True)
            rr = (r_out + r_in * 1.25) / 2.25 + D * 0.05
            x = c + rr * math.cos(ang) - rot.width / 2
            y = c + rr * math.sin(ang) - rot.height / 2
            img.alpha_composite(rot, (int(x), int(y)))
        self.wheel = np.array(img)
        self.r_mid = (r_out + r_in) / 2 + D * 0.03
        bg = np.full((self.H, self.W, 3), pal["paper"], np.uint8)
        self.bg = add_grain(bg, float(cfg["style"].get("grain", 0.03)), 31)
        self.spin = float(spec.get("spin", 2.6))
        self.turns = float(spec.get("turns", 2.5))
        self.mark_at = float(spec.get("mark_at", 3.0)) + lead_in
        self.red = tuple(int(x) for x in pal["red"])
        self.note = None
        if spec.get("note"):
            mf = font(resolve_font(cfg["fonts"]["marker"]), int(self.H * 0.042))
            self.note = text_block([spec["note"]], mf, fill=pal["red"], stroke=3, stroke_fill=pal["paper"])
        self.strokes = None

    def _angle(self, t: float) -> float:
        if self.spin <= 0:
            return 0.0
        p = min(1.0, max(0.0, t / self.spin))
        eased = 1 - (1 - p) ** 3
        return self.turns * 360 * (1 - eased)  # ends at 0 deg -> '0' on top

    def frame(self, t: float) -> np.ndarray:
        out = self.bg.copy()
        ang = self._angle(t)
        M = cv2.getRotationMatrix2D((self.D / 2, self.D / 2), ang, 1.0)
        wheel = cv2.warpAffine(self.wheel, M, (self.D, self.D), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
        x0, y0 = (self.W - self.D) // 2, int(self.H * 0.44) - self.D // 2
        blend(out, wheel, x0, y0)
        if t >= self.mark_at:
            if self.strokes is None:
                self.strokes = []
                for k, num in enumerate(("0", "00")):
                    a = self.pocket_angles[num]
                    px = x0 + self.D / 2 + self.r_mid * math.cos(a)
                    py = y0 + self.D / 2 + self.r_mid * math.sin(a)
                    self.strokes.append(mark_strokes({"type": "circle", "x": px / self.W, "y": py / self.H,
                                                      "w": self.D * 0.16 / self.W, "h": self.D * 0.2 / self.H}, self.W, self.H, seed=40 + k))
            for k, st in enumerate(self.strokes):
                _draw_marker(out, st, (t - self.mark_at - k * 0.5) / 0.45, self.red, max(5, self.H // 140))
            if self.note is not None and t >= self.mark_at + 1.1:
                op = min(1.0, (t - self.mark_at - 1.1) / 0.25)
                note = self.note
                if self.W > self.H:  # to the right of the wheel, vertically centred on it, shrunk to fit
                    room = self.W - (x0 + self.D) - int(self.W * 0.05)
                    if note.shape[1] > room > 0:
                        k = room / note.shape[1]
                        note = cv2.resize(note, (room, max(1, int(note.shape[0] * k))), interpolation=cv2.INTER_AREA)
                    nx = x0 + self.D + int(self.W * 0.025)
                    ny = y0 + self.D // 2 - note.shape[0] // 2
                else:
                    nx, ny = (self.W - self.note.shape[1]) // 2, max(int(self.H * 0.05), y0 - self.note.shape[0] - int(self.H * 0.02))
                blend(out, note, nx, ny, opacity=op)
        return out

    def sfx(self, start_abs: float) -> list[tuple[float, str]]:
        ev = [(start_abs + 0.05, "whirr")] if self.spin > 0 else []
        if self.mark_at < self.duration and self.mark_at > 0:
            ev += [(start_abs + self.mark_at, "scribble"), (start_abs + self.mark_at + 0.5, "scribble")]
        return ev


# ------------------------------------------------------------------ casino maze

class MazeShot(Shot):
    """Blueprint of a maze-like casino floor; a red marker traces the long way from YOU to the EXIT,
    a magnifier follows the pen. Little gold squares are slot-machine nooks in the dead ends.

    spec: note, seed
    """

    def __init__(self, start, duration, spec: dict, cfg: dict, size, lead_in: float = 0.0):
        super().__init__(start, duration)
        self.W, self.H = size
        self.cfg, self.spec, self.lead_in = cfg, spec, lead_in
        pal = self.pal = _pal(cfg)
        portrait = self.H > self.W
        cols, rows = (9, 15) if portrait else (17, 9)
        rnd = np.random.default_rng(int(spec.get("seed", 7)))
        # maze via randomized DFS
        walls_v = np.ones((rows, cols + 1), bool)  # vertical walls
        walls_h = np.ones((rows + 1, cols), bool)  # horizontal walls
        seen = np.zeros((rows, cols), bool)
        stack = [(rows // 2, cols // 2)]
        seen[rows // 2, cols // 2] = True
        while stack:
            r, c = stack[-1]
            nbrs = [(r + dr, c + dc, dr, dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= r + dr < rows and 0 <= c + dc < cols and not seen[r + dr, c + dc]]
            if not nbrs:
                stack.pop()
                continue
            nr, nc, dr, dc = nbrs[rnd.integers(len(nbrs))]
            if dr == 1:
                walls_h[r + 1, c] = False
            elif dr == -1:
                walls_h[r, c] = False
            elif dc == 1:
                walls_v[r, c + 1] = False
            else:
                walls_v[r, c] = False
            seen[nr, nc] = True
            stack.append((nr, nc))
        start_cell = (rows // 2, cols // 2)
        exit_cell = (rows - 1, 0) if not portrait else (rows - 1, cols - 1)
        walls_h[rows, exit_cell[1]] = False  # door in the outer wall

        def open_moves(r, c):
            if r > 0 and not walls_h[r, c]:
                yield r - 1, c
            if r < rows - 1 and not walls_h[r + 1, c]:
                yield r + 1, c
            if c > 0 and not walls_v[r, c]:
                yield r, c - 1
            if c < cols - 1 and not walls_v[r, c + 1]:
                yield r, c + 1

        prev = {start_cell: None}
        q = deque([start_cell])
        while q:
            cell = q.popleft()
            for nb in open_moves(*cell):
                if nb not in prev:
                    prev[nb] = cell
                    q.append(nb)
        path = []
        cell = exit_cell
        while cell is not None:
            path.append(cell)
            cell = prev[cell]
        path.reverse()
        # geometry
        mx, my = self.W * 0.08, self.H * (0.12 if portrait else 0.14)
        gw, gh = self.W - 2 * mx, self.H - my - self.H * (0.12 if portrait else 0.1)
        cs = min(gw / cols, gh / rows)
        ox, oy = (self.W - cs * cols) / 2, my
        self.cs, self.ox, self.oy = cs, ox, oy
        self.maze_rect = (ox, oy, ox + cs * cols, oy + cs * rows)
        blue = _darker(pal["green"], 0.85)
        line = (236, 230, 210)
        img = Image.new("RGB", (self.W, self.H), blue)
        d = ImageDraw.Draw(img)
        for gx in np.arange(0, self.W, cs / 2):  # blueprint grid
            d.line((gx, 0, gx, self.H), fill=_darker(blue, 1.12) if False else tuple(min(255, int(v * 1.12)) for v in blue), width=1)
        for gy in np.arange(0, self.H, cs / 2):
            d.line((0, gy, self.W, gy), fill=tuple(min(255, int(v * 1.12)) for v in blue), width=1)
        lw = max(4, int(cs * 0.09))
        for r in range(rows + 1):
            for c in range(cols):
                if walls_h[r, c]:
                    d.line((ox + c * cs, oy + r * cs, ox + (c + 1) * cs, oy + r * cs), fill=line, width=lw)
        for r in range(rows):
            for c in range(cols + 1):
                if walls_v[r, c]:
                    d.line((ox + c * cs, oy + r * cs, ox + c * cs, oy + (r + 1) * cs), fill=line, width=lw)
        # slot nooks in dead ends
        for r in range(rows):
            for c in range(cols):
                if (r, c) in (start_cell, exit_cell):
                    continue
                if len(list(open_moves(r, c))) == 1:
                    s = cs * 0.34
                    x, y = ox + c * cs + cs / 2, oy + r * cs + cs / 2
                    d.rectangle((x - s / 2, y - s / 2, x + s / 2, y + s / 2), fill=pal["accent"], outline=pal["ink"], width=2)
        head = resolve_font(cfg["fonts"]["headline"])
        lf = font(head, int(cs * 0.5))
        sx, sy = ox + start_cell[1] * cs + cs / 2, oy + start_cell[0] * cs + cs / 2
        d.ellipse((sx - cs * 0.22, sy - cs * 0.22, sx + cs * 0.22, sy + cs * 0.22), fill=pal["red"])
        d.text((sx, sy - cs * 0.45), "YOU", font=lf, fill=line, anchor="md")
        ex, ey = ox + exit_cell[1] * cs + cs / 2, oy + rows * cs
        d.text((ex, ey + cs * 0.1), "EXIT", font=lf, fill=pal["accent"], anchor="ma")
        title = spec.get("title", "CASINO FLOOR PLAN")
        tf = font(head, int(self.H * 0.045))
        d.text((self.W / 2, my * 0.5), title.upper(), font=tf, fill=line, anchor="mm")
        self.base = add_grain(np.array(img), 0.03, 12)
        pts = np.array([(ox + c * cs + cs / 2, oy + r * cs + cs / 2) for r, c in path] + [(ex, ey)], np.float32)
        # densify for smooth drawing
        dense = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            for f in np.linspace(0, 1, 8)[1:]:
                dense.append(a + (b - a) * f)
        self.path = np.array(dense, np.float32)
        self.red = tuple(int(x) for x in pal["red"])
        self.trace_start = 0.5 + lead_in
        self.trace_dur = max(1.5, duration - lead_in - 1.6)
        self.note = None
        if spec.get("note"):
            mf = font(resolve_font(cfg["fonts"]["marker"]), int(self.H * 0.042))
            self.note = text_block([spec["note"]], mf, fill=pal["accent"], stroke=3, stroke_fill=_darker(pal["green"], 0.5))
        self.mag_r = int(min(self.W, self.H) * 0.13)

    def frame(self, t: float) -> np.ndarray:
        out = self.base.copy()
        p = ease((t - self.trace_start) / self.trace_dur) if t > self.trace_start else 0.0
        n = max(2, int(len(self.path) * p))
        if p > 0:
            cv2.polylines(out, [self.path[:n].astype(np.int32).reshape(-1, 1, 2)], False, self.red, max(5, int(self.cs * 0.12)), cv2.LINE_AA)
            tip = self.path[n - 1]
            # magnifier: 1.9x of the region around the pen tip
            r, z = self.mag_r, 1.9
            src_r = int(r / z)
            x, y = int(tip[0]), int(tip[1])
            H, W = out.shape[:2]
            x0, y0 = max(0, x - src_r), max(0, y - src_r)
            x1, y1 = min(W, x + src_r), min(H, y + src_r)
            crop = out[y0:y1, x0:x1]
            if crop.size:
                big = cv2.resize(crop, (int(crop.shape[1] * z), int(crop.shape[0] * z)), interpolation=cv2.INTER_LINEAR)
                mag_x = int(min(max(x + r * 0.9, r * 1.1), W - r * 2.0))
                mag_y = int(min(max(y - r * 0.9, r * 1.1), H - r * 2.0))
                mask = np.zeros(big.shape[:2], np.uint8)
                cv2.circle(mask, (big.shape[1] // 2, big.shape[0] // 2), min(big.shape[:2]) // 2 - 2, 255, -1, cv2.LINE_AA)
                rgba = np.dstack([big, mask])
                blend(out, rgba, mag_x - big.shape[1] // 2, mag_y - big.shape[0] // 2)
                cv2.circle(out, (mag_x, mag_y), min(big.shape[:2]) // 2, (40, 30, 25), max(6, r // 12), cv2.LINE_AA)
                hx = int(mag_x + r * 0.75)
                hy = int(mag_y + r * 0.75)
                cv2.line(out, (hx, hy), (hx + int(r * 0.6), hy + int(r * 0.6)), (90, 55, 30), max(10, r // 6), cv2.LINE_AA)
        if self.note is not None and t > self.trace_start + self.trace_dur:
            op = min(1.0, (t - self.trace_start - self.trace_dur) / 0.25)
            x0, y0, x1, y1 = self.maze_rect
            if self.H > self.W:  # Shorts: the caption zone is under the maze — no note
                pass
            else:  # bottom-right, under the maze's outer wall, clear of EXIT (bottom-left) and the subtitles
                blend(out, self.note, int(x1 - self.note.shape[1]), int(y1 + self.cs * 0.12), opacity=op)
        z = 1.0 + 0.06 * ease(t / max(self.duration, 1e-6))
        if z > 1.001:
            cw, ch = int(self.W / z), int(self.H / z)
            out = cv2.resize(out[(self.H - ch) // 2 : (self.H - ch) // 2 + ch, (self.W - cw) // 2 : (self.W - cw) // 2 + cw], (self.W, self.H))
        return out

    def sfx(self, start_abs: float) -> list[tuple[float, str]]:
        return [(start_abs + self.trace_start + k * 0.9, "scribble") for k in range(int(self.trace_dur / 0.9))]


class NewsreelShot(Shot):
    """Wraps any shot with the newsreel film look (and 12 fps judder)."""

    def __init__(self, inner: Shot, cfg: dict, label: str | None, seed: int):
        super().__init__(inner.start, inner.duration)
        self.inner, self.cfg, self.label, self.seed = inner, cfg, label, seed

    def frame(self, t: float) -> np.ndarray:
        # smooth picture (no 12 fps judder of the camera); a gentle film weave of at most 1 px at <=2 Hz
        out = newsreel(self.inner.frame(t), t, self.seed, self.label, self.cfg)
        dx, dy = math.sin(t * 2 * math.pi * 1.1 + self.seed) * 0.8, math.sin(t * 2 * math.pi * 0.7 + 1.3 * self.seed) * 0.8
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        return cv2.warpAffine(out, M, (out.shape[1], out.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ------------------------------------------------------------------ slot machine

SLOT_SYMBOLS = ["7", "CHERRY", "BAR", "LEMON", "BELL", "CHERRY", "BAR", "LEMON", "BELL", "CHERRY", "BAR", "LEMON"]


def _symbol(kind: str, s: int, cfg: dict) -> np.ndarray:
    pal = _pal(cfg)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    if kind == "7":
        f = font(resolve_font(cfg["fonts"]["headline"]), int(s * 0.82))
        d.text((c, c), "7", font=f, fill=pal["red"], anchor="mm", stroke_width=max(3, s // 22), stroke_fill=pal["ink"])
    elif kind == "BAR":
        d.rounded_rectangle((s * 0.12, s * 0.3, s * 0.88, s * 0.7), radius=s * 0.08, fill=pal["ink"])
        f = font(resolve_font(cfg["fonts"]["headline"]), int(s * 0.28))
        d.text((c, c), "BAR", font=f, fill=pal["paper"], anchor="mm")
    elif kind == "CHERRY":
        d.line((s * 0.38, s * 0.62, s * 0.55, s * 0.2), fill=pal["green"], width=max(4, s // 18))
        d.line((s * 0.66, s * 0.6, s * 0.55, s * 0.2), fill=pal["green"], width=max(4, s // 18))
        for x, y in ((0.36, 0.66), (0.66, 0.64)):
            r = s * 0.16
            d.ellipse((s * x - r, s * y - r, s * x + r, s * y + r), fill=pal["red"], outline=pal["ink"], width=3)
    elif kind == "LEMON":
        d.ellipse((s * 0.18, s * 0.3, s * 0.82, s * 0.72), fill=pal["accent"], outline=pal["ink"], width=3)
    elif kind == "BELL":
        d.polygon([(s * 0.5, s * 0.18), (s * 0.68, s * 0.35), (s * 0.75, s * 0.68), (s * 0.25, s * 0.68), (s * 0.32, s * 0.35)],
                  fill=pal["accent"], outline=pal["ink"])
        d.ellipse((s * 0.44, s * 0.66, s * 0.56, s * 0.78), fill=pal["ink"])
    return np.array(img)


class SlotShot(Shot):
    """Code-drawn slot machine: reels stop one by one; result 7-7 on the line and the third 7 just above it
    (a near miss). spec: result ('near_miss' | 'win' | 'loss'), stops [s,s,s], mark (bool), note"""

    def __init__(self, start, duration, spec: dict, cfg: dict, size, lead_in: float = 0.0):
        super().__init__(start, duration)
        self.W, self.H = size
        self.cfg, self.spec, self.lead_in = cfg, spec, lead_in
        pal = self.pal = _pal(cfg)
        portrait = self.H > self.W
        s = int(min(self.W * 0.82 / 3, self.H * (0.16 if portrait else 0.19)))
        self.s = s
        win_w, win_h = s * 3, s * 3
        wy = int(self.H * 0.16) if portrait else int((self.H - win_h) / 2)
        self.win = (int((self.W - win_w) / 2), wy, win_w, win_h)
        self.portrait = portrait
        bg = Image.new("RGB", (self.W, self.H), _darker(pal["red"], 0.55))
        d = ImageDraw.Draw(bg)
        wx, wy, ww, wh = self.win
        pad = int(s * 0.35)
        d.rounded_rectangle((wx - pad, wy - pad * 3, wx + ww + pad, wy + wh + pad * 2), radius=pad, fill=pal["red"], outline=pal["ink"], width=8)
        f = font(resolve_font(cfg["fonts"]["headline"]), int(pad * 1.5))
        d.text((self.W / 2, wy - pad * 1.6), "JACKPOT", font=f, fill=pal["accent"], anchor="mm", stroke_width=4, stroke_fill=pal["ink"])
        d.rectangle((wx - 8, wy - 8, wx + ww + 8, wy + wh + 8), fill=(200, 200, 200), outline=pal["ink"], width=6)
        self.bulbs = [(wx - pad + k * (ww + 2 * pad) / 13, wy - pad * 2.9) for k in range(14)]
        self.bg = add_grain(np.array(bg), 0.03, 21)
        syms = {k: _symbol(k, s, cfg) for k in set(SLOT_SYMBOLS)}
        n = len(SLOT_SYMBOLS)
        strip = np.zeros((n * s * 3, s, 4), np.uint8)
        for rep in range(3):
            for k, name in enumerate(SLOT_SYMBOLS):
                strip[(rep * n + k) * s : (rep * n + k + 1) * s] = syms[name]
        self.strip, self.n = strip, n
        result = spec.get("result", "near_miss")
        i7 = SLOT_SYMBOLS.index("7")
        if result == "win":
            finals = [i7, i7, i7]
        elif result == "loss":
            finals = [2, 7, 4]
        else:
            finals = [i7, i7, i7 + 1]  # third 7 sits one row above the line
        self.finals = finals
        stops = spec.get("stops") or [1.0, 1.6, 2.6]
        self.stops = [lead_in + float(x) for x in stops]
        self.travel = [14, 20, 30]
        self.red = tuple(int(x) for x in pal["red"])
        self.mark_at = self.stops[-1] + 0.35
        self.note = None
        if spec.get("note"):
            mf = font(resolve_font(cfg["fonts"]["marker"]), int(self.H * 0.042))
            self.note = text_block([spec["note"]], mf, fill=pal["accent"], stroke=4, stroke_fill=pal["ink"])
        self.strokes = None

    def _pos(self, i: int, t: float) -> float:
        p = min(1.0, max(0.0, t / self.stops[i]))
        return self.finals[i] + self.n - self.travel[i] * (1 - p) ** 2

    def frame(self, t: float) -> np.ndarray:
        out = self.bg.copy()
        wx, wy, ww, wh = self.win
        s = self.s
        reel_bg = np.full((wh, ww, 3), (250, 246, 236), np.uint8)
        out[wy : wy + wh, wx : wx + ww] = reel_bg
        for i in range(3):
            pos = self._pos(i, t) % self.n + self.n
            top = int((pos - 1) * s)
            crop = self.strip[top : top + wh]
            if crop.shape[0] < wh:
                continue
            if t < self.stops[i]:  # motion blur while spinning
                crop = cv2.blur(crop, (1, max(1, int(s * 0.25))))
            blend(out, crop, wx + i * s, wy)
            if i:
                cv2.line(out, (wx + i * s, wy), (wx + i * s, wy + wh), (120, 120, 120), 3)
        # shading top/bottom of the window
        grad = np.linspace(0.55, 1.0, s // 2)[:, None, None]
        out[wy : wy + s // 2, wx : wx + ww] = (out[wy : wy + s // 2, wx : wx + ww] * grad).astype(np.uint8)
        out[wy + wh - s // 2 : wy + wh, wx : wx + ww] = (out[wy + wh - s // 2 : wy + wh, wx : wx + ww] * grad[::-1]).astype(np.uint8)
        ly = wy + wh // 2
        cv2.line(out, (wx - 20, ly), (wx + ww + 20, ly), self.red, max(4, s // 30), cv2.LINE_AA)
        for k, (bx, by) in enumerate(self.bulbs):  # chasing lights
            on = (k + int(t * 8)) % 3 == 0
            cv2.circle(out, (int(bx), int(by)), max(6, s // 18), self.pal["accent"] if on else (120, 90, 40), -1, cv2.LINE_AA)
        if self.spec.get("mark", True) and self.spec.get("result", "near_miss") == "near_miss" and t >= self.mark_at:
            if self.strokes is None:
                cx = (wx + 2.5 * s) / self.W
                cy = (wy + 0.5 * s) / self.H
                self.strokes = mark_strokes({"type": "circle", "x": cx, "y": cy, "w": s * 1.05 / self.W, "h": s * 1.05 / self.H}, self.W, self.H, seed=77)
            _draw_marker(out, self.strokes, (t - self.mark_at) / 0.45, self.red, max(6, self.H // 120))
            if self.note is not None and t >= self.mark_at + 0.6 and not self.portrait:  # Shorts: the caption zone is below
                if self.portrait:
                    nx, ny = (self.W - self.note.shape[1]) // 2, wy + wh + int(s * 0.9)
                else:
                    nx, ny = min(self.W - self.note.shape[1] - 10, wx + ww + int(s * 0.6)), wy + int(s * 0.2)
                blend(out, self.note, nx, ny, opacity=min(1.0, (t - self.mark_at - 0.6) / 0.25))
        z = 1.0 + 0.08 * ease(t / max(self.duration, 1e-6))
        cw, ch = int(self.W / z), int(self.H / z)
        return cv2.resize(out[(self.H - ch) // 2 : (self.H - ch) // 2 + ch, (self.W - cw) // 2 : (self.W - cw) // 2 + cw], (self.W, self.H))

    def sfx(self, start_abs: float) -> list[tuple[float, str]]:
        spinning = self.stops[-1] - self.lead_in > 0.2
        ev = [(start_abs + self.lead_in + 0.05, "whirr")] if spinning else []
        ev += [(start_abs + st, "hit") for st in self.stops] if spinning else []
        if self.spec.get("result", "near_miss") == "near_miss":
            ev.append((start_abs + self.mark_at, "scribble"))
        return ev
