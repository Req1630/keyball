#!/usr/bin/env python3
"""
PDF内のキーマップをレイヤーごとに切り出してPNG出力するスクリプト。

使い方:
  python split_keymap_pdf.py input.pdf
  python split_keymap_pdf.py input.pdf --output-dir images --scale 2

初期状態では、ページ上の切り出し範囲を画像の割合 (0.0～1.0) で指定します。
PDFごとにレイアウトが異なるため、REGIONS を必要に応じて調整してください。
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    import pymupdf  # PyMuPDF
except ImportError:
    print("PyMuPDF がありません。次のコマンドでインストールしてください: pip install pymupdf pillow")
    raise SystemExit(1)

try:
    from PIL import Image
except ImportError:
    print("Pillow がありません。次のコマンドでインストールしてください: pip install pymupdf pillow")
    raise SystemExit(1)


# 各レイヤーの切り出し範囲。
# 値は (left, top, right, bottom) の順で、ページ幅・高さに対する割合です。
# 今回の Keyball44 cheat sheet PDF のレイアウトに合わせた初期値です。
# 別のPDFで使う場合や余白を調整したい場合は、この値を変更してください。
layer_start_height = 0.020
layer_height = 0.132 - 0.020
layer_adj_height = 0.010
REGIONS: dict[str, tuple[float, float, float, float]] = {
    "layer0": (0.015, (layer_adj_height*0)+layer_start_height+layer_height*0, 0.985, (layer_adj_height*0)+(layer_start_height+layer_height*0)+layer_height),
    "layer1": (0.015, (layer_adj_height*1)+layer_start_height+layer_height*1, 0.985, (layer_adj_height*1)+(layer_start_height+layer_height*1)+layer_height),
    "layer2": (0.015, (layer_adj_height*2)+layer_start_height+layer_height*2, 0.985, (layer_adj_height*2)+(layer_start_height+layer_height*2)+layer_height),
    "layer3": (0.015, (layer_adj_height*3)+layer_start_height+layer_height*3, 0.985, (layer_adj_height*3)+(layer_start_height+layer_height*3)+layer_height),
    "layer4": (0.015, (layer_adj_height*4)+layer_start_height+layer_height*4, 0.985, (layer_adj_height*4)+(layer_start_height+layer_height*4)+layer_height),
    "layer5": (0.015, (layer_adj_height*5)+layer_start_height+layer_height*5, 0.985, (layer_adj_height*5)+(layer_start_height+layer_height*5)+layer_height),
    "layer6": (0.015, (layer_adj_height*6)+layer_start_height+layer_height*6, 0.985, (layer_adj_height*6)+(layer_start_height+layer_height*6)+layer_height),
    "layer7": (0.015, (layer_adj_height*7)+layer_start_height+layer_height*7, 0.985, (layer_adj_height*7)+(layer_start_height+layer_height*7)+layer_height),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PDFページからレイヤーごとの画像を切り出してPNG出力します。"
    )
    parser.add_argument("pdf", type=Path, help="入力PDFファイル")
    parser.add_argument(
        "--output-dir", "-o", type=Path, default=None,
        help="出力先ディレクトリ (省略時: PDFと同じ場所に <PDF名>_layers)"
    )
    parser.add_argument(
        "--page", type=int, default=1,
        help="対象ページ番号 (1始まり、既定値: 1)"
    )
    parser.add_argument(
        "--scale", type=float, default=2.0,
        help="画像の拡大倍率 (既定値: 2.0)"
    )
    parser.add_argument(
        "--margin", type=int, default=4,
        help="切り出し後に追加する白い余白のピクセル数 (既定値: 4)"
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="切り出し範囲の確認用に、ページ全体のPNGも出力"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.pdf.is_file():
        print(f"入力PDFが見つかりません: {args.pdf}")
        return 1
    if args.page < 1:
        print("--page は 1 以上を指定してください。")
        return 1
    if args.scale <= 0:
        print("--scale は 0 より大きい値を指定してください。")
        return 1

    output_dir = args.output_dir or args.pdf.with_name(f"{args.pdf.stem}_layers")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        document = pymupdf.open(args.pdf)
    except Exception as exc:
        print(f"PDFを開けませんでした: {exc}")
        return 1

    if args.page > len(document):
        print(f"指定ページがありません。PDFのページ数: {len(document)}")
        document.close()
        return 1

    page = document[args.page - 1]
    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(args.scale, args.scale),
        alpha=False,
        annots=True,
    )
    page_image_path = output_dir / f"page_{args.page:02d}.png"
    pix.save(page_image_path)

    with Image.open(page_image_path) as source:
        page_image = source.convert("RGB")
        width, height = page_image.size

        for layer_name, (left, top, right, bottom) in REGIONS.items():
            if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
                print(f"範囲設定が不正です: {layer_name}")
                continue

            # ピクセル座標へ変換
            x0 = round(left * width)
            y0 = round(top * height)
            x1 = round(right * width)
            y1 = round(bottom * height)

            cropped = page_image.crop((x0, y0, x1, y1))

            # 白い余白を付ける
            if args.margin > 0:
                canvas = Image.new(
                    "RGB",
                    (cropped.width + args.margin * 2, cropped.height + args.margin * 2),
                    "white",
                )
                canvas.paste(cropped, (args.margin, args.margin))
                cropped = canvas

            output_path = output_dir / f"{layer_name}.png"
            cropped.save(output_path, optimize=True)
            print(f"出力: {output_path}")

    if args.preview:
        print(f"ページ全体: {page_image_path}")
    else:
        page_image_path.unlink(missing_ok=True)

    document.close()

    # Markdownへの埋め込み例も出力
    md_path = output_dir / "keymap_layers.md"
    with md_path.open("w", encoding="utf-8", newline="\n") as md:
        md.write("# Keyball44 キーマップ\n\n")
        for layer_name in REGIONS:
            md.write(f"## {layer_name.replace('layer', 'Layer ')}\n\n")
            md.write(f"![{layer_name}]({layer_name}.png)\n\n")

    print(f"Markdown: {md_path}")
    print("完了しました。切り出し位置が合わない場合は、スクリプト内の REGIONS を調整してください。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
