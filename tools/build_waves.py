"""
生成横幅底部波浪的两张波形瓦片，写回 source/css/custom.css。

custom.css 里第 18 节的 --wave-back / --wave-front 是 data URI，长得没法
读也没法手改。它们是这个脚本生成的，改波形请改下面的常量，然后重跑：

    python tools/build_waves.py

脚本只替换 custom.css 里两处 @wave-generated 标记之间的内容，其余一个字
都不动。找不到标记就直接报错退出 —— 那是 custom.css 被改坏了，不该猜。

不需要 Pillow，只用标准库。
"""
import math
import os
import re
import urllib.parse

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(SITE, "source", "css", "custom.css")

# —— 波形几何 ——
# TILE_H 只是瓦片的内部坐标系，最终渲染多高由 CSS 的 --wave-h 决定
# （background-size 的高度给了 100%，所以瓦片是被纵向拉伸的）。
TILE_H = 48

# 两张瓦片，一层一张，都是 TILE_W 宽。
#
# 每条曲线是**两条正弦叠加**，不是一条：周期缩短到 300px 上下之后，单纯
# 一条正弦的重复感会很扎眼（一屏能看见四五个一模一样的浪，像饼干模子）。
# 叠一条周期不同的进去，浪高就有了起伏，看着才像水面。
# 两条分量各自的周期都必须整除 TILE_W，否则瓦片首尾对不上，平铺时会出现
# 一个断口 —— 周期整除就自动保证了 y 值和斜率在接缝处连续。
#
# 振幅与基线这两个数不是随便定的，见下面 WATERLINE_MAX。
LAYERS = [
    # 远景层：周期长、振幅小、走得慢
    dict(name="back", waves=[(300, 4.5, 0), (200, 1.5, 90)], baseline=35),
    # 近景层：周期短、振幅大、相位错开，走得快
    dict(name="front", waves=[(240, 5.5, 90), (400, 2.5, 0)], baseline=40),
]

TILE_W = 1200  # 必须能整除 CSS keyframes 里两个平移量，改要一起改

# 浪尖最高能到哪（瓦片坐标下，y 越小越高）。水画得低是**功能性的**，
# 不是审美：文章页横幅底部 30px 是标题和元信息胶囊，渲染到 60px 带高时
# 浪尖不能高过 30/60*TILE_H = 24。各层的 baseline - Σamp 必须 ≥ 这个余量。
# 见 custom.css 第 18 节的说明。
WATERLINE_MAX = 29

# 色阶。填色本身是纯的 --wave-fill，透明度从浪尖到带底一路升到 1 ——
# 底部不透明是为了和下面内容区的底色接上，不然会留一道缝。
FILLS = {"light": "#F6F2F8", "dark": "#16141E"}
RAMP = [("0", ".10"), (".33", ".42"), (".66", ".74"), ("1", "1")]

# 采样步长（瓦片坐标 px）。最短的周期是 200，步长 10 就是每周期 20 个点，
# 弦和曲线的偏差远小于 1px。用贝塞尔能再省一半字符，但没必要为这点体积
# 换一段难读的代码。必须整除 TILE_W。
STEP = 10


def wave_path(layer):
    """叠加成正弦的和，再闭合成「水面以下」的填充区域。"""
    pts = []
    for i in range(TILE_W // STEP + 1):
        x = i * STEP
        y = layer["baseline"] + sum(
            amp * math.sin(2 * math.pi * x / period + math.radians(phase))
            for period, amp, phase in layer["waves"]
        )
        pts.append((x, y))
    d = "M%.1f,%.1f" % pts[0]
    d += "".join("L%.1f,%.1f" % p for p in pts[1:])
    return d + "L%d,%dL0,%dZ" % (TILE_W, TILE_H, TILE_H)


def tile(layer, fill):
    stops = "".join(
        '<stop offset="%s" stop-color="%s" stop-opacity="%s"/>' % (o, fill, a) for o, a in RAMP
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%(w)d" height="%(h)d" '
        'viewBox="0 0 %(w)d %(h)d" preserveAspectRatio="none">'
        '<defs><linearGradient id="w" x1="0" y1="0" x2="0" y2="%(h)d" gradientUnits="userSpaceOnUse">'
        '%(stops)s</linearGradient></defs><path d="%(d)s" fill="url(#w)"/></svg>'
        % dict(w=TILE_W, h=TILE_H, stops=stops, d=wave_path(layer))
    )
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")


def check():
    """把几何约束在生成前验一遍 —— 这些数改错了不会报错，只会让浪尖顶到
    文章页的标题上，或者让平铺接缝跳一下，都是要眯着眼睛才看得出来的。"""
    for layer in LAYERS:
        worst = layer["baseline"] - sum(a for _, a, _ in layer["waves"])
        if worst < WATERLINE_MAX:
            raise SystemExit(
                "%s 层浪尖最高到 %.1f，高过了 %d —— 会顶到文章页标题，调整基线或振幅"
                % (layer["name"], worst, WATERLINE_MAX)
            )
        for period, _, _ in layer["waves"]:
            if TILE_W % period:
                raise SystemExit(
                    "%s 层有周期 %d 除不尽瓦片宽 %d，平铺接缝会断" % (layer["name"], period, TILE_W)
                )
    if TILE_W % STEP:
        raise SystemExit("步长 %d 除不尽瓦片宽 %d" % (STEP, TILE_W))


def block(theme):
    fill = FILLS[theme]
    lines = ["  /* @wave-generated %s 由 tools/build_waves.py 生成，别手改 */" % theme]
    for layer in LAYERS:
        lines.append('  --wave-%s: url("%s");' % (layer["name"], tile(layer, fill)))
    lines.append("  /* @wave-generated-end */")
    return "\n".join(lines)


def main():
    check()

    with open(CSS, encoding="utf-8") as f:
        css = f.read()

    for theme in ("light", "dark"):
        pattern = re.compile(
            r"[ \t]*/\* @wave-generated %s .*?\*/.*?/\* @wave-generated-end \*/" % theme,
            re.S,
        )
        if not pattern.search(css):
            raise SystemExit("custom.css 里找不到 %s 的 @wave-generated 标记，放弃" % theme)
        css = pattern.sub(lambda m: block(theme), css, count=1)

    with open(CSS, "w", encoding="utf-8") as f:
        f.write(css)
    print("已写回 " + os.path.relpath(CSS, SITE))


if __name__ == "__main__":
    main()
