"""河南移动 IPTV 直播源自动同步脚本

从多个上游来源下载、解析、去重合并直播源，输出统一的 m3u 文件。
"""

import urllib.request
import urllib.error
import sys
import os
import time
from dataclasses import dataclass, field

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
        "name": "ning87/hnydzb",
        "url": "https://gitee.com/ning87/hnydzb/raw/master/hn.m3u",
        "format": "m3u",
    },
    {
        "name": "xisohi/CHINA-IPTV",
        "url": "https://chinaiptv.pages.dev/Unicast/henan/mobile.txt",
        "format": "txt",
    },
]

EPG_URL = "https://live.lizanyang.top/e.xml"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lists")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "merged.m3u")
LOGO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logos")

# 需要备份的 logo 远程域名（这些 logo 会下载到本地）
LOGO_REMOTE_DOMAINS = [
    "live.fanmingming.cn",
    "live.fanmingming.com",
    "live.lizanyang.top",
]

# 分组排序权重（越小越靠前）
GROUP_ORDER = {
    "4K超高清": 0,
    "央视": 1,
    "卫视": 2,
    "省内": 3,
    "河南": 3,
    "港澳": 4,
    "省台": 5,
    "数字": 6,
    "广播": 7,
    "春晚": 8,
}

# 分组名统一映射（按匹配优先级排列，每个模式只匹配一类）
GROUP_NORMALIZE = [
    (r"^4K", "4K超高清"),
    (r"^央视", "央视频道"),
    (r"^卫视", "卫视频道"),
    (r"^省内频道$", "河南频道"),
    (r"^河南地方$", "河南频道"),
    (r"^河南广播$", "河南广播"),
    (r"^河南$", "河南频道"),
    (r"^港澳", "港澳频道"),
    (r"^省台", "省台频道"),
    (r"^数字综合", "数字综合"),
    (r"^数字", "数字频道"),
    (r"广播", "广播"),
    (r"春晚", "历年春晚"),
]


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
    req = urllib.request.Request(url, headers={"User-Agent": "HN-CMCC-IPTV-Sync/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8")


# ========== 解析 ==========


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
            # 这是一个 URL 行
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

    # 提取属性
    ch.tvg_id = _extract_attr(extinf, "tvg-id")
    ch.tvg_name = _extract_attr(extinf, "tvg-name")
    ch.tvg_logo = _extract_attr(extinf, "tvg-logo")
    ch.group = _extract_attr(extinf, "group-title") or "其它"
    ch.catchup = _extract_attr(extinf, "catchup")
    ch.catchup_source = _extract_attr(extinf, "catchup-source")

    # 提取频道名（逗号后面的部分）
    comma_idx = extinf.rfind(",")
    if comma_idx >= 0:
        ch.name = extinf[comma_idx + 1 :].strip()
    if not ch.name:
        ch.name = ch.tvg_name

    return ch


def _extract_attr(line: str, attr: str) -> str:
    """从 EXTINF 行提取属性值"""
    import re

    pattern = rf'{attr}="([^"]*)"'
    m = re.search(pattern, line)
    if m:
        return m.group(1)
    # 尝试单引号
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
                ch = Channel(
                    name=name,
                    url=url,
                    group=current_group,
                    source=source_name,
                )
                channels.append(ch)

    return channels


# ========== 分组统一 ==========


def normalize_group(group: str) -> str:
    """将各种分组名统一为标准名"""
    import re

    for pattern, standard in GROUP_NORMALIZE:
        if re.search(pattern, group):
            return standard
    return group


# ========== 去重合并 ==========


def merge_channels(all_channels: list[Channel]) -> list[Channel]:
    """去重合并：按 频道名+URL 去重，同时统一分组名"""
    seen = set()
    merged = []

    for ch in all_channels:
        # 统一分组名
        ch.group = normalize_group(ch.group)
        key = (ch.name, ch.url)
        if key not in seen:
            seen.add(key)
            merged.append(ch)

    return merged


# ========== 排序 ==========


def group_sort_key(group: str) -> int:
    """获取分组排序权重"""
    for keyword, weight in GROUP_ORDER.items():
        if keyword in group:
            return weight
    return 99


def sort_channels(channels: list[Channel]) -> list[Channel]:
    """按分组和频道名排序"""
    return sorted(channels, key=lambda ch: (group_sort_key(ch.group), ch.group, ch.name))


# ========== Logo 备份 ==========


def backup_logos(channels: list[Channel]) -> dict[str, str]:
    """将远程 logo 替换为本地路径，本地没有的尝试下载"""
    from urllib.parse import urlparse

    mapping = {}
    local_hit = 0
    downloaded = 0
    failed = 0

    remote_logos = set()
    for ch in channels:
        if ch.tvg_logo:
            domain = urlparse(ch.tvg_logo).netloc
            if domain in LOGO_REMOTE_DOMAINS:
                remote_logos.add(ch.tvg_logo)

    if not remote_logos:
        return {}

    print(f"\n处理 Logo: 共 {len(remote_logos)} 个远程引用")

    for url in remote_logos:
        filename = os.path.basename(urlparse(url).path)
        local_path = os.path.join(LOGO_DIR, "tv", filename)
        rel_path = f"logos/tv/{filename}"

        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            mapping[url] = rel_path
            local_hit += 1
            continue

        # 本地没有，尝试下载
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HN-CMCC-IPTV-Sync/1.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read()
            with open(local_path, "wb") as f:
                f.write(data)
            mapping[url] = rel_path
            downloaded += 1
        except Exception:
            # 下载失败保留原始远程地址
            failed += 1

    print(f"  本地命中: {local_hit}, 新下载: {downloaded}, 失败: {failed}")
    return mapping


# ========== 输出 ==========


def write_m3u(channels: list[Channel], filepath: str):
    """写入 m3u 文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U url-tvg="{EPG_URL}"\n')

        current_group = ""
        for ch in channels:
            extinf_parts = [f'-1']

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

    print(f"已输出: {filepath} ({len(channels)} 个频道)")


# ========== 主流程 ==========


def main():
    print(f"开始同步 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    all_channels = []

    for src in SOURCES:
        print(f"\n下载: {src['name']}")
        print(f"  URL: {src['url']}")
        try:
            text = download_text(src["url"])
            print(f"  大小: {len(text)} 字符")

            if src["format"] == "m3u":
                channels = parse_m3u(text, src["name"])
            else:
                channels = parse_txt(text, src["name"])

            print(f"  解析: {len(channels)} 个频道")
            all_channels.extend(channels)

        except urllib.error.URLError as e:
            print(f"  下载失败: {e}")
        except Exception as e:
            print(f"  处理失败: {e}")

    print(f"\n{'=' * 50}")
    print(f"合并前总计: {len(all_channels)} 个频道")

    merged = merge_channels(all_channels)
    print(f"去重后: {len(merged)} 个频道")

    sorted_ch = sort_channels(merged)

    # 备份 logo 并替换为本地路径
    logo_map = backup_logos(sorted_ch)
    if logo_map:
        for ch in sorted_ch:
            if ch.tvg_logo in logo_map:
                ch.tvg_logo = logo_map[ch.tvg_logo]

    write_m3u(sorted_ch, OUTPUT_FILE)

    # 输出分组统计
    groups = {}
    for ch in sorted_ch:
        groups.setdefault(ch.group, []).append(ch)

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"\n分组统计:")
    for g in sorted(groups, key=group_sort_key):
        print(f"  {g}: {len(groups[g])} 个频道")


if __name__ == "__main__":
    main()
