"""河南移动 IPTV 直播源同步脚本

检测上游仓库是否有更新，如有则同步到新文件供人工审核合并。
主文件 iptv.txt/iptv.m3u 作为底板，不会被自动覆盖。
"""

import urllib.request
import urllib.error
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass

# ========== 路径配置 ==========

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPTV_TXT = os.path.join(BASE_DIR, "lists", "iptv.txt")
IPTV_M3U = os.path.join(BASE_DIR, "lists", "iptv.m3u")
SYNC_DIR = os.path.join(BASE_DIR, "sync")
PENDING_TXT = os.path.join(SYNC_DIR, "pending.txt")
PENDING_M3U = os.path.join(SYNC_DIR, "pending.m3u")
PENDING_README = os.path.join(SYNC_DIR, "README.md")
STATE_FILE = os.path.join(BASE_DIR, ".sync_state.json")
LOGO_BASE = "https://gh-proxy.com/https://raw.githubusercontent.com/Elykia093/HA-CMCC-IPTV/main/logos"

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
VALID_URL_PREFIX = "http://iptv.cdn.ha.chinamobile.com/PLTV"

# ========== 数据结构 ==========


@dataclass
class Channel:
    name: str = ""
    url: str = ""
    group: str = "其它"


# ========== 下载 ==========


