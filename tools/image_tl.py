"""Replace baked-in Japanese text in tutorial images with English.

images/ja/<name>.png       original textures (exported from the game)
images/ocr.json            Vision OCR boxes per image (tools/ocr/ocr)
images/text_en.json        {image: [{"ja": <ocr text>, "en": <English>, "style": "headline"|"ui"|"keep"}]}
                           *word* in "en" = orange emphasis (headline style only)
                           optional per item: "size" (px), "color" [r,g,b], "dx"/"dy" (px nudge),
                           "erase": "box" | "glyphs" | "none"
                           "box": {"x","y","w","h"} to place text OCR missed ("ja" is then just a label)
images/spec/*.json         same format as text_en.json; merged over it (one file per translator batch)
images/en/<name>.png       output

usage: image_tl.py render [names...]
"""
import glob, json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images")
HEADLINE_FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
UI_FONT = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
WHITE, OUTLINE = (255, 255, 255), (40, 22, 12)
ORANGE_TOP, ORANGE_BOTTOM = (255, 196, 40), (240, 70, 20)


# ---------- erase ----------
def fill_holes(rgb, mask):
    """Fill masked pixels from their surroundings: coarse-to-fine diffusion (no OpenCV needed)."""
    img = rgb.astype(np.float32)
    known = ~mask
    levels = []
    cur_img, cur_known = img, known.astype(np.float32)
    while min(cur_img.shape[:2]) > 8:
        levels.append((cur_img, cur_known))
        h, w = cur_img.shape[0] // 2 * 2, cur_img.shape[1] // 2 * 2
        ci, ck = cur_img[:h, :w], cur_known[:h, :w]
        wsum = ck.reshape(h // 2, 2, w // 2, 2).sum((1, 3))
        csum = (ci * ck[..., None]).reshape(h // 2, 2, w // 2, 2, 3).sum((1, 3))
        cur_img = np.where(wsum[..., None] > 0, csum / np.maximum(wsum, 1e-6)[..., None], 0)
        cur_known = (wsum > 0).astype(np.float32)
    est = cur_img
    for lvl_img, lvl_known in reversed(levels):
        up = np.repeat(np.repeat(est, 2, 0), 2, 1)
        up = np.pad(up, ((0, lvl_img.shape[0] - up.shape[0]), (0, lvl_img.shape[1] - up.shape[1]), (0, 0)), mode="edge")
        est = np.where(lvl_known[..., None] > 0, lvl_img, up)
        for _ in range(4):  # smooth only the filled area
            blur = (np.roll(est, 1, 0) + np.roll(est, -1, 0) + np.roll(est, 1, 1) + np.roll(est, -1, 1)) / 4
            est = np.where(lvl_known[..., None] > 0, lvl_img, blur)
    return est.clip(0, 255).astype(np.uint8)


def glyph_mask(rgb, x0, y0, x1, y1, grow=2):
    """Pixels of the text itself inside a box: those contrasting with the box's dominant background."""
    lum = rgb[y0:y1, x0:x1].astype(np.float32).mean(2)
    bg = np.median(lum)
    m = (lum < bg - 50) if bg >= 128 else (lum > bg + 50)
    for _ in range(grow):  # dilate so anti-aliased edges go too
        m = m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
    return m


def erase(im, boxes):
    rgba = np.array(im.convert("RGBA"))
    mask = np.zeros(rgba.shape[:2], bool)
    for b in boxes:
        pad = b.get("pad", 6)
        x0, y0 = max(int(b["x"]) - pad, 0), max(int(b["y"]) - pad, 0)
        x1, y1 = min(int(b["x"] + b["w"]) + pad, im.width), min(int(b["y"] + b["h"]) + pad, im.height)
        if b.get("glyphs_only"):
            mask[y0:y1, x0:x1] |= glyph_mask(rgba[..., :3], x0, y0, x1, y1)
        else:
            mask[y0:y1, x0:x1] = True
    rgb = fill_holes(rgba[..., :3], mask)
    alpha = rgba[..., 3].astype(np.float32)
    alpha_f = fill_holes(np.repeat(alpha[..., None], 3, 2), mask)[..., 0]
    rgba[..., :3] = np.where(mask[..., None], rgb, rgba[..., :3])
    rgba[..., 3] = np.where(mask, alpha_f, rgba[..., 3])
    return Image.fromarray(rgba)


# ---------- draw ----------
def segments(text):
    """'Tap *Skill* now' -> [('Tap ', False), ('Skill', True), (' now', False)]"""
    parts = re.split(r"(\*[^*]+\*)", text)
    return [(p.strip("*"), p.startswith("*")) for p in parts if p]


def text_width(font, segs):
    return sum(font.getlength(s) for s, _ in segs)


def wrap(font, text, max_w):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if cur and text_width(font, segments(trial)) > max_w:
            lines.append(cur); cur = w
        else:
            cur = trial
    return lines + [cur]


def gradient_fill(size, top, bottom):
    h = max(size[1], 1)
    col = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(top) * (1 - col) + np.array(bottom) * col).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, max(size[0], 1), 1))


