# 河南移动 IPTV 直播源

> 自动从多个上游同步、去重、合并，生成统一直播源。
> 走的是运营商内网 HTTP 单播，不依赖机顶盒，有河南移动宽带就能看。
>
> **测试环境**：郑州移动宽带 ✅

---

## 📺 订阅地址

| 类型 | 地址 | 说明 |
|:---|:---|:---|
| **直播源（M3U）** | `https://raw.githubusercontent.com/Elykia093/HA-CMCC-IPTV/main/lists/merged.m3u` | 合并底板+上游，去重输出 |
| **直播源（TXT）** | `https://raw.githubusercontent.com/Elykia093/HA-CMCC-IPTV/main/lists/merged.txt` | 同上，TXT 格式 |
| **直播源（M3U 加速）** | `https://gh-proxy.com/https://raw.githubusercontent.com/Elykia093/HA-CMCC-IPTV/main/lists/merged.m3u` | 国内 gh-proxy 加速 |
| **直播源（TXT 加速）** | `https://gh-proxy.com/https://raw.githubusercontent.com/Elykia093/HA-CMCC-IPTV/main/lists/merged.txt` | 国内 gh-proxy 加速 |
| **EPG 节目指南** | `https://live.lizanyang.top/e.xml` | 引用上游，不同步到本地 |

---

## 📋 包含频道

按 5 个分类整理：

| 分类 | 说明 |
|:---|:---|
| **央视频道** | CCTV 全系列（1-17）、CCTV-4K、CETV、CGTN |
| **地方卫视** | 各省卫视（含卫视 4K）、港澳频道 |
| **河南频道** | 河南省级频道（都市、民生、法制等） |
| **河南地市** | 河南各地市县级频道 |
| **数字频道** | 付费数字频道、专业频道 |

---

## 🎬 推荐播放器

| 平台 | 播放器 | 下载地址 |
|:---|:---|:---|
| Android TV | mytv-android | [GitHub Releases](https://github.com/yaoxieyoulei/mytv-android/releases) |
| Android TV | Tivimate | [官网下载](https://tivimates.com/download-apk-tivimate-iptv-player/) |
| PC | VLC | [videolan.org](https://www.videolan.org/vlc/) |
| PC | PotPlayer | [potplayer.daum.net](https://potplayer.daum.net/) |
| iOS / macOS | APTV | [App Store](https://apps.apple.com/cn/app/aptv/id1630403500) |

---

## 🔄 同步机制

- **频率**：每 15 天自动同步（每月 1 日、16 日）
- **方式**：以本地验证源为底板，GitHub Actions 自动拉取上游检查新增 → 名称统一 → 去重合并 → 排序输出
- **手动触发**：在仓库 Actions 页面点击 `Run workflow` 即可

### 上游来源

| 来源 | 平台 | 说明 |
|:---|:---|:---|
| [vnsu/HeNanCMCCIPTV](https://github.com/vnsu/HeNanCMCCIPTV) | GitHub | 多线路备选，台标+分组 |
| [lizanyang3/lizanyang3.github.io](https://github.com/lizanyang3/lizanyang3.github.io) | GitHub | 回看支持，自托管台标+EPG |
| [xisohi/CHINA-IPTV](https://github.com/xisohi/CHINA-IPTV) | GitHub / Cloudflare Pages | 全国 IPTV 汇总，河南单播+组播 |

### 仓库结构

```
.
├── lists/
│   ├── merged.m3u          # 合并后的直播源 M3U（自动生成）
│   └── merged.txt          # 合并后的直播源 TXT（自动生成）
├── logos/                  # 台标备份（从上游同步）
├── scripts/
│   └── sync.py              # 同步脚本
├── 河南移动直播源.txt        # 本地验证底板
└── .github/workflows/
    └── sync.yml             # GitHub Actions 工作流
```

---

## ⚠️ 注意事项

1. **网络要求**：直播源走的是运营商内网 HTTP 单播，需要**河南移动宽带**环境下播放
2. **无需机顶盒**：不需要开通 IPTV 业务，光猫注册成功即可使用
3. **地址格式**：仅保留 `http://iptv.cdn.ha.chinamobile.com/PLTV` 格式的内网地址
4. **去重合并**：同一频道（名称+URL）自动去重，近似名称自动统一（如 CCTV4K/CCTV-4K/CCTV-4K超高清 → CCTV-4K）
5. **多线路**：同一频道多条线路全部保留，播放器会自动按顺序尝试切换
5. **双格式**：同时提供 M3U 和 TXT 两种格式，适配不同播放器
6. **稳定性**：上游项目内容可能随时变化，部分频道地址可能失效
7. **免责声明**：本仓库仅做自动同步整理，不存储任何流媒体内容，不对内容可用性做保证

---

*最后同步：2026-04-16*