def download_text(url: str, timeout: int = 30) -> str:
    """下载文本内容"""
    req = urllib.request.Request(url, headers={"User-Agent": "HA-CMCC-IPTV-Sync/1.0"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode("utf-8")


def compute_hash(text: str) -> str:
    """计算文本 MD5 哈希"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ========== 状态管理 ==========


def load_state() -> dict:
    """加载上次同步状态"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """保存同步状态"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ========== 解析 ==========


def parse_iptv_txt(filepath: str) -> list[Channel]:
    """解析本地 iptv.txt 底板"""
    channels = []
    current_group = "其它"
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.endswith(",#genre#"):
                current_group = line.split(",")[0]
                continue
            parts = line.split(",", 1)
            if len(parts) == 2:
                name, url = parts[0], parts[1]
                if url.startswith(VALID_URL_PREFIX):
                    channels.append(Channel(name=name, url=url, group=current_group))
    return channels


def parse_m3u(text: str) -> list[Channel]:
    """解析 M3U 格式"""
    channels = []
    lines = text.strip().split("\n")
    current_group = "其它"
    current_name = ""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#EXTM3U"):
            continue
        if line.startswith("#EXTINF"):
            # 提取 group-title
            m = re.search(r'group-title="([^"]*)"', line)
            if m:
                current_group = m.group(1)
            # 提取频道名（逗号后）
            comma = line.rfind(",")
            if comma >= 0:
                current_name = line[comma + 1 :].strip()
        elif line.startswith("http"):
            if current_name and line.startswith(VALID_URL_PREFIX):
                channels.append(Channel(name=current_name, url=line, group=current_group))
            current_name = ""
    return channels


def parse_txt(text: str) -> list[Channel]:
    """解析 TXT 格式"""
    channels = []
    current_group = "其它"
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.endswith(",#genre#"):
            current_group = line.split(",")[0]
            continue
        parts = line.split(",", 1)
        if len(parts) == 2:
            name, url = parts[0], parts[1]
            if url.startswith(VALID_URL_PREFIX):
                channels.append(Channel(name=name, url=url, group=current_group))
    return channels


# ========== 合并逻辑 ==========


def merge_new(base: list[Channel], upstream: list[Channel]) -> list[Channel]:
    """
    找出上游中 URL 不在底板的新增频道
    返回：新增频道列表（带分组信息）
    """
    base_urls = {ch.url for ch in base}
    seen = set()
    new_channels = []

    for ch in upstream:
        if ch.url not in base_urls and ch.url not in seen:
            seen.add(ch.url)
            new_channels.append(ch)

    return new_channels


# ========== 输出 ==========


def write_txt(channels: list[Channel], filepath: str):
    """写入 TXT 文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    groups: dict[str, list[Channel]] = {}
    for ch in channels:
        groups.setdefault(ch.group, []).append(ch)

    with open(filepath, "w", encoding="utf-8") as f:
        for group in sorted(groups.keys()):
            f.write(f"{group},#genre#\n")
            for ch in groups[group]:
                f.write(f"{ch.name},{ch.url}\n")


def write_m3u(channels: list[Channel], filepath: str):
    """写入 M3U 文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    groups: dict[str, list[Channel]] = {}
    for ch in channels:
        groups.setdefault(ch.group, []).append(ch)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U url-tvg="{EPG_URL}"\n')
        for group in sorted(groups.keys()):
            for ch in groups[group]:
                f.write(
                    f'#EXTINF:-1 tvg-name="{ch.name}" tvg-logo="{LOGO_BASE}/{ch.name}.png" group-title="{group}",{ch.name}\n'
                )
                f.write(f"{ch.url}\n")


# ========== 主流程 ==========


def write_sync_readme(new_channels: list[Channel], updated_sources: list[str]):
    """写入 sync/README.md，说明本次新增内容"""
    # 按来源统计
    groups: dict[str, list[Channel]] = {}
    for ch in new_channels:
        groups.setdefault(ch.group, []).append(ch)

    with open(PENDING_README, "w", encoding="utf-8") as f:
        f.write("# 待审核新增频道\n\n")
        f.write(f"检测时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"有更新的上游：{', '.join(updated_sources)}\n\n")
        f.write(f"新增频道共 **{len(new_channels)}** 个：\n\n")
        for group in sorted(groups.keys()):
            f.write(f"## {group}（{len(groups[group])} 个）\n\n")
            for ch in groups[group]:
                f.write(f"- {ch.name}\n")
            f.write("\n")
        f.write("---\n\n")
        f.write("审核完成后：\n")
        f.write("1. 将需要的频道从 `pending.txt` 合并到 `lists/iptv.txt`（注意分组顺序）\n")
        f.write("2. 运行 m3u 生成脚本或手动生成 `lists/iptv.m3u`\n")
        f.write("3. 补充对应台标到 `logos/`\n")
        f.write("4. 删除 `sync/` 目录下的 pending 文件\n")


def main():
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    force = "--force" in sys.argv

    print(f"上游更新检测 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 1. 加载上次状态
    state = load_state()
    updated_sources = []

    # 2. 检查每个上游是否有更新
    all_upstream = []
    for src in SOURCES:
        print(f"\n检查: {src['name']}")
        try:
            text = download_text(src["url"])
            current_hash = compute_hash(text)
            last_hash = state.get(src["name"], "")

            if current_hash != last_hash:
                print(f"  ⚠️  有更新（哈希变化）")
                state[src["name"]] = current_hash
                updated_sources.append(src["name"])
            else:
                print(f"  ✅ 无变化")

            # 解析
            if src["format"] == "m3u":
                channels = parse_m3u(text)
            else:
                channels = parse_txt(text)

            valid = [ch for ch in channels if ch.url.startswith(VALID_URL_PREFIX)]
            print(f"  有效频道: {len(valid)} 个")
            all_upstream.extend(valid)

        except Exception as e:
            print(f"  ❌ 获取失败: {e}")

    # 3. 如果没有更新且非强制模式，直接退出
    if not updated_sources and not force:
        print(f"\n{'=' * 50}")
        print("无上游更新，无需同步")
        return

    # 4. 读取本地底板
    print(f"\n{'=' * 50}")
    print("读取本地底板: lists/iptv.txt")
    base_channels = parse_iptv_txt(IPTV_TXT)
    base_url_set = {ch.url for ch in base_channels}
    print(f"  底板频道: {len(base_channels)} 个，URL: {len(base_url_set)} 条")

    # 5. 去重后统计上游
    upstream_url_set = set()
    deduped_upstream = []
    for ch in all_upstream:
        if ch.url not in upstream_url_set:
            upstream_url_set.add(ch.url)
            deduped_upstream.append(ch)
    print(f"  上游频道（去重）: {len(deduped_upstream)} 个")

    # 6. 找出新增频道（URL 不在底板中）
    new_channels = []
    seen = set()
    for ch in deduped_upstream:
        if ch.url not in base_url_set and ch.url not in seen:
            seen.add(ch.url)
            new_channels.append(ch)

    # 7. 写入 sync 目录
    os.makedirs(SYNC_DIR, exist_ok=True)

    if new_channels:
        # 按分组统计
        groups: dict[str, list[Channel]] = {}
        for ch in new_channels:
            groups.setdefault(ch.group, []).append(ch)

        print(f"\n新增频道: {len(new_channels)} 个")
        for g in sorted(groups.keys()):
            print(f"  {g}: {len(groups[g])} 个")
            for ch in groups[g]:
                print(f"    - {ch.name}")

        write_txt(new_channels, PENDING_TXT)
        write_m3u(new_channels, PENDING_M3U)
        write_sync_readme(new_channels, updated_sources)

        print(f"\n已写入 sync/:")
        print(f"  - pending.txt（待合并频道）")
        print(f"  - pending.m3u")
        print(f"  - README.md（审核说明）")
        print(f"\n请审核后合并到 lists/iptv.txt，然后删除 sync/ 下的 pending 文件")
    else:
        print("\n上游虽有更新，但无新增频道（URL 均已在底板中）")
        # 清理旧的 pending 文件
        for f in [PENDING_TXT, PENDING_M3U, PENDING_README]:
            if os.path.exists(f):
                os.remove(f)
                print(f"  已删除: {os.path.basename(f)}")

    # 8. 保存状态
    save_state(state)
    print(f"\n状态已保存: {STATE_FILE}")


if __name__ == "__main__":
    main()
