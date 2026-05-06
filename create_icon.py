"""
Generates reporter.ico from scratch using Pillow.
Run automatically by build.bat before PyInstaller.
"""
import math
import os
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
    sizes = [16, 24, 32, 48, 64, 128, 256]

    # Draw each size individually for best quality at small sizes
    frames = [draw_clock(s).convert('RGBA') for s in sizes]

    # Pillow ICO: save the largest frame, pass all pre-drawn frames via
    # append_images so each size uses its own hand-drawn version rather than
    # a low-quality downscale.  sizes= tells Pillow which entries to include.
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reporter.ico')

    # Build list of (size, image) pairs — largest first
    ico_frames = list(zip(sizes[::-1], frames[::-1]))  # 256 … 16

    # Save: Pillow ICO plugin accepts a list of images via append_images,
    # one per size entry.  We pass the 256px as the "primary" and the rest
    # as append_images, with matching sizes= so each slot maps to its frame.
    ico_frames_sorted = sorted(zip(sizes, frames), reverse=True)
    sorted_sizes  = [(s, s) for s, _ in ico_frames_sorted]
    sorted_images = [img     for _, img in ico_frames_sorted]

    sorted_images[0].save(
        out_path,
        format='ICO',
        sizes=sorted_sizes,
        append_images=sorted_images[1:],
    )

    # Verify the file was actually written
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError(f'ICO file was not created at {out_path}')

    print(f'reporter.ico created ({os.path.getsize(out_path)//1024} KB, '
          f'{len(sizes)} sizes: {sizes})')
    print(f'  -> {out_path}')


if __name__ == '__main__':
    main()
