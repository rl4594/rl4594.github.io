"""
从壁纸派生出站点的封面图和 favicon，并把头像裁成正方形。

source/img/covers/*.webp、source/img/favicon.png 和 source/img/avatar.webp
都是这个脚本生成的，不是手工裁的。换了壁纸或换了头像原图之后重跑一次：

    python tools/build_assets.py

依赖 Pillow（`pip install pillow`）。脚本会原地覆盖自己的产物。

原图放在 _originals/，不放项目根目录 —— 那个目录只装「用户给的原始素材」，
不进版本库也不用被 Hexo 看到。

这个文件放在 tools/ 而不是 source/ 是有意的：source/ 下的东西会被
Hexo 原样发布到站点上，一个 .md 还会被渲染成页面。
"""
import os
from PIL import Image, ImageFilter

# 相对脚本位置定位站点根目录，这样从任何工作目录跑都行
SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(SITE, "source", "img", "wallpaper.webp")
COVER_DIR = os.path.join(SITE, "source", "img", "covers")
AVATAR_SRC = os.path.join(SITE, "_originals", "avatar.png")

COVER_W, COVER_H = 1200, 750

# —— 头像 ——
# 裁切框是原图坐标下的正方形。660 见方，以头部为中心，四周各留一点。
# 原图高只有 720，所以纵向没有多少腾挪空间 —— 直接取满高（0..720）会让兜帽
# 顶到圆形裁切的边上，看着像被切了；收到 660 并下移 20，头顶才留出余量。
# 显示尺寸是 110px，这里给到 240 让高密度屏也够用。
AVATAR_BOX = (305, 20, 965, 680)
AVATAR_SIZE = 240

# 封面裁切框，坐标直接写在源图的 2560x1440 空间里。
# 每框都是 1200x750（16:10），正好是封面渲染的比例，不用再缩放拉伸。
# 五个区域分别取夜色、银河、暮云、花海铁轨、落日桥墩，凑成一组同色系的封面。
REGIONS = [
    ("night-sky",    60,   30, 1260,  780),
    ("star-river",  900,  100, 2100,  850),
    ("dusk-clouds",   0,  380, 1200, 1130),
    ("petal-rail",  450,  600, 1650, 1350),
    ("sunset-span", 1360,  560, 2560, 1310),
]


def build_covers(img):
    os.makedirs(COVER_DIR, exist_ok=True)
    W, H = img.size
    for name, x1, y1, x2, y2 in REGIONS:
        if (x2 - x1, y2 - y1) != (COVER_W, COVER_H):
            raise ValueError(f"{name} 的裁切框不是 {COVER_W}x{COVER_H}")
        if x2 > W or y2 > H:
            raise ValueError(f"{name} 的裁切框超出了源图 {W}x{H}")
        path = os.path.join(COVER_DIR, f"{name}.webp")
        img.crop((x1, y1, x2, y2)).save(path, "WEBP", quality=84, method=6)
        print(f"  cover  {name}.webp  {os.path.getsize(path) // 1024} KB")


def build_favicon(img):
    """定位落日本身取景，而不是写死坐标。

    做法：把右下象限去色、大幅高斯模糊（把飘落的花瓣和电线糊掉），
    再降采样，剩下最亮的那块就是太阳。
    """
    W, H = img.size
    q = img.crop((W // 2, H // 2, W, H)).convert("L")
    q = q.filter(ImageFilter.GaussianBlur(24))
    small = q.resize((q.width // 8, q.height // 8), Image.LANCZOS)
    px = small.load()
    bx = by = 0
    best = -1.0
    for y in range(small.height):
        for x in range(small.width):
            if px[x, y] > best:
                best, bx, by = px[x, y], x, y
    cx, cy = W // 2 + bx * 8, H // 2 + by * 8

    # 取景中心略微下移：桥面横在画面上部，小尺寸下会变成一道很重的黑边
    cy += 70

    side = 420
    # 正方形取景框要整体夹住，不能各边独立钳位 —— 那样太阳靠近边缘时会被压扁
    x1 = min(max(0, cx - side // 2), W - side)
    y1 = min(max(0, cy - side // 2), H - side)
    sun = img.crop((x1, y1, x1 + side, y1 + side))
    assert sun.size == (side, side), sun.size

    # 只出一个文件：PWA 没开，不会有东西去请求 apple-touch-icon
    path = os.path.join(SITE, "source", "img", "favicon.png")
    sun.resize((128, 128), Image.LANCZOS).save(path, "PNG", optimize=True)
    print(f"  favicon.png  128x128  {os.path.getsize(path) // 1024} KB  (太阳在 {cx},{cy})")


def build_avatar():
    """把头像原图裁成正方形并缩小。

    原图是 1280x720 的横图，左右各有一条模糊边 —— 那是给 16:9 凑画幅用的，
    不属于画面主体。用边缘能量（FIND_EDGES 后逐列求均值）量过：模糊边几乎没有
    高频细节（能量 0.3~0.6），清晰部分从 x≈280 开始，所以裁切框的左边界放在
    它内侧。主题把头像渲染成 110px 的圆形、object-fit: cover，也就是取中心
    正方形：与其让每页去下载并缩放一张 1280px 的图，不如这里裁好。

    改了裁切位置就重跑一次脚本，别直接改 source/img/avatar.webp —— 会被覆盖。
    """
    img = Image.open(AVATAR_SRC).convert("RGB")
    x1, y1, x2, y2 = AVATAR_BOX
    if (x2 - x1) != (y2 - y1):
        raise ValueError(f"头像裁切框不是正方形: {AVATAR_BOX}")
    if x2 > img.size[0] or y2 > img.size[1]:
        raise ValueError(f"头像裁切框超出了原图 {img.size}")

    path = os.path.join(SITE, "source", "img", "avatar.webp")
    img.crop(AVATAR_BOX).resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS).save(
        path, "WEBP", quality=88, method=6
    )
    print(f"  avatar.webp  {AVATAR_SIZE}x{AVATAR_SIZE}  {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    img = Image.open(SRC).convert("RGB")
    print(f"源图: {SRC}  {img.size[0]}x{img.size[1]}")
    build_covers(img)
    build_favicon(img)
    build_avatar()
    print("完成。")