def draw_headline(canvas, box, text, max_right):
    """Game-style headline: white + orange gradient emphasis, thick dark outline, drop shadow."""
    target_h = box["h"]
    max_w = max(max_right - box["x"], box["w"])
    for size in range(int(target_h * 0.82), int(target_h * 0.4), -1):
        font = ImageFont.truetype(HEADLINE_FONT, size)
        lines = wrap(font, text, max_w)
        if len(lines) == 1 or (len(lines) == 2 and size <= target_h * 0.62):
            break
    stroke = max(2, size // 9)
    line_h = int(size * 1.12)
    total_h = line_h * len(lines)
    y = box["y"] + (target_h - total_h) / 2
    for line in lines:
        x = box["x"]
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d, ds = ImageDraw.Draw(layer), ImageDraw.Draw(shadow)
        for seg, emph in segments(line):
            w = font.getlength(seg)
            ds.text((x + 2, y + 3), seg, font=font, fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
            d.text((x, y), seg, font=font, fill=WHITE + (255,), stroke_width=stroke, stroke_fill=OUTLINE + (255,))
            if emph:  # paint the glyph interiors with an orange gradient
                m = Image.new("L", canvas.size, 0)
                ImageDraw.Draw(m).text((x, y), seg, font=font, fill=255)
                top = int(y + size * 0.1)
                grad = gradient_fill((canvas.width, size), ORANGE_TOP, ORANGE_BOTTOM)
                full = Image.new("RGB", canvas.size); full.paste(grad, (0, top))
                layer.paste(full, (0, 0), m)
            x += w
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(2)))
        canvas.alpha_composite(layer)
        y += line_h


def fit_size(text, box, start):
    """Largest font size <= start whose single line fits in ~1.15x the original text width."""
    size = start
    while size > 8 and ImageFont.truetype(UI_FONT, size).getlength(text) > box["w"] * 1.25:
        size -= 1
    return size


def glyph_height(rgb, b):
    """Real text height inside an OCR box (OCR boxes are sometimes much taller than the letters)."""
    x0, y0 = max(int(b["x"]), 0), max(int(b["y"]) - 2, 0)
    x1, y1 = int(b["x"] + b["w"]), int(b["y"] + b["h"]) + 2
    rows = np.where(glyph_mask(rgb, x0, y0, x1, y1, grow=0).any(1))[0]
    return float(rows[-1] - rows[0] + 1) if len(rows) else b["h"]


def ui_groups(items, rgb=None):
    """Group UI lines that form one paragraph (same left edge, stacked) so they share a font size."""
    ui = sorted([(dict(b, h=glyph_height(rgb, b)) if rgb is not None else b, s)
                 for b, s in items if s["style"] == "ui"], key=lambda t: (t[0]["y"], t[0]["x"]))
    groups = []
    for b, s in ui:
        for g in groups:
            last = g[-1][0]
            similar = 0.75 < b["h"] / max(last["h"], 1) < 1.33
            if similar and abs(last["x"] - b["x"]) < 12 and 0 < b["y"] - last["y"] < 2.2 * max(last["h"], 12):
                g.append((b, s)); break
        else:
            groups.append([(b, s)])
    sizes = {}
    for g in groups:
        start = int(np.median([b["h"] for b, _ in g]) * 1.05)
        size = min(fit_size(s["en"], b, start) for b, s in g)
        for b, s in g:
            sizes[s["ja"]] = max(size, 9)
    return sizes


def draw_ui(canvas, box, text, color, size):
    font = ImageFont.truetype(UI_FONT, size)
    y = box["y"] + (box["h"] - size * 1.1) / 2
    ImageDraw.Draw(canvas).text((box["x"], y), text, font=font, fill=color)


def text_color(im, box):
    """Darkest common colour inside the box = the original text colour (UI text is dark on light)."""
    crop = np.array(im.convert("RGB").crop((int(box["x"]), int(box["y"]), int(box["x"] + box["w"]), int(box["y"] + box["h"]))))
    px = crop.reshape(-1, 3)
    lum = px.mean(1)
    dark = px[lum <= np.percentile(lum, 10)]
    return tuple(int(c) for c in dark.mean(0)) if len(dark) else (60, 50, 40)


def render(name, ocr, spec):
    im = Image.open(f"{ROOT}/ja/{name}.png").convert("RGBA")
    boxes = {b["text"]: b for b in ocr[f"{name}.png"]}
    for s in spec:
        if "box" in s:
            boxes[s["ja"]] = dict(s["box"], text=s["ja"])
    items = [(boxes[s["ja"]], s) for s in spec if s["ja"] in boxes and s.get("style") != "keep"]
    colors = {s["ja"]: text_color(im, b) for b, s in items if s["style"] == "ui"}
    sizes = ui_groups(items, np.array(im.convert("RGB")))
    def erase_spec(b, s):
        mode = s.get("erase", "box" if s["style"] == "headline" else "glyphs")
        return None if mode == "none" else dict(b, pad=6 if s["style"] == "headline" else 3, glyphs_only=mode == "glyphs")
    out = erase(im, [e for e in (erase_spec(b, s) for b, s in items) if e])
    for b, s in items:
        b = dict(b, x=b["x"] + s.get("dx", 0), y=b["y"] + s.get("dy", 0))
        if s["style"] == "headline":
            draw_headline(out, b, s["en"], max_right=im.width - 20)
        else:
            draw_ui(out, b, s["en"], tuple(s.get("color", colors[s["ja"]])), s.get("size", sizes[s["ja"]]))
    os.makedirs(f"{ROOT}/en", exist_ok=True)
    out.save(f"{ROOT}/en/{name}.png")
    missing = [s["ja"] for s in spec if s["ja"] not in boxes]
    if missing:
        print(f"{name}: OCR text not found for {missing}")


if __name__ == "__main__":
    ocr = json.load(open(f"{ROOT}/ocr.json"))
    spec = json.load(open(f"{ROOT}/text_en.json"))
    for f in sorted(glob.glob(f"{ROOT}/spec/*.json")):
        spec.update(json.load(open(f)))
    names = sys.argv[2:] or sorted(spec)
    for n in names:
        render(n, ocr, spec[n])
        print("rendered", n)
