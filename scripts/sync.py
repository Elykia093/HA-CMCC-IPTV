"""河南移动 IPTV 直播源自动同步脚本

以本地验证的直播源为底板，定期从上游检查新增频道，输出 m3u 和 txt 两种格式。
仅保留 http://iptv.cdn.ha.chinamobile.com/PLTV 格式的内网地址。
"""

import urllib.request
import urllib.error
import sys
import os
import time
import re
from dataclasses import dataclass
from urllib.parse import urlparse, quote
from pypinyin import lazy_pinyin

# ========== 路径配置 ==========

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_FILE = os.path.join(BASE_DIR, "河南移动直播源.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "lists")
OUTPUT_M3U = os.path.join(OUTPUT_DIR, "merged.m3u")
OUTPUT_TXT = os.path.join(OUTPUT_DIR, "merged.txt")
LOGO_DIR = os.path.join(BASE_DIR, "logos")

# ========== 上游来源配置 ==========

SOURCES = [
    {
        "name": "vnsu/HeNanCMCCIPTV",
        "url": "https://raw.githubusercontent.com/vnsu/HeNanCMCCIPTV/main/SU.m3u",
        "format": "m3u",
    },
    {
        "name": "lizanyang3/lizanyang3.github.io",
        "url": "https://raw.githubusercontent.com/lizanyang3/lizanyang3.github.io/main/hn.m3u",
        "format": "m3u",
    },
    {
        "name": "xisohi/CHINA-IPTV",
        "url": "https://chinaiptv.pages.dev/Unicast/henan/mobile.txt",
        "format": "txt",
    },
]

EPG_URL = "https://live.lizanyang.top/e.xml"

# 合法的 URL 前缀（仅保留河南移动内网单播地址）
VALID_URL_PREFIX = "http://iptv.cdn.ha.chinamobile.com/PLTV"

# 需要备份的 logo 远程域名
LOGO_REMOTE_DOMAINS = [
    "live.fanmingming.cn",
    "live.fanmingming.com",
    "live.lizanyang.top",
]

# 分组排序权重（越小越靠前）
GROUP_ORDER = {
    "央视频道": 0,
    "地方卫视": 1,
    "河南频道": 2,
    "河南地市": 3,
    "数字频道": 4,
    "其它": 99,
}

# 底板分组名 → 标准分组名
BASE_GROUP_MAP = {
    "中央-河南移动": "央视频道",
    "卫视-河南移动": "地方卫视",
    "省级-河南移动": "河南频道",
    "地方-河南移动": "河南地市",
    "数字-河南移动": "数字频道",
}

# 河南地市/县区 → 行政区划代码（用于排序）
CITY_CODE = {
    # 省辖市
    "郑州": 410100, "开封": 410200, "洛阳": 410300, "平顶山": 410400,
    "安阳": 410500, "鹤壁": 410600, "新乡": 410700, "焦作": 410800,
    "濮阳": 410900, "许昌": 411000, "漯河": 411100, "三门峡": 411200,
    "南阳": 411300, "商丘": 411400, "信阳": 411500, "周口": 411600,
    "驻马店": 411700,
    # 省直辖县级市
    "济源": 419001,
    # 郑州市辖
    "巩义": 410181, "荥阳": 410182, "新密": 410183, "新郑": 410184,
    "登封": 410185,
    # 开封市辖
    "祥符": 410212, "杞县": 410221, "兰考": 410225,
    # 洛阳市辖
    "孟津": 410308, "新安": 410323, "嵩县": 410325, "汝阳": 410326,
    "宜阳": 410327, "洛宁": 410328, "伊川": 410329, "偃师": 410381,
    # 平顶山市辖
    "舞钢": 410481, "宝丰": 410421, "叶县": 410422, "鲁山": 410423,
    "郏县": 410425,
    # 安阳市辖
    "林州": 410581, "滑县": 410526, "汤阴": 410523, "内黄": 410527,
    # 鹤壁市辖
    "浚县": 410621, "淇县": 410622,
    # 新乡市辖
    "卫辉": 410781, "辉县": 410782, "长垣": 410783,
    "新乡县": 410721, "获嘉": 410724, "原阳": 410725, "延津": 410726,
    "封丘": 410727,
    # 焦作市辖
    "沁阳": 410882, "孟州": 410883, "温县": 410825,
    # 濮阳市辖
    "华龙": 410902, "南乐": 410923, "清丰": 410922, "台前": 410927, "范县": 410926,
    # 许昌市辖
    "禹州": 411081, "襄城": 411025,
    # 漯河市辖
    "舞阳": 411121, "临颍": 411122,
    # 三门峡市辖
    "陕州": 411203, "义马": 411281, "灵宝": 411282, "渑池": 411221, "卢氏": 411224,
    # 南阳市辖
    "邓州": 411381, "方城": 411322, "镇平": 411324, "淅川": 411326,
    "唐河": 411328, "新野": 411329, "内乡": 411325, "社旗": 411327,
    "西峡": 411323, "桐柏": 411330, "南召": 411321,
    # 商丘市辖
    "永城": 411481, "夏邑": 411426, "虞城": 411425, "柘城": 411424,
    "宁陵": 411423, "民权": 411421, "睢县": 411422,
    # 信阳市辖
    "平桥": 411503, "浉河": 411502, "光山": 411522, "新县": 411523,
    "淮滨": 411527, "商城": 411524, "罗山": 411521, "潢川": 411526,
    "固始": 411525, "息县": 411528,
    # 周口市辖
    "项城": 411681, "西华": 411622, "沈丘": 411624, "郸城": 411625,
    "太康": 411627, "鹿邑": 411628, "扶沟": 411621, "商水": 411623,
    "淮阳": 411626,
    # 驻马店市辖
    "上蔡": 411722, "正阳": 411724, "泌阳": 411726, "遂平": 411728,
    "新蔡": 411729, "西平": 411721, "平舆": 411723, "汝南": 411727,
    "确山": 411725,
}


# ========== 数据结构 ==========


@dataclass
class Channel:
    name: str = ""
    url: str = ""
    group: str = "其它"
    tvg_id: str = ""
    tvg_name: str = ""
    tvg_logo: str = ""
    catchup: str = ""
    catchup_source: str = ""
    source: str = ""


# ========== 下载 ==========


def download_text(url: str, timeout: int = 30) -> str:
    """下载文本内容"""
    req = urllib.request.Request(url, headers={"User-Agent": "HA-CMCC-IPTV-Sync/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8")


# ========== 解析 ==========


def parse_base_txt(filepath: str) -> list[Channel]:
    """解析本地底板 TXT 文件"""
    channels = []
    current_group = "其它"

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if ",#genre#" in line:
                current_group = line.split(",")[0].strip()
                continue

            parts = line.split(",", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                url = parts[1].strip()
                # 修复双逗号等格式问题（如 "江苏卫视,,http://..."）
                while url.startswith(","):
                    url = url[1:].strip()
                if url and url.startswith(VALID_URL_PREFIX):
                    ch = Channel(name=name, url=url, group=current_group, source="底板")
                    channels.append(ch)

    return channels


def parse_m3u(text: str, source_name: str) -> list[Channel]:
    """解析 EXTM3U 格式"""
    channels = []
    lines = text.strip().split("\n")
    current_extinf = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF"):
            current_extinf = line
        elif line.startswith("#"):
            continue
        else:
            ch = _parse_extinf(current_extinf, source_name)
            ch.url = line
            channels.append(ch)
            current_extinf = ""

    return channels


def _parse_extinf(extinf: str, source_name: str) -> Channel:
    """解析 #EXTINF 行"""
    ch = Channel(source=source_name)
    if not extinf:
        return ch

    ch.tvg_id = _extract_attr(extinf, "tvg-id")
    ch.tvg_name = _extract_attr(extinf, "tvg-name")
    ch.tvg_logo = _extract_attr(extinf, "tvg-logo")
    ch.group = _extract_attr(extinf, "group-title") or "其它"
    ch.catchup = _extract_attr(extinf, "catchup")
    ch.catchup_source = _extract_attr(extinf, "catchup-source")

    comma_idx = extinf.rfind(",")
    if comma_idx >= 0:
        ch.name = extinf[comma_idx + 1:].strip()
    if not ch.name:
        ch.name = ch.tvg_name

    return ch


def _extract_attr(line: str, attr: str) -> str:
    """从 EXTINF 行提取属性值"""
    pattern = rf'{attr}="([^"]*)"'
    m = re.search(pattern, line)
    if m:
        return m.group(1)
    pattern = rf"{attr}='([^']*)'"
    m = re.search(pattern, line)
    if m:
        return m.group(1)
    return ""


def parse_txt(text: str, source_name: str) -> list[Channel]:
    """解析 TXT 格式（频道名,URL 或 分组名,#genre#）"""
    channels = []
    current_group = "其它"

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if ",#genre#" in line:
            current_group = line.split(",")[0].strip()
            continue

        parts = line.split(",", 1)
        if len(parts) == 2:
            name = parts[0].strip()
            url = parts[1].strip()
            if url and url.startswith("http"):
                ch = Channel(name=name, url=url, group=current_group, source=source_name)
                channels.append(ch)

    return channels


# ========== 分组统一 ==========


def normalize_base_group(group: str) -> str:
    """底板分组名 → 标准分组名"""
    if group in BASE_GROUP_MAP:
        return BASE_GROUP_MAP[group]
    return group


def normalize_upstream_group(group: str, name: str = "") -> str:
    """上游分组名 → 标准分组名，4K超高清按频道名路由"""
    # 4K超高清 分组不直接映射，按频道名路由
    if re.search(r"4K", group):
        return _route_by_name(name)

    rules = [
        (r"^央视", "央视频道"),
        (r"^卫视", "地方卫视"),
        (r"^省内频道$", "河南频道"),
        (r"^河南地方$", "河南地市"),
        (r"^河南广播$", "河南频道"),
        (r"^河南$", "河南频道"),
        (r"^港澳", "地方卫视"),
        (r"^省台", "河南频道"),
        (r"^数字综合", "数字频道"),
        (r"^数字", "数字频道"),
        (r"广播", "数字频道"),
        (r"春晚", "数字频道"),
    ]
    for pattern, standard in rules:
        if re.search(pattern, group):
            return standard
    return group


def _route_by_name(name: str) -> str:
    """根据频道名判断所属分类（用于 4K 等混合分组路由）"""
    if re.search(r"CCTV|CGTN|CETV", name, re.IGNORECASE):
        return "央视频道"
    if re.search(r"卫视|兵团|三沙|康巴|延边|厦门|山东教育", name):
        return "地方卫视"
    if re.search(r"河南|大象|睛彩|健康河南|大美河南", name):
        return "河南频道"
    return "数字频道"




# ========== 合并逻辑 ==========


def merge_channels(base_channels: list[Channel], upstream_channels: list[Channel]) -> tuple[list[Channel], int]:
    """
    以底板为基准，合并上游新增频道。

    1. 底板频道全部保留，标准化分组名
    2. 从上游构建元数据映射（频道名 → logo/tvg_id），丰富底板频道
    3. 上游中 URL 不在底板的视为新增频道
    """
    # 收集底板所有 URL
    base_urls = {ch.url for ch in base_channels}

    # 从上游构建元数据映射（频道名 → metadata）
    # 同名频道取第一个有 logo 的
    # 同时用归一化名称建映射，确保底板归一化后也能命中
    metadata_map: dict[str, dict] = {}
    for ch in upstream_channels:
        for key in (ch.name, _normalize_channel_name(ch.name)):
            if key not in metadata_map:
                metadata_map[key] = {
                    "tvg_id": ch.tvg_id,
                    "tvg_name": ch.tvg_name,
                    "tvg_logo": ch.tvg_logo,
                    "catchup": ch.catchup,
                    "catchup_source": ch.catchup_source,
                }
            elif not metadata_map[key].get("tvg_logo") and ch.tvg_logo:
                metadata_map[key]["tvg_logo"] = ch.tvg_logo

    # 丰富底板频道的元数据
    for ch in base_channels:
        ch.group = normalize_base_group(ch.group)
        ch.name = _normalize_channel_name(ch.name)
        if ch.name in metadata_map:
            meta = metadata_map[ch.name]
            if not ch.tvg_id and meta["tvg_id"]:
                ch.tvg_id = meta["tvg_id"]
            if not ch.tvg_name and meta["tvg_name"]:
                ch.tvg_name = meta["tvg_name"]
            if not ch.tvg_logo and meta["tvg_logo"]:
                ch.tvg_logo = meta["tvg_logo"]
            if not ch.catchup and meta["catchup"]:
                ch.catchup = meta["catchup"]
            if not ch.catchup_source and meta["catchup_source"]:
                ch.catchup_source = meta["catchup_source"]

    # 找出上游新增频道（URL 不在底板中）
    new_channels = []
    seen_new = set()
    for ch in upstream_channels:
        if ch.url not in base_urls:
            key = (ch.name, ch.url)
            if key not in seen_new:
                seen_new.add(key)
                ch.group = normalize_upstream_group(ch.group, ch.name)
                ch.name = _normalize_channel_name(ch.name)
                new_channels.append(ch)

    # 合并后再次去重（名称归一化后可能产生重复）
    result = base_channels + new_channels
    seen_final = set()
    used_urls = set()
    deduped = []
    for ch in result:
        key = (ch.name, ch.url)
        if key not in seen_final and ch.url not in used_urls:
            seen_final.add(key)
            used_urls.add(ch.url)
            deduped.append(ch)

    return deduped, len(new_channels)


# ========== 排序 ==========


def group_sort_key(group: str) -> int:
    """获取分组排序权重"""
    for keyword, weight in GROUP_ORDER.items():
        if keyword in group:
            return weight
    return 99


def _get_city_sort_key(name: str) -> tuple:
    """从频道名提取地区排序键（区划代码, 子频道名）
    如 '郑州新闻综合' → (410100, '新闻综合')
    如 '巩义' → (410181, '')
    """
    for city_name, code in sorted(CITY_CODE.items(), key=lambda x: -len(x[0])):
        if name.startswith(city_name):
            sub = name[len(city_name):]
            return (code, sub)
    return (999999, name)


def _channel_sort_key(ch: Channel) -> tuple:
    """频道排序键：分组 → 分组内排序规则"""
    group_key = group_sort_key(ch.group)
    if ch.group == "河南地市":
        city_key = _get_city_sort_key(ch.name)
        return (group_key, ch.group, city_key, ch.name)
    return (group_key, ch.group, _normalize_for_sort(ch.name), ch.name)


def _normalize_for_sort(name: str) -> str:
    """归一化频道名用于排序：拼音 → 去分隔符、去后缀 → 数字补零
    CCTV1 → CCTV001, CCTV10 → CCTV010
    东方卫视 → dongfangweishi, 三沙卫视 → sanshaweishi
    4K 映射为高序号，排在编号频道之后
    """
    n = name
    # 4K 映射为高序号，排在编号频道之后
    n = re.sub(r"4K", "99", n)
    # 数字补零：CCTV1 → CCTV001, CCTV10 → CCTV010
    n = re.sub(r"(\d+)", lambda m: m.group(1).zfill(3), n)
    # 去除中文/英文连字符和空格
    n = n.replace("-", "").replace("—", "").replace(" ", "")
    # 去除常见后缀
    n = re.sub(r"超高清$", "", n)
    # 中文转拼音（用于地方卫视、数字频道等按拼音排序）
    n = "".join(lazy_pinyin(n))
    return n.lower()


def _normalize_channel_name(name: str) -> str:
    """统一频道名变体：CCTV4K / CCTV-4K / CCTV-4K超高清 → CCTV-4K"""
    # CCTV 4K 变体统一
    if re.match(r"^CCTV[-]?4K", name, re.IGNORECASE):
        return "CCTV-4K"
    return name


def sort_channels(channels: list[Channel]) -> list[Channel]:
    """按分组和频道名排序（近似名聚合）"""
    return sorted(channels, key=_channel_sort_key)


# ========== Logo 备份 ==========


def backup_logos(channels: list[Channel]) -> dict[tuple[str, str], str]:
    """将远程 logo 下载到本地，每个频道独立文件，文件名 = 频道名.png
    返回映射：(远程 URL, 频道名) → 本地路径 (logos/tv/频道名.png)
    """
    mapping = {}
    local_hit = 0
    downloaded = 0
    failed = 0

    # 收集所有需要备份的 (url, name) 对
    tasks = []
    for ch in channels:
        if ch.tvg_logo:
            domain = urlparse(ch.tvg_logo).netloc
            if domain in LOGO_REMOTE_DOMAINS:
                tasks.append((ch.tvg_logo, ch.name))

    if not tasks:
        return {}

    # 去重
    seen = set()
    unique_tasks = []
    for url, name in tasks:
        if (url, name) not in seen:
            seen.add((url, name))
            unique_tasks.append((url, name))

    print(f"\n处理 Logo: 共 {len(unique_tasks)} 个频道需要备份")

    # 先按 URL 下载到临时缓存（避免同一 URL 多次下载）
    url_cache: dict[str, bytes] = {}

    for url, name in unique_tasks:
        filename = f"{name}.png"
        local_path = os.path.join(LOGO_DIR, "tv", filename)
        rel_path = f"logos/tv/{filename}"
        mapping[(url, name)] = rel_path

        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            local_hit += 1
            continue

        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # 从缓存或下载获取数据
        if url in url_cache:
            data = url_cache[url]
        else:
            try:
                parsed = urlparse(url)
                safe_url = parsed._replace(path=quote(parsed.path)).geturl()
                req = urllib.request.Request(safe_url, headers={"User-Agent": "HA-CMCC-IPTV-Sync/1.0"})
                resp = urllib.request.urlopen(req, timeout=15)
                data = resp.read()
                url_cache[url] = data
            except Exception:
                failed += 1
                continue

        with open(local_path, "wb") as f:
            f.write(data)
        downloaded += 1

    print(f"  本地命中: {local_hit}, 新下载: {downloaded}, 失败: {failed}")
    return mapping


# ========== 输出 ==========


def write_m3u(channels: list[Channel], filepath: str):
    """写入 m3u 文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U url-tvg="{EPG_URL}"\n')

        for ch in channels:
            extinf_parts = ["-1"]

            if ch.tvg_id:
                extinf_parts.append(f'tvg-id="{ch.tvg_id}"')
            if ch.tvg_name:
                extinf_parts.append(f'tvg-name="{ch.tvg_name}"')
            if ch.tvg_logo:
                extinf_parts.append(f'tvg-logo="{ch.tvg_logo}"')

            extinf_parts.append(f'group-title="{ch.group}"')

            if ch.catchup:
                extinf_parts.append(f'catchup="{ch.catchup}"')
            if ch.catchup_source:
                extinf_parts.append(f'catchup-source="{ch.catchup_source}"')

            extinf = " ".join(extinf_parts)
            f.write(f"#EXTINF:{extinf},{ch.name}\n")
            f.write(f"{ch.url}\n")

    print(f"已输出 M3U: {filepath} ({len(channels)} 个频道)")


def write_txt(channels: list[Channel], filepath: str):
    """写入 txt 文件（分组名,#genre# 格式）"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # 按分组组织
    groups: dict[str, list[Channel]] = {}
    for ch in channels:
        groups.setdefault(ch.group, []).append(ch)

    with open(filepath, "w", encoding="utf-8") as f:
        for group in sorted(groups, key=group_sort_key):
            f.write(f"{group},#genre#\n")
            for ch in groups[group]:
                f.write(f"{ch.name},{ch.url}\n")

    total = sum(len(v) for v in groups.values())
    print(f"已输出 TXT: {filepath} ({total} 个频道, {len(groups)} 个分组)")


# ========== 测活 ==========


def check_alive(channels: list[Channel], timeout: int = 5) -> list[Channel]:
    """逐个检测频道是否存活（302/200=存活），移除失效频道"""
    alive = []
    dead = []
    total = len(channels)

    for i, ch in enumerate(channels, 1):
        status = _probe_url(ch.url, timeout)
        if status == "alive":
            alive.append(ch)
        else:
            dead.append(ch)
        # 进度条
        pct = i * 100 // total
        bar = "█" * (pct // 2) + "░" * (50 - pct // 2)
        sys.stdout.write(f"\r  检测进度: [{bar}] {i}/{total} ({pct}%) 存活:{len(alive)} 失效:{len(dead)}")
        sys.stdout.flush()

    print()  # 换行

    if dead:
        print(f"\n失效频道 ({len(dead)} 个):")
        for ch in dead:
            print(f"  ❌ {ch.name} → {ch.url}")

    return alive


def _probe_url(url: str, timeout: int) -> str:
    """探测单个 URL 是否存活"""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "HA-CMCC-IPTV-Sync/1.0"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return "alive"
    except urllib.error.HTTPError as e:
        # 302 重定向也视为存活（IPTV 源常见行为）
        if e.code in (301, 302, 303, 307, 308):
            return "alive"
        return f"dead:{e.code}"
    except Exception:
        return "dead:timeout"


# ========== 主流程 ==========


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    do_check = "--check" in sys.argv

    print(f"开始同步 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 1. 读取本地底板
    print("\n读取本地底板: 河南移动直播源.txt")
    if not os.path.exists(BASE_FILE):
        print(f"错误: 底板文件不存在 {BASE_FILE}")
        sys.exit(1)

    base_channels = parse_base_txt(BASE_FILE)
    print(f"  底板频道: {len(base_channels)} 个")

    # 2. 下载上游并提取合法频道
    all_upstream = []
    for src in SOURCES:
        print(f"\n下载上游: {src['name']}")
        print(f"  URL: {src['url']}")
        try:
            text = download_text(src["url"])
            print(f"  大小: {len(text)} 字符")

            if src["format"] == "m3u":
                channels = parse_m3u(text, src["name"])
            else:
                channels = parse_txt(text, src["name"])

            # 过滤：仅保留合法 URL
            valid = [ch for ch in channels if ch.url.startswith(VALID_URL_PREFIX)]
            skipped = len(channels) - len(valid)
            print(f"  解析: {len(channels)} 个频道, 合法内网: {len(valid)} 个, 跳过: {skipped} 个")
            all_upstream.extend(valid)

        except urllib.error.URLError as e:
            print(f"  下载失败: {e}")
        except Exception as e:
            print(f"  处理失败: {e}")

    print(f"\n{'=' * 50}")
    print(f"底板频道: {len(base_channels)} 个")
    print(f"上游合计: {len(all_upstream)} 个（仅合法内网地址）")

    # 3. 合并：底板 + 上游新增
    merged, new_count = merge_channels(base_channels, all_upstream)
    print(f"合并结果: {len(merged)} 个频道（含上游新增 {new_count} 个）")

    # 4. 排序
    sorted_ch = sort_channels(merged)

    # 5. 测活（仅 --check 模式）
    if do_check:
        print(f"\n开始测活检测（{len(sorted_ch)} 个频道）...")
        before = len(sorted_ch)
        sorted_ch = check_alive(sorted_ch)
        removed = before - len(sorted_ch)
        print(f"测活完成: 存活 {len(sorted_ch)} 个, 移除 {removed} 个失效频道")

    # 6. 备份 logo 并替换为本地路径
    logo_map = backup_logos(sorted_ch)
    if logo_map:
        for ch in sorted_ch:
            if ch.tvg_logo in logo_map:
                ch.tvg_logo = logo_map[ch.tvg_logo]

    # 7. 输出 m3u 和 txt
    write_m3u(sorted_ch, OUTPUT_M3U)
    write_txt(sorted_ch, OUTPUT_TXT)

    # 8. 分组统计
    base_urls = {ch.url for ch in base_channels}
    groups: dict[str, list[Channel]] = {}
    for ch in sorted_ch:
        groups.setdefault(ch.group, []).append(ch)

    print(f"\n分组统计:")
    for g in sorted(groups, key=group_sort_key):
        new_in_group = sum(1 for ch in groups[g] if ch.url not in base_urls)
        marker = f" (+{new_in_group} 新增)" if new_in_group > 0 else ""
        print(f"  {g}: {len(groups[g])} 个频道{marker}")


if __name__ == "__main__":
    main()
