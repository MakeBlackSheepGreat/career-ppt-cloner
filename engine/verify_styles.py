import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES = os.path.join(ROOT, 'styles')

if not os.path.isdir(STYLES):
    print('没有 styles 目录。先用 build_style.py 从参考 pptx 抽一套风格包。')
    sys.exit(1)

problems = []
for name in sorted(os.listdir(STYLES)):
    d = os.path.join(STYLES, name)
    if not os.path.isdir(d):
        continue
    need = ['pack.pptx', 'slots.json', 'catalog.md', 'meta.json', 'thumbs']
    missing = [f for f in need if not os.path.exists(os.path.join(d, f))]
    if missing:
        problems.append('%s 缺少 %s' % (name, missing))
        continue
    meta = json.load(open(os.path.join(d, 'meta.json'), encoding='utf-8'))
    slots = json.load(open(os.path.join(d, 'slots.json'), encoding='utf-8'))
    thumbs = len([f for f in os.listdir(os.path.join(d, 'thumbs')) if f.endswith('.png')])
    pages = len(slots['pages'])
    text_slots = sum(len([s for s in p['slots'] if s['role'] != 'glyph']) for p in slots['pages'])
    photos = sum(len(p.get('photos', [])) for p in slots['pages'])
    titled = sum(len(p.get('title_slots', [])) for p in slots['pages'])
    # 封面与章节页的主标题如果原本是图片印上去的，换内容后旧标题仍在图上，这套包
    # 就只能用于内页复刻，不能用于封面。
    covers = [p for p in slots["pages"] if p["kind"] in ("cover", "section")]
    image_titles = sum(len(p.get("title_slots", [])) for p in covers)
    usable = "全篇可用" if image_titles == 0 else "仅内页可用（封面主标题是图）"
    print('%-16s %-6s %2d页 %2d缩略图 文本槽%3d 照片槽%2d 标题槽%2d %5.1fMB  %s' % (
        name, meta.get('tier'), pages, thumbs, text_slots, photos, titled,
        os.path.getsize(os.path.join(d, 'pack.pptx')) / 1e6, usable))
    if thumbs != pages:
        problems.append('%s 缩略图 %d 与页数 %d 不符' % (name, thumbs, pages))

print()
if problems:
    print('问题：')
    for p in problems:
        print('  -', p)
    sys.exit(1)
print('全部风格包结构完整')
