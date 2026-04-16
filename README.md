# 河南移动 IPTV 直播源

> 自动从多个上游同步、去重、合并，生成统一直播源。
> 走的是运营商内网 HTTP 单播，不依赖机顶盒，有河南移动宽带就能看。

---

## 📺 订阅地址

| 类型 | 地址 | 说明 |
|:---|:---|:---|
| **直播源** | `https://raw.githubusercontent.com/Elykia/HN-CMCC-IPTV/main/lists/merged.m3u` | 合并 4 个上游，去重后输出 |
| **EPG 节目指南** | `https://live.lizanyang.top/e.xml` | 引用上游，不同步到本地 |

---

## 📋 包含频道

- 4K 超高清频道（CCTV-4K、卫视 4K）
- 央视频道（CCTV 全系列）
- 卫视频道（各省卫视）
- 河南省内频道（各地市频道）
- 河南广播、数字频道、港澳频道等

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
- **方式**：GitHub Actions 自动拉取上游 → 去重合并 → 提交更新
- **手动触发**：在仓库 Actions 页面点击 `Run workflow` 即可

### 上游来源

| 来源 | 平台 | 说明 |
|:---|:---|:---|
| [vnsu/HeNanCMCCIPTV](https://github.com/vnsu/HeNanCMCCIPTV) | GitHub | 多线路备选，台标+分组 |
| [lizanyang3/lizanyang3.github.io](https://github.com/lizanyang3/lizanyang3.github.io) | GitHub | 回看支持，自托管台标+EPG |
| [ning87/hnydzb](https://gitee.com/ning87/hnydzb) | Gitee | IPv6 直播源 |
| [xisohi/CHINA-IPTV](https://github.com/xisohi/CHINA-IPTV) | GitHub / Cloudflare Pages | 全国 IPTV 汇总，河南单播+组播 |

### 仓库结构

```
.
├── lists/
│   └── merged.m3u          # 合并后的直播源（自动生成）
├── logos/                  # 台标备份（从上游同步）
├── scripts/
│   └── sync.py              # 同步脚本
└── .github/workflows/
    └── sync.yml             # GitHub Actions 工作流
```

---

## ⚠️ 注意事项

1. **网络要求**：直播源走的是运营商内网 HTTP 单播，需要**河南移动宽带**环境下播放
2. **无需机顶盒**：不需要开通 IPTV 业务，光猫注册成功即可使用
3. **多线路**：同一频道可能有多条线路，播放器会自动按顺序尝试切换
4. **稳定性**：上游项目内容可能随时变化，部分频道地址可能失效
5. **免责声明**：本仓库仅做自动同步整理，不存储任何流媒体内容，不对内容可用性做保证

---

*最后同步：2026-04-16*
