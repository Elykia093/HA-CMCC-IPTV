# 河南移动 IPTV 直播源

> 自动从多个上游同步、去重、合并，生成统一直播源。
> 走的是运营商内网 HTTP 单播，不依赖机顶盒，有河南移动宽带就能看。
>
> **测试环境**：郑州移动宽带 ✅

---

## 📺 订阅地址

| 类型 | 地址 | 说明 |
|:---|:---|:---|
| **直播源（M3U）** | `https://raw.githubusercontent.com/Elykia093/HA-CMCC-IPTV/main/lists/iptv.m3u` | 合并上游，去重输出 |
| **直播源（TXT）** | `https://raw.githubusercontent.com/Elykia093/HA-CMCC-IPTV/main/lists/iptv.txt` | 同上，TXT 格式 |
| **直播源（M3U 加速）** | `https://gh-proxy.com/https://raw.githubusercontent.com/Elykia093/HA-CMCC-IPTV/main/lists/iptv.m3u` | 国内 gh-proxy 加速 |
| **直播源（TXT 加速）** | `https://gh-proxy.com/https://raw.githubusercontent.com/Elykia093/HA-CMCC-IPTV/main/lists/iptv.txt` | 国内 gh-proxy 加速 |
| **EPG 节目指南** | `https://live.lizanyang.top/e.xml` | 引用上游，不同步到本地 |

---

## 📋 包含频道

按 5 个分类整理，共 **251 个频道**，**489 条线路**：

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
| Android TV | TVBox | [GitHub](https://github.com/CatVodTVOfficial/TVBoxOSC) |
| PC | VLC | [videolan.org](https://www.videolan.org/vlc/) |
| PC | PotPlayer | [potplayer.daum.net](https://potplayer.daum.net/) |
| iOS / macOS | APTV | [App Store](https://apps.apple.com/cn/app/aptv/id1630403500) |

---

## 🔄 上游来源参考

| 来源 | 平台 | 说明 |
|:---|:---|:---|
| [vnsu/HeNanCMCCIPTV](https://github.com/vnsu/HeNanCMCCIPTV) | GitHub | 多线路备选，台标+分组 |
| [lizanyang3/lizanyang3.github.io](https://github.com/lizanyang3/lizanyang3.github.io) | GitHub | 回看支持，自托管台标+EPG |
| [xisohi/CHINA-IPTV](https://github.com/xisohi/CHINA-IPTV) | GitHub | 全国 IPTV 汇总，河南单播+组播 |

---

## 🖼️ 图标来源参考

| 来源 | 说明 |
|:---|:---|
| [wanglindl/TVlogo](https://github.com/wanglindl/TVlogo) | 央视、卫视、数字频道等主流频道台标 |
| [lizanyang3/lizanyang3.github.io](https://github.com/lizanyang3/lizanyang3.github.io) | 部分地市级频道台标 |

---

## 📁 仓库结构

```
.
├── lists/
│   ├── iptv.m3u           # 直播源 M3U
│   └── iptv.txt           # 直播源 TXT
├── logos/iptv/             # 台标（频道名.png，251 个）
├── scripts/
│   └── sync.py              # 同步脚本
└── .github/workflows/
    └── sync.yml             # GitHub Actions 工作流
```

---

## ⚠️ 注意事项

1. **网络要求**：直播源走的是运营商内网 HTTP 单播，需要**河南移动宽带**环境下播放
2. **无需机顶盒**：不需要开通 IPTV 业务，光猫注册成功即可使用
3. **地址格式**：仅保留 `http://iptv.cdn.ha.chinamobile.com/PLTV` 格式的内网地址
4. **去重合并**：同一频道（名称+URL）自动去重，近似名称自动统一
5. **多线路**：同一频道多条线路全部保留，播放器会自动按顺序尝试切换
6. **双格式**：同时提供 M3U 和 TXT 两种格式，适配不同播放器
7. **稳定性**：上游项目内容可能随时变化，部分频道地址可能失效
8. **免责声明**：本仓库仅做自动同步整理，不存储任何流媒体内容，不对内容可用性做保证
