"""
Generates reporter.ico from scratch using Pillow.
Run automatically by build.bat before PyInstaller.
"""
import math
from PIL import Image, ImageDraw


def draw_clock(size):
    img  = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = size / 2
    r  = size / 2

    # blue background circle
    draw.ellipse([0, 0, size - 1, size - 1], fill='#3B82F6')

    # white clock face (inner circle, subtle)
    pad  = r * 0.12
    draw.ellipse([pad, pad, size - 1 - pad, size - 1 - pad],
                 fill=None, outline='white', width=max(1, int(r * 0.09)))

    # hour ticks at 12, 3, 6, 9
    tick_outer = r * 0.82
    tick_inner = r * 0.68
    tick_w     = max(1, int(r * 0.09))
    for angle_deg in (0, 90, 180, 270):
        a = math.radians(angle_deg - 90)
        x1 = cx + tick_outer * math.cos(a)
        y1 = cy + tick_outer * math.sin(a)
        x2 = cx + tick_inner * math.cos(a)
        y2 = cy + tick_inner * math.sin(a)
        draw.line([x1, y1, x2, y2], fill='white', width=tick_w)

    # hour hand — pointing ~10  (300°)
    hand_w = max(1, int(r * 0.12))
    a_h = math.radians(300 - 90)
    draw.line([cx, cy,
               cx + r * 0.45 * math.cos(a_h),
               cy + r * 0.45 * math.sin(a_h)],
              fill='white', width=hand_w)

    # minute hand — pointing ~2  (60°)
    a_m = math.radians(60 - 90)
    draw.line([cx, cy,
               cx + r * 0.62 * math.cos(a_m),
               cy + r * 0.62 * math.sin(a_m)],
              fill='white', width=max(1, int(r * 0.08)))

    # center dot
    dot = r * 0.12
    draw.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill='white')

    return img


def main():
    sizes  = [16, 24, 32, 48, 64, 128, 256]
    frames = [draw_clock(s) for s in sizes]
    # Save multi-size ICO
    frames[0].save(
        'reporter.ico',
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f'reporter.ico created ({len(sizes)} sizes: {sizes})')


if __name__ == '__main__':
    main()
