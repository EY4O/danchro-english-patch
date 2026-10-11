"""English versions of the Awakening / Mastery Up effect textures (fx_003_0011).

These are shader inputs, not plain pictures, so image_tl.py's styles cannot express them. This script
rebuilds each channel with the same encoding the originals use (measured from images/extra/ja):

  07_TextMask  RGB = A = white text, anti-aliased (premultiplied white)
  07_TextMap   A = same text; RGB = white where A > 0, black elsewhere inside the text bbox, white
               band to the left/right of the bbox (the original's block-bleed layout)
  07_TextMapC  inner-edge glow: A peaks 1-3 px inside the glyph edge and falls to ~13 in the middle,
               ~49 one px outside; RGB = hsv(hue(y), 0.55, 1) * A * 0.9 with hue = 202 + 3.5 deg/px down
  09_Text      white text core, cyan (65,163,184) halo ~5 px wide; alpha 218/148/70/30/9 by px outside

All three 07 textures share one text mask, so the layered effect lines up.
usage: tools/fx_text_gen.py images/extra/en   (reads the originals from images/extra/ja)
"""
import colorsys, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

JA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images", "extra", "ja")
PFX = "fx_003_0011_assets_all__ET_003_0011_"
SS = 4  # supersampling for distance-based glows


def text_mask(size, text, font_path, box, stretch_y=1.0):
    """Anti-aliased L mask of `text` fitted into box=(cx, cy, max_w, max_h), rendered at SS x."""
    W, H = size
    big = ImageFont.truetype(font_path, 400)
    l, t, r, b = big.getbbox(text)
    tmp = Image.new("L", (r - l + 40, b - t + 40), 0)
    ImageDraw.Draw(tmp).text((20 - l, 20 - t), text, font=big, fill=255)
    tmp = tmp.crop(tmp.getbbox())
    cx, cy, max_w, max_h = box
    s = min(max_w / tmp.width, max_h / (tmp.height * stretch_y))
    w, h = round(tmp.width * s * SS), round(tmp.height * s * stretch_y * SS)
    m = Image.new("L", (W * SS, H * SS), 0)
    m.paste(tmp.resize((w, h), Image.LANCZOS), (round(cx * SS - w / 2), round(cy * SS - h / 2)))
    return np.array(m).astype(np.float32) / 255


def chamfer(m, n):
    """Per-pixel count of erosion steps survived (approximate distance to the edge, in px of m)."""
    d = np.zeros(m.shape, np.float32); cur = m.copy()
    for _ in range(n):
        d += cur
        if not cur.any():
            break
        cur = cur & np.roll(cur, 1, 0) & np.roll(cur, -1, 0) & np.roll(cur, 1, 1) & np.roll(cur, -1, 1)
    return d


def down(a):
    h, w = a.shape[0] // SS, a.shape[1] // SS
    return a.reshape(h, SS, w, SS, *a.shape[2:]).mean((1, 3))


def interp(dist_px, xs, ys):
    return np.interp(dist_px, xs, ys)


def build_07(out):
    W, H = 512, 512
    # original glyph block: x 71..440, y 159..336 (centre 255.5, 247.5). English is wider, so use
    # nearly the full texture width and stretch the serif capitals vertically to keep the weight.
    m = text_mask((W, H), "AWAKENING", "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
                  (256, 248, 476, 170), stretch_y=2.0)
    a = down(m)
    A8 = np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)

    mask = np.zeros((H, W, 4), np.uint8)
    mask[..., 0] = mask[..., 1] = mask[..., 2] = A8; mask[..., 3] = A8
    Image.fromarray(mask).save(f"{out}/{PFX}07_TextMask.png")

    ys, xs = np.where(A8 > 0)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    tm = np.zeros((H, W, 4), np.uint8)
    rgb = np.where(A8 > 0, 255, 0).astype(np.uint8)
    rgb[y0:y1 + 1, :x0] = 255; rgb[y0:y1 + 1, x1 + 1:] = 255
    tm[..., 0] = tm[..., 1] = tm[..., 2] = rgb; tm[..., 3] = A8
    Image.fromarray(tm).save(f"{out}/{PFX}07_TextMap.png")

    # inner glow from distance to the glyph edge, measured on the supersampled mask
    inside = m >= 0.5
    di = chamfer(inside, 16 * SS) / SS          # px inside
    do = chamfer(~inside, 4 * SS) / SS          # px outside
    prof_in_x = [0, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 11, 14]
    prof_in_y = [120, 171, 217, 189, 135, 96, 66, 46, 31, 22, 17, 14, 13]
    alpha_big = np.where(inside, interp(di, prof_in_x, prof_in_y),
                         interp(do, [0, 0.5, 1.5, 2.5], [120, 49, 3, 0]))
    ac = down(alpha_big)
    top = y0
    yy = np.arange(H, dtype=np.float32)[:, None].repeat(W, 1)
    hue = ((202 + 3.5 * (yy - top)) % 360) / 360
    lut = np.array([colorsys.hsv_to_rgb(i / 360, 0.55, 1.0) for i in range(360)])
    col = lut[(hue * 360).astype(int) % 360]
    mc = np.zeros((H, W, 4), np.uint8)
    mc[..., :3] = np.clip(col * ac[..., None] * 0.9, 0, 255).astype(np.uint8)
    mc[..., 3] = np.clip(ac, 0, 255).astype(np.uint8)
    Image.fromarray(mc).save(f"{out}/{PFX}07_TextMapC.png")


def build_09(out):
    W, H = 256, 256
    # original core text: x 18..239, y 104..146; halo reaches ~6 px past that
    m = text_mask((W, H), "Mastery Up", "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
                  (128.5, 125, 222, 43))
    inside = m >= 0.5
    do = chamfer(~inside, 10 * SS) / SS
    a_out = interp(do, [0, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5], [255, 218, 148, 70, 30, 9, 2, 0])
    alpha = np.where(inside, 255, a_out)
    cyan = np.array([65, 163, 184], np.float32)
    fade = interp(do, [0, 5.5, 6.5, 7.5, 8.5, 9.5], [1, 1, 0.57, 0.25, 0.1, 0])
    rgb = np.where(inside[..., None], 255, cyan * fade[..., None])
    rgb = down(rgb); alpha = down(alpha)
    o = np.zeros((H, W, 4), np.uint8)
    o[..., :3] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    o[..., 3] = np.clip(alpha + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(o).save(f"{out}/{PFX}09_Text.png")


if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    build_07(out); build_09(out)
    print("wrote", out)
