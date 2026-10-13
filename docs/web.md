# 华南农业大学（SCAU）官网及信息发布页面总览

> **整理范围**：华南农业大学主站、全部学院（教学单位）官网、机关部处 / 派驻机构 / 教辅单位 / 科研单位 / 群团附属单位官网、招生就业校友等专题门户，以及各站点**信息发布（列表）页面**的直达地址。
> **同时保留新版网站与旧版网站入口。**
>
> **采集方式**：逐一抓取各站点首页、栏目导航与列表页，实测 HTTP 可访问性。凡未经确认的地址一律标注「未确认」，不以推测填充。
> **站点内容所显示的最新时间**：2026 年 10 月。

---

## 0. 阅读说明

### 0.0 文档结构

| 章节 | 内容 |
|---|---|
| 0 | 阅读说明、状态记号、站点技术形态与列表页规律 |
| 1 | 学校主站（含旧版入口） |
| 2 | 教学单位（27 个学院/教学部官网 + 各自列表页面） |
| 3 | 机关部处（18 个部处官网 + 各自列表页面） |
| 4 | 派驻机构 |
| 5 | 教辅单位（8 个，含图书馆完整列表页） |
| 6 | 科研单位（国家级平台 + 其他科研机构） |
| 7 | 群团组织 / 附属单位（纪委、工会、团委、资产公司、校医院、附小、幼儿园） |
| 8 | 招生 / 就业 / 校友 / 捐赠专题门户 |
| 9 | 专题网站 / 业务系统 |
| 10 | **旧版网站汇总（重点保留）** —— 识别方法、已确认入口、站点 ID 对照、英文版汇总 |
| 11 | **网站群子域名清单** —— SCAU 域名资产全表 |
| 12 | 内容量最大的列表页（爬取优先级参考） |
| 13 | 使用建议 |

### 0.1 状态记号

| 记号 | 含义 |
|---|---|
| ✅ | 已实际抓取，HTTP 200 可访问 |
| ⚠️ | 可访问但结构特殊（需登录 / JS 渲染 / 跨协议跳转） |
| ❌ | 抓取失败或站点疑似下线 |
| 未确认 | 站内链接可见但未逐一验证 |

### 0.2 站点技术形态（决定「列表页」规律）

华南农业大学全部站点均使用同一套 CMS（清华同方 **Webplus** 网站群），因此列表页 URL 高度规律化：

| 形态 | 列表页规律 | 正文页规律 |
|---|---|---|
| **新版站点群** | `https://站点/栏目别名/list.htm` | `/年/月日/c栏目号a文章号/page.htm` |
| **旧版站点群（Webplus 1.x/2.x）** | `https://站点/数字栏目号/list.htm` | 同上，或 `page.psp` |
| **多模板集群（主站特有）** | `/_s数字/`、`/_t数字/` 前缀分区 | `.psp` 结尾 |

**通用分页规则**：列表页第 N 页 = `listN.htm`
例如：`/xxyw/list.htm` → `/xxyw/list2.htm` → `/xxyw/list3.htm` …… 直到 `listN.htm`（N = 总页数）
**每页条数**：主站常见 10 或 14 条；学院站点常见 20 条；宣传部理论动态每页 50 条。

**统一后台入口**：`http://webplus.scau.edu.cn/login.jsp?inner=1`（几乎所有站点的「管理登录」）

**旧版站群统一门户**：`https://webplus.scau.edu.cn/_s{站点ID}/main.psp`
这是识别某个站点旧版的最可靠方法（详见第 10 节）。

---

## 1. 学校主站（华南农业大学）

### 1.1 主站入口

| 名称 | 地址 | 状态 |
|---|---|---|
| 学校官网（新版） | https://www.scau.edu.cn/ | ✅ |
| 官网首页（直连） | https://www.scau.edu.cn/main.htm | ✅ |
| **返回旧版**（官网右上角入口） | https://www.scau.edu.cn/_t104/main.htm | ✅ |
| 旧版模板区（psp 渲染入口） | https://www.scau.edu.cn/_t104/main.psp | ✅ |
| 多模板集群分区示例 | https://www.scau.edu.cn/_s3/17935/list.psp | ✅ |
| 融合门户（统一身份认证） | http://portal.scau.edu.cn/ | ⚠️ 需登录 |
| 统一身份认证 CAS | https://cas.scau.edu.cn | ⚠️ 需登录 |
| 信息公开网 | https://xxgk.scau.edu.cn/ | ⚠️ 需登录 |
| 学校规章 | https://xngk.scau.edu.cn/gzzd/list.htm | ✅ |
| 教工邮箱 | https://mail.scau.edu.cn | ⚠️ 需登录 |
| 网站群管理登录 | https://webplus.scau.edu.cn/login.jsp?inner=1 | ⚠️ 仅管理 |
| OA 办公系统 | http://oa.scau.edu.cn/seeyon/ | ⚠️ 需登录 |
| 网上办事大厅 / 任务中心 | https://service.scau.edu.cn/taskcenter-v4-new/workflow/index | ⚠️ 需登录 |
| 校长信箱 | https://service.scau.edu.cn/scau_cms_yx/portal/letter_sy.jsp | ⚠️ |
| English Site（英文版） | http://english.scau.edu.cn/ | 未确认 |

### 1.2 主站新闻与信息发布（列表）页面

| 栏目 | 列表页地址 | 备注 |
|---|---|---|
| 新闻网首页（聚合） | https://www.scau.edu.cn/xww/list.htm | 要闻/综合/融媒/媒体/专题/学术/校报/文化 聚合页 |
| 学校要闻 | https://www.scau.edu.cn/xxyw/list.htm | 别名入口；每页 14 条，共 204 页 |
| 学校要闻（数字栏目） | https://www.scau.edu.cn/17646/list.htm | 每页 10 条，共 285 页 |
| 综合新闻 | https://www.scau.edu.cn/zhxw/list.htm | 别名入口 |
| 学术动态 | https://www.scau.edu.cn/17863/list.htm | 每页 10 条，共 76 页 |
| 学术动态（别名入口） | https://www.scau.edu.cn/xsdt/list.htm | — |
| 学术动态（首页版块） | https://www.scau.edu.cn/17648/list.htm | 每页 14 条，共 54 页 |
| 讲座论坛 | https://www.scau.edu.cn/17649/list.htm | 每页 14 条，共 75 页 |
| 媒体华农 | https://www.scau.edu.cn/17864/list.htm | 每页 10 条，共 460 页 |
| 融媒头条 | https://www.scau.edu.cn/17651/list.htm | 每页 10 条，共 42 页 |
| 专题报道 | https://www.scau.edu.cn/ztbd/list.htm | 专题合集 |
| 专题网站汇总 | https://www.scau.edu.cn/17655/list.htm | 专题站目录 |
| 通知公告（科研类） | https://www.scau.edu.cn/1390/list.htm | ⚠️ 跳转 cas.scau.edu.cn，需登录 |

### 1.3 主站学校概况类页面

| 栏目 | 地址 |
|---|---|
| 学校概况（总） | https://www.scau.edu.cn/17623/list.htm |
| 学校简介 | https://www.scau.edu.cn/17830/list.htm |
| 现任领导 | https://www.scau.edu.cn/xrld/list.htm |
| 办学数据 | https://www.scau.edu.cn/17832/list.htm |
| 历史沿革 | https://www.scau.edu.cn/17833/list.htm |
| 学校章程 | https://www.scau.edu.cn/17834/list.htm |
| 师资队伍（总） | https://www.scau.edu.cn/17665/list.htm |
| 师资概况 | https://www.scau.edu.cn/17665/list.htm |
| 教授名录 | https://www.scau.edu.cn/17666/list.htm |
| 学校标识 | https://www.scau.edu.cn/xxbs_17923/list.htm |

### 1.4 主站机构设置（导航枢纽）

| 栏目 | 地址 | 说明 |
|---|---|---|
| 机构设置（总） | https://www.scau.edu.cn/17935/list.htm | 进入全部机构官网的统一入口 |
| 机关部处 | https://www.scau.edu.cn/17935/list.htm | 18 个机关部处链接 |
| 派驻机构 | https://www.scau.edu.cn/pzjg/list.htm | 省纪委监委驻校纪检监察组 |
| 教学单位 | https://www.scau.edu.cn/17936/list.htm | 25 个学院/教学部链接 |
| 教辅单位 | https://www.scau.edu.cn/17937/list.htm | 8 个教辅单位链接 |
| 科研单位 | https://kyy.scau.edu.cn/sbjyszdsys/list.htm | 科研平台清单 |
| 群团/附属单位 | https://www.scau.edu.cn/qtwfsdw/list.htm | 工会/团委/资产公司/校医院/附小/幼儿园 |

### 1.5 主站校园文化类页面

| 栏目 | 地址 |
|---|---|
| 大美华农 | https://www.scau.edu.cn/dmhn/list.htm |
| 校园文化路线（总） | https://www.scau.edu.cn/xywhlx/list.htm |
| 历史文化路线 | https://www.scau.edu.cn/lswhlx/list.htm |
| 党建思政路线 | https://www.scau.edu.cn/djszlx/list.htm |
| 廉洁文化路线 | https://www.scau.edu.cn/ljwhlx/list.htm |
| 专业特色路线 | https://www.scau.edu.cn/zytslx/list.htm |
| 校园风光路线 | https://www.scau.edu.cn/xyfglx/list.htm |
| 校园地图 | https://www.scau.edu.cn/17991/list.htm |
| 进校预约 | https://www.scau.edu.cn/17992/list.htm |
| 来访预约 | https://www.scau.edu.cn/2023/1007/c6617a357265/page.htm |
| 5 号楼校史文化展馆（VR） | https://www.720yun.com/vr/1d5jepwOOv9 |
| 卢永根先进事迹陈列展（VR） | https://07fhkv3t4.720think.com/t/07fhkv3t4?def_sid=1153627 |

### 1.6 主站分角色 / 快捷入口

| 入口 | 地址 |
|---|---|
| 在校生 | https://www.scau.edu.cn/2024/0704/c17636a379849/page.htm |
| 教职工 | https://www.scau.edu.cn/2024/0704/c17637a379860/page.htm |
| 考生 | https://www.scau.edu.cn/2024/0704/c17639a379859/page.htm |
| 校友 | https://scauxyh.scau.edu.cn/ |
| 招聘（人力资源处招聘专栏） | https://hr.scau.edu.cn/6122/list.htm |
| 捐赠（教育发展基金会） | https://jyjjh.scau.edu.cn/ |
| 招标采购系统 | https://cgglxt.scau.edu.cn |
| 阳光体育 | https://tyb.scau.edu.cn/ |

### 1.7 主站社交与融媒体矩阵

| 平台 | 地址 |
|---|---|
| 抖音 | https://www.douyin.com/user/MS4wLjABAAAAlksGVSHxxL-Z2vHcjLDOpIYVwCNvWimDzrswl36Tei8 |
| B 站 | https://space.bilibili.com/619722846 |
| 微博 | https://weibo.com/u/3271376974 |
| 南方都市报 N 视频号 | https://v.oeeee.com/u/10810.html |
| 微信公众号 | https://mp.weixin.qq.com/ |

### 1.8 电子校报

| 名称 | 地址 |
|---|---|
| 华南农业大学电子校报 | https://hnxb.scau.edu.cn/ | ✅（按期号访问：`https://hnxb.scau.edu.cn/#bid=357` 等） |

---

## 2. 教学单位（学院 / 教学部）

### 2.1 学院官网总表

| 学院名称 | 官网地址 | 状态 |
|---|---|---|
| 农学院 | https://nxy.scau.edu.cn/ | ✅ |
| 植物保护学院 | https://zb.scau.edu.cn/ | ✅ |
| 林学与风景园林学院 | https://lf.scau.edu.cn/ | ✅ |
| 园艺学院 | https://yy.scau.edu.cn/ | ✅ |
| 兽医学院 | http://vet.scau.edu.cn/ | ✅ |
| 动物科学学院 | https://dongke.scau.edu.cn/ | ✅ |
| 资源环境学院 | https://zyhjxy.scau.edu.cn/ | ✅ |
| 海洋学院 | https://hy.scau.edu.cn/ | ✅ |
| 生命科学学院 | https://life.scau.edu.cn/ | ✅ |
| 工程学院 | https://gcxy.scau.edu.cn/ | ✅ |
| 食品学院 | https://spxy.scau.edu.cn/ | ✅ |
| 水利与土木工程学院 | https://wcce.scau.edu.cn/ | ✅ |
| 数学与信息学院、软件学院 | https://info.scau.edu.cn/ | ✅ |
| 人工智能与低空技术学院 | https://dzxy.scau.edu.cn/ | ✅（原「电子工程学院、人工智能学院」） |
| 材料与化学工程学院 | https://cmce.scau.edu.cn/ | ✅（原「材料与能源学院」，旧域名 `cme.scau.edu.cn`） |
| 生物质学院 | https://cfb.scau.edu.cn/ | ✅ |
| 马克思主义学院 | https://mkszyxy.scau.edu.cn/ | ✅ |
| 经济管理学院 | https://cem.scau.edu.cn/ | ✅ |
| 公共管理学院 | https://ggglxy.scau.edu.cn/ | ✅ |
| 人文与法学学院 | https://rw.scau.edu.cn/ | ✅ |
| 外国语学院 | https://sfs.scau.edu.cn/ | ✅ |
| 湾区设计与艺术学院 | https://art.scau.edu.cn/ | ✅（原「艺术学院」） |
| 体育学院（体育教学研究部） | https://tyb.scau.edu.cn/ | ✅ |
| 继续教育学院 | https://jxjy.scau.edu.cn/ | ✅ |
| 国际教育学院 | https://cie.scau.edu.cn/ | ✅ |
| 广州都柏林国际生命科学与技术学院 | https://gdic.scau.edu.cn/ | ✅ |
| 创新创业学院 | https://cxcyxy.scau.edu.cn/ | ✅ |
| 珠江学院（独立学院，校外域名） | http://www.scauzhujiang.cn/ | 未确认 |

---

### 2.2 农学院 https://nxy.scau.edu.cn/

- **旧版入口**：「旧版回顾」→ http://nxy.scau.edu.cn/_t1378/main.htm
  ⚠️ **http↔https 重定向循环，已失效**
- 旧版 webplus 路径：http://webplus.scau.edu.cn/_s287/_t1693/xyxw/list.psp ；教师详情托管于 https://webplus.scau.edu.cn/_s18/2023/0911/c419a355084/page.psp
- 路由风格：两者都有
- 生物信息平台：首页为 `javascript:void(0)`（未配置链接）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://nxy.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /xyxw/list.htm | 183 条 / 23 页 |
| 通知公告（学院） | /tzgg/list.htm | 191 条 / 24 页 |
| 讲座论坛 | /jzltw/list.htm | 61 条 / 8 页 |
| 党建动态 | /djdt/list.htm | 46 条 / 6 页；上级为党群动态 `/dqdt/list.htm` |
| 科研进展 | /kyjz/list.htm | 92 条 / 12 页 |
| 工会工作 | /ghgz/list.htm | 未确认 |
| 党群动态 | /dqdt/list.htm | 未确认 |
| 招贤纳士 | /zxns/list.htm | 未确认 |
| 学院概况 | /xygk_17945/list.htm | |
| 学院简介 | /xyjj_17955/list.htm | 未确认 |
| 现任领导 | /xrld_17997/list.htm | 未确认 |
| 机构设置 | /jgsz/list.htm | 未确认 |
| 师资队伍 | /szdw_17946/list.htm | 未确认 |
| 优秀人才 | /yxrc/list.htm | 未确认 |
| 在编教师 | /jsmlw/list.htm | 未确认 |
| 行政教辅人员 | /xzjfry/list.htm | 未确认 |
| 辅导员 | /fdy/list.htm | 未确认 |
| 实验中心人员 | /syzxry/list.htm | 未确认 |
| 博士后 | /bsh/list.htm | 未确认 |
| 班主任 | /bzr/list.htm | 未确认 |
| 人才培养 | /rcpy_17947/list.htm | 未确认 |
| 专业建设 | /zyjs_17962/list.htm | 未确认 |
| 课程设置 | /kcsz/list.htm | 未确认 |
| 慕课学习 | /mkxx/list.htm | 未确认 |
| 教学研究 | /jxyj/list.htm | 未确认 |
| 实践基地 | /sjjd/list.htm | 未确认 |
| 招生工作 | /zsgz_18654/list.htm | 未确认 |
| 研究生教育 | /yjsjy_18766/list.htm | 未确认 |
| 科学研究 | /kxyj_17948/list.htm | 未确认 |
| 科研平台 | /kypt_17966/list.htm | 未确认 |
| 科研成果 | /kycg_17968/list.htm | 未确认 |
| 社会服务 | /shfw/list.htm | 未确认 |
| 服务动态 | /fwdt/list.htm | 未确认 |
| 服务团队 | /fwtd/list.htm | 未确认 |
| 成果转化 | /cgzh/list.htm | 未确认 |
| 校地企合作 | /xdqhz/list.htm | 未确认 |
| 对口支持 | /dkzc/list.htm | 未确认 |
| 服务需求 | /fwxq/list.htm | 未确认 |
| 学生工作 | /xsgz_17951/list.htm | 未确认 |
| 学生工作—通知公告 | /tzgg_17977/list.htm | 未确认 |
| 学生活动 | /xshd/list.htm | 未确认 |
| 共青团工作 | /gqtgz/list.htm | 未确认 |
| 学生会工作 | /xshgz/list.htm | 未确认 |
| 奖助贷工作 | /jzdgz/list.htm | 未确认 |
| 本科生综合测评及评优实施 | /bkszhcpjzyssj/list.htm | 未确认 |
| 大事记 | /dsj/list.htm | 未确认 |
| 服务指南 | /fwzn_17953/list.htm | 未确认 |
| 办事指引 | /bszy_17983/list.htm | 未确认 |
| 规章制度 | /gzzd_17984/list.htm | 未确认 |
| 资料下载 | /zlxz_17985/list.htm | 未确认 |
| 学科成果信息填报表 | /xkcgxxtb/list.htm | 未确认 |
| 校友之窗 | /xyzc/list.htm | 未确认 |
| 校友服务 | /xyfw/list.htm | 未确认 |
| 校友风采 | https://gaokaobang.360eol.com/rector/2024/scau/department_custom.html?id=19906&custom=%E6%A0%A1%E5%8F%8B%E9%A3%8E%E9%87%87&v=1 | 第三方（360eol） |
| 招生宣传门户 | https://gaokaobang.360eol.com/rector/2024/scau/index.html?v=102 | 第三方（360eol） |

#### 子站点 / 下属机构

- **英文版**：https://nxy.scau.edu.cn/nxyenglish/ ✅
  - 列表页：`/nxyenglish/News1/list.htm`、`/Situationw/list.htm`、`/Exploreus/list.htm`、`/Overview/list.htm`、`/Faculty/list.htm`、`/5938/list.htm`、`/5939/list.htm`、`/5940/list.htm`、`/5941/list.htm`、`/5942/list.htm`、`/Video/list.htm`
- 国家植物航天育种工程技术研究中心 https://htyzzx.scau.edu.cn/
- 植物新品种测试（广州）分中心 https://gzdus.scau.edu.cn/
- 节水抗旱稻绿色产业研究院 https://wdr.scau.edu.cn/

---

### 2.3 植物保护学院 https://zb.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：新版栏目为主（含数字栏目）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://zb.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /xydt/list.htm | 186 条 / 14 页 |
| 学院通知 | /jgtz/list.htm | 326 条 / 24 页 |
| 讲座预告 | /jzyg_12113/list.htm | 120 条 / 9 页 |
| 学术进展 | /xsjz/list.htm | 82 条 / 6 页 |
| 信息公开 | /xxgk/list.htm | 577 条 / 42 页 |
| 媒体植保 | /mtzb/list.htm | 232 条 / 17 页 |
| 党政工会 | /dzgh/list.htm | 14 条 |
| 本科生通知 | /bks/list.htm | 310 条 / 23 页 |
| 研究生通知 | /yjs/list.htm | 189 条 / 14 页 |
| 党建动态 | /djxw/list.htm | 空栏目（0 条） |
| 学院概况 | /xygk/list.htm | 未确认 |
| 学院简介 | /xyjj/list.htm | 未确认 |
| 现任领导 | /xrld/list.htm | 未确认 |
| 机构设置 | /jgsz/list.htm | 未确认 |
| 党群组织 | /dqzz/list.htm | 未确认 |
| 学院标识 | /xybs/list.htm | 未确认 |
| 师资队伍 | /szdw/list.htm | 未确认 |
| 人才招聘 | /rczp/list.htm | 未确认 |
| 师资概况 | /szgk/list.htm | 未确认 |
| 专业教师/昆虫学系 | /kcxx/list.htm | 未确认 |
| 农药学系 | /nyxx/list.htm | 未确认 |
| 植物病理学系 | /zwblxx/list.htm | 未确认 |
| 群体微生物研究中心 | /qtwswyjzx/list.htm | 未确认 |
| 实验中心 | /syzx/list.htm | 未确认 |
| 科学研究 | /kxyj/list.htm | 未确认 |
| 科研成果 | /kycg/list.htm | 未确认 |
| 科研团队 | /kytd/list.htm | 未确认 |
| 科研团队（图墙） | /kytd_12048/list.htm | 未确认 |
| 学术交流 | /xsjl/list.htm | 未确认 |
| 实验室建设 | /sysjs/list.htm | 未确认 |
| 本科生培养 | /bkspy/list.htm | 未确认 |
| 专业设置 | /zysz/list.htm | 未确认 |
| 培养方案（本科） | /pyfa_11956/list.htm | 未确认 |
| 教学大纲 | /jxdg/list.htm | 未确认 |
| 文件规定 | /wjgd/list.htm | 未确认 |
| 科普基地 | /kpjd/list.htm | 未确认 |
| 研究生培养 | /yjspy/list.htm | 未确认 |
| 培养方案（研究生） | /pyfa/list.htm | 未确认 |
| 学位工作 | /xwgz/list.htm | 未确认 |
| 办事流程（研究生） | /bslc/list.htm | 未确认 |
| 博士后培养 | /bshpy/list.htm | 未确认 |
| 流动站简介 | /ldzjj/list.htm | 未确认 |
| 合作导师 | /hzds/list.htm | 未确认 |
| 博士后招聘 | /bshzp/list.htm | 未确认 |
| 博士后管理 | /bshgl/list.htm | 未确认 |
| 招生就业 | /zsjy/list.htm | 未确认 |
| 招生专栏 | /yjszs/list.htm | 未确认 |
| 学生工作 | /xsgz/list.htm | 未确认 |
| 学工队伍 | /xgdw/list.htm | 未确认 |
| 学生动态 | /xsdt/list.htm | 未确认 |
| 学生组织 | /txzz/list.htm | 未确认 |
| 团委 | /tw/list.htm | 未确认 |
| 学生会 | /xsh/list.htm | 未确认 |
| 党务管理委员会 | /dwglwyh/list.htm | 未确认 |
| 媒体中心 | /mtzx/list.htm | 未确认 |
| 本科生工作 | /bksgz/list.htm | 未确认 |
| 研究生工作 | /yjsgz/list.htm | 未确认 |
| 资助工作 | /zzgz/list.htm | 未确认 |
| 办事流程（学生工作） | /bslc_12310/list.htm | 未确认 |
| 党建专栏 | /djzx/list.htm | 未确认 |
| 组织架构 | /zzjg/list.htm | 未确认 |
| 支部风采 | /zbfc/list.htm | 未确认 |
| 党务指南 | /dwzn/list.htm | 未确认 |
| 公示情况 | /gsqk/list.htm | 未确认 |
| 学习平台 | /xzyd/list.htm | 未确认 |
| 办事流程（党务） | /wdxz_12229/list.htm | 未确认 |
| 社会服务 | /shfw/list.htm | 未确认 |
| 培训 | /px/list.htm | 未确认 |
| 乡村振兴 | /xczx/list.htm | 未确认 |

#### 子站点 / 下属机构

- 招生就业网 http://zb.scau.edu.cn/zbzs （未确认）
- 实验教学示范中心 https://zb.scau.edu.cn/syjxzx/ （未确认）
- 页脚「植物保护学院」链接指向 http://zb.scauzhujiang.cn/ （珠江学院镜像）

---

### 2.4 林学与风景园林学院 https://lf.scau.edu.cn/

- 旧版入口：未发现「旧版」链接
  - 旧版 webplus 师资名录：http://webplus.scau.edu.cn/_s24/_t636/lxxk/list.psp
  - 页脚 logo 指向旧模板首页：`/_upload/tpl/02/7c/636/template636/index.htm`
- 路由风格：两者都有（数字栏目 `/885`、`/887`、`/888` + 命名栏目）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://lf.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /885/list.htm | 518 条 / 37 页 |
| 教工通知 | /887/list.htm | 317 条 / 23 页 |
| 学生通知 | /888/list.htm | 851 条 / 61 页 |
| 学术报告 | /xsbg/list.htm | 62 条 / 5 页 |
| 党建动态 | /djdt/list.htm | 203 条 / 15 页 |
| 学生培养 | /xspy/list.htm | 93 条 / 7 页 |
| 师资队伍（师资名录） | /lxxk/list.htm | |
| 师资—正高职称 | /zg/list.htm | 未确认 |
| 师资—副高职称 | /fg/list.htm | 未确认 |
| 师资—中级、初级职称 | /zjwqt/list.htm | 未确认 |
| 师资名录（旧版 .psp） | http://webplus.scau.edu.cn/_s24/_t636/lxxk/list.psp | 未确认 |
| 风景园林学科 | /fjylxk/list.htm | 未确认 |
| 草学学科 | /cykxxk/list.htm | 未确认 |
| 实验中心（师资） | /jxsyzx_9315/list.htm | 未确认 |
| 博士后之家/流动站介绍 | /ldzjs/list.htm | 未确认 |
| 合作导师简介 | /hzdsjj/list.htm | 未确认 |
| 博士后通知公告 | /tzgg_10882/list.htm | 未确认 |
| 人事服务 | /rsfw/list.htm | 未确认 |
| 学院概况 | /xygkw/list.htm | 未确认 |
| 学院简介 | /xyjj_9776/list.htm | 未确认 |
| 院徽院训 | /yhyx_9777/list.htm | 未确认 |
| 治理架构 | /zljg/list.htm | 未确认 |
| 党委委员 | /dwwy/list.htm | 未确认 |
| 领导班子 | /ldbz/list.htm | 未确认 |
| 学术委员会 | /xswyh/list.htm | 未确认 |
| 学位委员会 | /xwwyh/list.htm | 未确认 |
| 隶属机构及其负责人 | /yltxgzxz/list.htm | 未确认 |
| 院务公开 | /ywgk/list.htm | 未确认 |
| 院务公开—基本信息 | /jbxx/list.htm | 未确认 |
| 院务公开—招生考试信息 | /zsksxx/list.htm | 未确认 |
| 院务公开—财务、资产及收费信息 | /cwwzcjsfxx/list.htm | 未确认 |
| 院务公开—人事师资信息 | /rsszxx/list.htm | 未确认 |
| 院务公开—教学质量信息 | /jxzlxx/list.htm | 未确认 |
| 院务公开—学生管理服务信息 | /xsglfwxx/list.htm | 未确认 |
| 院务公开—学风建设信息 | /xfjsxx/list.htm | 未确认 |
| 院务公开—学位、学科信息 | /xwwxkxx/list.htm | 未确认 |
| 院务公开—对外交流与合作信息 | /dwjlyhzxx/list.htm | 未确认 |
| 院务公开—综合安全治理 | /zhaqzl/list.htm | 未确认 |
| 院务公开—党建思政 | /djsz/list.htm | 未确认 |
| 院务公开—其他 | /qt/list.htm | 未确认 |
| 联系我们 | /lxwm/list.htm | 未确认 |
| 人才培养 | /rcpyw/list.htm | 未确认 |
| 本科教育教学审核评估 | /bkjyjxshpg/list.htm | 未确认 |
| 专业建设 | /zyjs_9785/list.htm | 未确认 |
| 课程建设 | /kcjs/list.htm | 未确认 |
| 本科生教育 | /bksjy/list.htm | 未确认 |
| 研究生教育 | /yjsjy/list.htm | 未确认 |
| 学位点质量年报 | /xwdzlnb/list.htm | 未确认 |
| 学位点年报—风景园林 | /fjyl/list.htm | 未确认 |
| 学位点年报—林学 | /lx/list.htm | 未确认 |
| 学位点年报—林业 | /ly/list.htm | 未确认 |
| 学位点年报—草学 | /cx/list.htm | 未确认 |
| 教学实习 | /jxsx/list.htm | 未确认 |
| 科学研究 | /kxyjw/list.htm | 未确认 |
| 学科介绍 | /kytd/list.htm | 未确认 |
| 科研平台 | /ptjd/list.htm | 未确认 |
| 重点实验室 | /kypt/list.htm | 未确认 |
| 教学实验中心 | /kyjd/list.htm | 未确认 |
| 科研动态 | /kydt/list.htm | 未确认 |
| 科研成果 | /kycg/list.htm | 未确认 |
| 实验室管理 | /sysgl/list.htm | 未确认 |
| 党群工作 | /dqgz/list.htm | 未确认 |
| 教工之家 | /jgzj/list.htm | 未确认 |
| 离退休工作 | /ltxgz/list.htm | 未确认 |
| 学生工作 | /xsgzw/list.htm | 未确认 |
| 辅导员信息 | /fdyxx/list.htm | 未确认 |
| 班主任信息 | /bzrxx/list.htm | 未确认 |
| 学生组织 | /xszz_9800/list.htm | 未确认 |
| 学生动态 | /xsdt/list.htm | 未确认 |
| 招生就业 | /zsjyw/list.htm | 未确认 |
| 本科生招生信息 | /bkszsxx/list.htm | 未确认 |
| 招生—学院介绍 | /xyjs/list.htm | 未确认 |
| 招生—专业介绍 | /zyjs_10878/list.htm | 未确认 |
| 招生—学子风采 | /xzfc_11101/list.htm | 未确认 |
| 招生—招生计划 | /zsjh_11102/list.htm | 未确认 |
| 研究生招生信息 | /yjszsxx/list.htm | 未确认 |
| 招生简章 | /zsjz/list.htm | 未确认 |
| 招生目录 | /zsml/list.htm | 未确认 |
| 招生宣讲 | /zsxj/list.htm | 未确认 |
| 对外交流 | /dwjlw/list.htm | 未确认 |
| 国际交流 | /gjjl/list.htm | 未确认 |
| 社会服务 | /shfw/list.htm | 未确认 |
| 校友之家 | /xyzjw/list.htm | 未确认 |
| 校友活动 | /xyh/list.htm | 未确认 |
| 预约返校 | /yyfx/list.htm | 未确认 |
| 饮水思源 | /yssy/list.htm | 未确认 |
| 学院教育发展基金 | /yjyfzjj/list.htm | 未确认 |
| 善境基金 | /sjjj/list.htm | 未确认 |
| 捐赠项目 | /jzxm/list.htm | 未确认 |
| 捐赠鸣谢 | /jzmx/list.htm | 未确认 |
| 校友服务 | /xyfw/list.htm | 未确认 |
| 办事指南 | /bszn/list.htm | 未确认 |
| 常用模板 | /bszn_14642/list.htm | 未确认 |
| 办事流程 | /bslc/list.htm | 未确认 |

#### 子站点 / 下属机构

- **党建工作网**：https://lf.scau.edu.cn/dangjiangongzuo/ ✅
  - 列表页：`/dangjiangongzuo/8604/list.htm`、`/8605/list.htm`、`/dangjiangongzuo/djxw/list.htm`、`/dangjiangongzuo/zbfc/list.htm`、`/8607/list.htm`、`/8608/list.htm`、`/8609/list.htm`、`/8610/list.htm`、`/8611/list.htm`
  - 旧版 `.psp`：http://webplus.scau.edu.cn/dangjiangongzuo/djxw/list.psp
- 英文版 https://lf.scau.edu.cn/lfen/ ❌ 跨协议重定向循环，抓取失败
- 卢永根专题网站 https://lyg.scau.edu.cn/
- 就业信息网 http://202.116.160.44:8004/linxuejob/

---

### 2.5 园艺学院 https://yy.scau.edu.cn/

- 旧版入口：未发现
- 英文版 http://yy.scau.edu.cn/yyen ❌ 跨协议重定向循环，抓取失败
- 路由风格：两者都有（数字栏目 `/2447`、`/2448`、`/2449`、`/2165`、`/2167`、`/2430`、`/2433`、`/2438`、`/2439`、`/2440`、`/2185`、`/2429`、`/2189` + 命名栏目）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://yy.scau.edu.cn`） | 说明 |
|---|---|---|
| 新闻中心 | /2447/list.htm | 309 条 / 23 页 |
| 通知公告 | /2448/list.htm | 1083 条 / 78 页 |
| 学术报告 | /2449/list.htm | 108 条 / 8 页 |
| 新闻公告（父栏目） | /xwgg/list.htm | 未确认 |
| 业内新闻 | /ynxw/list.htm | 未确认 |
| 媒体园艺 | /mtyy/list.htm | 未确认 |
| 学院概况 | /xygk_/list.htm | 未确认 |
| 学院简介 | /xyjj/list.htm | 未确认 |
| 现任领导 | /ldjs/list.htm | 未确认 |
| 机构设置 | /xsfwyh/list.htm | 未确认 |
| 大事记 | /dsj/list.htm | 未确认 |
| 联系我们 | /lxwm/list.htm | 未确认 |
| 师资队伍 | /szdw_/list.htm | 未确认 |
| 师资概况 | /szgk/list.htm | 未确认 |
| 教师名录 | /gsxx01/list.htm | 未确认 |
| 客座教授 | /kzjs/list.htm | 未确认 |
| 校外导师 | /xwds/list.htm | 未确认 |
| 博士后之家 | /bszp/list.htm | 未确认 |
| 人才培养 | /2165/list.htm | 未确认 |
| 一流专业 | /ylzy/list.htm | 未确认 |
| 本科生 | /2185/list.htm | 未确认 |
| 研究生 | /2429/list.htm | 未确认 |
| 国际教育 | /gjjy/list.htm | 未确认 |
| 教学成果 | /jxcg/list.htm | 未确认 |
| 基地建设 | /2189/list.htm | 未确认 |
| 科学研究 | /2167/list.htm | 未确认 |
| 学科建设 | /gjzdxk/list.htm | 未确认 |
| 科研平台 | /kypt/list.htm | 未确认 |
| 科研成果 | /kyxm/list.htm | 未确认 |
| 党群工作 | /2430/list.htm | 未确认 |
| 党建工作 | /2430/list.htm | 文章前缀 c12145 |
| 工会工作 | /2433/list.htm | 未确认 |
| 党团活动 | /dthd/list.htm | 未确认 |
| 理论学习 | /llxx/list.htm | 未确认 |
| 学生工作/学生组织 | /2438/list.htm | 未确认 |
| 学生动态 | /2439/list.htm | 未确认 |
| 创新创业 | /2440/list.htm | 未确认 |
| 学生风采 | /xsfc/list.htm | 未确认 |
| 院务公开/学院规章 | /xygz_9184/list.htm | 未确认 |
| 党政联席会 | /dzlxh/list.htm | 未确认 |
| 院内公告 | /yngs/list.htm | 未确认 |
| 校友工作 | /xygz/list.htm | 未确认 |
| 校友工作机构 | /xylsh/list.htm | 未确认 |
| 校友名录 | /xyml/list.htm | 未确认 |
| 校友风采 | /xyfc/list.htm | 未确认 |
| 园艺文化 | /yywh/list.htm | 未确认 |
| 历史沿革 | /lsyg_9166/list.htm | 未确认 |
| 历届领导 | /ljld_9168/list.htm | 未确认 |
| 园艺人物 | /lsrw/list.htm | 未确认 |
| 教学科研（动态） | /jxky/list.htm | 文章前缀 c9052 |
| 招生就业 | /zscy/list.htm | 文章前缀 c9050 |
| 视听园艺 | /xjlmcs/list.htm | 文章前缀 c14341 |

#### 子站点 / 下属机构

- **园艺学实验教学中心**：https://yy.scau.edu.cn/syjxsfzx/ ✅
  - 列表页（前缀 `https://yy.scau.edu.cn/syjxsfzx`）：`/zxjs/list.htm`（中心介绍）、`/zxdt/list.htm`（中心动态）、`/jsdw/list.htm`（教师队伍）、`/jxcg/list.htm`（教学成果）、`/syjx/list.htm`（实验教学）、`/sysxxgjc/list.htm`（实验室信息与改进）、`/cddsyjxxm/list.htm`（承担的大型实验项目）、`/yqsb/list.htm`（仪器设备）、`/sbyy/list.htm`（设备预约）、`/wxgzhyy/list.htm`（维修故障与报验）、`/gzzd/list.htm`（规章制度）、`/dxyqggptglzd/list.htm`（大型仪器共享平台管理规定）、`/tsycg/list.htm`（特色与成果）、`/cdkyxm/list.htm`（承担科研项目）、`/sdpz/list.htm`（示导片展）、`/hjqk/list.htm`（环境情况）、`/sqzl/list.htm`（社区质量）、`/fbkylwwzww/list.htm`、`/fbkylwwyww/list.htm`、`/sysaq/list.htm`（实验室安全）
  - 外部预约系统：http://222.201.228.129/login.html ；http://iot.enzyun.com/scau-eqmgrb/login
- 招生网 https://yy.scau.edu.cn/zs/ （未确认）
- http://yy.scau.edu.cn/yysys （未确认）
- 关联站点：https://lyg.scau.edu.cn/ ；http://nz.scau.edu.cn/

---

### 2.6 兽医学院 https://vet.scau.edu.cn/

- 首页：http://vet.scau.edu.cn/ → 301 至 https://vet.scau.edu.cn/ ✅
- 旧版入口：未发现
- 英文版 https://vet.scau.edu.cn/veten/ ❌ 跨协议重定向循环，抓取失败
- 路由风格：两者都有（数字栏目 `/814`、`/860`、`/863`、`/802`、`/803`、`/822`、`/827`、`/828`、`/804`、`/846`、`/847`、`/849`、`/845`、`/807`、`/862`、`/829`、`/848`、`/844`、`/855`、`/856`、`/809`、`/857`、`/858`、`/859`、`/939` + 命名栏目）
- ⚠️ 「通知公告」`/tzgg/list.htm` **抓取失败（跨协议重定向循环）**；文章前缀 c18287（栏目 id 18287）
- 旧版分区页面：`/_t436/…`（国家地方联合工程实验室、国家兽医微生物耐药性风险评估实验室）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://vet.scau.edu.cn`） | 说明 |
|---|---|---|
| 新闻动态 | /860/list.htm | 455 条 / 33 页 |
| 学院动态（父栏目） | /814/list.htm | 未确认 |
| 社会服务与企业合作 | /863/list.htm | 26 条（每页 30 条） |
| 通知公告 | /tzgg/list.htm | ⚠️ 抓取失败（跨协议重定向循环） |
| 学术活动公告 | /939/list.htm | 文章前缀 c939 |
| 联系我们 | http://vet.scau.edu.cn/2020/0516/c803a229476/page.htm | 单篇文章 |
| 学院概况 | /802/list.htm | 未确认 |
| 学院介绍 | /xygk/list.htm | 未确认 |
| 机构设置 | /803/list.htm | 未确认 |
| 领导班子 | /822/list.htm | 未确认 |
| 历史沿革 | /827/list.htm | 未确认 |
| 党建引领 | /djyl/list.htm | 未确认 |
| 形象标识 | /828/list.htm | 未确认 |
| 师资队伍 | /804/list.htm | 未确认 |
| 博士生上岗导师 | /846/list.htm | 未确认 |
| 硕士生上岗导师 | /847/list.htm | 未确认 |
| 兽医药理学与毒理学 | /syylxydlx/list.htm | 未确认 |
| 动物解剖学、组织胚胎学与病理学 | /dwjpxwzzptxyblx/list.htm | 未确认 |
| 兽医传染病学 | /sycrbx/list.htm | 未确认 |
| 兽医微生物学 | /sywswx/list.htm | 未确认 |
| 兽医寄生虫学 | /syjscx/list.htm | 未确认 |
| 兽医内科学、诊断学与中兽医学 | /synkxwzdxyzsyx/list.htm | 未确认 |
| 兽医外科学与临床科学 | /sywkxyckx/list.htm | 未确认 |
| 兽医学实验教学中心 | /syxsyjxzx/list.htm | 未确认 |
| 动物医院 | /dwyy/list.htm | 未确认 |
| 农业部畜禽产品质量监督检验测试中心（广州） | /nybcqcpzljdjczxwgzw/list.htm | 未确认 |
| 人才培养 | /rcpy_9750/list.htm | 未确认 |
| 教学动态 | /jxdt/list.htm | 未确认 |
| 本科生培养 | /849/list.htm | 未确认 |
| 研究生培养 | /845/list.htm | 未确认 |
| 博士后之家 | /bshzj/list.htm | 未确认 |
| 精品课程 | /jpkc/list.htm | 未确认 |
| 教学成果奖 | /jxcgj/list.htm | 未确认 |
| 教学研究与改革 | /jxyjygg/list.htm | 未确认 |
| 教学平台 | /jxpt/list.htm | 未确认 |
| 科学研究 | /807/list.htm | 未确认 |
| 学术交流 | /xsjl/list.htm | 未确认 |
| 科研进展 | /862/list.htm | 未确认 |
| 科研团队 | /kytd/list.htm | 未确认 |
| 研究平台 | /829/list.htm | 未确认 |
| 实验室建设 | /sysjs/list.htm | 未确认 |
| 下载专区 | /xzzq/list.htm | 未确认 |
| 招生就业 | /zsjy/list.htm | 未确认 |
| 本科生招生简章 | /848/list.htm | 未确认 |
| 研究生招生简章 | /844/list.htm | 未确认 |
| 就业工作 | /855/list.htm | 未确认 |
| 就业信息 | /856/list.htm | 未确认 |
| 学生成果 | /xscg/list.htm | 未确认 |
| 学生风采 | /xsfc/list.htm | 未确认 |
| 学生工作 | /809/list.htm | 未确认 |
| 学生动态 | /857/list.htm | 未确认 |
| 资料下载（学生工作） | /858/list.htm | 未确认 |
| 奖助学金 | /859/list.htm | 未确认 |
| 校友之家 | /xyzj/list.htm | 未确认 |
| 校友分会 | /xyfh/list.htm | 未确认 |
| 校友动态 | /xydt/list.htm | 文章前缀 c19601 |
| 信息公开 | /ywgk/list.htm | 未确认 |
| 院务公开 | /gzzd_12422/list.htm | 未确认 |
| 党务公开 | /dzlxh/list.htm | 未确认 |

#### 子站点 / 下属机构

- **华南农业大学兽医党建网**：https://vet.scau.edu.cn/sydj/ ✅
  - 列表页：`/sydj/jgsz/list.htm`（机构设置）、`/xydwgk/list.htm`（学院党委概况）、`/zbjj/list.htm`（支部简介）、`/djdt/list.htm`（党建动态）、`/djxw/list.htm`（党建新闻）、`/zbdt/list.htm`（支部动态）、`/szxx/list.htm`（思政学习）、`/xydx/list.htm`（学院党校，前缀 c12918）、`/dwgk/list.htm`（党务公开）、`/bgjs/list.htm`（班子建设，前缀 c7976）
- **国家级实验室页面（旧分区 `_t436`）**：
  - 人兽共患病防控制剂国家地方联合工程实验室（广东）https://vet.scau.edu.cn/_t436/2015/1116/c829a53772/page.psp
  - 国家兽医微生物耐药性风险评估实验室 https://vet.scau.edu.cn/_t436/2015/1116/c829a53951/page.psp
- 学科大模型 https://5wmhafdxzfc4o.ok.kimi.link/
- 安全生产专题/实验教学中心/实验动物中心/《养禽与禽病防治》使用 `/_redirect?siteId=25&columnId=7715&articleId=...` 内部跳转

---

### 2.7 动物科学学院 https://dongke.scau.edu.cn/

- **旧版入口**：未发现显式「旧版」链接；仅有页脚管理登录
- **英文版**：https://dongke.scau.edu.cn/dongke_en/main.psp ✅（独立模板，栏目 `/dongke_en/5481~5500/list.htm`，新闻 `/dongke_en/5499/list.psp`，内容更新至 2020 年）
- 路由风格：两者都有（命名栏目 + webplus 数字栏目 `611`–`678`）
- 招生就业子站 `https://dongke.scau.edu.cn/dkzsw/` **已失效**（302 回主站）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://dongke.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院动态 | /xydt/list.htm | 319 条 / 23 页，主新闻栏目 |
| 党建引领 | /dqgz/list.htm | 71 条 / 6 页，栏目 ID c10007 |
| 媒体动科 | /mtdk/list.htm | 253 条 / 19 页，校外媒体报道 |
| 教学科研 | /jxky/list.htm | 67 条 / 5 页 |
| 交流活动 | /jlhd_10003/list.htm | 137 条 / 10 页，含「动科大讲坛」 |
| 学院概况 | /xyjj/list.htm | 栏目组 |
| 学院简介 | /xyjj_10028/list.htm | |
| 现任领导 | /xrld/list.htm | |
| 历届领导 | /ljld/list.htm | |
| 机构设置 | /jgsz/list.htm | |
| 在校生 | /zxs/list.htm | |
| 师资队伍 | /szdww/list.htm | 栏目组 |
| 师资概况 | /szgk/list.htm | |
| 教师总览 | /jszl_10543/list.htm | |
| 教师总览—动物营养与饲料科学系 | /dwyyyslkxx/list.htm | |
| 教师总览—动物遗传育种与繁殖系 | /dwycyzyfzx_10553/list.htm | |
| 教师总览—智慧养殖系 | /dwscyglx_10554/list.htm | |
| 教师总览—蚕丝科学系 | /cskxx_10555/list.htm | |
| 教师总览—实验教学中心 | /syjxzx/list.htm | |
| 人才项目 | /rcxm/list.htm | 栏目组 |
| 国家杰青 | /gjjq/list.htm | |
| 国家优青 | /gjyq/list.htm | |
| 国家高层次人才 | /gjgccrc/list.htm | |
| 国家高层次青年人才项目 | /gjgccqnrcxm/list.htm | |
| 国家特支计划科技创新领军人才 | /gjwrjh/list.htm | |
| 珠江学者 | /zjxz/list.htm | |
| 教育部新世纪优秀人才 | /jybxsjyxrc/list.htm | |
| 科技部中青年创新领军人才 | /kjbzqncxljrc/list.htm | |
| 广东省教学名师 | /gdsjxms/list.htm | |
| 广东省珠江学者—青年学者 | /gdszjxzwqnxz/list.htm | |
| 广东省高校「千百十工程」省级培养对象 | /gdsgdxxwqbsgcwsjpydx/list.htm | |
| 广东特支计划青年拔尖人才 | /gdtzjhqnbjrc/list.htm | |
| 广东省优秀青年教师培养计划 | /gdsyxqnjspyjh/list.htm | |
| 珠江科技新星 | /zjkjxx/list.htm | |
| 丁颖人才支持工程 | /dyrczcgc/list.htm | |
| 博士生导师 | /bssds/list.htm | 栏目组 |
| 博导—动物营养与饲料学系 | /dwyyyslxx/list.htm | |
| 博导—动物遗传育种与繁殖系 | /dwycyzyfzx/list.htm | |
| 博导—智慧养殖系 | /dwscyglx/list.htm | |
| 博导—蚕丝科学系 | /cskxx/list.htm | |
| 硕士生导师 | /sssds/list.htm | 栏目组 |
| 硕导—动物营养与饲料学系 | /dwyyyslxx_10050/list.htm | |
| 硕导—动物遗传育种与繁殖系 | /dwycyzyfzx_10051/list.htm | |
| 硕导—智慧养殖系 | /dwscyglx_10052/list.htm | |
| 硕导—蚕丝科学系 | /cskxx_10053/list.htm | |
| 校外导师（第一导师） | /xwds/list.htm | 栏目组 |
| 校外导师—中国农科院北京畜牧兽医研究所 | /zgnykxybjcmsyyjs/list.htm | |
| 校外导师—广东省农业科学院 | /gdsnykxy/list.htm | |
| 党建工作 | /611/list.htm | 3 条，旧版数字栏目 |
| 党建—规章制度 | /629/list.htm | |
| 党建—入党流程 | /634/list.htm | |
| 党建—党支部概况 | /635/list.htm | |
| 党建—共产党章程 | /636/list.htm | |
| 党建—党课培训 | /630/list.htm | |
| 党建—特色项目 | /631/list.htm | |
| 学科平台 | /612/list.htm | |
| 学科介绍 | /637/list.htm | |
| 科研成果 | /638/list.htm | |
| 平台建设 | /639/list.htm | |
| 人才培养 | /613/list.htm | |
| 本科生培养 | /640/list.htm | |
| 本科—专业设置 | /642/list.htm | |
| 本科—培养方案 | /pyfa/list.htm | |
| 本科—实践教学 | /644/list.htm | |
| 本科—教育教学 | /645/list.htm | |
| 本科—教学管理文件 | /646/list.htm | |
| 本科—文档下载 | /647/list.htm | |
| 研究生培养 | /641/list.htm | |
| 研究生招生目录 | /yjszsml/list.htm | |
| 研究生培养方案 | /pyfa_13894/list.htm | |
| 研究生—管理文件 | /glwj/list.htm | |
| 研究生—文档下载 | /wdxz/list.htm | |
| 博士后培养 | /bshpy/list.htm | |
| 博士后招聘 | /bshzp/list.htm | |
| 博士后—合作导师简介 | /hzdsjj/list.htm | |
| 博士后—流动站介绍 | /ldzjs/list.htm | |
| 博士后—通知公告 | /tzgg/list.htm | 空栏目 |
| 学生工作 | /614/list.htm | |
| 学工—规章制度 | /649/list.htm | |
| 学生组织 | /650/list.htm | |
| 学生组织—团委学生会 | /656/list.htm | |
| 学生组织—学生教学信息委员会 | /657/list.htm | |
| 学生组织—启明心工作室 | /658/list.htm | |
| 学生组织—党务工作室 | /659/list.htm | |
| 学生组织—青廉社 | /qls/list.htm | |
| 校企合作 | /615/list.htm | |
| 温氏班 | /674/list.htm | |
| 友好合作企业 | /675/list.htm | |
| 校友工作 | /616/list.htm | |
| 杰出校友 | /677/list.htm | |
| 校友活动 | /678/list.htm | |
| 招生就业—专业视频 | /zyjs/list.htm | 14 条 |
| 招生就业—本科生招生 | /bkszs/list.htm | 10 条 |
| 招生就业—研究生招生 | /yjszs/list.htm | 94 条 / 7 页 |
| 招生就业—升学就业 | /jy/list.htm | |
| 升学 | /sx/list.htm | 2 条 |
| 就业 | /jy_10546/list.htm | 未确认 |
| 学院工会（教代会） | /xyghwjdhw/list.htm | 4 条 |
| 院务公开 | /ywgk_14130/list.htm | |
| 院务公开—规章制度 | /gzzd/list.htm | 16 条 / 2 页 |

#### 子站点 / 下属机构

- 广东省畜禽种质资源库 / 国家区域性畜禽基因库：http://www.gdgenebank.scau.edu.cn/gw/ ✅
- 书记/院长信箱：https://service.scau.edu.cn/portal/taskcenter-v4/service_guide.jsp?gid=30212

---

### 2.8 资源环境学院 https://zyhjxy.scau.edu.cn/

- **旧版入口**：页面右上角「旧版回顾」href 为 `javascript:void(0)`（无实际 URL）；
  **经验证可用的真实旧版站点**：https://webplus.scau.edu.cn/_s82/main.psp ✅（站点 ID `_s82`，模板 `_t1734`，内容与新版同步）
- 路由风格：两者都有（命名栏目 + `_NNNNN` 后缀型数字栏目）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://zyhjxy.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院要闻 | /xyyw/list.htm | 223 条 / 16 页 |
| 通知公告 | /tzgg_19902/list.htm | 422 条 / 31 页，栏目 ID c19902 |
| 科教动态 | /kjdt_19378/list.htm | 学术报告/科研进展，c19378 |
| 学术活动 | /xshd/list.htm | 11 条，讲座报告，c18688 |
| 党建工作 | /djdt/list.htm | c13023 |
| 媒体资环 | /mtzh/list.htm | 60 条 / 5 页 |
| 学院概况 | /xygkw_18693/list.htm | 栏目组 |
| 学院介绍 | /xyjs/list.htm | |
| 现任领导 | /xrld_13232/list.htm | |
| 组织机构 | /zzjg_18694/list.htm | |
| 院系设置 | /yxsz/list.htm | |
| 师资队伍 | /szdwwazcw/list.htm | 按职称 |
| 师资队伍—创新人才 | /jcrc_19590/list.htm | |
| 师资队伍—教授名录 | /js_18802/list.htm | 含副教授/讲师/实验技术/行政管理分组，c18802–c18808 |
| 党群工作 | /dqgz_18728/list.htm | 栏目组 |
| 党建动态 | /djdt_18729/list.htm | c18729 |
| 党建公示 | /djgs/list.htm | |
| 党建通知 | /djtz/list.htm | |
| 工会动态 | /ghdt/list.htm | |
| 人才培养 | /rcpyw/list.htm | 栏目组 |
| 本科生培养 | /bkspy/list.htm | |
| 研究生培养 | /yjspy/list.htm | |
| 教学研究 | /jxyj/list.htm | |
| 实践基地 | /sjjd/list.htm | |
| 科学研究 | /kxyjw/list.htm | 栏目组 |
| 科研平台 | /kypt_18740/list.htm | |
| 科研成果 | /kycg_18741/list.htm | |
| 学生工作 | /xsgzw/list.htm | 栏目组 |
| 学工动态 | /xgdt_19919/list.htm | 11 条 |
| 学生组织 | /xszz_18744/list.htm | |
| 学子风采 | /xzfc_18745/list.htm | |
| 社会服务 | /shfww/list.htm | 栏目组 |
| 社会服务动态 | /shfwdt/list.htm | |
| 服务团队 | /fwtd/list.htm | |
| 成果转化 | /cgzh/list.htm | |
| 招生就业 | /zsjyw/list.htm | 栏目组 |
| 招生就业动态 | /zsjydt/list.htm | |
| 本科生招生 | /zsjz_18752/list.htm | |
| 研究生招生 | /yjszs/list.htm | |
| 服务指南 | /fwznw/list.htm | 栏目组 |
| 办事指引 | /bszy/list.htm | |
| 规章制度 | /gzzd_18755/list.htm | |
| 资料下载 | /zlxz/list.htm | |
| 校友之窗 | /xyzcw/list.htm | 栏目组 |
| 校友活动 | /xyhd_18758/list.htm | |
| 校友风采 | /xyfc_18759/list.htm | |

#### 子站点 / 下属机构

- 旧版 webplus 站点：https://webplus.scau.edu.cn/_s82/main.psp ✅
- 师资队伍专用 webplus 入口（3 个视图）：
  - 按职称：http://webplus.scau.edu.cn/_s82/_t1734/szdwwazcw/list.psp ✅
  - 按系室：http://webplus.scau.edu.cn/_s82/_t1734/szdwwaxsw/list.psp （未确认）
  - 按一级学科：https://webplus.scau.edu.cn/_s82/_t1734/szdwwyjxkw/list.psp （未确认）
  - 杰出人才：http://webplus.scau.edu.cn/_s82/_t1734/jcrc_18727/list.psp （未确认）

---

### 2.9 海洋学院 https://hy.scau.edu.cn/

- **旧版入口**：https://webplus.scau.edu.cn/_s125/_t1778/main.psp ✅（站点 ID `_s125`，模板 `_t1778`；页面顶部 banner 即指向此地址）
- 路由风格：两者都有（命名栏目 + 数字栏目 `/5379`、`/5381`、`/5384`、`/5407`）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://hy.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /xyxw/list.htm | 718 条 / 52 页，主新闻栏目，c19878 |
| 党群动态（党建） | /dqdt/list.htm | 195 条 / 14 页，c9366 |
| 教工通知 | /jgtz2026/list.htm | 40 条 / 3 页，c19883 |
| 学生通知 | /xstz2026/list.htm | c5388，未确认 |
| 教育教学 | /wkjx/list.htm | c8914，未确认 |
| 学术科研 | /xsky/list.htm | 21 条 / 2 页，c19808 |
| 学生活动 | /xshd2026/list.htm | c19885，未确认 |
| 信息公开 | /xxgk/list.htm | c19871，未确认 |
| 学生工作 | /xsgz/list.htm | 6 条 |
| 学生工作—通知公告 | /tzgg/list.htm | 未确认 |
| 学院概况 | /5379/list.htm | 栏目组 |
| 学院简介 | /5399/list.htm | |
| 学科专业 | /5400/list.htm | |
| 现任领导 | /xrld/list.htm | |
| 行政教辅人员 | /xzjfry/list.htm | |
| 辅导员 | /fdy/list.htm | |
| 实验中心人员 | /syzxry/list.htm | |
| 校院标识 | /xyyhyq/list.htm | |
| 师资队伍 | /tpzj/list.htm | 栏目组 |
| 特聘专家 | /tpzj/list.htm | |
| 海洋资源与环境系 | /hyzyyhjx/list.htm | |
| 水生动物医学系 | /ssdwyxx/list.htm | |
| 水产养殖系 | /scyzx/list.htm | |
| 水生动物营养与饲料科学系 | /ssdwyyyslkxx/list.htm | |
| 退休教师 | /txjs/list.htm | |
| 学院建设 | /5381/list.htm | 栏目组 |
| 学位点建设 | /xwdjs/list.htm | |
| 专业建设 | /zyjs/list.htm | |
| 学科建设 | /xkjs/list.htm | |
| 规章制度 | /gzzd_19517/list.htm | |
| 党群工作 | /5382/list.htm | |
| 博士后之家 | /bshzp/list.htm | 2 条（名单表格） |
| 博士后—流动站简介 | /ldzjj/list.htm | 未确认 |
| 博士后—合作导师信息 | /hzdsxx/list.htm | 未确认 |
| 博士后—通知公告 | /xgtz/list.htm | 未确认 |
| 招生就业 | /5384/list.htm | 2 条 |
| 招生就业—招聘实习 | /5407/list.htm | 未确认 |
| 招生就业—招生宣传 | /5408/list.htm | 未确认 |
| 校友专栏 | /5385/list.htm | |
| 校友风采 | /xyfc/list.htm | 未确认 |
| 校友活动 | /xyhd/list.htm | 未确认 |

#### 子站点：海洋学院实验教学中心 https://hy.scau.edu.cn/hysyzx/ ✅

- 旧版入口：http://webplus.scau.edu.cn/hysyzx/main.psp ；旁路 http://webplus.scau.edu.cn/_s287/main.psp
- 列表页（前缀 `https://hy.scau.edu.cn/hysyzx`）：

| 栏目 | 列表页 |
|---|---|
| 中心概况 | /zxgk/list.htm |
| 中心简介 | /zxjj/list.htm |
| 师资队伍 | /szdw/list.htm |
| 实验教学体系 | /syjxtx/list.htm |
| 实验教学方法与手段 | /syjxffysd/list.htm |
| 运行机制 | /yxjz/list.htm |
| 规章制度 | /gzzd/list.htm |
| 国家级制度 | /gjjzd/list.htm |
| 校级制度 | /xjzd/list.htm |
| 院级制度 | /yjzd/list.htm |
| 实验教学 | /syjx/list.htm |
| 实验课程 | /sykc/list.htm |
| 海洋科学专业 | /hykxzy/list.htm |
| 水产养殖学专业 | /scyzxzy/list.htm |
| 实验室概况 | /sysgk/list.htm |
| 实验仪器 | /syyq/list.htm |
| 实验仪器概况 | /syyqgk/list.htm |
| 教学仪器 | /jxyq/list.htm |
| 实践创新 | /sjcx/list.htm |
| 课程实习 | /kcsx/list.htm |
| 专业实习 | /zysx/list.htm |
| 创新创业 | /cxcy/list.htm |
| 教学实践基地 | /jxsjjd/list.htm |
| 实践活动 | /sjhd/list.htm |
| 教学改革 | /jxgg/list.htm |
| 教学质量工程项目 | /jpkc/list.htm |
| 教改项目 | /jgxm/list.htm |
| 教学成果 | /jxcg/list.htm |
| 虚拟仿真实验 | /xnfzsys/list.htm |
| 珊瑚礁生态系统调查虚拟仿真实验 | /shjstxtdcxnfzsy/list.htm |
| 近海海洋生物调查虚拟仿真实验 | /jhhyswdcxnfzsy/list.htm |
| 网络资源 | /wlzy/list.htm |
| 实验室安全 | /sysaq/list.htm |
| 安全宣传 | /aqxc/list.htm |
| 安全检查 | /aqjc/list.htm |
| 一月一度安全检查 | /yyydaqjc/list.htm |
| 年度安全总结报告 | /ndaqzjbg/list.htm |
| 危险源和风险点 | /wxyhfxd/list.htm |
| 安全考试 | /aqks/list.htm |
| 开放共享 | /kfgx/list.htm |
| 实验室开放共享项目 | /syskfgxxm/list.htm |
| 实验室预约流程 | /sysyywlcw/list.htm |
| 仪器共享 | /yqgx/list.htm |
| 下载中心 | /xzzx/list.htm |
| 表格模板 | /bgmb/list.htm |
| 操作指引 | /czzy/list.htm |
| 中心新闻 | /zxxw/list.htm |
| 实验教学公告 | /syjxgg/list.htm |
| 实践课程大纲 | /kcdl/list.htm |
| 本科教学实验室 | /bkjxsys/list.htm |

- 外部快速通道：实验安全考试系统 http://labsra.scau.edu.cn/ ；学校虚拟仿真实验平台 http://xnfzsyjx.scau.edu.cn/virexp/casLogin ；国家虚拟仿真实验平台 http://www.ilab-x.com

---

### 2.10 生命科学学院 https://life.scau.edu.cn/

- **旧版入口**：https://webplus.scau.edu.cn/_s83/main.psp ✅（站点 ID `_s83`；站内无显式「旧版」链接，但「联系我们」指向该站）
- 英文版 `https://life.scau.edu.cn/life_en/` → **重定向回主站，未确认**
- 路由风格：两者都有（数字栏目 `/10056`、`/10123` + 命名栏目；部分正文仍为 `.psp`）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://life.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院动态 | /xydt/list.htm | 259 条 / 19 页，c19095 |
| 通知公告 | /tzgg/list.htm | 645 条 / 47 页，c19097 |
| 通知公告—教师通知 | /jstz/list.htm | |
| 通知公告—学生通知 | /xstz/list.htm | |
| 通知公告—学术通知 | /xstz_19158/list.htm | |
| 学术动态 | /xsdt/list.htm | 83 条 / 6 页，c19096 |
| 讲座报告 | /jzbg/list.htm | 55 条 / 4 页，c19052 |
| 快捷导航 | /kjrk1/list.htm | 栏目组 |
| 学院概况 | /10056/list.htm | 栏目组 |
| 学院简介 | /10091/list.htm | |
| 立院先贤 | /10092/list.htm | |
| 历届领导 | /10093/list.htm | |
| 现任领导 | /10094/list.htm | |
| 机构设置 | /10095/list.htm | |
| 党群组织 | /10096/list.htm | |
| 师资队伍 | /10057/list.htm | 栏目组 |
| 师资概况 | /10098/list.htm | |
| 杰出人才 | /10099/list.htm | |
| 专业教师 | /3077/list.htm | |
| 管理人员 | /glry/list.htm | |
| 兼职教授、客座教授 | /jzwkzjs/list.htm | |
| 退休教工 | /txjs/list.htm | |
| 科学研究 | /10058/list.htm | 栏目组 |
| 科研成果 | /10103/list.htm | |
| 科研平台 | /10101/list.htm | |
| 科研团队 | /10102/list.htm | |
| 学术交流 | /10104/list.htm | |
| 学科方向 | /10105/list.htm | |
| 实验室建设 | /10150/list.htm | |
| 本科生培养 | /10059/list.htm | 栏目组 |
| 本科—专业设置 | /10106/list.htm | |
| 本科—培养方案 | /10107/list.htm | |
| 本科—教学大纲 | /10108/list.htm | |
| 本科—教学成果 | /10109/list.htm | |
| 本科—教研与改革 | /jyygg/list.htm | |
| 本科—智慧课程 | /zhkc/list.htm | |
| 研究生培养 | /10060/list.htm | 栏目组 |
| 研究生—培养方案 | /10111/list.htm | |
| 研究生—学位工作 | /10112/list.htm | |
| 研究生—校外导师 | /xwds/list.htm | |
| 研究生—文档下载 | /10113/list.htm | |
| 博士后培养 | /10141/list.htm | 栏目组 |
| 博士后—流动站简介 | /10480/list.htm | |
| 博士后—合作导师 | /10481/list.htm | |
| 博士后—博士后招聘 | /10479/list.htm | |
| 博士后—博士后管理 | /10482/list.htm | |
| 招生就业 | /10061/list.htm | 栏目组 |
| 招生就业—本科招生 | /bkzs/list.htm | |
| 招生就业—研究生招生 | /yjszs/list.htm | |
| 招生就业—就业情况 | /10117/list.htm | |
| 党建思政 | /10063/list.htm | 栏目组 |
| 党建—组织架构 | /10132/list.htm | |
| 党建动态 | /10133/list.htm | 101 条 / 8 页 |
| 党建—支部风采 | /10134/list.htm | |
| 党建—党务指南 | /10135/list.htm | |
| 党建—党建引领 | /ltgzs/list.htm | |
| 学生工作 | /10062/list.htm | 栏目组 |
| 学工动态 | /10123/list.htm | |
| 学工—团学组织 | /10124/list.htm | |
| 学工—本科生工作 | /bksgz/list.htm | |
| 学工—研究生工作 | /yjsgz/list.htm | |
| 学工—文档下载 | /10131/list.htm | |
| 校友之家 | /xyzj/list.htm | 栏目组 |
| 校友工作 | /xygz/list.htm | |
| 校友风采 | /xyfc_17408/list.htm | |
| 生物化学实验技能大赛 | /shds/list.htm | 独立赛事栏目组 |
| 生化大赛—第二十五届 2026 | /deswjw2026n/list.htm | 3 条，c20173 |
| 生化大赛—第二十四届 2025 | /dessjw2025n/list.htm | |
| 生化大赛—第二十三届 2024 | /dessjw2024n/list.htm | |
| 生化大赛—第二十二届 2023 | /desejw2023n/list.htm | |
| 生化大赛—第二十一届 2022 | /desyjw2022n/list.htm | |
| 生化大赛—第二十届 2021 | /desjw2021n/list.htm | |
| 生化大赛—第十九届 2020 | /dsjjw2020n/list.htm | |
| 生化大赛—第十八届 2019 | /dsbjw2019n/list.htm | |
| 生化大赛—第十七届 2018 | /dsqjw2018n/list.htm | |
| 生化大赛—往届大赛 | /wjds/list.htm | |

#### 子站点 / 下属机构

- **农业部转基因植物及植物用微生物环境安全监督检验测试中心（广州）**：https://swjsxy.scau.edu.cn/ ✅
  - 英文版：https://swjsxy.scau.edu.cn/jczx/
  - 列表页：`/3525/list.htm` 中心简介、`/3631/list.htm`、`/3632/list.htm` 组织机构、`/3633/list.htm` 中心成员、`/3526/list.htm` 服务项目、`/3634/list.htm` 检测服务、`/3635/list.htm` 技术咨询服务、`/3527/list.htm` 业务办理、`/3528/list.htm` 计量资格、`/3529/list.htm` 科技知识、`/3530/list.htm` 客户留言、`/3531/list.htm` 联系我们、`/alzs/list.htm` 案例展示
  - 旧入口：http://202.116.160.8/_s90/... （站点 ID `_s90`）
- 会议室预约系统：http://skhysjy.scau.edu.cn/index.html （未确认）

---

### 2.11 工程学院 https://gcxy.scau.edu.cn/

- 旧版入口：**未发现**（无「旧版」链接）；但页脚保留旧版数字栏目 `/2084`–`/2091`
- 英文版 `https://gcxy.scau.edu.cn/gcxyen/` → **重定向回主站，未确认**
- 路由风格：两者都有（命名栏目 + 数字栏目 `/2104`、`/2105`）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://gcxy.scau.edu.cn`） | 说明 |
|---|---|---|
| 新闻动态 | /2104/list.htm | 350 条 / 18 页，每页 20 条 |
| 通知公告 | /2105/list.htm | 223 条 / 12 页 |
| 党建动态 | /zbsz/list.htm | |
| 学术交流 | /xsjl_16788/list.htm | 33 条，工程名师名家论坛 / 永根大讲堂，c16788 |
| 学生园地 | /xsyd/list.htm | c16789 |
| 视频展示（招生宣传） | /spzs/list.htm | 8 条，c16531 |
| 学子风采 | /xzfc/list.htm | 9 条，c16535 |
| 学科介绍（招生） | /zyjs/list.htm | |
| 学院概况 | /xygk/list.htm | 栏目组 |
| 学院简介 | /xyjj/list.htm | |
| 机构设置 | /jgsz/list.htm | |
| 现任领导 | /xrld/list.htm | |
| 师资力量 | /szll/list.htm | 栏目组 |
| 师资—农业工程系 | /nygcx_20104/list.htm | 系栏目组 |
| 农工系—正高级 | /zgjwjswyjyw/list.htm | |
| 农工系—副高级 | /fgjwfjswfyjyw/list.htm | |
| 农工系—中级 | /zjwjswzlyjyw/list.htm | |
| 农工系—正高级实验师 | /zgjsys_20131/list.htm | |
| 农工系—高级实验师 | /gjsys_20132/list.htm | |
| 农工系—实验师 | /sys_20133/list.htm | |
| 师资—机械工程系 | /jxgcx_20105/list.htm | 系栏目组 |
| 机械系—正高级 | /zgjwjswyjyw_20111/list.htm | |
| 机械系—副高级 | /fgjwfjswfyjyw_20112/list.htm | |
| 机械系—中级 | /zjwjswzlyjyw_20113/list.htm | |
| 机械系—正高级实验师 | /zgjsys_20134/list.htm | |
| 机械系—高级实验师 | /gjsys_20135/list.htm | |
| 机械系—实验师 | /sys_20136/list.htm | |
| 师资—南方农业机械与装备关键技术教育部重点实验室 | /nfnyjxyzbgjjsjybzdsys/list.htm | 实验室栏目组 |
| 重点实验室—正高级 | /zgjsys/list.htm | |
| 重点实验室—副高级 | /gjsys/list.htm | |
| 重点实验室—中级 | /sys/list.htm | |
| 重点实验室—正高级实验师 | /bsh/list.htm | |
| 重点实验室—高级实验师 | /gjsys_20137/list.htm | |
| 重点实验室—实验师 | /sys_20138/list.htm | |
| 师资—党政管理部门 | /dzglbm/list.htm | 栏目组 |
| 党政办 | /dzb/list.htm | |
| 学科办 | /xkb/list.htm | |
| 学工办 | /xgb/list.htm | |
| 党建工作 | /djgz/list.htm | 栏目组 |
| 党建—组织架构 | /dwwy/list.htm | |
| 党建—支部风采 | /zbdt/list.htm | |
| 本科生培养 | /bkspy/list.htm | 栏目组 |
| 本科—招生简章 | /zsjz_16505/list.htm | |
| 本科—专业设置 | /zysz_16506/list.htm | |
| 本科—培养方案 | /pyfa_16507/list.htm | |
| 研究生培养 | /yjspy/list.htm | 栏目组 |
| 研究生—信息公开 | /zsjz/list.htm | |
| 研究生—专业设置 | /zysz/list.htm | |
| 研究生—导师目录 | /dsml/list.htm | 栏目组 |
| 导师目录—博士生导师 | /bssds/list.htm | |
| 导师目录—硕士生导师 | /sssds/list.htm | |
| 研究生—培养方案 | /pyfa/list.htm | |
| 研究生—学位授权点建设年度报告 | /xwsqdjsndbg/list.htm | |
| 科学研究 | /kxyj/list.htm | 栏目组 |
| 科研概况 | /kygk/list.htm | |
| 科研平台 | /kypt/list.htm | |
| 科研团队 | /kytd/list.htm | |
| 科研项目 | /kyxm/list.htm | |
| 科研成果 | /kycg/list.htm | 栏目组 |
| 成果—论文 | /lw/list.htm | |
| 成果—专利 | /zl/list.htm | |
| 成果—获奖 | /hj/list.htm | |
| 学术交流（科研） | /xsjl/list.htm | |
| 学生工作 | /xsgz/list.htm | 2 条 |
| 学工通知 | /xszz/list.htm | |
| 学工公示 | /xsdt/list.htm | |
| 学生组织 | /jycy/list.htm | 栏目组 |
| 学生组织介绍 | /xszzjs/list.htm | |
| 学生动态 | /xsdt_16787/list.htm | |
| 就业创业 | /xsdt_16786/list.htm | |
| 校友工作 | /xygz/list.htm | 7 条 |
| 信息公开 | /ywgk/list.htm | 23 条 / 2 页 |
| 信息公开—规章制度 | /gzzd/list.htm | |
| 信息公开—通知信息 | /tzgg/list.htm | |
| 信息公开—公告公示 | /zxns/list.htm | |
| 信息公开—联系我们 | /lxwm/list.htm | |
| **【旧版遗留】科学研究** | /2084/list.htm | 页脚链接，未确认 |
| **【旧版遗留】科研项目** | /2085/list.htm | 页脚链接，未确认 |
| **【旧版遗留】科研成果** | /2086/list.htm | 页脚链接，未确认 |
| **【旧版遗留】学术交流** | /2087/list.htm | 页脚链接，未确认 |
| **【旧版遗留】科研基地** | /2088/list.htm | 页脚链接，未确认 |
| **【旧版遗留】论文** | /2089/list.htm | 页脚链接，未确认 |
| **【旧版遗留】专利** | /2090/list.htm | 页脚链接，未确认 |
| **【旧版遗留】获奖** | /2091/list.htm | 页脚链接，未确认 |

#### 子站点 / 下属机构

- 本科生学业导师管理系统：http://222.201.225.29/ （未确认）
- 课程思政资源平台：http://222.201.225.29:8099 （未确认）
- 招生政策（校级）：https://zsb.scau.edu.cn/4284/list.htm

---

### 2.12 食品学院 https://spxy.scau.edu.cn/

- 旧版入口：未发现（仅有后台入口）
- 路由风格：两者都有（旧版数字栏目 `/6186`、`/6187` + 新版语义栏目）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://spxy.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院要闻 / 新闻动态 | /6186/list.htm | 869 条，分页至 list63 |
| 学院通告 / 通知公告 | /6187/list.htm | 1335 条，分页至 list96 |
| 思政动态 | /szdt/list.htm | 499 条，分页至 list36 |
| 本科生教育 | /bksjy/list.htm | 394 条，c10715 |
| 研究生教育 | /yjsjy/list.htm | 182 条，c10716 |
| 媒体食品 | /jyxx/list.htm | 177 条（外媒报道，多为外链） |
| 院务公开 | /6192/list.htm | 107 条 |
| 学术交流（食品大讲堂） | /xsjl/list.htm | 73 条，c17186 |
| 党建之窗 | /6179/list.htm | 83 条 |
| 学生风采 | /xsfc/list.htm | |
| 学生工作 | /6180/list.htm | |
| 辅导员信息 | /fdyxx/list.htm | |
| 班主任信息 | /bzrxx/list.htm | |
| 学生组织 | /xszz/list.htm | |
| 奖助学金 | /jzxj/list.htm | |
| 招生就业 | /6181/list.htm | |
| 本科生招生 | /6234/list.htm | |
| 招生计划 | /6242/list.htm | |
| 各专业历年录取情况 | /6243/list.htm | |
| 本科生历年就业情况 | /6245/list.htm | |
| 本科生各专业升学情况 | /6249/list.htm | |
| 专业介绍 | /zyjs/list.htm | |
| 师兄师姐说专业 | /sxsjszy/list.htm | |
| 招生简章（本科） | /zssc/list.htm | |
| 研究生招生 | /6235/list.htm | |
| 招生简章（研究生） | /zsjz/list.htm | |
| 报考我院六大理由 | /bkldly/list.htm | |
| 食品学院招生视频 | /spxyzssp/list.htm | |
| 校友园地 | /6182/list.htm | |
| 校友风采 | /xyfc/list.htm | |
| 校友活动 | /xyhd/list.htm | |
| 学院概况 | /6175/list.htm | |
| 学院简介 | /6197/list.htm | |
| 学科专业及机构设置 | /6198/list.htm | |
| 现任领导 | /6199/list.htm | |
| 历任领导 | /6200/list.htm | |
| 学术、学位评定委员会 | /6202/list.htm | |
| 党政管理 | /dzgl/list.htm | |
| 院党委 | /dwwyh_8972/list.htm | |
| 各系负责人 | /6201/list.htm | |
| 关工委 | /ggw/list.htm | |
| 院工会 | /ygh/list.htm | |
| 院团委、学工办 | /ytwwxgb/list.htm | |
| 党政办公室 | /dzbgs/list.htm | |
| 教学办公室 | /jxbgs/list.htm | |
| 实验中心 | /syzx/list.htm | |
| 学科建设 | /xkjs/list.htm | |
| 学科简介 | /xkjj/list.htm | |
| 学科设置 | /xksz/list.htm | |
| 重点学科 | /zdxk/list.htm | |
| 博士后流动站 | /bsh/list.htm | |
| 学科团队 | /xktd/list.htm | |
| 学科动态 | /xkdt/list.htm | |
| 师资力量 | /6203/list.htm | |
| 队伍概况 | /dwgk/list.htm | |
| 师资信息（按姓氏笔划） | /szxx/list.htm | |
| 教授 | /6298/list.htm | |
| 副教授 | /6299/list.htm | |
| 中级 | /6300/list.htm | |
| 高级实验师 | /gjsys/list.htm | |
| 实验师 | /sys/list.htm | |
| 客座教授 | /kzjs/list.htm | |
| 科研推广 | /6177/list.htm | |
| 科研项目 | /6213/list.htm | |
| 科研成果 | /6214/list.htm | |
| 科研平台 | /6215/list.htm | |
| 产学研合作 | /cxyhz/list.htm | |
| 校企合作 | /xqhz_16722/list.htm | |
| 企业展示 | /qyzs_16723/list.htm | |
| 社会效应 | /shxy_16724/list.htm | |
| 人才培养 | /6178/list.htm | |
| 本科生（人才培养） | /6217/list.htm | |
| 专业设置 | /6222/list.htm | |
| 培养方案（本科） | /6223/list.htm | |
| 教学实习基地 | /6224/list.htm | |
| 教学成果 | /6225/list.htm | |
| 精品课程 | /6226/list.htm | |
| 研究生（人才培养） | /6218/list.htm | |
| 研究生培养方案 | /6228/list.htm | |
| 研究生各专业介绍 | /6229/list.htm | |
| 学位授予 | /6230/list.htm | |
| 博士生导师介绍 | /6231/list.htm | |
| 硕士生导师介绍 | /6232/list.htm | |
| 2026 年硕士推免 | /2026nhnnydxssyjslhpyzxxwdsjjwspxyw/list.htm | |
| 技能考评 | /yqzl/list.htm | |
| 招生简介（技能考评） | /zsjj/list.htm | |

#### 子站点 / 下属机构

- **英文版**：https://spxy.scau.edu.cn/spxy_en/ ✅
  - 列表页：`/spxy_en/5249/list.htm`（College Introduction，下含 5254/5255/5256）、`/spxy_en/5250/list.htm`（Compacts at Home and Abroad）、`/spxy_en/5251/list.htm`（Faculty）、`/spxy_en/5252/list.htm`（About Us）、`/spxy_en/5253/list.htm`（Contact Us）
- **专业认证专题站**：https://spxy.scau.edu.cn/sprz/ ✅
  - 列表页：`/sprz/zyjs/list.htm`、`/sprz/spzlyaq/list.htm`、`/sprz/spkxygc/list.htm`、`/sprz/szdw/list.htm`、`/sprz/spzlyaqzy_19858/list.htm`、`/sprz/spkxygczy_19859/list.htm`、`/sprz/pymb/list.htm`、`/sprz/spzlyaqzy_19860/list.htm`、`/sprz/spkxygczy_19861/list.htm`、`/sprz/byyq/list.htm`、`/sprz/spzlyaqzy_19862/list.htm`、`/sprz/spkxygczy_19863/list.htm`、`/sprz/kctx/list.htm`、`/sprz/spzlyaqzy/list.htm`、`/sprz/spkxygczy/list.htm`、`/sprz/zctj/list.htm`、`/sprz/spzlyaqzy_19864/list.htm`、`/sprz/spkxygczy_19865/list.htm`、`/sprz/jxzd/list.htm`、`/sprz/xwdt/list.htm`、`/sprz/rzzs/list.htm`、`/sprz/wjzl/list.htm`
- **就业与创业信息网**：https://spxy.scau.edu.cn/jiuye/ ✅
  - 列表页：`/jiuye/main.htm`、`/jiuye/16141/list.htm`（生源信息）、`/jiuye/16142/list.htm`（最新动态）、`/jiuye/16143/list.htm`（就业百科）、`/jiuye/16144/list.htm`（合作企业）、`/jiuye/16145/list.htm`（创业支持）、`/jiuye/16156/list.htm`（招聘信息）、`/jiuye/16157/list.htm`（友情转载）、`/jiuye/jcjy/list.htm`（基层就业）、`/jiuye/gxjmhqyxx/list.htm`、`/jiuye/16147/list.htm`（学生风采）、`/jiuye/16149/list.htm`、`/jiuye/16150/list.htm`、`/jiuye/16151/list.htm`、`/jiuye/16152/list.htm`、`/jiuye/16148/list.htm`（联系我们）、`/jiuye/syjh/list.htm`（师友计划）、`/jiuye/16154/list.htm`（导师风采）、`/jiuye/16155/list.htm`（师友动态）、`/jiuye/cxcycgz/list.htm`、`/jiuye/yqlj/list.htm`

---

### 2.13 水利与土木工程学院 https://wcce.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：两者都有（旧版数字栏目 `/4274`、`/4275` + 新版语义栏目 `/djdt`、`/xsdt`、`/jzbg`）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://wcce.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院动态 | /4274/list.htm | 184 条，c4274 |
| 通知公告 | /4275/list.htm | 133 条，c4275 |
| 党建工作（动态） | /djdt/list.htm | 22 条，c13343 |
| 学生工作（动态） | /xsdt/list.htm | 152 条，c13339 |
| 政务公开 | /xxgk/list.htm | 20 条，c13512 |
| 讲座报告 | /jzbg/list.htm | 20 条，c13648 |
| 就业 | /jy/list.htm | 空栏目 |
| 教学科研 | 未确认 | 首页「更多+」错误指向 `/jy/list.htm`；内容栏目 c17467 |
| 党务公开 | /dwgk/list.htm | |
| 政务公开（子项） | /zwgk/list.htm | |
| 资料下载 | /zlxz/list.htm | |
| 学术交流 | /xsjl/list.htm | |
| 出国（境）留学 | /lgwjwlx/list.htm | |
| 博士后招聘公告 | /bshzpgg/list.htm | |
| 博士后培养 | /bshpy/list.htm | |
| 博士后流动站简介 | /bshldzjj/list.htm | |
| 博士后合作导师 | /bshhzdsjs/list.htm | |
| 党群工作 | /djgz/list.htm | |
| 党建工作（党群下级） | /djgz_13503/list.htm | |
| 规章制度（党建） | /gzzd/list.htm | |
| 支部风采 | /jczz/list.htm | |
| 工会工作 | /ghgz/list.htm | |
| 学生工作（党群下级） | /xsgz/list.htm | |
| 团委学生会 | /twxsh/list.htm | |
| 创新创业 | /xkjs_13642/list.htm | |
| 学科竞赛 | /xkjs_13646/list.htm | |
| 学子风采 | /xzfc/list.htm | |
| 班主任队伍 | /bzrdw/list.htm | |
| 人才培养 | /rcpyw/list.htm | |
| 本科生培养 | /bkspy/list.htm | |
| 规章制度（本科） | /gzzd_13643/list.htm | |
| 专业设置及介绍 | /zyszjjs/list.htm | |
| 培养方案（本科） | /pyfa/list.htm | |
| 实践教学平台 | /sjjxpt/list.htm | |
| 专业认证 | /zyrz_18113/list.htm | |
| 教学成果 | /jxcg/list.htm | |
| 研究生培养 | /yjspy/list.htm | |
| 学科介绍（研究生） | /xkjs_13561/list.htm | |
| 培养方案（研究生） | /pyfa_13562/list.htm | |
| 联合培养基地 | /lhpyjd/list.htm | |
| 科学研究 | /kxyjw/list.htm | |
| 学科介绍（科研） | /xkjs/list.htm | |
| 科研成果 | /kycg/list.htm | |
| 项目团队 | /xmtd/list.htm | |
| 招生就业 | /zsjyw/list.htm | |
| 研究生招生 | /yjszs_13567/list.htm | |
| 本科生招生 | /zs/list.htm | |
| 招生简章 | /bkszs/list.htm | |
| 招生计划 | /yjszs_13566/list.htm | |
| 招生概况 | /zsgk_13574/list.htm | |
| 校友工作 | /xygzw/list.htm | |
| 历届校友 | /ljxy/list.htm | |
| 校友会 | /xyh/list.htm | |
| 校友会章程 | /xyhzc/list.htm | |
| 理事会成员 | /lshcy/list.htm | |
| 联系方式（校友会） | /lxfs/list.htm | |
| 校友捐赠 | /xyjz/list.htm | |
| 基金管理办法 | /jjglbf/list.htm | |
| 捐赠方式 | /jzfs/list.htm | |
| 捐赠项目 | /jzxm/list.htm | |
| 学院概况 | /xygkw/list.htm | |
| 学院简介 | /xyjj/list.htm | |
| 现任领导 | /yxld/list.htm | |
| 机构设置 | /jgsz/list.htm | |
| 师资队伍 | /szdw/list.htm | |
| 师资概况 | /szgk/list.htm | |
| 教师总览 | /jszl/list.htm | |
| 土木工程系 | /tmx/list.htm | |
| 水利水电工程系 | /slsdgcx/list.htm | |
| 办公室 | /bgs/list.htm | |
| 力学与实验教学中心 | /syzx/list.htm | |
| 研究生导师 | /bssds/list.htm | |
| 校外导师 | /xwds/list.htm | |

---

### 2.14 数学与信息学院、软件学院 https://info.scau.edu.cn/

- 旧版入口：未发现显式「旧版」链接；但存在「移除栏目备份2020」父栏目及一批备份栏目
- 英文版 `http://info.scau.edu.cn/info_en/` → 跨域重定向，未确认
- 路由风格：两者都有（旧版数字栏目 `/3749`、`/3758`、`/3759` + 新版语义栏目 `/bksjy`、`/xsdt`）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://info.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /3758/list.htm | 首页「更多>>」指向 |
| 学术动态 | /xsdt/list.htm | 166 条，c12892 |
| 通知（父栏目） | /3759/list.htm | 渲染「教工通知」，c3770 |
| 教工通知 | /3770/list.htm | 11 条，c3770 |
| 研究生通知 | /3771/list.htm | c3771 |
| 本科生通知 | /3772/list.htm | c3772 |
| 通知公告 | /tzgg/list.htm | 备份栏目清单中出现 |
| 学院动态 | /3761/list.htm | 备份栏目 |
| 学术新闻 | /3762/list.htm | 备份栏目 |
| 党群动态 | /3763/list.htm | 备份栏目（首页页签正式 URL 未确认） |
| 学科设置 | /3767/list.htm | 备份栏目 |
| 学生动态 | 未确认 | 首页页签 `#notice5`，未取得 list URL |
| 个人中心 | /3757/list.htm | 登录页，含备份栏目清单 |
| **移除栏目备份2020（父）** | /yclmbf2020/list.htm | 备份栏目父页 |
| 教授 | /js/list.htm | 名单列表（备份清单） |
| 副教授 | /fjs/list.htm | |
| 讲师 | /js_3820/list.htm | |
| 班主任 | /3796/list.htm | |
| 辅导员 | /3797/list.htm | |
| 双周学习 | /szxx/list.htm | 备份栏目 |
| 校友之家 | /xyzj/list.htm | 备份栏目 |
| 学科建设（备份） | /3753/list.htm | |
| 人才培养（备份） | /3752/list.htm | |
| 飘窗 | /3779/list.htm | |
| exp1 / exp2 / exp3 | /3787/list.htm、/3788/list.htm、/exp3/list.htm | 测试栏目 |
| 老师介绍（后台） | /lsjswhtw/list.htm | 后台栏目 |
| 学院概况 | /3749/list.htm | |
| 学院简介 | /3765/list.htm | |
| 组织架构 | /3766/list.htm | |
| 现任领导 | /3812/list.htm | |
| 学术/学位/教学/督导委员会 | /xswxwwyh/list.htm | |
| 党建工作 | /3750/list.htm | |
| 组织设置 | /3789/list.htm | |
| 支部风采 | /zbfc/list.htm | |
| 师资队伍 | /3751/list.htm | |
| 师资概况 | /szgk/list.htm | |
| 各系教师 | /gxjs/list.htm | |
| 研究生导师 | /yjsds_11779/list.htm | |
| 本科生教育 | /bksjy/list.htm | |
| 专业设置（本科） | /zysz/list.htm | |
| 优秀课程 | /jpkc/list.htm | |
| 培养方案（本科） | /pyfa/list.htm | |
| 教学平台 | /jxpt/list.htm | |
| 实践基地 | /sjjd/list.htm | |
| 产业学院 | /cyxy/list.htm | |
| 研究生教育 | /yjsjy/list.htm | |
| 专业设置（研究生） | /zysz_11789/list.htm | |
| 精品课程 | /jpkc_11790/list.htm | |
| 培养方案（研究生） | /pyfa_11791/list.htm | |
| 导师选聘 | /dsxp/list.htm | |
| 学位授权点建设年度报告 | /xwsqdjsndbg/list.htm | |
| 规章制度（研究生） | /gzzd/list.htm | |
| 科学研究 | /kxyj/list.htm | |
| 学科建设 | /xkjs/list.htm | |
| 科研平台 | /kypt/list.htm | |
| 学生工作 | /3760/list.htm | |
| 学工队伍 | /xgdw/list.htm | |
| 学生组织 | /xszz/list.htm | |
| 科创竞赛 | /3755/list.htm | |
| 奖助学金 | /jzxj/list.htm | |
| 招生宣传 | /zsxc/list.htm | |
| 报考指南 | /bkzn/list.htm | |
| 学生风采 | /zsfc/list.htm | |
| 本科生招生 | /bkszs/list.htm | |
| 研究生招生 | /yjszs/list.htm | |
| 博士后之家 | /bshzj/list.htm | |
| 博士后流动站简介 | /ldzjj/list.htm | |
| 导师信息（博士后） | /hzdsxx/list.htm | |

---

### 2.15 人工智能与低空技术学院 https://dzxy.scau.edu.cn/

- **旧版入口**：https://dzxy.scau.edu.cn/_s156/_t432/main.psp ✅
  （原「电子工程学院（人工智能学院）」旧版整站，含 CN 入口 `/_s156/main.psp` 与 EN 入口 `http://dzxy.scau.edu.cn:88`）
- 路由风格：两者都有（新版语义栏目 + 旧版 `/_t432/NNNN/list.htm`、`/_s156/NNNN/list.psp`）

#### 信息发布（列表）页面（新版）

| 栏目名称 | 列表页 URL（前缀 `https://dzxy.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院动态 | /xydt/list.htm | 509 条，c9671，分页至 list37 |
| 通知 | /tz/list.htm | 268 条，c9673，分页至 list20 |
| 讲座 | /gg/list.htm | 24 条，c9674 |
| 公示 | /gs/list.htm | c9675 |
| 教学信息 | /jxxx/list.htm | c9683 |
| 科研信息 | /kyxx/list.htm | c9684 |
| 学术交流 | /jlhd/list.htm | c9685 |
| 学工动态 | /xgdt/list.htm | c9686 |
| 团学工作 | /twgz/list.htm | c9687 |
| 就业资源 | /jyxx_10370/list.htm | c10370 |
| 创新创业 | /cxcy/list.htm | c18223 |
| 专题链接 | /ztlj/list.htm | |
| 博士之家 | /bshzj/list.htm | |
| 学院招生 | /xyzs/list.htm | |
| 学院概况 | /xygkw/list.htm | |
| 学院简介 | /xyjj/list.htm | |
| 领导班子 | /ldbz/list.htm | |
| 机构设置 | /jgsz/list.htm | |
| 师资队伍/专家教授 | /zjjs/list.htm | |
| 博士生导师 | /bssds/list.htm | |
| 学术型硕士导师 | /xsxssds/list.htm | |
| 学术型—教授、正高 | /js/list.htm | |
| 学术型—副教授、副高 | /fjs/list.htm | |
| 学术型—中级、初级 | /js_10018/list.htm | |
| 专业型硕士导师 | /zyxssds/list.htm | |
| 专业型—教授、正高 | /js_10019/list.htm | |
| 专业型—副教授、副高 | /fjs_10020/list.htm | |
| 专业型—中级、初级 | /js_10021/list.htm | |
| 专业教师 | /zyjs/list.htm | |
| 专业建设 | /zyjsw/list.htm | |
| 本科生专业简介 | /zyjj/list.htm | |
| 本科生各专业培养方案 | /gzypyfa/list.htm | |
| 本科生修读指南 | /xdzn/list.htm | |
| 研究生招生专业与培养方案 | /yjszszyypyfa/list.htm | |
| 教育教学 | /jyjxw/list.htm | |
| 教学大纲 | /jxdg/list.htm | |
| 教学改革 | /jxgg/list.htm | |
| 教学研究 | /jxyj/list.htm | |
| 实验室建设 | /sysjs/list.htm | |
| 人才培养方案 | /rcpyw/list.htm | |
| 本科生（培养方案） | /bkspy/list.htm | |
| 研究生（培养方案） | /yjspy/list.htm | |
| 修读指南 | /xdzn_18154/list.htm | |
| 科学研究 | /kxyjw/list.htm | |
| 科研平台 | /kypt/list.htm | |
| 科研成果 | /kycg/list.htm | |
| 科研项目 | /kyxm/list.htm | |
| 科研论文 | /kylw/list.htm | |
| 学生工作 | /fdy_18230/list.htm | |
| 辅导员 | /fdy_18230/list.htm | |
| 班主任 | /bzr/list.htm | |
| 学生组织 | /xszz/list.htm | |
| 文件制度 | /wjzd/list.htm | |
| 招生就业 | /bkszs/list.htm | |
| 本科生招生 | /bkszs/list.htm | |
| 研究生招生 | /yjszs/list.htm | |
| 特色展示（三全育人） | /jyxx/list.htm | |

#### 子站点 / 下属机构

- **党建专题网**：https://dzxy.scau.edu.cn/dzdj/ ✅
  - 列表页：`/dzdj/main.htm`、`/dzdj/djdt/list.htm`（党建动态）、`/dzdj/tzgg/list.htm`（通知公告）、`/dzdj/dxpx/list.htm`（党校培训）、`/dzdj/fzdy/list.htm`（党员发展）、`/dzdj/zbfc/list.htm`（支部风采）、`/dzdj/dyfc/list.htm`（党员风采）、`/dzdj/ztxx/list.htm`（专题学习）、`/dzdj/ztlj/list.htm`（专题链接）
- English 版（新版）：https://dzxy.scau.edu.cn/dzxyen/ （未确认）
- **旧版整站列表页**（前缀 `https://dzxy.scau.edu.cn`）：
  - `/_t432/6960/list.htm`（学院概况）、`/_t432/6969/list.htm`（学院简介）、`/_t432/6971/list.htm`（组织架构）、`/_t432/xygzjx/list.htm`（学院工作简讯）
  - `/_t432/6961/list.htm`（师资队伍）、`/_t432/6972/list.htm`（博士生导师）、`/_t432/6973/list.htm`（学术型硕士导师）、`/_t432/6974/list.htm`（专业型硕士导师）、`/_t432/6975/list.htm`（专业教师）
  - `/_t432/6962/list.htm`（教学管理）、`/_t432/6976/list.htm`（专业简介）、`/_t432/6977/list.htm`（教学改革）、`/_t432/6978/list.htm`（教学成果）、`/_t432/6979/list.htm`（精品课程）
  - `/_t432/6963/list.htm`（科学研究）、`/_t432/6980/list.htm`（科研成果）、`/_t432/6981/list.htm`（科研项目）
  - `/_t432/6964/list.htm`（实验中心）、`/_t432/dzxxgcjxzdsys/list.htm`（电子信息工程教学重点实验室）
  - `/_t432/6965/list.htm`（招生就业）、`/_t432/6986/list.htm`（招聘信息）
  - `/_t432/6966/list.htm`（学生工作）、`/_t432/6987/list.htm`（辅导员）、`/_t432/6988/list.htm`（班主任）、`/_t432/6989/list.htm`（学生组织）、`/_t432/6990/list.htm`（相关政策）
  - `/_t432/6967/list.htm`（党建工作）、`/_t432/6991/list.htm`（党务工作中心）、`/_t432/6992/list.htm`（支部风采）、`/_t432/6993/list.htm`（公示信息）、`/_t432/6994/list.htm`（理论学习）、`/_t432/6995/list.htm`（党员风采）
  - `/_t432/6968/list.htm`（工会风采）、`/_t432/6996/list.htm`（工会介绍）、`/_t432/6997/list.htm`（工会活动）
  - `/_s156/6999/list.psp`（学院新闻）、`/_s156/7000/list.psp`（学生新闻）、`/_s156/7002/list.psp`（学院通知）、`/_s156/7003/list.psp`（教学通知）、`/_s156/7004/list.psp`（科研通知）、`/_s156/7005/list.psp`（学工通知）、`/_s156/7006/list.psp`（招聘信息）、`/_s156/bshzj/list.psp`（博士后之家）、`/_s156/xzzq/list.psp`（下载专区）
  - 旧版英文站：http://dzxy.scau.edu.cn:88
  - 旧版外链：http://scaudianzigongcheng.jz.fkw.com/（本科生招生）、http://job.scautiu.com/（本科生就业）、http://yjsglxt.scau.edu.cn/open/RecruitTkss/ZsDir_View.aspx（研究生招生）

---

### 2.16 材料与化学工程学院 https://cmce.scau.edu.cn/

- 旧版入口：未发现（学院 2025 年 12 月新成立）
- 路由风格：两者都有（旧版数字栏目 `/4553`、`/4639`、`/4640`、`/4581`、`/111` + 新版语义栏目）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://cmce.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻/学院要闻 | /xyxw/list.htm | 61 条，c4637，分页至 list5 |
| 通知公告（父栏目） | /tzgg/list.htm | 106 条，c4638，分页至 list8 |
| 教工通知 | /4639/list.htm | 12 条，c4639 |
| 学生通知 | /4640/list.htm | c4640 |
| 学术讲座（材化论坛） | /4581/list.htm | 10 条，c4581 |
| 科教成果 | /kjcg/list.htm | 6 条，c20496 |
| 学生动态 | /ssdt/list.htm | c20492 |
| 党建工作（动态） | /djdt/list.htm | |
| 党建概况 | /djgk/list.htm | |
| 组织架构（党建） | /zzjg/list.htm | |
| 党务公开 | /dwgk/list.htm | |
| 学院概况 | /4553/list.htm | |
| 学院简介 | /4567/list.htm | |
| 历史沿革 | /lsyg/list.htm | |
| 现任领导 | /xrld/list.htm | |
| 机构设置 | /4564/list.htm | |
| 学院党委会 | /111/list.htm | |
| 学院纪委 | /xyjw/list.htm | |
| 教学指导委员会 | /jxzdwyh/list.htm | |
| 学位评定委员会 | /xswyh/list.htm | |
| 学术委员会 | /xswyh_20688/list.htm | |
| 学院工会 | /xygh/list.htm | |
| 师资力量 | /4568/list.htm | |
| 师资概况 | /szgk/list.htm | |
| 专任教师 | /4568/list.htm | |
| 材料系 | /clx_20584/list.htm | |
| 化工与制药工程系 | /hgyzygcx/list.htm | |
| 实验中心 | /syzx/list.htm | |
| 教授（实验中心） | /js_20597/list.htm | |
| 高级实验师 | /gjsys_20598/list.htm | |
| 实验师 | /sys_20599/list.htm | |
| 博士生导师 | /bssds/list.htm | |
| 硕士生导师 | /sssds/list.htm | |
| 行政教辅人员 | /xzjfry/list.htm | |
| 党政办公室 | /dzbgs/list.htm | |
| 学生工作办公室 | /xgbgs/list.htm | |
| 教学科研办公室 | /jxkybgs/list.htm | |
| 博士后 | /bsh/list.htm | |
| 博士后（名单） | /bsh_20684/list.htm | |
| 联合招收培养博士后 | /lhzspybsh/list.htm | |
| 人才培养 | /rcpy/list.htm | |
| 培养计划 | /rcpy_19698/list.htm | |
| 实践教学基地 | /zyts/list.htm | |
| 研究生联合培养基地 | /jxpt/list.htm | |
| 优秀学子代表 | /pydx/list.htm | |
| 科学研究 | /4555/list.htm | |
| 学科建设 | /6813/list.htm | |
| 科研平台 | /6814/list.htm | |
| 科研团队 | /4582/list.htm | |
| 科研成果 | /4583/list.htm | |
| 学生工作 | /4557/list.htm | |
| 学生组织架构 | /4604/list.htm | |
| 学生动态（学生工作下级） | /4602/list.htm | |
| 招生与就业 | /4558/list.htm | |
| 本科生（招生） | /4615/list.htm | |
| 研究生（招生） | /yjszs/list.htm | |
| 信息公开 | /ywgk/list.htm | |
| 学院文件 | /xywj/list.htm | |
| 学院标识 | /xybs_20474/list.htm | |
| 年度报告 | /ndbg/list.htm | |
| 校友工作 | /xydt/list.htm | |
| 校友服务 | /xyfw_20517/list.htm | |
| 校友动态 | /xydt_20518/list.htm | |
| 校友风采 | /xyfc_20589/list.htm | |
| 联系我们 | /lxwm/list.htm | |

---

### 2.17 生物质学院 https://cfb.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：新版栏目为主

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://cfb.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /xyxw/list.htm | 99 条 / 8 页 |
| 公告 | /gwg/list.htm | 9 条 |
| 媒体报道 | /mtbd/list.htm | 9 条 |
| 教务教学 | /jwjx/list.htm | 7 条 |
| 教工通知 | /jgtz/list.htm | 14 条 |
| 本科生通知 | /bkstz/list.htm | 57 条 / 5 页 |
| 研究生通知 | /yjstz/list.htm | 54 条 / 4 页 |
| 学术讲座 | /xsjz/list.htm | 空 |
| 科研进展 | /kyjz/list.htm | 空 |
| 院务公开（学院规章） | /bszn/list.htm | 7 条（栏目页 `/xxgk/list.htm` 渲染此页） |
| 院内公告 | /zlxz/list.htm | 未确认 |
| 党群工作 | /dqgz/list.htm | 7 条（栏目页 `/szdj/list.htm` 渲染此页） |
| 工会工作 | /ghgz/list.htm | 未确认 |
| 党团活动 | /dthd/list.htm | 未确认 |
| 理论学习 | /llxx/list.htm | 未确认 |
| 学生动态 | /xgdw/list.htm | 12 条（栏目页 `/xsgz/list.htm` 渲染此页） |
| 学生组织 | /xszz/list.htm | 未确认 |
| 创新创业 | /xsst/list.htm | 未确认 |
| 学生风采 | /sqyr/list.htm | 未确认 |
| 奖助学金 | /jzxj/list.htm | 未确认 |
| 师资概况 | /szdw/list.htm | 未确认 |
| 教师名录 | /zjjs/list.htm | 未确认（下设能源系/材料系/家居系，链接均指向此页） |
| 客座教授 | /kzjs/list.htm | 未确认 |
| 博士后之家 | /bshzj/list.htm | 未确认 |
| 人才培养—一流专业 | /ylzy/list.htm | 未确认 |
| 人才培养—本科生 | /bks/list.htm | 未确认 |
| 人才培养—培养方案 | /pyfa/list.htm | 未确认 |
| 人才培养—研究生 | /yjs/list.htm | 未确认 |
| 人才培养—国际教育 | /gjjy/list.htm | 未确认 |
| 人才培养—教学成果 | /jxcg/list.htm | 未确认 |
| 人才培养—基地建设 | /jdjs/list.htm | 未确认 |
| 人才培养—实验教学中心 | /syjxzx/list.htm | 未确认 |
| 科研—学科建设 | /xsdt_19633/list.htm | 未确认 |
| 科研—科研团队 | /kytd/list.htm | 未确认 |
| 科研—科研成果 | /kycg_19637/list.htm | 未确认 |
| 科研—科研平台 | /kycg_19673/list.htm | 未确认 |
| 校友工作—本科生招生 | /bkszs/list.htm | 未确认 |
| 校友工作—研究生招生 | /yjszs/list.htm | 未确认 |
| 校友工作—就业创业 | /jycy/list.htm | 未确认 |
| 学院概况—学院简介 | /xyjj/list.htm | 未确认 |
| 学院概况—现任领导 | /xrld/list.htm | 未确认 |
| 学院概况—机构设置 | /zzjg/list.htm | 未确认 |
| 学院概况—学术委员会 | /xswxwwyh/list.htm | 未确认 |
| 学院概况—联系我们 | /lxwm_19663/list.htm | 未确认 |
| 学院文化—历史沿革 | /lsyg/list.htm | 未确认 |
| 学院文化—历届领导 | /ljld/list.htm | 未确认 |
| 学院文化—学院人物 | /xyrw/list.htm | 未确认 |

---

### 2.18 马克思主义学院 https://mkszyxy.scau.edu.cn/

- **旧版入口**：站点 logo 指向 http://webplus.scau.edu.cn/_s287/main.psp （跨协议跳转，未确认内容）
- 路由风格：新版栏目

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://mkszyxy.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院要闻 | /xydt2/list.htm | 115 条 / 8 页 |
| 教工通知 | /jgtz_16222/list.htm | 21 条 / 2 页 |
| 学生通知 | /xstz_16223/list.htm | 157 条 / 11 页 |
| 党建动态 | /djhd_16221/list.htm | 39 条 / 3 页 |
| 媒体聚焦 | /mtmy/list.htm | 76 条 / 6 页 |
| 学术动态 | /xsdtw/list.htm | 46 条 / 4 页 |
| 学术前沿 | /xsqy/list.htm | 11 条 |
| 教学活动 | /jxdt_16224/list.htm | 35 条 / 3 页 |
| 学工工作 | /xgdt/list.htm | 42 条 / 3 页 |
| 视频资源 | /spzy/list.htm | 10 条 |
| 培训动态 | /pxdt/list.htm | 空 |
| 下载专区 | /xzzq/list.htm | 2 条 |
| 科研成果 | /kycg/list.htm | 抓取失败（跨协议跳转），未确认 |
| 党建工作（学院党委） | /xydw/list.htm | 未确认 |
| 支部建设 | /zbjs/list.htm | 未确认 |
| 学院概况—简介 | /xyjj/list.htm | 未确认 |
| 学院概况—现任领导 | /xrld/list.htm | 未确认 |
| 学院概况—机构设置 | /jgsz/list.htm | 未确认 |
| 学院概况—院徽院训 | /yhyx/list.htm | 未确认 |
| 机构—广东省高校思想政治理论课教学指导委员会 | /gdsgdxxsxzzllkjxzdwyhwy/list.htm | 未确认 |
| 机构—学术委员会 | /xswyh/list.htm | 未确认 |
| 机构—学位评定分委员会 | /xwpdfjwyh/list.htm | 未确认 |
| 机构—教学指导委员会 | /jxzdwyh/list.htm | 未确认 |
| 机构—教学督导委员会 | /jxddwyh/list.htm | 未确认 |
| 机构—教师发展中心 | /jsfzfzx_15522/list.htm | 未确认 |
| 师资—基础教研室 | /jcyjs/list.htm | 未确认 |
| 师资—概论教研室 | /gljys_15227/list.htm | 未确认 |
| 师资—习近平新时代中国特色社会主义思想教研室 | /xsxjys/list.htm | 未确认 |
| 师资—思想道德与法治教研室 | /sxddyfzjys/list.htm | 未确认 |
| 师资—纲要教研室 | /gyyjs/list.htm | 未确认 |
| 师资—形势与政策教研室 | /xszcjys/list.htm | 未确认 |
| 师资—军事理论教研室 | /jsllyjs/list.htm | 未确认 |
| 师资—研究生公共政治理论课教研室 | /yjsggzzllkjys/list.htm | 未确认 |
| 人才培养—本科生培养 | /bkspy/list.htm | 未确认 |
| 人才培养—研究生培养 | /yjspy/list.htm | 未确认 |
| 人才培养—精品课程 | /zsjy_15182/list.htm | 未确认 |
| 学科学术—学位点概况 | /xkgk/list.htm | 未确认 |
| 学科学术—学科简介 | /xkjj/list.htm | 未确认 |
| 学科学术—年度报告 | /ndbg/list.htm | 未确认 |
| 学科学术—研究平台 | /yjpt/list.htm | 未确认 |
| 学科学术—导师队伍 | /xwdjs/list.htm | 未确认 |
| 招生就业—本科招生 | /bkszs/list.htm | 未确认 |
| 招生就业—研究生招生 | /yjszs/list.htm | 未确认 |
| 招生就业—就业服务 | /jyfw/list.htm | 未确认 |
| 培训研修—培训指南 | /pxzn/list.htm | 未确认 |
| 培训研修—联系我们 | /lxwm/list.htm | 未确认 |

---

### 2.19 经济管理学院 https://cem.scau.edu.cn/

- 旧版入口：未发现明确「旧版」链接（主体本身就是 webplus 旧版数字栏目结构）
- 英文站入口：http://cem.scau.edu.cn/cem_en （跨协议跳转，未确认）
- 本科招生站：https://cem.scau.edu.cn/cemzs/ （未确认，`/cemzs/index.htm` 返回 404）
- 内部通告：http://cem.scau.edu.cn/7320/list.htm
- 路由风格：**两者都有**，主体为旧版数字栏目（`/NNNN/list.htm`）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://cem.scau.edu.cn`） | 说明 |
|---|---|---|
| 经管要闻 | /5591/list.htm | 抓取失败（跨协议跳转），URL 已确证存在 |
| 学术动态 | /5592/list.htm | 同上 |
| 通知公告 | /5593/list.htm | 同上；已通过正文页 `2026/1013/c5593a448562/page.htm` 确认栏目存在 |
| 学术活动（讲座/论坛） | /5594/list.htm | 同上 |
| 内部通告 | /7320/list.htm | 同上 |
| 党建工作—机构设置 | /jgsz/list.htm | 4 条（栏目页 `/djgz/list.htm` 渲染此页） |
| 党建工作—通知公告 | /tzgg/list.htm | 4 条 |
| 党建工作—理论学习 | /llxx/list.htm | 抓取失败 |
| 党建工作—工作动态 | /gzdt/list.htm | 抓取失败 |
| 党建工作—社区党建 | /sqdj/list.htm | 未确认 |
| 学生工作—本科生通知公告 | /bkstzgg/list.htm | 抓取失败 |
| 学生工作—研究生通知公告 | /yjstzgg/list.htm | 未确认 |
| 学生工作—团学工作 | /xshd/list.htm | 抓取失败 |
| 学生工作—奖助贷 | /jzd/list.htm | 未确认 |
| 学生工作—就业创业 | /jyzd/list.htm | 抓取失败 |
| 学院概况—简介 | /5640/list.htm | 未确认 |
| 学院概况—历史沿革 | /5641/list.htm | 未确认 |
| 学院概况—院徽院训 | /5642/list.htm | 未确认 |
| 学院概况—现任领导 | /5643/list.htm | 未确认 |
| 学院概况—组织架构 | /5644/list.htm | 未确认 |
| 学院概况—学术学位委员会 | /5645/list.htm | 未确认 |
| 学院概况—系（中心）介绍 | /xwzxwjs/list.htm | 未确认 |
| 学院概况—办事指南 | /5646/list.htm | 未确认 |
| 教学成果—主要成果 | /zycg/list.htm | 未确认 |
| 教学成果—实施成效 | /sscx/list.htm | 未确认 |
| 教学成果—推广应用 | /tgyy/list.htm | 未确认 |
| 教学成果—视频展示 | /spzs/list.htm | 未确认 |
| 教学成果—团队介绍 | /tdjs/list.htm | 未确认 |
| 教学成果—思政育人 | /szyr/list.htm | 未确认 |
| 教育教学—本科生 | /5598/list.htm | 未确认 |
| 教育教学—硕士 | /5599/list.htm | 未确认 |
| 教育教学—博士 | /5600/list.htm | 未确认 |
| 教育教学—MBA | /MBA/list.htm | 抓取失败 |
| 教育教学—实验室建设 | /sysjs/list.htm | 未确认 |
| 师资力量—教师名录 | /5627/list.htm | 未确认 |
| 师资力量—讲座教授 | /5628/list.htm | 未确认 |
| 科学研究—学科点 | /5629/list.htm | 未确认 |
| 科学研究—科研机构 | /5630/list.htm | 未确认 |
| 科学研究—学术交流 | /5631/list.htm | 未确认 |
| 科学研究—科研动态 | /5632/list.htm | 未确认 |
| 对外交流—国际交流项目 | /5633/list.htm | 未确认 |
| 对外交流—国际学术会议 | /5634/list.htm | 未确认 |
| 校友—校友新闻 | /5635/list.htm | 未确认 |
| 校友—地方校友分会 | /5636/list.htm | 未确认 |
| 校友—校友讲座 | /5637/list.htm | 未确认 |
| 校友—校友捐赠 | /5638/list.htm | 未确认 |
| 校友—校友服务 | /5639/list.htm | 未确认 |
| 招生—学术硕士 | /5585/list.htm | 未确认 |
| 招生—博士 | /5586/list.htm | 未确认 |
| 招生—会计硕士 | /5587/list.htm | 未确认 |
| 招生—金融硕士 | /5588/list.htm | 未确认 |
| 招生—农业硕士 | /5589/list.htm | 未确认 |
| 招生—EDP | /5590/list.htm | 未确认 |
| 招生—MBA | /MBA_17375/list.htm | 未确认 |
| 博士后之家 | /bshzj/list.htm | 未确认 |

---

### 2.20 公共管理学院 https://ggglxy.scau.edu.cn/

- **旧版入口**：https://ggglxy.scau.edu.cn/_t206/ ✅（站头「旧版网站」链接；本工具抓取遇跨协议跳转，浏览器可访问）
- 英文版：https://ggglxy.scau.edu.cn/english/ （跨协议跳转，`/english/index.htm` 返回 404）
- 路由风格：新版栏目

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://ggglxy.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /xyxw_11881/list.htm | 674 条 / 49 页 |
| 教工通知 | /jgtz/list.htm | 192 条 / 14 页 |
| 学工通知 | /xgtz/list.htm | 1042 条 / 75 页 |
| 公告公示 | /gs/list.htm | 552 条 / 40 页 |
| 媒体公管 | /mtgg/list.htm | 124 条 / 9 页 |
| 学术动态（学术研究） | /xsdt_11884/list.htm | 306 条 / 22 页 |
| 学术动态（旧栏目） | /xsdt/list.htm | 13 条，最新止于 2020 年 |
| 党建工作 | /djgz2020/list.htm | 274 条 / 20 页 |
| 信息公开—公示 | /gs_17062/list.htm | 抓取失败，未确认 |
| 考勤公示 | /kqgs/list.htm | 未确认 |
| 会议纪要 | /hyjy/list.htm | 未确认 |
| 学院发文 | /xyfw/list.htm | 未确认 |
| 成绩录入 | /cjlr/list.htm | 未确认 |
| 资料下载 | /zlxz/list.htm | 未确认 |
| 其他（信息公开） | /qt/list.htm | 未确认 |
| 党建动态 | /djdt/list.htm | 未确认 |
| 党史学习教育 | /dsxxjy/list.htm | 未确认 |
| 规章制度 | /gzzd/list.htm | 未确认 |
| 党课培训 | /dkpx/list.htm | 未确认 |
| 师资队伍—行政教辅 | /xzjf/list.htm | 未确认 |
| 师资队伍—行政管理系 | /xzglx/list.htm | 未确认 |
| 师资队伍—土地资源管理系 | /tdzyglx/list.htm | 未确认 |
| 师资队伍—公共事业管理系 | /ggsyglx/list.htm | 未确认 |
| 师资队伍—社会保障与风险管理系 | /ldyshbzx/list.htm | 未确认 |
| 师资队伍—社会工作系 | /shgzx/list.htm | 未确认 |
| 研究生导师—硕士生导师 | /sssds_11612/list.htm | 未确认 |
| 研究生导师—博士生导师 | /bssds_16319/list.htm | 未确认 |
| 人才培养—教学简报 | /jxjb/list.htm | 未确认 |
| 人才培养—培养方案 | /pyfa/list.htm | 未确认 |
| 人才培养—实践教学 | /sjjx/list.htm | 未确认 |
| 人才培养—优秀学子 | /yxxz/list.htm | 未确认 |
| 人才培养—教学通知 | /jxtz/list.htm | 未确认 |
| 人才培养—合作办学 | /hzbx/list.htm | 未确认 |
| 人才培养—精品课程 | /jpkc/list.htm | 未确认 |
| 人才培养—就业创业 | /jycy/list.htm | 未确认 |
| 研究生—学术研究生 | /xsyjs/list.htm | 未确认 |
| 研究生—MPA 研究生 | /MPAyjs/list.htm | 未确认 |
| 研究生—MSW 研究生 | /MSWyjs/list.htm | 未确认 |
| 学位点年度报告 | /xwdndbg/list.htm | 未确认 |
| 教务简报 | /jwjb/list.htm | 未确认 |
| 成果荟萃 | /cghc/list.htm | 未确认 |
| 社会服务—服务工作 | /fwgz/list.htm | 未确认 |
| 社会服务—典型案例 | /dxal/list.htm | 未确认 |
| 招生就业—专业视频 | /zysp/list.htm | 未确认 |
| 招生就业—招生材料 | /zscl/list.htm | 未确认 |
| 招生就业—升学就业 | /sxjy/list.htm | 未确认 |
| 招生就业—学子风采 | /xzfc/list.htm | 未确认 |
| MPA 招生 | /MPAzs/list.htm | 未确认 |
| 学生组织—通知 | /xszz/list.htm | 未确认 |
| 学生组织—通知（明细） | /xszztz/list.htm | 未确认 |
| 学生组织—动态 | /xszzdt/list.htm | 未确认 |
| 文件制度 | /wjzd/list.htm | 未确认 |
| 校友风采—历届校友 | /ljxy/list.htm | 未确认 |
| 校友风采—行政管理专业 | /xzglzy/list.htm | 未确认 |
| 校友风采—土地资源管理专业 | /tdzyglzy/list.htm | 未确认 |
| 校友风采—公共事业管理专业 | /ggsyglzy/list.htm | 未确认 |
| 校友风采—社会保障专业 | /ldyshbzzy/list.htm | 未确认 |
| 校友风采—社会工作专业 | /shgzzy/list.htm | 未确认 |
| 校友风采—社会学专业 | /shxzy/list.htm | 未确认 |
| 校友风采—行政管理（专升本） | /xzqyglzy/list.htm | 未确认 |
| 校友风采—公共管理硕士专业 | /ggymszy/list.htm | 未确认 |
| 校友风采—杰出校友 | /jcxy/list.htm | 未确认 |
| 校友风采—校友活动 | /xyhd/list.htm | 未确认 |
| 学院概况—简介 | /xyjj/list.htm | 未确认 |
| 学院概况—现任领导 | /xrld_11745/list.htm | 未确认 |
| 学院概况—历届领导 | /ljld/list.htm | 未确认 |
| 学院概况—组织机构 | /jgsz/list.htm | 未确认 |
| 学院概况—院徽院训 | /yhyx/list.htm | 未确认 |
| 学院概况—20 周年院庆标识 | /20znyqbs/list.htm | 未确认 |

#### 子站点 / 下属机构

- 书记院长信箱：http://estop.scau.edu.cn/phone/detail.html?gid=30212
- 常用链接：OA http://oa.scau.edu.cn/seeyon/ ；网上办事大厅 http://estop.scau.edu.cn/portal/index.jsp ；教务系统 http://jwxt.scau.edu.cn/ ；科研系统 http://202.116.162.70/business/login.jsp

---

### 2.21 人文与法学学院 https://rw.scau.edu.cn/

- 旧版入口：未发现显式链接（但站内大量使用 webplus 数字栏目 `/3691`–`/3694`）
- 路由风格：两者都有（旧版数字栏目 + 新版栏目；另有 `.psp` 后缀页）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://rw.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /3691/list.htm | 359 条 / 26 页 |
| 学术动态 | /3692/list.htm | 75 条 / 6 页 |
| 党务动态 | /3693/list.htm | 空（内容在党建子站） |
| 学生活动 | /3694/list.htm | 18 条 / 2 页 |
| 社会服务 | /shfw/list.htm | 未确认 |
| 媒体人文 | /mtrw/list.htm | 142 条 / 11 页 |
| 教工通知 | /jgtz/list.htm | 26 条 / 2 页 |
| 本科生通知 | /bkstz/list.htm | 405 条 / 29 页 |
| 研究生通知 | /yjstz/list.htm | 111 条 / 8 页 |
| 教务教学 | /jwjx/list.htm | 73 条 / 6 页 |
| 科研成果 | /kycg/list.htm | 84 条 / 6 页 |
| 信息公开—规章制度 | /gzzd_10689/list.htm | 14 条（栏目页 `/xxgk/list.htm` 渲染此页） |
| 信息公开—公示 | /gs/list.htm | 空 |
| 办事指南 | /bszn_9413/list.htm | 未确认 |
| 会议纪要 | /hyjy/list.htm | 未确认 |
| 资料下载 | /zlxz/list.htm | 未确认 |
| 其他（信息公开） | /qt/list.htm | 未确认 |
| 本科生教育—人才培养 | /bksrcpy/list.htm | 未确认 |
| 本科生教育—规章制度 | /gzzd/list.htm | 未确认 |
| 研究生教育—人才培养 | /yjsrcpy/list.htm | 未确认 |
| 研究生教育—规章制度 | /gzzd_9628/list.htm | 未确认 |
| 教学研究与改革 | /jxyjygg/list.htm | 未确认 |
| 实验室建设 | /sysjs_9398/list.htm | 未确认 |
| 教研室建设 | /sysjs/list.htm | 未确认 |
| 实践教学—基地 | /sjjxjd/list.htm | 未确认 |
| 实践教学—活动 | /sjjxhd/list.htm | 未确认 |
| 集雅讲堂 | /jyjt/list.htm | 未确认 |
| 师资—中文系 | /zwx/list.htm | 未确认 |
| 师资—历史系 | /lsx/list.htm | 未确认 |
| 师资—法律系 | /flx/list.htm | 未确认 |
| 师资—硕士导师 | /ssds/list.htm | 未确认 |
| 师资—退休教师 | /txjs/list.htm | 未确认 |
| 民法典普法宣讲团—兼职教授 | /mfdpfjst/list.htm | 未确认 |
| 民法典普法宣讲团—校外专家 | /xwzj/list.htm | 未确认 |
| 民法典普法宣讲团—教授 | /js_11142/list.htm | 未确认 |
| 民法典普法宣讲团—副教授 | /fjs_11143/list.htm | 未确认 |
| 民法典普法宣讲团—讲师 | /js_11144/list.htm | 未确认 |
| 学科分析 | /xkfx/list.htm | 未确认 |
| 科研平台 | /kypt/list.htm | 未确认 |
| 科研团队 | /kytd/list.htm | 未确认 |
| 本科生招生—招生简章 | /zsjz/list.htm | 未确认 |
| 本科生招生—专业介绍 | /zyjs/list.htm | 未确认 |
| 本科生招生—师兄师姐说专业 | /sxsjszy/list.htm | 未确认 |
| 本科生招生—专业宣传视频 | /wawzy/list.htm | 未确认 |
| 本科生招生—作品展 | /wwawzywzpzs/list.htm | 未确认 |
| 本科生招生—生源基地建设 | /syjdjs/list.htm | 未确认 |
| 本科生招生—就业前景 | /jyqj/list.htm | 未确认 |
| 本科生招生—招生计划/历年录取分数 | /zsjhjlqfs/list.htm | 未确认 |
| 本科生招生—往年录取情况 | /wnlqqk/list.htm | 未确认 |
| 研究生招生—学位点概况 | /4036/list.htm | 未确认 |
| 研究生招生—联系我们 | /4042/list.htm | 未确认 |
| 联系我们 | /lxwm_9416/list.htm | 未确认 |
| 学生工作—学工队伍 | /xgdw/list.htm | 未确认 |
| 学生工作—学生组织 | /xszz/list.htm | 未确认 |
| 学生工作—团学组织 | /txgz/list.htm | 未确认 |
| 学生工作—学生会 | /xsh/list.htm | 未确认 |
| 学生工作—党务信息中心 | /dwxxzx/list.htm | 未确认 |
| 学生工作—党务工作室 | /dwgzs/list.htm | 未确认 |
| 学生工作—人文红十之家 | /rwhszh/list.htm | 未确认 |
| 学生工作—人文其他学生工作室 | /rwqtxlgzs/list.htm | 未确认 |
| 学生工作—勤工俭学服务中心 | /qyqgzxfwzx/list.htm | 未确认 |
| 学生工作—就业与创新创业服务中心 | /jyycxcyfwzx_17180/list.htm | 未确认 |
| 学生工作—学生社团 | /xsst/list.htm | 未确认 |
| 学生工作—中文实践教学中心 | /zwsjjxzx/list.htm | 未确认 |
| 学生工作—法律实践教学中心 | /flsjjxzx/list.htm | 未确认 |
| 学生工作—历史实践教学中心 | /lssjjxzx/list.htm | 未确认 |
| 学生工作—集佳书社 | /jjss/list.htm | 未确认 |
| 学生工作—其他队伍 | /qtdw/list.htm | 未确认 |
| 学生工作—校青年志愿者服务队 | /xcqnzyzfwd/list.htm | 未确认 |
| 学生工作—人文艺术团 | /rwyst/list.htm | 未确认 |
| 学生工作—人文运动队 | /rwyd/list.htm | 未确认 |
| 学生工作—三全育人 | /sqyr/list.htm | 未确认 |
| 学生工作—奖助学金 | /jzxj2/list.htm | 未确认 |
| 学生工作—国家风采 | /gjfc_20176/list.htm | 未确认 |
| 学生工作—民法典宣讲 | /mfyl_20177/list.htm | 未确认 |
| 学生工作—三下乡 | /sxx/list.htm | 未确认 |
| 学生工作—人文通讯 | /rwts/list.htm | 未确认 |
| 学生工作—土地日 | /tdr/list.htm | 未确认 |
| 学生工作—法治宣传媒体号 | /fzzsxcmh/list.htm | 未确认 |
| 学生工作—机构管理 | /jgll/list.htm | 未确认 |
| 学生工作—宿舍 | /ss/list.htm | 未确认 |
| 学生工作—数据库 | /sjk/list.htm | 未确认 |
| 学生工作—人文喜讯 | /rwxx/list.htm | 未确认 |
| 工会家园—工会简介 | /ghjj/list.htm | 未确认 |
| 工会家园—教代会 | /jdh/list.htm | 未确认 |
| 工会家园—工会活动 | /ghjdh/list.htm | 未确认 |
| 校友之家—校友联谊会 | /xylyh/list.htm | 未确认 |
| 校友之家—校友动态 | /xydt/list.htm | 未确认 |
| 学院概况—简介 | /xyjj/list.htm | 未确认 |
| 学院概况—组织架构 | /jgsz/list.htm | 未确认 |
| 学院概况—领导班子 | /xrld/list.htm | 未确认 |
| 学院概况—学术学位委员会 | /xswxwwyh/list.htm | 未确认 |
| 学院概况—系所介绍 | /xsjs1/list.htm | 未确认 |
| 学院概况—中国农业历史遗产研究所 | /zgnylsycyjs_8851/list.htm | 未确认 |
| 学院概况—中文系 | /zwx_7502/list.htm | 未确认 |
| 学院概况—历史系 | /lsx_7501/list.htm | 未确认 |
| 学院概况—法律系 | /flx_20234/list.htm | 未确认 |
| 学院概况—视觉标识 | /xysjbs/list.htm | 未确认 |
| 学院概况—院歌 | /yg/list.htm | 未确认 |
| 学院概况—院表情包 | /bqb/list.htm | 未确认 |

#### 子站点 / 下属机构

- **党建工作网**：https://rw.scau.edu.cn/dangjian/main.htm ✅
  - 机构设置 `/dangjian/dwgk/list.htm`；学院党委 `/dangjian/xydw/list.htm`；支部概况 `/dangjian/zbgk/list.htm`；党务工作室 `/dangjian/dwgzs/list.htm`
  - 党建动态 `/dangjian/djdt/list.htm`；新闻报道 `/dangjian/xwbd/list.htm`；通知公告 `/dangjian/tzgg/list.htm`
  - 党团教育 `/dangjian/dtjy/list.htm`；现场教学 `/dangjian/xcjx/list.htm`
  - 支部风采 `/dangjian/zbfc/list.htm`；社区党建 `/dangjian/sqdj/list.htm`；理论学习 `/dangjian/llxx/list.htm`；模范引领 `/dangjian/mfyl/list.htm`；规章制度 `/dangjian/gzzd/list.htm`
- **就业与创新创业服务中心**：https://rw.scau.edu.cn/jicengjiuye/ ✅
  - 生源信息 `/jicengjiuye/4004/list.htm`；招聘资讯 `/jicengjiuye/4005/list.htm`；资讯动态 `/jicengjiuye/4006/list.htm`
  - 就业百科 `/jicengjiuye/4007/list.htm`（简历制作 4013 / 面试技巧 4014 / 职场礼仪 4015 / 政策指南 4016）
  - 学生风采 `/jicengjiuye/4008/list.htm`；创新田园 `/jicengjiuye/4009/list.htm`（导师团队 4017 / 项目团队 4018 / 政策指南 4019）
  - 基层就业 `/jicengjiuye/4010/list.htm`；联系我们 `/jicengjiuye/4011/list.htm`；本科生通知 `/jicengjiuye/bkstz/list.htm`
- **岭南农耕文明重点实验室**：https://rw.scau.edu.cn/lnngwmzdsys/list.htm ✅
  - 子页：`/sysgk/list.htm`（实验室概况）、`/zzjg/list.htm`（组织架构）、`/xsdt/list.htm`（学术动态）、`/xsjl_18273/list.htm`（学术交流）
- 民法典宣讲：https://rw.scau.edu.cn/mfdpf/list.htm
- 人文风采（`.psp`）：https://rw.scau.edu.cn/rwfc/list.psp
- 研究生招生目录（外部系统）：http://yjsglxt.scau.edu.cn/open/Wechat/SsZsZyml/ZymlYx.aspx?xxfs=1&yxsh=010&nd=2024

---

### 2.22 外国语学院 https://sfs.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：两者都有（`/3284/list.htm` 数字栏目 + `/xyld/list.htm` 语义栏目）

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://sfs.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /3514/list.htm | 230 条 / 17 页 |
| 党群新闻 | /3515/list.htm | 未确认 |
| 教师通知 | /3517/list.htm | 117 条 / 9 页 |
| 公告公示 | /3518/list.htm | **1375 条 / 99 页（全站最大栏目）** |
| 党建通知 | /3519/list.htm | 未确认 |
| 学生通知 | /xstzcscj/list.htm | 455 条 / 33 页 |
| 奖助育人 | /3521/list.htm | 未确认 |
| 工作动态 | /3522/list.htm | 未确认 |
| 就业信息 | /3523/list.htm | 未确认 |
| 学术动态（讲座） | /xsdt/list.htm | 5 条 |
| 区域国别研究 | /qygbyj/list.htm | 8 条 |
| 媒体外语 | /mtwy/list.htm | 未确认 |
| 榜样学子 | /byxz/list.htm | 未确认 |
| 图片新闻 | /3509/list.htm | 未确认 |
| 新闻中心 | /3510/list.htm | 未确认 |
| 通知通告 | /3511/list.htm | 未确认 |
| 学生工作（banner 版） | /3512/list.htm | 13 条 |
| 漂浮新闻 | /3513/list.htm | 未确认 |
| banner | /banner/list.htm | 未确认 |
| 党建通知（支部） | /3324/list.htm | 10 条 |
| 党建动态 | /3325/list.htm | 未确认 |
| 外语党课 | /wydk/list.htm | 未确认 |
| 学工队伍 | /xgdw/list.htm | 未确认 |
| 班主任工作 | /3317/list.htm | 未确认 |
| 学工动态 | /xgdt/list.htm | 未确认 |
| 心理健康教育 | /3315/list.htm | 未确认 |
| 校友工作 | /xygz/list.htm | 未确认 |
| 下载中心 | /xzzx/list.htm | 10 条 |
| 师资—研究生导师 | /3295/list.htm | 23 位 |
| 师资—英语系 | /3296/list.htm | 未确认 |
| 师资—公共外语系 | /ggglxjs/list.htm | 未确认 |
| 师资—日语系 | /3297/list.htm | 未确认 |
| 师资—教学实验中心 | /jxsyzx/list.htm | 未确认 |
| 本科教学 | /3301/list.htm | 未确认 |
| 本科—专业介绍 | /3369/list.htm | 7 条 |
| 本科—实践教学基地 | /3371/list.htm | 未确认 |
| 本科—教学改革质量工程 | /jxggyzl/list.htm | 未确认 |
| 本科—招生简章 | /3373/list.htm | 未确认 |
| 研究生教学 | /3302/list.htm | 未确认 |
| 研究生—专业简介 | /3377/list.htm | 未确认 |
| 研究生—招生简章 | /3380/list.htm | 未确认 |
| 公共外语教学 | /3303/list.htm | 未确认 |
| 本科生公共外语 | /3381/list.htm | 未确认 |
| 研究生公共英语 | /3382/list.htm | 未确认 |
| 课程思政建设专题 | /kcszjszt/list.htm | 未确认 |
| 涉农翻译与国际传播研究基地 | /snfyygjcbyjjd/list.htm | 未确认 |
| 学院概况 | /3284/list.htm | |
| 学院领导 | /xyld/list.htm | 未确认 |
| 行政人员 | /xydzbgs/list.htm | 未确认 |
| 学院党政办公室 | /xydzbgs/list.htm | 未确认 |
| 学生工作办公室 | /xsgzbgs/list.htm | 未确认 |
| 教学科研办公室 | /jxkybgs_20380/list.htm | 未确认 |
| 党建工作 | /3289/list.htm | |
| 师资队伍 | /3285/list.htm | 未确认 |
| 人才培养 | /3286/list.htm | |
| 学生工作 | /3288/list.htm | 未确认 |
| **English Version（英文简介页）** | /3291/list.htm | ✅（非独立英文站） |

---

### 2.23 湾区设计与艺术学院 https://art.scau.edu.cn/

- 旧版入口：未发现
- ⚠️ 导航 HTML 中的链接带模板前缀 `/_t1368/xxx/list.htm`，实测 `https://art.scau.edu.cn/_t1368/2515/list.htm` **跨域重定向失效**；无前缀版本 `/2515/list.htm` 正常 200。**可用路径为无前缀版。**
- 英文版 `https://art.scau.edu.cn/arten/` → 跨域重定向，未确认
- 路由风格：两者都有

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://art.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /2552/list.htm | 685 条 / 49 页 |
| 学院通知（通知公告） | /2551/list.htm | 305 条 / 22 页 |
| 团学活动（其他栏目版） | /2553/list.htm | 58 条 / 5 页 |
| 奖罚公告 | /2554/list.htm | 未确认 |
| 专业介绍 | /2530/list.htm | 空栏目 |
| 招聘信息 | /2555/list.htm | **711 条 / 51 页** |
| 招生信息 | /2556/list.htm | 未确认 |
| 科技创新 | /2557/list.htm | 未确认 |
| 学生创新 | /2558/list.htm | 未确认 |
| 其他栏目（兜底） | /qtlm/list.htm | 5 条 |
| 党建动态 | /dwdt/list.htm | 113 条 / 9 页（= 栏目 /2516/list.htm） |
| 党建工作 | /2516/list.htm | |
| 党务公示 | /dwgs/list.htm | 未确认 |
| 党务通知 | /dwtz/list.htm | 未确认 |
| 党史学习教育 | /dsxxjy/list.htm | 未确认 |
| 科学研究 | /xkyj/list.htm | 未确认 |
| 项目申报 | /ktyj/list.htm | 未确认 |
| 科研活动 | /kycg/list.htm | 未确认 |
| 科研成果 | /jzhd/list.htm | 未确认 |
| 科研团队 | /kytd/list.htm | 未确认 |
| 美丽乡村 | /mlxc/list.htm | 未确认 |
| 教学工作 | /2517/list.htm | 未确认 |
| 教务信息 | /2536/list.htm | 未确认 |
| 教学计划 | /2537/list.htm | 未确认 |
| 教学文件下载 | /2539/list.htm | 未确认 |
| 学生工作 | /2518/main.htm | 未确认 |
| 团学活动 | /2731/list.htm | 未确认 |
| 学生创新 | /2732/list.htm | 未确认 |
| 奖惩公告 | /2733/list.htm | 未确认 |
| 科技创新 | /2736/list.htm | 未确认 |
| 联系我们 | /2737/list.htm | 未确认 |
| 图文 | /2739/list.htm | 未确认 |
| 招聘投递 | /2741/list.htm | 未确认 |
| 招生就业 | /zsjy/list.htm | 11 条 |
| 招聘信息（招生就业下） | /zpxx/list.htm | 未确认 |
| 招聘信息（数字栏目） | /2734/list.htm | 未确认 |
| 招生信息（数字栏目） | /2735/list.htm | 未确认 |
| 本科专业介绍 | /bkzyjs/list.htm | 未确认 |
| 招生动态 | /zsdt/list.htm | 未确认 |
| 研究生教育 | /2519/list.htm | |
| 研究生导师 | /2541/list.htm | 10 条 |
| 研究生培养方案 | /2542/list.htm | 未确认 |
| 研究生专业介绍 | /yjszyjs/list.htm | 未确认 |
| 研究生相关通知 | /yjsxgtz/list.htm | 未确认 |
| 研究生招生 | /yjszs/list.htm | 未确认 |
| 研究生教学动态 | /yjsjw/list.htm | 未确认 |
| 合作交流 | /2522/list.htm | 未确认 |
| 学术活动（讲座） | /2545/list.htm | 3 条（更新停滞于 2024） |
| 对外交流 | /2546/list.htm | 未确认 |
| 校友会 | /2523/list.htm | 未确认 |
| 校友动态 | /2547/list.htm | 未确认 |
| 活动剪影 | /2549/list.htm | 未确认 |
| 办事指南 | /bszn/list.htm | 未确认 |
| 办事指南（栏目） | /2525/list.htm | 未确认 |
| 相关下载 | /2524/list.htm | 未确认 |
| 学院概况 | /2515/list.htm | 未确认 |
| 学院简介 | /2526/list.htm | 未确认 |
| 学院领导 | /2527/list.htm | 未确认 |
| 机构设置 | /2528/list.htm | 未确认 |
| 师资力量 | /2529/list.htm | 未确认 |
| 服装系 | /2559/list.htm | 未确认 |
| 环境设计系 | /2560/list.htm | 未确认 |
| 视觉传达设计系 | /2561/list.htm | 未确认 |
| 动画系 | /2562/list.htm | 未确认 |
| 传媒系 | /2563/list.htm | 未确认 |
| 美术学系 | /2564/list.htm | 未确认 |
| 音乐系 | /2565/list.htm | 未确认 |
| 产品设计系 | /2566/list.htm | 未确认 |
| 表演系 | /2567/list.htm | 未确认 |
| 建筑学系 | /jzxx/list.htm | 未确认 |
| 工业设计系 | /gysjx/list.htm | 未确认 |
| 本科专业—服装与服饰设计 | /2575/list.htm | 未确认 |
| 本科专业—表演 | /2576/list.htm | 未确认 |
| 本科专业—视觉传达设计 | /2577/list.htm | 未确认 |
| 本科专业—环境设计 | /2578/list.htm | 未确认 |
| 本科专业—产品设计 | /2579/list.htm | 未确认 |
| 本科专业—动画 | /2580/list.htm | 未确认 |
| 本科专业—音乐 | /2581/list.htm | 未确认 |
| 本科专业—广播电视编导 | /2582/list.htm | 未确认 |

---

### 2.24 体育学院（体育教学研究部） https://tyb.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：两者都有
- **下属系统（独立子域）**：体质测试系统 http://tybtcxt.scau.edu.cn/ ；阳光体育 http://tybyldpage.scau.edu.cn/login.html

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://tyb.scau.edu.cn`） | 说明 |
|---|---|---|
| 综合新闻（新闻资讯） | /5443/list.htm | 179 条 / 18 页 |
| 公告通知 | /5442/list.htm | 55 条 / 6 页 |
| 教学展示 | /jxzs/list.htm | 53 条 / 6 页 |
| 体育风采 | /tyfc/list.htm | 8 条 |
| 部门概况 | /5411/list.htm | |
| 部门简介 | /5421/list.htm | 未确认 |
| 部门领导 | /5422/list.htm | 未确认 |
| 部门架构 | /5423/list.htm | 未确认 |
| 师资力量 | /5424/list.htm | 未确认 |
| 体育场馆 | /tycg/list.htm | 图文介绍，无列表 |
| 党建工作 | /5412/list.htm | 未确认 |
| 支部建设 | /5425/list.htm | 未确认 |
| 学习专题 | /5426/list.htm | 未确认 |
| 党群动态 | /5427/list.htm | 未确认 |
| 党员风采 | /5428/list.htm | 未确认 |
| 体育教学 | /tyjx/list.htm | 未确认 |
| 教学指南 | /jxzn/list.htm | 未确认 |
| 科研动态 | /5414/list.htm | |
| 动态信息 | /5429/list.htm | 单页，无列表 |
| 项目简介 | /5430/list.htm | 未确认 |
| 体育竞技 | /tyjj/list.htm | |
| 校外活动 | /xwhd/list.htm | 空栏目 |
| 校内活动 | /xnhd/list.htm | 16 条 / 2 页 |
| 运动队 | /ydd/list.htm | 未确认 |
| 杰出体育人 | /jctyr/list.htm | 空栏目 |
| 体质测试—相关文件 | /5431/list.htm | 未确认 |
| 体质测试—测试内容 | /5432/list.htm | 未确认 |
| 体质测试—评分标准 | /5433/list.htm | 未确认 |
| 体质测试—时间安排 | /5434/list.htm | 未确认 |
| 资料下载 | /5418/list.htm | 24 条 / 3 页 |

---

### 2.25 继续教育学院 https://jxjy.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：两者都有

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://jxjy.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻/学院动态 | /4917/list.htm | 147 条 / 11 页 |
| 通知公告 | /4920/list.htm | 16 条 / 2 页 |
| 通知公告—学院通知 | /4967/list.htm | 52 条 / 4 页 |
| 通知公告—成人教育 | /4968/list.htm | 25 条 / 2 页 |
| 通知公告—自学考试 | /4969/list.htm | 30 条 / 3 页 |
| 通知公告—教育培训 | /4970/list.htm | 40 条 / 3 页 |
| 招生信息 | /4919/list.htm | 86 条 / 7 页 |
| 信息公开 | /4913/list.htm | 实际渲染规章制度 |
| 信息公开—规章制度 | /4952/list.htm | 5 条 |
| 信息公开—工作总结及计划 | /gzzjjjh/list.htm | 未确认 |
| 信息公开—收费标准 | /sfbz/list.htm | 未确认 |
| 信息公开—合作机构 | /hzjg/list.htm | 未确认 |
| 信息公开—证书样式 | /4942/list.htm | 未确认 |
| 信息公开—继教质量提升工程 | /jjzltsgc/list.htm | 未确认 |
| 学院概况 | /4907/list.htm | 未确认 |
| 学院简介 | /4928/list.htm | 未确认 |
| 现任领导 | /4929/list.htm | 未确认 |
| 机构设置 | /4930/list.htm | 未确认 |
| 交通指南 | /4944/list.htm | 未确认 |
| 联系方式 | /4931/list.htm | 未确认 |
| 党建工作 | /4908/list.htm | 实际渲染组织机构 |
| 党建—组织机构 | /4932/list.htm | 名单，非列表 |
| 党建—工作动态 | /4933/list.htm | 未确认 |
| 成人教育 | /4909/list.htm | 14 条 |
| 成人教育—招生信息 | /zsxx_19606/list.htm | 4 条 |
| 成人教育—全部招生专业 | /4936/list.htm | 未确认 |
| 成人教育—校本部招生专业 | /4937/list.htm | 未确认 |
| 成人教育—专业介绍 | /4938/list.htm | 未确认 |
| 成人教育—报考须知 | /4939/list.htm | 未确认 |
| 成人教育—录取照顾政策 | /4940/list.htm | 未确认 |
| 自学考试 | /4910/list.htm | 8 条 |
| 自考—专业介绍 | /4943/list.htm | 未确认 |
| 自考—招生信息 | /zsxx/list.htm | 5 条 |
| 自考—合作机构 | /hzjg_16654/list.htm | 未确认 |
| 自考—资料下载 | /zlxz_19534/list.htm | 未确认 |
| 非学历培训 | /4911/list.htm | 实际渲染中心简介 |
| 非学历培训—中心简介 | /zxjj/list.htm | 文字简介 |
| 非学历培训—培训动态 | /4950/list.htm | 22 条 / 2 页 |
| 非学历培训—培训专题 | /pxzt/list.htm | 未确认 |
| 非学历培训—校园设施 | /xyss/list.htm | 未确认 |
| 自考脱产助学及技能培训项目 | /zbbxxm/list.htm | 2 条 |

#### 下属平台 / 系统

| 名称 | 地址 |
|---|---|
| 成人教育授课平台 | https://hnnydx.jxjy.chaoxing.com/login |
| 成人学历教育登录 | https://scaujxjy.o-learn.cn/login.jsp |
| 成教毕业论文查重 | https://vpcs.fanyu.com/personal/hnndjxjy |
| 继教管理员登录（OA） | https://hnndoa.o-learn.cn/ |

---

### 2.26 国际教育学院 https://cie.scau.edu.cn/

- 旧版入口：未发现（存在 `.psp` 路由）
- 路由风格：两者都有 + `.psp`

#### 信息发布（列表）页面（中文主站）

| 栏目名称 | 列表页 URL（前缀 `https://cie.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院动态 | /xydt/list.htm | 146 条 / 11 页（含都柏林学院新闻） |
| 通知公告 | /5513/list.htm | 63 条 / 5 页 |
| 招生信息 | /zsxx/list.htm | 14 条 |
| 院务公开 | /ywgk/list.htm | 聚合页 |
| 院务公开—学院规章 | /xygz/list.htm | 未确认 |
| 院务公开—院内公告 | /yngg/list.htm | 未确认 |
| 院务公开—人才招聘 | /rczp/list.htm | 正文页，非列表 |
| 院务公开—下载中心 | /xzzx/list.htm | 未确认 |
| 党务公开 | /dwgk_17185/list.htm | 2 条 |
| 学院介绍 | /lxhn/list.htm | 长文简介 |
| 现任领导 | /xrld/list.htm | 未确认 |
| 机构设置 | /jgsz/list.htm | 未确认 |
| 联系我们 | /lxwm/list.htm | 未确认 |
| 出国（境）留学 | /cjlx/list.htm | 未确认 |
| 中外学分互认项目 | /zwxfhrxm/list.htm | 未确认 |
| 中外学分互认—招生简章 | /zsjz/list.htm | 空栏目 |
| 中外学分互认—专业设置 | /zysz/list.htm | 未确认 |
| 中外学分互认—合作院校 | /hzyx/list.htm | 未确认 |
| 自主招生项目 | /zzzsxm/list.htm | 未确认 |
| 自主招生—招生简章 | /zsjz_12466/list.htm | 未确认 |
| 短期项目 | /dqxm/list.htm | 未确认 |
| 其它活动 | /qthd/list.htm | 未确认 |
| 来华留学（栏目入口，`.psp`） | /bksy/list.psp | 未确认 |
| 来华留学—招生信息 | /jxgl/list.htm | 实际为留学生概况 |
| 来华留学—留学生概况 | /bksy/list.htm | 未确认 |
| 来华留学—课程及入学要求 | /kcjrxyq/list.htm | 未确认 |
| 来华留学—学习费用 | /xxfy/list.htm | 未确认 |
| 来华留学—联系导师 | /lxds/list.htm | 未确认 |
| 来华留学—在线申请及流程 | /zxsqjlc/list.htm | 未确认 |
| 来华留学—奖学金 | /jxj/list.htm | 未确认 |
| 来华留学—中国政府奖学金 | /zgzfjxj/list.htm | 未确认 |
| 来华留学—广东省政府来粤留学生奖学金 | /gdlyjxj/list.htm | 未确认 |
| 来华留学—教学管理 | /jxgl_12618/list.htm | 未确认 |
| 来华留学—下载中心 | /xzzx_12621/list.htm | 未确认 |
| 来华留学—留学生活 | /lxsh/list.htm | 未确认 |
| 来华留学—保险指南 | /bxzn/list.htm | 未确认 |
| 来华留学—学生活动 | /xshd/list.htm | 未确认 |
| 来华留学—生活指南 | /shzn/list.htm | 未确认 |
| 来华留学—报到须知（旧 IP 站，`.psp`） | http://202.116.160.8/_s128/_t1200/2021/0118/c12475a266880/page.psp | 未确认 |
| 援外培训 | /ywpxw/list.htm | 实际为援外培训中心简介 |
| 援外培训—中心简介 | /ywpxzxjj_12459/list.htm | 长文 |
| 援外培训—项目介绍 | /xmjs/list.htm | 未确认 |
| 援外培训—项目动态 | /xmdt_12631/list.htm | 未确认 |
| 党建工作 | /dqgz/list.htm | 15 条 / 2 页 |
| 党建—学院党委 | /ghgz/list.htm | 未确认 |
| 党建—党建动态 | /zbdt/list.htm | 未确认 |
| 党建—党员发展 | /dyfz/list.htm | 未确认 |
| 党建—党校培训 | /dxpx_12722/list.htm | 未确认 |
| 学生工作 | /xsgz/list.htm | 未确认 |
| 学生工作—学生组织 | /xszz/list.htm | 未确认 |
| 学生工作—学生动态 | /xsdt/list.htm | 26 条 / 2 页 |
| 学生工作—英语俱乐部 | /yyjlb/list.htm | 未确认 |
| 学生工作—学子风采 | /xzfc/list.htm | 21 条 / 2 页 |
| 学生工作—校园生活 | /xysh/list.htm | 未确认 |
| 校友天地 | /xytd/list.htm | 实际为校友风采 |
| 校友天地—校友风采 | /xyfc/list.htm | 3 条 |
| 校友天地—校友分享 | /xyfx/list.htm | 未确认 |
| 留学华农 | /lxhn_12626/list.htm | 未确认 |
| 交流活动 | /jlhd/list.htm | 未确认 |

#### 子站点：英文站 https://cie.scau.edu.cn/cie_english/ ✅

- 列表页（前缀 `https://cie.scau.edu.cn/cie_english`）：
  - Home `/`；About `/About/list.htm`；About CIE `/AboutCIE/list.htm`；Leadership `/Leadership/list.htm`；Structure & Organization `/Structure8Organization/list.htm`；Contact Us `/ContactUs/list.htm`
  - Study Abroad `/StudyAbroad/list.htm`；Credit Transfer Programme `/CreditTransferProgramme/list.htm`；Admission `/Admission_17440/list.htm`；Partner Institutions `/PartnerInstitutions/list.htm`；Associate Programme Degree `/Associate/list.htm`
  - Study in China `/InternationalStudentsinSCAU/list.htm`；Admission `/Admission/list.htm`；Fees `/17431/list.htm`；Funding & Costs `/17432/list.htm`；Online Application `/OnlineApplication/list.htm`；Downloads `/Downloads/list.htm`；Useful Information `/UsefulInformation/list.htm`
  - Foreign-aid Training `/ForeignwaidTraining/list.htm`；Overview `/Overview/list.htm`；News & Events `/NewswEvents/list.htm`
  - Students `/Students/list.htm`；Students News `/StudentsNews/list.htm`；Activities & Events `/ActivitieswEvents/list.htm`；Campus Life `/CampusLife/list.htm`
  - Alumni `/Alumni/list.htm`；Interviews `/Interviews/list.htm`；Alumni Stories `/AlumniStories/list.htm`
  - 新闻列表：http://cie.scau.edu.cn/cie_english/wews/list.htm （注意路径拼写为 `wews`）
  - 模板前缀形式：`/cie_english/_t1662/Admission/list.htm`、`/_t1662/Interviews/list.psp`、`/_t1662/AlumniStories/list.psp`、`/_t1662/CreditTransferProgramme/list.htm`、`/_t1662/Associate/list.psp`
- 留学生报名系统：https://scau.at0086.cn/student

---

### 2.27 广州都柏林国际生命科学与技术学院 https://gdic.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：新版栏目为主（无 `/NNNN/list.htm`）
- ⚠️ 首页「学院新闻」与「通知公告」的「更多」指向 `/xyxw/list.htm`、`/tzgg/list.htm`，但**实测均发生跨协议重定向并落到站点根**，列表内容未确认（栏目实体存在：c11154 学院新闻 / c11155 通知公告）
- 页面存在模板报错残留 `[an error occurred while processing this directive]`

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://gdic.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /xyxw/list.htm | **未确认**（重定向至站点根） |
| 通知公告 | /tzgg/list.htm | **未确认**（同上） |
| 学院简介 | /xyjj/list.htm | ✅ 长文 |
| 组织架构 | /zzjg/list.htm | ✅ |
| 学院领导 | /xyld/list.htm | 未确认 |
| 师资队伍（中方教师） | /zfjs/list.htm | ✅ |
| 中方教师—高级 | /gj/list.htm | ✅ |
| 中方教师—中级 | /zj/list.htm | 未确认 |
| 外方教师 | /wfjs/list.htm | 未确认 |
| 专业介绍—生物科学 | /swkx/list.htm | 2 条 |
| 专业介绍—食品质量与安全 | /spzlyaq/list.htm | 未确认 |
| 专业介绍—园艺 | /yy/list.htm | 未确认 |
| 招生信息 | /zsjz/list.htm | 11 条 / 2 页 |
| 学生工作 | /xsgz/list.htm | 实际显示学生动态 |
| 学生工作—学生组织 | /xszz/list.htm | 未确认 |
| 学生工作—学生动态 | /xsdt/list.htm | 20 条 / 2 页 |
| 学生工作—英语俱乐部 | /yyjlb/list.htm | 未确认 |
| 学生工作—学子风采 | /xzfc/list.htm | 未确认 |
| 党建工作 | /djgz/list.htm | 实际显示党建动态 |
| 党建—党建动态 | /zbdt/list.htm | 9 条 |
| 党建—党校培训 | /dxpx/list.htm | 未确认 |
| 党建—党员发展 | /dyfz/list.htm | 未确认 |
| 联系我们 | /lxwm/list.htm | 未确认 |

#### 子站点：英文站 https://gdic.scau.edu.cn/gdicen/ ✅

- 列表页（前缀 `https://gdic.scau.edu.cn/gdicen`）：
  - Home `/`；About `/About/list.htm`；Introduction of GDIC `/IntroductionofGDIC/list.htm`；Organization Structure `/OrganizationStructure/list.htm`；Leadership `/Leadership/list.htm`
  - Majors `/Majors/list.htm`；Biological Sciences `/BiologicalSciences/list.htm`；Food Quality and Safety `/FoodQualityandSafety_17547/list.htm`；Horticulture `/Horticulture_17548/list.htm`
  - Faculty `/Faculty/list.htm`；Chinese teachers `/Chineseteachers_17549/list.htm`；Foreign teachers `/Foreignteachers_17550/list.htm`
  - Students `/Students/list.htm`；Campus life `/Campuslife/list.htm`；Students Achievements `/StudentsAchievements/list.htm`；Graduate Prospects `/GraduateProspects/list.htm`
  - Admission `/Admission/list.htm`；Contact US `/ContactUS_17542/list.htm`
  - College News：http://gdic.scau.edu.cn/gdicen/COLLEGENEWS/list.htm
- 都柏林大学侧官方页：https://www.ucd.ie/gdic/

---

### 2.28 创新创业学院 https://cxcyxy.scau.edu.cn/

- 旧版入口：未发现
- 下属系统：学科竞赛管理系统 https://cxcygl.scau.edu.cn/

#### 信息发布（列表）页面

| 栏目名称 | 列表页 URL（前缀 `https://cxcyxy.scau.edu.cn`） | 说明 |
|---|---|---|
| 学院新闻 | /4448/list.htm | |
| 通知公告 | /4449/list.htm | |
| 发展动态（总） | /4435/list.htm | |
| 百千万工程 | /bqwgc/list.htm | |
| 关于我们 | /4434/list.htm | |
| 学院介绍 | /4444/list.htm | |
| 领导团队 | /4445/list.htm | |
| 教育教学 | /4437/list.htm | |
| 双创课程 | /4452/list.htm | |
| 教学资源 | /4453/list.htm | |
| 师资力量 | /4454/list.htm | |
| 双创实践 | /scsj/list.htm | |
| 双创赛事 | /4439/list.htm | |
| 国创大赛 | /4457/list.htm | |
| 挑战杯 | /4458/list.htm | |
| 双创平台 | /4436/list.htm | |
| 基地入孵 | /4450/list.htm | |
| 场地管理 | /4451/list.htm | |
| 创业服务 | /cyfw/list.htm | |
| 双创活动 | /4441/list.htm | |
| 创新创业论坛 | /4462/list.htm | |
| 校科联社团 | /4463/list.htm | |
| 双创项目 | /4438/list.htm | |
| 创新创业计划 | /4455/list.htm | |
| 大创项目 | /18824/list.htm | |
| 大创年会 | /18825/list.htm | |
| 双创成果 | /sccg/list.htm | |
| 人物风采 | /18828/list.htm | |
| 优秀项目 | /18829/list.htm | |
| 课题课程 | /18830/list.htm | |
| 专著教材 | /18831/list.htm | |
| 合作交流 | /hzjl/list.htm | |
| 校企合作 | /xqhz/list.htm | |
| 校友资源对接 | /xyzydj/list.htm | |
| 竞赛管理 | /jsgl/list.htm | |
| 视频教育 | /spjy/list.htm | |
| 基地荣誉 | /4446/list.htm | |
| 校科联 | /2025/0319/c18899a402874/page.htm | |

---

## 3. 机关部处

### 3.1 机关部处官网总表

| 部处名称 | 官网地址 | 状态 |
|---|---|---|
| 党政办公室、政策研究室 | https://dzbgs.scau.edu.cn/ | ✅ |
| 党委组织部（党委统战部）、机关党委 | https://zzb.scau.edu.cn/ | ✅ |
| 党委宣传部 | https://xcb.scau.edu.cn/ | ✅ |
| 党委学生工作部（党委研究生工作部） | https://xg.scau.edu.cn/ | ✅ |
| 党委保卫部（人民武装部、保卫处） | https://bwc.scau.edu.cn/ | ✅ |
| 党委教师工作部、人力资源处 | https://hr.scau.edu.cn/ | ✅ |
| 党委离退休工作部（离退休工作处） | https://ltx.scau.edu.cn/ | ✅ |
| 发展规划处（对外合作办公室） | https://fzghc.scau.edu.cn/ | ✅ |
| 本科生院（招生办公室） | https://jwc.scau.edu.cn/ | ✅ |
| 研究生院 | https://yjsy.scau.edu.cn/ | ✅ |
| 科学研究院（新农村发展研究院） | https://kyy.scau.edu.cn/ | ✅ |
| 财务处 | https://cwc.scau.edu.cn/ | ✅（首页需用 `/main.psp`） |
| 资产与实验室管理处 | http://zcc.scau.edu.cn/ | ✅ |
| 总务部 | http://hqglc.scau.edu.cn/ | ✅ |
| 审计处 | http://sjc.scau.edu.cn/ | ✅ |
| 国际交流处（港澳台事务办公室） | http://fao.scau.edu.cn/ | ✅ |
| 乡村振兴与社会服务处 | http://xzc.scau.edu.cn/ | ✅ |
| 对外联络处（校友会、教育发展基金会秘书处） | https://dwllc.scau.edu.cn/ | ✅ |

> **另见**：统战工作（党委统战部）https://dwtzb.scau.edu.cn/ ；党委教师工作部/师德师风 https://jsgzb.scau.edu.cn/ ；教师教学发展中心 https://cfd.scau.edu.cn/

---

### 3.2 党政办公室、政策研究室 https://dzbgs.scau.edu.cn/

- **别名域名**：`dwbgs.scau.edu.cn` 与 `dzbgs.scau.edu.cn` 同时可访问（列表页两域名均可）
- 旧版入口：未发现
- 路由风格：新版栏目

| 栏目名称 | 列表页 URL | 说明 |
|---|---|---|
| 学校要闻 | https://dwbgs.scau.edu.cn/xxyw/list.htm | 2844 条，204 页 |
| 支部建设 | https://dwbgs.scau.edu.cn/zbjs/list.htm | 24 条，2 页 |
| 通知公告 | https://dwbgs.scau.edu.cn/tzgg/list.htm | 20 条，2 页 |
| 工作动态 | https://dwbgs.scau.edu.cn/gzdt/list.htm | 22 条，2 页 |
| 信息化工作 | https://dwbgs.scau.edu.cn/xxhgz/list.htm | 14 条 |
| 规章制度 | https://dwbgs.scau.edu.cn/gzzd/list.htm | 10 条 |
| 办事指南 | https://dwbgs.scau.edu.cn/bszn/list.htm | 23 条，2 页 |
| 部门概况 | https://dwbgs.scau.edu.cn/jgjs/list.htm | 正文单页 |
| 理论动态 | https://dwbgs.scau.edu.cn/zcyj/list.htm | 空栏目 |
| 联系我们 | https://dwbgs.scau.edu.cn/lxwm/list.htm | 单页 |

**下属系统**：OA http://oa.scau.edu.cn/seeyon/ ；网办大厅 https://service.scau.edu.cn/taskcenter-v4-new/workflow/index ；信息公开 https://xxgk.scau.edu.cn/ ；学校规章 https://xngk.scau.edu.cn/gzzd/list.htm ；校长信箱 https://service.scau.edu.cn/scau_cms_yx/portal/letter_sy.jsp

---

### 3.3 党委组织部（党委统战部）、机关党委 https://zzb.scau.edu.cn/

- 旧版入口：未发现（管理登录为 `http://202.116.160.8/login.jsp?inner=1`）
- 路由风格：新版栏目 + 数字栏目

| 栏目名称 | 列表页 URL（前缀 `https://zzb.scau.edu.cn`） | 说明 |
|---|---|---|
| 部门情况 | /4385/list.htm | 渲染「工作职能」 |
| 工作职能 | /4394/list.htm | |
| 人员介绍 | /4395/list.htm | |
| 组织建设 | /djgz/list.htm | 渲染「学校动态」，4 页 |
| 学校动态 | /4386/list.htm | |
| 院系动态 | /jcdj/list.htm | 未确认 |
| 干部工作 | /gbgz/list.htm | 渲染「干部选拔任用」 |
| 干部选拔任用 | /gbxbry/list.htm | 4 条 |
| 干部培养锻炼 | /gbpydl/list.htm | 未确认 |
| 干部监督管理 | /gbjdgl/list.htm | 未确认 |
| 党校工作 | /dxgz/list.htm | 4 页 |
| 机关党建 | /jgdj/list.htm | 1 条 |
| 机关党委概况 | /jgdwjj/list.htm | 未确认 |
| 机关党建动态 | /jgdjdt/list.htm | 未确认 |
| 规章制度（总） | /gzzd/list.htm | 栏目级空页 |
| 校内制度 | /xnzd/list.htm | 栏目级空页 |
| 党建工作（制度） | /djgz_17113/list.htm | 未确认 |
| 干部工作（制度） | /gbgz_17114/list.htm | 未确认 |
| 党校工作（制度） | /dxgz_17115/list.htm | 未确认 |
| 机关党建工作（制度） | /jgdjgz/list.htm | 未确认 |
| 通知公告 | /tzgg/list.htm | 4 页 |
| 通知公告—组织科 | /zzk/list.htm | 3 页 |
| 通知公告—干部科 | /gbk/list.htm | 空 |
| 通知公告—教育培训科 | /jypxk/list.htm | 4 条 |
| 通知公告—机构编制办公室 | /jgbzbgs/list.htm | 空 |
| 通知公告—机关党委 | /jgdw/list.htm | 空 |
| 工作动态 | /gzdt/list.htm | 9 页 |
| 常用下载 | /cyxz/list.htm | **未确认**（跨协议重定向） |
| 常用下载—党建专区 | /djzq/list.htm | 2 条 |
| 常用下载—干部专区 | /gbzq/list.htm | 5 条 |

**下属系统**：统战工作 https://dwtzb.scau.edu.cn/ ；党员管理系统 https://210.76.83.199 ；干部培训系统 https://gbpx.gd.gov.cn/gdceportal/index.aspx ；智慧党建系统 https://hndj.scau.edu.cn/#/login

---

### 3.4 党委宣传部 https://xcb.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：两者都有

| 栏目名称 | 列表页 URL（前缀 `https://xcb.scau.edu.cn`） | 说明 |
|---|---|---|
| 部门概况 | /378/list.htm | 渲染「部门领导」 |
| 部门领导 | /gzry/list.htm | |
| 科室分工 | /ksfg/list.htm | 2 条 |
| 办事流程 | /bslc/list.htm | 6 条 |
| 理论动态 | /lldt/list.htm | 332 条 / 7 页（每页 50） |
| 媒体华农 | /380/list.htm | **4597 条 / 92 页** |
| 视听华农 | /sthn/list.htm | 13 条 |
| 规章制度 | /gzzd/list.htm | 正文页 |
| 工作动态 | /gzdt/list.htm | 93 条 / 2 页 |
| 部门通知 | /bmtz/list.htm | 70 条 / 2 页 |
| 学校要闻 | /xxyw/list.htm | 2843 条 / 57 页 |
| 学习强国 | /xxqg/list.htm | 30 条 |

**专题网**：

- `/xjp/`「树立和践行正确政绩观」https://xcb.scau.edu.cn/xjp/ ✅
  - 学习动态 https://xcb.scau.edu.cn/xjp/xxdt/list.htm **未确认**
  - 重要论述 `/xjp/zygs/list.htm`、工作部署 `/xjp/gzbs/list.htm`、权威解读 `/xjp/qwjd/list.htm`、学习资料 `/xjp/xxzl/list.htm`（未确认）
- `/bqw/`「服务『百千万工程』」https://xcb.scau.edu.cn/bqw/ ✅
  - 工作动态 `/bqw/gzdt/list.htm`、媒体报道 `/bqw/mtbd/list.htm`、上级部署 `/bqw/sjbs/list.htm`、通知文件 `/bqw/tzwj/list.htm`（未确认）
- `/20th`（校庆专题）https://xcb.scau.edu.cn/20th **未确认**

---

### 3.5 党委学生工作部（党委研究生工作部）https://xg.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：两者都有

| 栏目名称 | 列表页 URL（前缀 `https://xg.scau.edu.cn`） | 说明 |
|---|---|---|
| 新闻动态 | /xwdt/list.htm | ⚠️ HTTPS 可访问（HTTP 访问时跨协议循环） |
| 通知公告—本科生 | /bks/list.htm | ⚠️ 同上 |
| 通知公告—研究生 | /yjs/list.htm | ⚠️ 同上 |
| 通知公告—教职工 | /jzg/list.htm | ⚠️ 同上 |
| 部门概况 | /bmgk/list.htm | 未确认 |
| 工作职能 | /gzzn/list.htm | 未确认 |
| 现任领导 | /bmld/list.htm | 未确认 |
| 机构设置 | /jgsz/list.htm | 未确认 |
| 联系我们 | /lxwm/list.htm | 未确认 |
| 党建工作 | /djgz/list.htm | 3 条 |
| 队伍建设 | /dwjs/list.htm | 未确认 |
| 资助工作（总） | /jlzz/list.htm | 4 条 |
| 工作简介 | /gzzz/list.htm | 未确认 |
| 奖助学金 | /jxj/list.htm | 未确认 |
| 助学贷款 | /zxdk/list.htm | 未确认 |
| 绿色通道 | /lstd/list.htm | 未确认 |
| 心理健康 | /xljk/list.htm | 正文/通知页 |
| 心理健康辅导中心 | /xljkfdzx/list.htm | 未确认 |
| 就业创业 | /jycy/list.htm | 未确认 |
| 就业服务 | /jyfw/list.htm | 未确认 |
| 创新创业 | /cxcy/list.htm | 未确认 |
| 三全育人 | /sqyr/list.htm | 未确认 |
| 共青团工作 | /tjgz/list.htm | 未确认 |
| 主题教育 | /xskj_16623/list.htm | 未确认（数字栏目） |
| 规章制度 | /gzzd/list.htm | ⚠️ HTTPS 可访问 |
| 信息公开 | /xxgk/list.htm | 15 条 / 2 页 |
| 办事指南 | /bszn/list.htm | 5 条 |
| 下载专区—业务表格 | /ywbg/list.htm | 10 条 |
| 下载专区—文件下载 | /wjxz/list.htm | 3 条 |
| 智慧学工 | /zhxg/list.htm | 系统入口聚合 |
| 学子星光 | /xzxg/list.htm | 未确认 |
| 十佳辅导员 | /sjfdy/list.htm | 未确认 |
| 十佳班主任 | /yxbzr/list.htm | 未确认 |
| 部长信箱 | http://xg.scau.edu.cn/2020/0811/c11465a246963/page.htm | 单页 |

**下属站点 / 系统**：

- 大学生思政在线 https://szzx.scau.edu.cn/
- 勤工助学 http://qgzx.scau.edu.cn/
- 就业创业信息网 http://jyzx.scau.edu.cn/
- 团委 https://xtw.scau.edu.cn/
- 学生工作系统门户 http://xgxt.scau.edu.cn/ （迎新系统 `/yxxt`、迎新服务网 `/yxwz`、综合测评 `/zhcp`、学生信息管理 `/xsxx`、学工队伍管理 `/xgdw`）
- 心理健康教育管理平台 http://xl.psyedu.cn/scau ；心理健康辅导中心 http://202.116.162.93:81
- 创新创业学院 https://cxcyxy.scau.edu.cn/

---

### 3.6 党委保卫部（人民武装部、保卫处）https://bwc.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：webplus 旧版数字栏目（全站统一）

| 栏目名称 | 列表页 URL（前缀 `https://bwc.scau.edu.cn`） | 说明 |
|---|---|---|
| 单位概况 | /779/list.htm | 7 条 |
| 工作动态 | /780/list.htm | 162 条 / 11 页 |
| 安全教育 | /781/list.htm | 83 条 / 6 页 |
| 安全教育—消防安全教育 | /1873/list.htm | 未确认 |
| 安全教育—国家安全教育 | /6958/list.htm | 未确认 |
| 安全教育—交通安全教育 | /17182/list.htm | 未确认 |
| 安全教育—禁毒教育 | /17183/list.htm | 未确认 |
| 安全教育—灾害防治教育 | /zhfzjy/list.htm | 未确认 |
| 武装工作 | /782/list.htm | 聚合页 |
| 武装工作—工作动态 | /795/list.htm | 119 条 / 8 页 |
| 武装工作—通知公告 | /796/list.htm | 未确认 |
| 武装工作—政策法规 | /797/list.htm | 9 条 |
| 武装工作—国防知识 | /798/list.htm | 未确认 |
| 武装工作—模范榜样 | /799/list.htm | 未确认 |
| 办事指南（总） | /783/list.htm | 15 条 |
| 办事指南—规章制度 | /788/list.htm | 未确认 |
| 办事指南—因私出国（境） | /789/list.htm | 未确认 |
| 办事指南—车辆审批 | /790/list.htm | 未确认 |
| 办事指南—户政办理 | /791/list.htm | 未确认 |
| 办事指南—活动审批 | /792/list.htm | 未确认 |
| 办事指南—消防业务 | /793/list.htm | 未确认 |
| 办事指南—征兵工作 | /794/list.htm | 未确认 |
| 下载专区 | /784/list.htm | 26 条 / 2 页 |
| 联系我们 | /785/list.htm | 1 条 |
| 通知公告 | /786/list.htm | 824 条 / 55 页 |
| 安全警讯 | /787/list.htm | 8 条 |
| 反诈宣传专栏 | 未确认 | 首页专栏存在，「更多」为 `javascript:void(0)` |
| 交通曝光台 | 未确认 | 首页专栏存在，「更多」为 `javascript:void(0)` |

**外链**：全国征兵网 https://www.gfbzb.gov.cn/

**报警电话**：保卫处报警中心 8528-0110；五山派出所 8528-6072

---

### 3.7 党委教师工作部、人力资源处 https://hr.scau.edu.cn/

- 旧版入口：无显式「返回旧版」，但侧栏保留整套 webplus 旧栏目（含「没有用到的栏目」）；旧域路径 https://webplus.scau.edu.cn/pd/…
- 路由风格：两者都有

| 栏目名称 | 列表页 URL（前缀 `https://hr.scau.edu.cn`） | 说明 |
|---|---|---|
| 通知公告 | /tzgg/list.htm | 501 条 / 36 页 |
| 工作动态（人事动态） | /rsdt/list.htm | 235 条 / 17 页 |
| 招聘公告（新） | /zpgg/list.htm | 67 条 / 5 页 |
| 招聘公告（旧数字栏） | /6122/list.htm | 65 条 / 5 页 |
| 结果公示 | /6123/list.htm | 4 条 |
| 招聘信息（总） | /6117/list.htm | 未确认 |
| 图片新闻 | /tpxw/list.htm | 未确认 |
| 部门概况 | /jgsz/list.htm | 渲染「部门领导」 |
| 部门领导 | /bmld/list.htm | |
| 科室分工 | /ksfg/list.htm | 未确认 |
| 办事指引 | /bszy/list.htm | 未确认 |
| 机构简介 | /jgjj/list.htm | 未确认 |
| 机构职能 | /6115/list.htm | 未确认 |
| 政策法规 | /6116/list.htm | 未确认 |
| 政策制度（总） | /gzzd2/list.htm | 渲染「人才工作」 |
| 政策制度—人才工作 | /rcgz_15286/list.htm | 未确认 |
| 政策制度—人事管理 | /rsgl_15283/list.htm | 未确认 |
| 政策制度—师资管理 | /szgl_15284/list.htm | 未确认 |
| 政策制度—薪酬福利 | /xcfl_15285/list.htm | 未确认 |
| 政策制度—博士后工作 | /bshgz_15287/list.htm | 未确认 |
| 政策制度—博士后管理 | /bshgl/list.htm | 未确认 |
| 政策制度—综合管理 | /zhgl_15282/list.htm | 未确认 |
| 服务指南（总） | /bszn/list.htm | 渲染「人事服务」 |
| 服务指南—人事服务 | /rsk/list.htm | 6 条 |
| 服务指南—工资社保 | /gzsbk/list.htm | 未确认 |
| 服务指南—职称师资 | /zcszk/list.htm | 未确认 |
| 服务指南—人才引育 | /rcgzkwbshglbgsw/list.htm | 未确认 |
| 服务指南—发展支持 | /fwsxqd/list.htm | 未确认 |
| 服务指南—劳动合同制职工 | /zhkwkhbgsw/list.htm | 未确认 |
| 服务指南明细栏（22 项） | `/19351/`、`/19352/`、`/19353/`、`/19354/`、`/19355/`、`/19356/`、`/19357/`、`/19358/`、`/19359/`、`/19360/`、`/19361/`、`/19362/`、`/19363/`、`/19364/`、`/19366/`、`/19367/`、`/19369/`、`/19370/`、`/19371/`、`/19372/`、`/19375/`、`/19376/` + `/list.htm`；另有 `/gzsbshbshzxkczbjjbtsqsh/list.htm` | 入职/在职证明/签证/调配/收入证明/社保/退休/抚恤/职称评审/进修访学等 |
| 下载专区（总） | /xzzq/list.htm | 渲染「人才工作」 |
| 下载专区—人才工作 | /rcgzkwbshglbgsw_15204/list.htm | 13 条 |
| 下载专区—人事工作 | /rsk_15201/list.htm | 未确认 |
| 下载专区—师资管理 | /zcszk_15202/list.htm | 未确认 |
| 下载专区—薪酬福利 | /gzsbk_15203/list.htm | 未确认 |
| 下载专区—综合管理 | /zhkwkhbgsw_15200/list.htm | 未确认 |
| 下载专区—考核与聘用 | /khypy/list.htm | 未确认 |
| 党建工作 | /djgz/list.htm | 未确认 |
| 党建工作—支部动态 | /zbdt/list.htm | 未确认 |
| 党建工作—党的理论 | /ddll/list.htm | 未确认 |
| 党建工作—上级制度 | /sjzd/list.htm | 未确认 |
| 党建工作—学校制度 | /xxzd/list.htm | 未确认 |
| 师资队伍 | /szdw/list.htm | 未确认 |
| 【旧栏】人事调配 | /6007/list.htm | 未确认 |
| 【旧栏】师资管理 | /6009/list.htm | 未确认 |
| 【旧栏】职称评聘 | /6010/list.htm | 未确认 |
| 【旧栏】工资社保 | /6011/list.htm | 未确认 |
| 【旧栏】人事综合 | /6014/list.htm | 未确认 |
| 【旧栏】工作动态 | /6118/list.htm | 未确认 |
| 人力资源处（站点根栏） | /3976/list.htm | 未确认 |
| 旧/备用栏目群 | `/pfck/`、`/pfck2/`、`/bsznw/`、`/bszn_17322/`、`/bsznww/`、`/ywfwzn/`、`/zlxzzq/`、`/rcgz_17323/`、`/rsgz/`、`/rsgz1/`、`/rcgz1/`、`/szgl1/`、`/xcfl_17329/`、`/zbdt_16398/`、`/zbdt1/`–`/zbdt5/`、`/rsdt1/`–`/rsdt5/`、`/tzgg1/`、`/tzgg2/`、`/djgz1/`、`/banner3/`、`/wzdbyqlj/`、`/wzdbewm/`、`/xtlj/`、`/fwznzlj/`、`/wzlj/`、`/myyddlm/`（均 + `/list.htm`） | 历史/未用栏目 |
| 招聘公告页内子栏 | `/p15207c6117/list.htm`、`/p15207c6122/list.htm` | c15207 系列 |

**博士后之家**（https://hr.scau.edu.cn/pd/ ✅）：

- 新闻动态 `/pd/9917/list.htm`、导师介绍 `/pd/9918/list.htm`、管理规定 `/pd/9919/list.htm`、通知公告 `/pd/9920/list.htm`、招聘信息 `/pd/9921/list.htm`、下载专区 `/pd/9922/list.htm`、联系我们 `/pd/9923/list.htm`、进站指南及在站管理 `/pd/9925/list.htm`、出站指南 `/pd/9926/list.htm`、常见问题 `/pd/9927/list.htm`、优秀博士后项目申请 `/pd/yxbshxmsq_10702/list.htm`
- 博士后进出站系统 http://bg.chinapostdoctor.org.cn/V3/Manage/Login.aspx

**下属系统**：招聘系统 https://zp.scau.edu.cn/ ；人力资源管理系统 https://hr2.scau.edu.cn/ ；人事业务一站通 https://hr.scau.edu.cn/2023/0403/c14870a341155/page.htm ；党委教师工作部 https://jsgzb.scau.edu.cn/ （名师风采 https://jsgzb.scau.edu.cn/szff/list.htm）；教师教学发展中心 https://cfd.scau.edu.cn/

---

### 3.8 党委离退休工作部（离退休工作处）https://ltx.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：两者都有

| 栏目名称 | 列表页 URL（前缀 `https://ltx.scau.edu.cn`） | 说明 |
|---|---|---|
| 工作动态 | /gzdt_1819/list.htm | 45 条 / 4 页 |
| 通知公告 | /tzgg/list.htm | 2 条 |
| 活动风采 | /hdfc/list.htm | 图片型列表 |
| 思政党建 | /szjd/list.htm | 3 条 |
| 关工委 | /ggw/list.htm | 5 条 |
| 规章制度（栏目） | /gzzd/list.htm | 实际落到「领导讲话」 |
| 领导讲话 | /ldjh/list.htm | c1830 系列 |
| 上级文件 | /sjwj/list.htm | 未确认 |
| 学校文件 | /xxwj/list.htm | 未确认 |
| 本处制度 | /bcwj/list.htm | 未确认 |
| 机构简介 | /jgjj/list.htm | 未确认 |
| 部门简介 | /bmjj/list.htm | 未确认 |
| 工作职责 | /gzzz_1836/list.htm | 未确认 |
| 机构人员 | /ryfg_1837/list.htm | 未确认 |
| 老年团体 | /327/list.htm | 数字栏目 |
| 离退休教职工协会 | /355/list.htm | 未确认 |
| 老年人体育协会 | /354/list.htm | 未确认 |
| 金穗艺术团 | /353/list.htm | 未确认 |
| 夕阳红诗社 | /352/list.htm | 未确认 |
| 各学院部处离退休小组 | /358/list.htm | 未确认 |
| 离休干部直属党支部 | /lxgbzsdzb/list.htm | 未确认 |
| 书画摄影协会 | /shsyxh/list.htm | 未确认 |
| 自娱自乐团体 | /zyzltt/list.htm | 未确认 |
| 广东老教授协会农业专家委员会 | /gdljsxhnyzjwyh/list.htm | 未确认 |
| 紫荆花语 | /zjhy/list.htm | 未确认 |
| 养生保健 | /326/list.htm | 未确认 |
| 服务指南 | /fwzn/list.htm | 2 条 |

---

### 3.9 发展规划处（对外合作办公室）https://fzghc.scau.edu.cn/

- 旧版入口：未发现
- ⚠️ 部分正文链接被重写为 VPN 镜像域 `www-scau-edu-cn-s.vpn.scau.edu.cn`
- 路由风格：新版栏目

| 栏目名称 | 列表页 URL（前缀 `https://fzghc.scau.edu.cn`） | 说明 |
|---|---|---|
| 新闻动态 | /xwdt/list.htm | 130 条 / 8 页 |
| 党建工作 | /djgz/list.htm | 未确认 |
| 党建工作—支部简介 | /zbjj/list.htm | 未确认 |
| 党建工作—党建活动 | /djhd/list.htm | 未确认 |
| 党建工作—党纪党规 | /djdg/list.htm | 未确认 |
| 党建工作—理论学习 | /llxx/list.htm | 未确认 |
| 发展规划 | /fzghw/list.htm | 12 条 |
| 发展规划—学校发展规划 | /xxfzgh/list.htm | 未确认 |
| 发展规划—校园建设规划 | /xyjsgh/list.htm | 未确认 |
| 学科建设 | /xkjs/list.htm | 40 条 / 3 页 |
| 学科建设—重点学科 | /xkjj/list.htm | 重点学科一览表（静态） |
| 学科建设—第三方评价 | /dsfpj/list.htm | 未确认 |
| 学科建设—学科建设工作委员会 | /xkjsgzwyh/list.htm | 未确认 |
| 学科建设—学科负责人 | /xkfzr/list.htm | 未确认 |
| 学科建设—一流/高水平大学建设 | /cylwgspdxjs/list.htm | 未确认 |
| 考核评估 | /khpg/list.htm | 未确认 |
| 考核评估—目标考核 | /mbkh/list.htm | 未确认 |
| 考核评估—学科评估 | /xkpg_19338/list.htm | 未确认 |
| 考核评估—学院发展性评估 | /xyfzxpg/list.htm | 未确认 |
| 对外合作 | /dwhz/list.htm | 未确认 |
| 对外合作—粤港澳大湾区 | /ygadyw/list.htm | 未确认 |
| 对外合作—交流合作 | /jlhz/list.htm | 未确认 |
| 学术委员会 | /xswyh/list.htm | 未确认 |
| 学术委员会—校学术委员会 | /xxswyh/list.htm | 未确认 |
| 学术委员会—学术道德委员会 | /xsddwyh/list.htm | 未确认 |
| 学术委员会—学术委员会分会 | /xswyhfh/list.htm | 未确认 |
| 政策规章 | /zcgz/list.htm | 未确认 |
| 政策规章—上级文件 | /sjwj/list.htm | 未确认 |
| 政策规章—学校文件 | /xxwj/list.htm | 未确认 |
| 部门概况 | /bmgk/list.htm | 落到单位职能 |
| 部门概况—领导简介 | /ldjj/list.htm | 未确认 |
| 部门概况—内设机构 | /nsjg/list.htm | 未确认 |
| 友情链接 | /yqlj/list.htm | 未确认 |

---

### 3.10 本科生院（招生办公室）https://jwc.scau.edu.cn/

- **旧版入口**：**https://jwc.scau.edu.cn/_t291/main.psp** ✅（页眉「旧版网站」）；旧版路由前缀 `/_t291/`，另有 `/_s124/` 呈现前缀
- ⚠️ 部分 `.htm` 列表页在 https 下命中 scheme 跳转，**改用同栏目 `/_s124/xxx/list.psp` 形式可 200**
- 路由风格：两者都有

| 栏目名称 | 列表页 URL | 说明 |
|---|---|---|
| 教务公告 | https://jwc.scau.edu.cn/5113/list.htm | 750 条 / 54 页；（psp 形式 `/_s124/5113/list.psp` ✅） |
| 教务公告—综合科 | https://jwc.scau.edu.cn/5133/list.htm | 未确认 |
| 教务公告—教学运行科 | https://jwc.scau.edu.cn/5134/list.htm | 未确认 |
| 教务公告—学籍科 | https://jwc.scau.edu.cn/5135/list.htm | 未确认 |
| 教务公告—教学质量管理科 | https://jwc.scau.edu.cn/5137/list.htm | 未确认 |
| 教务公告—实践教学科 | https://jwc.scau.edu.cn/5138/list.htm | 未确认 |
| 教务公告—教学研究科 | https://jwc.scau.edu.cn/5139/list.htm | 未确认 |
| 教务新闻 | https://jwc.scau.edu.cn/5114/list.htm | 153 条 / 11 页；（psp ✅） |
| 党建工作 | https://jwc.scau.edu.cn/djgz/list.htm | 13 条 |
| 机构设置 | https://jwc.scau.edu.cn/5107/list.htm | 含主要职能、现任领导、各科室 |
| 专业设置 | https://jwc.scau.edu.cn/5108/list.htm | 专业一览表 |
| 专业设置—明细 | https://jwc.scau.edu.cn/zysz_15017/list.htm | 未确认 |
| 专业白皮书 | https://jwc.scau.edu.cn/zysz/list.htm | 未确认 |
| 管理文件（总） | https://jwc.scau.edu.cn/5109/list.htm | |
| 管理文件—教育部/教育厅文件 | https://jwc.scau.edu.cn/5125/list.htm | 14 条 |
| 管理文件—教务/教材管理 | https://jwc.scau.edu.cn/5126/list.htm | 未确认 |
| 管理文件—学籍管理 | https://jwc.scau.edu.cn/5127/list.htm | 未确认 |
| 管理文件—考务管理 | https://jwc.scau.edu.cn/5128/list.htm | 未确认 |
| 管理文件—教学质量监控 | https://jwc.scau.edu.cn/5129/list.htm | 未确认 |
| 管理文件—实践教学管理 | https://jwc.scau.edu.cn/5130/list.htm | 未确认 |
| 管理文件—教学研究与评估 | https://jwc.scau.edu.cn/5131/list.htm | 未确认 |
| 管理文件—教师教学发展 | https://jwc.scau.edu.cn/5132/list.htm | 未确认 |
| 办事指南（总） | https://jwc.scau.edu.cn/5110/list.htm | 科室入口页 |
| 办事指南—学籍科 | https://jwc.scau.edu.cn/5142/list.htm | 注册/退学/休学/复学/转学 `/5157`/转专业/补办学生证/应征入伍休学/学籍信息变更/学历信息勘误 `/xlxxkw`/补发毕业证明书/保留恢复入学资格/辅修/延长学习年限 |
| 办事指南—教学运行科 | https://jwc.scau.edu.cn/5143/list.htm | 选课 `/5172`、缓考、借课室、重修、调停课、分散考试申请、补办四六级成绩证明、中英文成绩单 `/hnnydxywcjdwxlxwzmjqtzm`、交换生学分认定 `/jhsxfrdjcjzh`、AI 助手「紫荆小 U」`/AIzswzjxUw` |
| 办事指南—实践教学科 | https://jwc.scau.edu.cn/5145/list.htm | 实习经费申请 `/sxjfsq`、实践教学基地申报 `/sjjxjdsb` |
| 办事指南—教学质量管理科 | https://jwc.scau.edu.cn/5146/list.htm | 评教结果证明、教学差错事故、学生信息反馈 |
| 办事指南—教学研究科 | https://jwc.scau.edu.cn/jxyjypgzx/list.htm | 教学成果奖 `/jxcgjpsgzlc`、质量工程、状态数据库、质量年报、毕业生需求评价 |
| 信息公开 | https://jwc.scau.edu.cn/xxgk/list.htm | （psp ✅） |
| 信息公开—院务会议 | https://jwc.scau.edu.cn/ywhyt/list.htm | 36 条 / 3 页 |
| 资料下载（总） | https://jwc.scau.edu.cn/5111/list.htm | （psp ✅） |
| 资料下载—学籍科 | https://jwc.scau.edu.cn/5147/list.htm | 学籍 `/5184`（17 条）、成绩 `/5185`、学历学位 `/5186` |
| 资料下载—教学运行科 | https://jwc.scau.edu.cn/5148/list.htm | 教材 `/5187`、考务安排 `/5190`、课程 `/5188`、试卷管理 `/5191`、学生相关 `/5189`、缓考与四六级 `/5192`、平时成绩考核 `/5193`、考务工作量统计 `/5194` |
| 资料下载—实践教学科 | https://jwc.scau.edu.cn/5150/list.htm | 实习经费 `/5195`、基地申报 `/5196`、毕业论文（设计）`/5197` |
| 资料下载—教学质量管理科 | https://jwc.scau.edu.cn/5151/list.htm | 学生评教 `/5198`、教学督导 `/5199`、听课 `/5200`、教学检查 `/5202` |
| 资料下载—教学研究科 | https://jwc.scau.edu.cn/5152/list.htm | 教改课题 `/5203`、新增专业 `/5204`、质量工程 `/5206`、教学类项目协议 |
| 资料下载—综合科 | https://jwc.scau.edu.cn/zhk_19373/list.htm | 学生手册 `/xssc` |
| 校历查询 | https://jwc.scau.edu.cn/xl/list.htm | |

**下属系统 / 子站**：

- 本科招生网 https://zsb.scau.edu.cn/
- 教师教学发展中心 https://cfd.scau.edu.cn/ （通知公告 https://cfd.scau.edu.cn/tzgg/list.htm）
- 新教务系统 https://jwxt.scau.edu.cn/
- 教务管理系统 https://jwzf.scau.edu.cn/sso/lyiotlogin
- 旧教务系统 http://jwxtxs.scau.edu.cn/default2.aspx
- 教学质量管理平台 https://jxpj.scau.edu.cn
- 教学质量监控平台 http://jkpt.jwc.scau.edu.cn/MIS/
- 毕业论文（设计）系统 http://bkbylw.scau.edu.cn/index.aspx
- 质量工程网 http://pgzx.scau.edu.cn/PGZX/Index.aspx
- 旧版站点 https://jwc.scau.edu.cn/_t291/main.psp ；旧版首页 https://jwc.scau.edu.cn/_s124/main.psp

---

### 3.11 研究生院 https://yjsy.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：webplus 旧版数字栏目为主

| 栏目名称 | 列表页 URL（前缀 `https://yjsy.scau.edu.cn`） | 说明 |
|---|---|---|
| 工作动态/新闻动态 | /207/list.htm | 128 条 / 10 页 |
| 通知公告 | /208/list.htm | **1469 条 / 105 页** |
| 通知公告—综合管理办公室 | /275/list.htm | 未确认 |
| 通知公告—招生办公室 | /276/list.htm | 未确认 |
| 通知公告—培养办公室 | /277/list.htm | 未确认 |
| 通知公告—学位办公室 | /278/list.htm | 未确认 |
| 办事流程 | /214/list.htm | 2 条 |
| 办事流程—综合科 | /279/list.htm | 未确认 |
| 办事流程—培养科 | /281/list.htm | 未确认 |
| 办事流程—学位科 | /282/list.htm | 未确认 |
| 资料下载 | /215/list.htm | |
| 资料下载—综合科 | /283/list.htm | 未确认 |
| 资料下载—招生科 | /284/list.htm | 9 条 |
| 资料下载—培养科 | /285/list.htm | 未确认 |
| 资料下载—学位科 | /286/list.htm | 未确认 |
| 信息公开 | /xxgk/list.htm | 17 条 / 2 页 |
| 信息公开—信息公示 | /288/list.htm | 未确认 |
| 信息公开—统计信息 | /289/list.htm | 未确认 |
| 信息公开—工作简报 | /290/list.htm | 未确认 |
| 信息公开—机构设置 | /jgsz/list.htm | 未确认 |
| 信息公开—规章制度 | /zcgz/list.htm | 未确认 |
| 信息公开—遗失声明 | /yssm/list.htm | 未确认 |
| 院部概览 | /151/list.htm | 未确认 |
| 研究生教育简介 | /yjsjyjj/list.htm | 未确认 |
| 单位职能 | /230/list.htm | 下含研究生院 `/yjsy` |
| 机构设置 | /231/list.htm | 下含院领导 `/296`、综合科 `/297`、招生科 `/298`、培养科 `/299`、学位科 `/300` |
| 学位工作 | /153/list.htm | 下含 `/234` 开题报告及中期考核、`/235` 答辩与学位、`/236` 优秀论文评选、`/237` 论文质量评估、`/238` 学术道德、`/239` 学位点建设、`/240` 学位委员会 |
| 培养管理 | /154/list.htm | 下含 `/241` 培养方案、`/242` 学籍管理、`/243` 教务管理、`/244` 考务管理、`/246` 其他 |
| 导师队伍 | /155/list.htm | 下含 `/247` 导师聘任、`/248` 导师培训、`/249` 导师名单 |
| 创新工程 | /156/list.htm | 下含 `/250` 创新计划项目、`/256` 联合培养项目 |
| 国际交流 | /gjjl/list.htm | 下含 `/1647` 国家公派、`/1648` 广州市菁英计划、`/1649` 学校出国项目 |
| 校历查询 | /xl/list.htm | |
| 新闻动态子栏 | `/270`、`/271`、`/272`、`/273`、`/274/list.htm` | 下载型子栏 |
| **旧版兼容路径** | `https://yjsy.scau.edu.cn/207/list.htm` 等 `.htm` 形式；旧版入口页形式为 `https://yjsy.scau.edu.cn/151/list.htm` | |

**下属系统 / 子站**：研究生招生网 https://yzb.scau.edu.cn ；研究生教育管理系统（入口页 `/2024/0325/c17347a369507/page.htm`）；可信电子成绩平台（入口页 `/2024/0325/c17347a369509/page.htm`）；研究生在线课程平台 https://gsscau.yuketang.cn/pro/portal/home/ ；「华农小研」智能问答 http://voyage001.scau.edu.cn/agentdev/chat/PtQpWLR4pOLrDeaG

---

### 3.12 科学研究院（新农村发展研究院）https://kyy.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：新版栏目

| 栏目名称 | 列表页 URL（前缀 `https://kyy.scau.edu.cn`） | 说明 |
|---|---|---|
| 工作动态 | /gzdt/list.htm | |
| 通知公告 | /tzgg/list.htm | 1798 条 / 129 页 |
| 公示信息 | /gsxx/list.htm | ⚠️ 跨协议跳转 |
| 学术交流 | /xsjl/list.htm | |
| 机构介绍 | /jgjs/list.htm | 落到部门介绍 |
| 部门介绍 | /bmjs/list.htm | 未确认 |
| 领导成员 | /ldbz/list.htm | 未确认 |
| 处室职能 | /bczn/list.htm | 未确认 |
| 联系方式 | /lxwm/list.htm | 未确认 |
| 项目管理 | /kyxm/list.htm | 下含 `/zdxmglbgs` 基础研究项目、`/jcyjglbgs` 高新项目 |
| 人文社科 | /rwsk/list.htm | 下含 `/rwskxmglbgs`、`/zkglbgs`、`/glgd` |
| 成果管理 | /kycg/list.htm | 下含 `/hjcg1` 获奖成果、`/zscqcg` 知识产权成果、`/ttc/` 成果转化 |
| 平台建设（总） | /kypt/list.htm | 9 条 |
| 国家级科研平台 | /sbjyszdsys/list.htm | |
| 国家发改委 | /gjfgw/list.htm | |
| 教育部 | /jyb/list.htm | |
| 自然资源部 | /zrzyb/list.htm | |
| 农业农村部 | /nyncb/list.htm | |
| 广东省平台 | /gdspt/list.htm | |
| 市厅局级科研平台 | /tjjkypt/list.htm | |
| 自设研究机构 | /xjkypt/list.htm | |
| 地方/企业共建科研平台 | /hnwskjcxzx/list.htm | |
| 下载中心 | /cyxz/list.htm | ⚠️ 跨协议跳转 |
| 下载中心—项目管理 | /xmgl1/list.htm | 子：`/gjzrkxjjxgbg`、`/gxjsxmyjgl`、`/xmxdwj`、`/qtbgxz` |
| 下载中心—社会服务 | /shfw_11898/list.htm | |
| 下载中心—人文社科 | /rwsk_11899/list.htm | 子：`/zhxz_12106`、`/xmgl_12107` |
| 下载中心—成果管理 | /cggl/list.htm | 子：`/cgdj`、`/hxxmgl`、`/jlsb`、`/zscq_12116`、`/cgzh_12117`、`/cgzl_12118`、`/zcfg_12119` |
| 下载中心—平台建设 | /ptjs/list.htm | 子：`/123`、`/sbjptxgglbf`、`/stjjptxgglbf`、`/xjptxgglbf` |
| 下载中心—学报编辑 | /xbbj/list.htm | |
| 下载中心—其它下载 | /qtxz/list.htm | |
| 常用下载 | /cyxz_12102/list.htm | 当前为空表 |

**子站点：科技成果转化网（技术转移中心）** https://kyy.scau.edu.cn/ttc/ ✅

| 栏目名称 | 列表页 URL |
|---|---|
| 中心概况 | https://kyy.scau.edu.cn/ttc/zxjs/list.htm |
| 成果专利 | https://kyy.scau.edu.cn/ttc/kjcg/list.htm |
| 科技成果 | https://kyy.scau.edu.cn/ttc/kjcg/list.htm （59 条 / 4 页）|
| 专利库 | https://kyy.scau.edu.cn/ttc/2026/0320/c14657a429721/page.htm （单页表格）|
| 展会信息 | https://kyy.scau.edu.cn/ttc/jsxq_14755/list.htm |
| 转化项目 | https://kyy.scau.edu.cn/ttc/hxxm/list.htm |
| 专家团队 | https://kyy.scau.edu.cn/ttc/zjtd/list.htm |
| 专家库 | https://kyy.scau.edu.cn/ttc/zjk/list.htm |
| 政策法规 | https://kyy.scau.edu.cn/ttc/zcfg/list.htm |
| 政策解读 | https://kyy.scau.edu.cn/ttc/zcjd/list.htm |
| 办事指南 | https://kyy.scau.edu.cn/ttc/bszn/list.htm |
| 联系我们 | https://kyy.scau.edu.cn/ttc/lxwm/list.htm |
| 资讯中心 | https://kyy.scau.edu.cn/ttc/zxzx/list.htm |
| 新闻动态 | https://kyy.scau.edu.cn/ttc/xwdt/list.htm |
| 通知公告 | https://kyy.scau.edu.cn/ttc/tzgg/list.htm |
| 转化公示 | https://kyy.scau.edu.cn/ttc/zhgs/list.htm （272 条 / 19 页）|
| 综合立项项目 | https://kyy.scau.edu.cn/ttc/zhlxxm/list.htm |

**下属系统 / 子站**：学报编辑部 http://xuebao.scau.edu.cn/ch/index.aspx ；原重点实验室建设办公室 http://sysjs.scau.edu.cn ；科研管理系统 https://kyglxt.scau.edu.cn/srm-web/systemsso/login_ssoLogin.html

---

### 3.13 财务处 https://cwc.scau.edu.cn/

- ⚠️ 裸根 `http://cwc.scau.edu.cn/` 与 `https://cwc.scau.edu.cn/` 均返回 scheme 跳转；**实际首页为 https://cwc.scau.edu.cn/main.psp** ✅
- 页眉「旧版回顾」指向 `https://www.scau.edu.cn/`（模板占位，非真旧版）；本站旧版路由前缀为 `/_s9/`（`https://cwc.scau.edu.cn/_s9/main.psp`）
- ⚠️ `.htm` 直取多命中 scheme 跳转，改用 `/_s9/….list.psp` 即 200

| 栏目名称 | 列表页 URL | 说明 |
|---|---|---|
| 通知公告 | https://cwc.scau.edu.cn/tzgg/list.htm | 344 条 / 25 页（psp ✅）；学费、报销、年终结算等 |
| 工作动态（新闻） | https://cwc.scau.edu.cn/xw/list.htm | psp ✅ |
| 办事指南 | https://cwc.scau.edu.cn/62/list.htm | 37 条 / 3 页（psp ✅） |
| 办事指南—办公地址及电话 | https://cwc.scau.edu.cn/70/list.htm | 未确认 |
| 办事指南—财务监管科业务 | https://cwc.scau.edu.cn/71/list.htm | 未确认 |
| 办事指南—会计科业务 | https://cwc.scau.edu.cn/hjhskyw/list.htm | 未确认 |
| 办事指南—资金科业务 | https://cwc.scau.edu.cn/73/list.htm | 未确认 |
| 办事指南—预算科业务 | https://cwc.scau.edu.cn/74/list.htm | 未确认 |
| 办事指南—后勤核算科业务 | https://cwc.scau.edu.cn/78/list.htm | 未确认 |
| 办事指南—收费及校园卡科业务 | https://cwc.scau.edu.cn/79/list.htm | 未确认 |
| 办事指南—经资委办公室业务 | https://cwc.scau.edu.cn/jzwbgsyw/list.htm | 未确认 |
| 收费公示 | https://cwc.scau.edu.cn/64/list.htm | 28 条 / 2 页（psp ✅） |
| 文件下载 | https://cwc.scau.edu.cn/wjxz/list.htm | 72 条 / 6 页（psp ✅） |
| 科研经费专区 | https://cwc.scau.edu.cn/yjfgl/list.htm | psp ✅ |
| 外币来款信息 | https://cwc.scau.edu.cn/wblkxx/list.htm | psp ✅ |
| 部门概况 | https://cwc.scau.edu.cn/bmgk/list.htm | 含部门简介 `/bmjj`、部门领导 `/bmld`、科室设置 `/kssz` |
| 支部党建 | https://cwc.scau.edu.cn/zbdj/list.htm | 未确认 |
| 规章制度 | https://cwc.scau.edu.cn/gzzdw/list.htm | 含上级财经法规 `/sjcjfg`、校内管理制度 `/xnglzd` |
| 规章制度—上级·财务管理 | https://cwc.scau.edu.cn/cwgl/list.htm | 未确认 |
| 规章制度—上级·会计核算 | https://cwc.scau.edu.cn/hjhsgl/list.htm | 未确认 |
| 规章制度—上级·科研经费 | https://cwc.scau.edu.cn/kyjfgl_19060/list.htm | 未确认 |
| 规章制度—上级·资金 | https://cwc.scau.edu.cn/zjgl_19061/list.htm | 未确认 |
| 规章制度—上级·收费 | https://cwc.scau.edu.cn/sfgl/list.htm | 未确认 |
| 规章制度—校内·财务管理 | https://cwc.scau.edu.cn/cwgl_19063/list.htm | 未确认 |
| 规章制度—校内·会计核算 | https://cwc.scau.edu.cn/hjhsgl_19064/list.htm | 未确认 |
| 规章制度—校内·科研经费 | https://cwc.scau.edu.cn/kyjfgl_19065/list.htm | 未确认 |
| 规章制度—校内·资金 | https://cwc.scau.edu.cn/zjgl_19066/list.htm | 未确认 |
| 规章制度—校内·收费 | https://cwc.scau.edu.cn/sfgl_19067/list.htm | 未确认 |
| 规章制度—校内·资产公司经营管理 | https://cwc.scau.edu.cn/zcgsjygl/list.htm | 未确认 |

**下属系统**：智慧财务网上综合服务平台 http://202.116.160.105:6060 ；内部控制信息系统 http://222.201.226.48:8080/app/portlet/newIndex.jsp ；统一支付平台 http://pay.scau.edu.cn/login.aspx?local=zh-cn ；智慧差旅平台 https://clpt.scau.edu.cn/szht_trip_pc_1/user/hnnyTripLogin

---

### 3.14 资产与实验室管理处 https://zcc.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：两者都有（webplus 数字栏目 `/3978`、`/4029` + 拼音别名 `/ldfg`、`/ggfwgl`、`/dbgg`）
- ⚠️ `/3979/`（新闻公告）、`/4029/`（通知公告）、`/3982/`（文件下载）为 **https↔http 重定向环，无法抓取**

| 栏目名称 | 列表页 URL（前缀 `https://zcc.scau.edu.cn`） | 说明 |
|---|---|---|
| 部门介绍 | /3978/list.htm | 含子栏 |
| 单位简介 | /4045/list.htm | 未确认 |
| 领导分工 | /ldfg/list.htm | 未确认 |
| 具体职责 | /4046/list.htm | 未确认 |
| 新闻公告（一级） | /3979/list.htm | ⚠️ 重定向环 |
| 通知公告 | /4029/list.htm | ⚠️ 重定向环 |
| 规章制度（一级） | /3980/list.htm | 12 条 |
| 公共房屋管理 | /ggfwgl/list.htm | 未确认 |
| ├ 学校文件 | /xxwj_12591/list.htm | 未确认 |
| └ 上级文件 | /sjwj_12592/list.htm | 未确认 |
| 教职工周转房 | /jzgzzf/list.htm | 未确认 |
| ├ 学校文件 | /xxwj_12589/list.htm | 未确认 |
| └ 上级文件 | /sjwj_12590/list.htm | 未确认 |
| 资源有偿使用 | /zyycsy/list.htm | 未确认 |
| ├ 学校文件 | /xxwj_12586/list.htm | 未确认 |
| └ 上级文件 | /sjwj_12585/list.htm | 未确认 |
| 设备家具管理 | /sbjjgl/list.htm | 未确认 |
| ├ 学校文件 | /xxwj_12588/list.htm | 未确认 |
| └ 上级文件 | /sjwj_12587/list.htm | 未确认 |
| 实验室安全管理 | /sysaqgl/list.htm | 未确认 |
| ├ 学校文件 | /xxwj/list.htm | 未确认 |
| └ 上级文件 | /sjwj/list.htm | 未确认 |
| 规章制度—上级文件（汇总） | /12153/list.htm | 未确认 |
| 规章制度—学校文件（汇总） | /12154/list.htm | 未确认 |
| 办事指南（一级） | /3981/list.htm | 图片导航页 |
| 办事指南—入口 | /12133/list.htm | 未确认 |
| 公用房屋管理（办事） | /tzsbgl/list.htm | 未确认 |
| 教职工周转房（办事） | /3992/list.htm | 未确认 |
| 资源有偿使用（办事） | /3993/list.htm | 未确认 |
| 设备家具管理（办事） | /3995/list.htm | 未确认 |
| 实验室安全管理（办事） | /3991/list.htm | 未确认 |
| 文件下载（一级） | /3982/list.htm | ⚠️ 重定向环 |
| ├ 资源有偿使用 | /tdgl/list.htm | 未确认 |
| ├ 设备家具管理 | /fwgl/list.htm | 未确认 |
| ├ 设备家具维修 | /sbjjwxgl/list.htm | 未确认 |
| ├ 教职工周转房 | /gfgl/list.htm | 未确认 |
| └ 实验室安全管理 | /sysaq/list.htm | 未确认 |
| 党建工作—学习园地 | /xxyd/list.htm | 71 条 / 6 页 |
| 党建工作—支部动态 | /zbdt/list.htm | 7 条 |
| 党建工作—党务文件 | /dwwj/list.htm | 未确认 |
| 调拨公告（调拨信息） | /dbgg/list.htm | 29 条 / 3 页 |
| 业务管理平台 | /12131/list.htm | 未确认 |
| 大仪共享 | /12132/list.htm | 未确认 |

**下属系统**：设备家具固定资产管理系统 https://asset.scau.edu.cn/main/login.shtml ；仪器设备报修管理系统 http://emrs.scau.edu.cn/itsf/caslogin ；智慧实验室管理平台 http://222.201.228.129/login.html ；大仪共享预约 http://mis2.scau.edu.cn/scau-eqmgr （另有 `/scau-eqmgrb`、`/scau-eqmgrb/campusScreen`）

---

### 3.15 总务部 https://hqglc.scau.edu.cn/

- **旧版入口**：顶部 LOGO 与「网站首页」指向旧版 webplus：
  http://webplus.scau.edu.cn/_s287/main.psp ；http://webplus.scau.edu.cn/_s51/_t888/main.psp
- 路由风格：两者都有（数字栏目 `/1885`、`/1908` + 拼音别名 `/bmgk`、`/zwjj`）

| 栏目名称 | 列表页 URL（前缀 `https://hqglc.scau.edu.cn`） | 说明 |
|---|---|---|
| 部门概况 | /bmgk/list.htm | |
| 总务简介 | /zwjj/list.htm | 未确认 |
| 现任领导 | /xrld/list.htm | 未确认 |
| 机构设置 | /jgsz/list.htm | 未确认 |
| 机构设置—党政办公室 | /dzbgs/list.htm | 未确认 |
| 机构设置—前期计划科 | /qqjhk/list.htm | 未确认 |
| 机构设置—造价管理科 | /zjglk/list.htm | 未确认 |
| 机构设置—工程管理科 | /gcglk/list.htm | 未确认 |
| 机构设置—环境与物业科 | /hjywyk/list.htm | 未确认 |
| 机构设置—水电科（节能办） | /sdkwjnbw/list.htm | 未确认 |
| 机构设置—修缮管理科 | /xsglk/list.htm | 未确认 |
| 机构设置—饮食服务中心 | /ysfwzx_15403/list.htm | 未确认 |
| 机构设置—生活服务中心 | /shfwzx/list.htm | 未确认 |
| 机构设置—学生公寓服务中心 | /shfwzxwxsgyglfwzxw/list.htm | 未确认 |
| 管理制度（一级） | /1885/list.htm | 46 条 / 4 页 |
| ├ 综合管理类 | /zhgll/list.htm | 未确认 |
| ├ 财务经费类 | /cwjfl/list.htm | 未确认 |
| ├ 采购招标类 | /cgzbl/list.htm | 未确认 |
| ├ 安全生产类 | /aqscl/list.htm | 未确认 |
| ├ 基建维修类 | /jjwxl/list.htm | 未确认 |
| ├ 环境物业类 | /hjwyl/list.htm | 未确认 |
| ├ 水电管理类 | /sdgll/list.htm | 未确认 |
| ├ 宿舍管理类 | /ssgll/list.htm | 未确认 |
| ├ 小区物业类 | /xqwyl/list.htm | 未确认 |
| └ 中心实体类 | /zxstl/list.htm | 未确认 |
| 办事指南（一级） | /1886/list.htm | 9 条 |
| ├ 党政办公室 | /dzbgs_16560/list.htm | 未确认 |
| ├ 前期计划科 | /qqjhk_16561/list.htm | 未确认 |
| ├ 造价管理科 | /zjglk_16562/list.htm | 未确认 |
| ├ 环境与物业管理科 | /hjywyglk/list.htm | 未确认 |
| ├ 水电科（节能办） | /sdkwjnbw_16565/list.htm | 未确认 |
| ├ 饮食服务中心 | /ysfwzx_16566/list.htm | 未确认 |
| ├ 生活服务中心（学生公寓） | /shfwzxwxsgyw/list.htm | 未确认 |
| ├ 生活服务中心（物业） | /shfwzxwwyw/list.htm | 未确认 |
| ├ 生活服务中心（修建） | /shfwzxwxjw/list.htm | 未确认 |
| └ 修缮管理科 | /xsglk_18919/list.htm | 未确认 |
| 下载园地 | /1889/list.htm | 17 条 / 2 页 |
| 党建工作（一级） | /1888/list.htm | 无正文 |
| ├ 组织架构 | /zzjg/list.htm | 未确认 |
| └ 党务公开 | /djdt/list.htm | 未确认 |
| 工作动态 | /1908/list.htm | 62 条 / 5 页 |
| 总务通知（通知公告） | /1907/list.htm | 23 条 / 2 页 |
| 总务公开（招标/中标公示） | /1891/list.htm | 264 条 / 19 页 |
| 总务官微 | /1890/list.htm | 169 条 / 13 页 |
| 总务风采 | /zwfc/list.htm | 正文空 |
| 文化建设（一级） | /whjs/list.htm | |
| ├ 工会工作 | /ghgz/list.htm | 2 条 |
| ├ 离退休工作 | /ltxgz/list.htm | 未确认 |
| └ 其它工作 | /qtgz/list.htm | 未确认 |
| 办事指南侧栏模块 | /15409/list.htm | 文章前缀 c15409，未确认 |

**下属系统**：工程项目管理信息系统 http://202.116.162.108:81/Default.aspx

---

### 3.16 审计处 https://sjc.scau.edu.cn/

- 旧版入口：无独立「旧版」按钮；历史审计公告大量指向旧 webplus 站文章 `http://webplus.scau.edu.cn/_s3/...`
- 路由风格：两者都有（数字栏目 `/949`、`/1028` + 别名 `/zcfgw`、`/gjfg`、`/kysj`）

| 栏目名称 | 列表页 URL（前缀 `https://sjc.scau.edu.cn`） | 说明 |
|---|---|---|
| 部门概况 | /bmgk/list.htm | 未确认 |
| 部门简介 | /bmjj/list.htm | 未确认 |
| 机构设置 | /jgsz/list.htm | 未确认 |
| 职责范围 | /zzfw/list.htm | 未确认 |
| 审计动态 | /949/list.htm | 171 条 / 13 页 |
| 审计公告 | /1028/list.htm | 91 条 / 7 页 |
| 政策法规（表格视图） | /zcfgw/list.htm | 标题/文号/发文日期表格 |
| ├ 国家法规 | /gjfg/list.htm | 11 条 |
| ├ 省内法规 | /snfg/list.htm | 未确认 |
| └ 校内法规 | /xnfg/list.htm | 未确认 |
| 组织风采 | /zzfc/list.htm | 未确认 |
| 服务指南 | /kysj/list.htm | 未确认 |
| ├ 财务审计科 | /kysj/list.htm | 未确认 |
| ├ 工程审计科 | /jjzrsj/list.htm | 未确认 |
| └ 整改监督科 | /jsgcglsj/list.htm | 未确认 |
| 理论研究 | /llyj/list.htm | 10 条 |
| 典型案例 | /dxal/list.htm | 未确认 |
| 系统操作指引 | /xtczzy/list.htm | 正文空 |

**下属系统**：华南农业大学慧审通平台（审计管理/在线作业/整改跟踪/工程审计/数据分析预警/决策支持/远程协同，同一入口）http://222.201.224.99:8080/ais/login/loginView.jsp

---

### 3.17 国际交流处（港澳台事务办公室）https://fao.scau.edu.cn/

- 旧版入口：未发现；英文版入口 `ENGLISH` → http://english.scau.edu.cn/
- 路由风格：两者都有（数字栏目 `/4650`–`/4704` + 别名 `/bszn`、`/jdzn`、`/sqzn`）；每页 6 条

| 栏目名称 | 列表页 URL（前缀 `https://fao.scau.edu.cn`） | 说明 |
|---|---|---|
| 机构简介 | /4650/list.htm | 内容为「分管校长」 |
| ├ 分管校长 | /4660/list.htm | 未确认 |
| ├ 部门职能 | /4661/list.htm | 未确认 |
| ├ 科室设置 | /4662/list.htm | 未确认 |
| └ 联系我们 | /4663/list.htm | 未确认 |
| 政策法规 | /4651/list.htm | 内容为「来访交流」 |
| ├ 国际化建设 | /4666/list.htm | 未确认 |
| ├ 来访交流 | /4667/list.htm | 4 条 |
| ├ 因公出国（境） | /4668/list.htm | 未确认 |
| ├ 学生项目 | /4669/list.htm | 未确认 |
| ├ 外国人来华工作许可 | /4670/list.htm | 未确认 |
| └ 国际会议 | /4671/list.htm | 未确认 |
| 新闻中心 | /4652/list.htm | 13 条 / 3 页 |
| ├ 新闻速递 & 外事动态 | /4673/list.htm | 未确认 |
| └ 公告通知 | /4674/list.htm | 43 条 / 8 页 |
| 国际合作与交流 | /4653/list.htm | 未确认 |
| ├ 规章制度 | /4675/list.htm | 未确认 |
| ├ 合作院校（全球合作院校） | /4676/list.htm | 未确认 |
| ├ 来访交流 | /4677/list.htm | 未确认 |
| └ 接待指南 | /jdzn/list.htm | 未确认 |
| 学生项目 | /4655/list.htm | 内容为「项目申请流程」 |
| ├ 项目申请流程 | /sqzn/list.htm | 未确认 |
| ├ 项目一览表 | /xmylb/list.htm | 未确认 |
| ├ 奖学金项目 | /4681/list.htm | 未确认 |
| ├ 奖学金—留基委 | /4682/list.htm | 未确认 |
| ├ 寒暑假项目 | /4684/list.htm | 未确认 |
| ├ 学分转换 | /4685/list.htm | 未确认 |
| └ 联合培养 | /4686/list.htm | 未确认 |
| 国际会议 | /4656/list.htm | 未确认 |
| └ 会议指南 | /4688/list.htm | 未确认 |
| 外国人来华工作许可 | /4657/list.htm | 未确认 |
| ├ 管理条例 | /4691/list.htm | 未确认 |
| ├ 聘任手续 | /4692/list.htm | 未确认 |
| ├ 办事指南 | /4693/list.htm | 未确认 |
| └ 引智项目 | /4694/list.htm | 未确认 |
| 因公出访 | /4658/list.htm | 未确认 |
| ├ 管理办法 | /4695/list.htm | 未确认 |
| ├ 办理流程 | /4696/list.htm | 未确认 |
| ├ 出国办理指南 | /4697/list.htm | 未确认 |
| ├ 港澳办理指南 | /4698/list.htm | 未确认 |
| └ 台湾办事指南 | /4699/list.htm | 未确认 |
| 常用下载 | /4659/list.htm | 内容为「因公出访」下载表 |
| ├ 因公出访 | /4700/list.htm | 4 条 |
| ├ 来访交流 | /4701/list.htm | 未确认 |
| ├ 学生项目 | /4702/list.htm | 未确认 |
| ├ 外专外教 | /4703/list.htm | 未确认 |
| └ 国际会议 | /4704/list.htm | 未确认 |
| 办事指南（一级） | /bszn/list.htm | |
| ├ 来访报备流程 | /lfbblc/list.htm | 含流程图 |
| ├ 因公出访流程 | /ygcflc/list.htm | 未确认 |
| ├ 外专外教办证流程 | /wzwjbzlc/list.htm | 未确认 |
| └ 学生项目申请流程 | /xsxmsqlc/list.htm | 未确认 |
| **港澳台事务（一级）** | /4654/list.htm | 侧栏出现 |
| ├ 合作院校 | /4678/list.htm | 未确认 |
| ├ 交流动态 | /4679/list.htm | 41 条 / 7 页 |
| ├ 交流项目 | /4680/list.htm | 未确认 |
| └ 政策动态 | /zcdt/list.htm | 未确认 |

**下属子站**：英文版 http://english.scau.edu.cn/ ；中国—拉丁美洲农业教育科技创新联盟 https://claeria.scau.edu.cn/ ；中外合作办学 https://cie.scau.edu.cn/5523/list.htm ；网上办事服务大厅（外事报备入口）http://estop.scau.edu.cn/portal/index.jsp

---

### 3.18 乡村振兴与社会服务处 https://xzc.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：新版栏目别名（部分带数字后缀）；每页 15 条

| 栏目名称 | 列表页 URL（前缀 `https://xzc.scau.edu.cn`） | 说明 |
|---|---|---|
| 部门概况 | /bmgk/list.htm | 未确认 |
| 部门简介 | /bmgk_17791/list.htm | 未确认 |
| 部门领导 | /bmld/list.htm | 未确认 |
| 工作动态 | /gzdt/list.htm | 210 条 / 14 页 |
| 双百行动 | /sbxd/list.htm | 71 条 / 5 页 |
| 通知公告 | /tzgg/list.htm | 21 条 / 2 页 |
| 媒体报道 | /mtbd/list.htm | 311 条 / 21 页 |
| 支部建设（党建） | /zbjs/list.htm | 2 条 |
| 科技推广 | /kjtg/list.htm | 内容为「永根科技（服务）站」 |
| ├ 永根科技（服务）站 | /ygkjwfwwz/list.htm | 2 条 |
| ├ 科技特派员 | /kjtpy/list.htm | 未确认 |
| ├ 社会服务工作量管理 | /shfwgzlgl/list.htm | 未确认 |
| └ 乡村振兴百万人才团队 | /xczxbwrctd/list.htm | 未确认 |
| 产学研合作 | /cxyhz/list.htm | 内容为「校外产学研科创平台」 |
| ├ 校外产学研科创平台 | /ykcptsbygl/list.htm | 5 条 |
| └ 先行从化 | /xxch/list.htm | 未确认 |
| 定点帮扶 | /wsbxdwzcwj/list.htm | 内容为「"双百行动"政策文件」 |
| ├ 「双百行动」政策文件 | /wsbxdwzcwj/list.htm | 4 条 |
| ├ 高校联盟建设 | /gxlmjs/list.htm | 未确认 |
| └ 其他 | /qt/list.htm | 未确认 |
| 办事指南 | /bszn/list.htm | 内容为「办事流程」 |
| ├ 办事流程 | /bslc/list.htm | OA 审批操作指引 |
| └ 规章制度 | /gzzd/list.htm | 正文空 |
| 联系我们 | /lxwm/list.htm | 未确认 |

**下属子站**：广东农村政策研究中心 https://rprc.scau.edu.cn/ ；社会服务管理系统 https://shfw.scau.edu.cn/login

---

### 3.19 对外联络处（校友会、教育发展基金会秘书处）https://dwllc.scau.edu.cn/

- 旧版入口：未发现
- 路由风格：两者都有（数字栏目 `/20281`–`/20424` + 别名 `/xwdt`、`/djgz`、`/tzgg`、`/jzdt`）

| 栏目名称 | 列表页 URL（前缀 `https://dwllc.scau.edu.cn`） | 说明 |
|---|---|---|
| 组织架构 | /20281/list.htm | 未确认 |
| ├ 单位简介 | /20321/list.htm | 未确认 |
| ├ 单位领导 | /bmld/list.htm | 未确认 |
| ├ 科室职责 | /20322/list.htm | 未确认 |
| └ 规章制度 | /20323/list.htm | 未确认 |
| 资讯动态（一级） | /20282/list.htm | 未确认 |
| ├ 新闻动态 | /xwdt/list.htm | 39 条 / 3 页 |
| ├ 党建动态 | /djgz/list.htm | 21 条 / 2 页 |
| └ 通知公告 | /tzgg/list.htm | 15 条 / 2 页 |
| 校董事会 | /20283/list.htm | 未确认 |
| ├ 简介章程 | /20349/list.htm | 未确认 |
| └ 工作动态 | /20351/list.htm | 15 条 / 2 页 |
| 香港教育发展基金会 | /20286/list.htm | 内容为「机构简介」 |
| ├ 机构简介 | /20361/list.htm | 未确认 |
| └ 工作动态 | /20362/list.htm | 未确认 |
| 校友企业家联盟 | /20287/list.htm | 内容为「联盟简介」 |
| ├ 联盟简介 | /20363/list.htm | 未确认 |
| └ 联盟动态 | /20364/list.htm | 未确认 |
| 办事指南 | /20288/list.htm | 5 条图片入口 |
| ├ 校友服务 | /xy_20491/list.htm | 未确认 |
| ├ 下载专区 | /20420/list.htm | 正文仅「下载内容1」 |
| ├ 公益项目 | /20423/list.htm | 未确认 |
| └ 捐赠指南 | /20424/list.htm | 未确认 |
| **捐赠动态** | /jzdt/list.htm | **1553 条 / 111 页**（捐赠人/金额明细） |

**下属子站**：校友会 https://scauxyh.scau.edu.cn/ （子栏 `/3556/list.htm` 校友服务、`/14883/list.htm` 校友活动）；教育发展基金会 https://jyjjh.scau.edu.cn/ （子栏 `/3539/list.htm` 捐赠服务）

---

### 3.20 资产与实验室管理处、总务部以外的其余部处入口

| 部处 | 官网 | 状态 |
|---|---|---|
| 党委统战部 | https://dwtzb.scau.edu.cn/ | 未确认 |
| 党委教师工作部（师德师风） | https://jsgzb.scau.edu.cn/ | 未确认 |
| 教师教学发展中心 | https://cfd.scau.edu.cn/ | ✅（通知公告 https://cfd.scau.edu.cn/tzgg/list.htm） |

---

## 4. 派驻机构

| 机构名称 | 官网地址 | 状态 |
|---|---|---|
| 省纪委监委驻华南农业大学纪检监察组（校纪委） | https://jiwei.scau.edu.cn/ | ✅（旧域名 `http://jiwei.scau.edu.cn`） |

---

## 5. 教辅单位

| 单位名称 | 官网地址 | 状态 |
|---|---|---|
| 采购招标中心 | https://cgglxt.scau.edu.cn/ | ✅ |
| 测试中心（实验动物中心） | http://cszx.scau.edu.cn/ | ✅ |
| 信息网络中心 | http://inc.scau.edu.cn/ | ✅（旧域名 `metc.scau.edu.cn`） |
| 基础实验与实践训练中心 | http://syxl.scau.edu.cn/ | ✅ |
| 图书馆 | https://lib.scau.edu.cn/ | ✅ |
| 文博馆（档案馆、华南农业博物馆） | http://wbg.scau.edu.cn/ | ✅ |
| 农业农村部植物新品种测试（广州）分中心 | https://gzdus.scau.edu.cn/ | ✅ |
| 科教基地服务中心 / 基地管理处 | https://jd.scau.edu.cn/ | ✅ |

### 5.1 图书馆 https://lib.scau.edu.cn/

| 栏目名称 | 列表页 URL | 说明 |
|---|---|---|
| 通知公告 | https://lib.scau.edu.cn/tzgg/list.htm | |
| 新闻通知（聚合） | http://lib.scau.edu.cn/xwtz/list.htm | |
| 本馆资讯 | http://lib.scau.edu.cn/bgzx/list.htm | |
| 培训信息 | http://lib.scau.edu.cn/pxxx/list.htm | |
| 电子资源 | https://lib.scau.edu.cn/dzzy/list.htm | |
| 馆藏书刊 | https://lib.scau.edu.cn/gzsk/list.htm | |
| 馆藏书刊—特色资源 | https://lib.scau.edu.cn/tszy/list.htm | |
| 服务—科研服务 | https://lib.scau.edu.cn/kyfw/list.htm | |
| 服务—教学培训 | https://lib.scau.edu.cn/jxpx/list.htm | |
| 服务—借阅服务 | https://lib.scau.edu.cn/ggyl_14651/list.htm | |
| 服务—其他服务 | https://lib.scau.edu.cn/sqzy/list.htm | |
| 服务—申请指引 | https://lib.scau.edu.cn/sqzy_15050/list.htm | |
| 本馆概况 | https://lib.scau.edu.cn/bggk/list.htm | |
| 本馆概况—本馆简介 | https://lib.scau.edu.cn/bgjj/list.htm | |
| 本馆概况—规章制度 | https://lib.scau.edu.cn/gzzd_11451/list.htm | |
| 本馆概况—组织机构 | https://lib.scau.edu.cn/jgsz1/list.htm | |
| 本馆概况—党建工作 | https://lib.scau.edu.cn/dj/main.htm | |
| 本馆概况—布局风貌 | https://lib.scau.edu.cn/grgm/list.htm | |
| 本馆概况—招标公告 | https://lib.scau.edu.cn/zbgg/list.htm | |
| 本馆概况—图书馆教师发展分中心 | https://lib.scau.edu.cn/tsgjsfz/list.htm | |
| 科技查新 | http://lib.scau.edu.cn/kjcx/list.htm | |
| 校外访问—使用帮助 | https://lib.scau.edu.cn/sybz/list.htm | |
| 校外访问—WebVPN 座位预约 | https://lib.scau.edu.cn/sjdtgVPNfwwzwwkjyyw/list.htm | |
| 校外访问—aTrust 座位预约 | https://lib.scau.edu.cn/aTrustfwzwyy/list.htm | |
| 读者培训 | http://lib.scau.edu.cn/xxsykc/list.htm | |
| 研究生新生入馆培训 | http://lib.scau.edu.cn/yjsrxpx/list.htm | |
| 本科毕业生培训 | http://lib.scau.edu.cn/xspx/list.htm | |
| 检索技术 | http://lib.scau.edu.cn/jsjs_14822/list.htm | |
| 数据管理 | http://lib.scau.edu.cn/sjgl/list.htm | |
| 论文排版 | http://lib.scau.edu.cn/lwpb/list.htm | |
| 论文相似性检测 | http://lib.scau.edu.cn/xsbdylwxsxjc/list.htm | |
| 信息素养微课堂 | http://lib.scau.edu.cn/wlwk/list.htm | |
| 微课堂—检索类 | http://lib.scau.edu.cn/jsjs/list.htm | |
| 微课堂—工具类 | http://lib.scau.edu.cn/gjl/list.htm | |
| 微课堂—写作类 | http://lib.scau.edu.cn/xzl/list.htm | |
| 微课堂—资源发现 | http://lib.scau.edu.cn/zyfx/list.htm | |
| 数据库在线培训 | http://lib.scau.edu.cn/sjkspx/list.htm | |
| 周二四晚培训 | http://lib.scau.edu.cn/cgpx/list.htm | |
| 好书推荐 | http://lib.scau.edu.cn/hstj/list.htm | |
| 在线展览/图片展览 | http://lib.scau.edu.cn/tpzl/list.htm | |
| FAQ 常见问题 | http://lib.scau.edu.cn/yjhkswd/list.htm | |
| 电子资源相关问题 | https://lib.scau.edu.cn/2021/1228/c14631a301389/page.htm | |
| 图书借还及座位问题 | https://lib.scau.edu.cn/2021/1228/c14631a301392/page.htm | |
| 研究生论文提交问题 | https://lib.scau.edu.cn/2021/1228/c14631a301393/page.htm | |
| 学科馆员咨询 | https://lib.scau.edu.cn/2020/0611/c14394a248101/page.htm | |
| 数据库试用/购买（kx 栏目） | https://lib.scau.edu.cn/kx_14371/list.htm | |
| 线下+线上培训（xsxx） | https://lib.scau.edu.cn/xsxx/list.htm | |

**下属系统 / 平台**：

| 名称 | 地址 |
|---|---|
| 实时馆情 | https://scau.libtop.com/v3/ |
| 座位/空间预约 | https://libseat.scau.edu.cn |
| 书目检索（OPAC） | https://libopac.scau.edu.cn/ |
| 电子资源平台 | https://lib2.scau.edu.cn/esourceController.do?db&page=db&siteCode=portal |
| 知识产权信息服务 | https://ipis.scau.edu.cn/ |
| 华农学术成果库 | https://scholar.scau.edu.cn/ |
| 校外访问 WebVPN | https://lib-scau-edu-cn-s.vpn.scau.edu.cn:443/ |

---

## 6. 科研单位（科研平台 / 实验室 / 研究中心）

### 6.1 国家级科研平台（独立网站）

| 平台名称 | 官网地址 | 状态 |
|---|---|---|
| 国家植物航天育种工程技术研究中心 | https://htyzzx.scau.edu.cn/ | ✅ |
| 国家生猪种业工程技术研究中心 | https://hnszzx.scau.edu.cn/ | ✅ |
| 国家精准农业航空施药技术国际联合研究中心 | https://npaac.scau.edu.cn/ | ✅ |
| 人兽共患病防控制剂国家地方联合工程实验室（广东） | https://vet.scau.edu.cn/_t436/2015/1116/c829a53772/page.psp | ✅ |
| 国家兽医微生物耐药性风险评估实验室 | https://vet.scau.edu.cn/_t436/2015/1116/c829a53951/page.psp | ✅ |
| 亚热带农业生物资源保护与利用国家重点实验室 | 见科研平台页转链 | 未确认独立域名 |
| 农业装备技术全国重点实验室（共建） | https://kyy.scau.edu.cn/2025/0214/c11891a399113/page.htm | ✅ |
| 猪禽种业全国重点实验室（共建） | https://kyy.scau.edu.cn/2025/0214/c11891a399117/page.htm | ✅ |
| 动物疫病防控全国重点实验室（共建） | https://kyy.scau.edu.cn/2025/0214/c11891a399118/page.htm | ✅ |
| 绿色农药全国重点实验室（共建） | https://kyy.scau.edu.cn/2025/0214/c11891a399120/page.htm | ✅ |
| 畜禽育种国家地方联合工程研究中心（广东） | https://kyy.scau.edu.cn/2025/0214/c11891a399125/page.htm | ✅ |
| 畜禽产品精准加工与安全控制技术国家地方联合工程研究中心 | https://kyy.scau.edu.cn/2025/0214/c11891a399130/page.htm | ✅ |
| 国家禽流感专业实验室（广州） | https://kyy.scau.edu.cn/2025/0214/c11891a399128/page.htm | ✅ |
| 国家非洲猪瘟区域实验室（广州） | https://kyy.scau.edu.cn/2025/0214/c11891a399129/page.htm | ✅ |

### 6.2 其他科研机构站点

| 机构名称 | 地址 | 状态 |
|---|---|---|
| 农业部转基因植物及植物用微生物环境安全监督检验测试中心（广州） | https://swjsxy.scau.edu.cn/ | ✅ |
| 广东省畜禽种质资源库 / 国家区域性畜禽基因库 | http://www.gdgenebank.scau.edu.cn/gw/ | ✅ |
| 节水抗旱稻绿色产业研究院 | https://wdr.scau.edu.cn/ | 未确认（农学院公布） |
| 广东农村政策研究中心 | https://rprc.scau.edu.cn/ | 未确认（乡村振兴与社会服务处公布） |
| 岭南农耕文明重点实验室 | https://rw.scau.edu.cn/lnngwmzdsys/list.htm | ✅ |
| 南方农业机械与装备关键技术教育部重点实验室 | https://gcxy.scau.edu.cn/nfnyjxyzbgjjsjybzdsys/list.htm | ✅ |
| 海洋学院实验教学中心 | https://hy.scau.edu.cn/hysyzx/ | ✅ |
| 亚热带农业生物资源保护与利用国家重点实验室 | 未确认独立域名 | — |

### 6.3 国际联盟 / 国际合作机构

| 机构名称 | 地址 |
|---|---|
| 中国—拉丁美洲农业教育科技创新联盟 | https://claeria.scau.edu.cn/ |
| 中外合作办学（托管于国际教育学院） | https://cie.scau.edu.cn/5523/list.htm |

> **完整科研平台清单**（国家级 / 省部级 / 市厅级 / 自设 / 校企共建）：
> - 国家级 https://kyy.scau.edu.cn/sbjyszdsys/list.htm
> - 国家发改委 https://kyy.scau.edu.cn/gjfgw/list.htm
> - 教育部 https://kyy.scau.edu.cn/jyb/list.htm
> - 自然资源部 https://kyy.scau.edu.cn/zrzyb/list.htm
> - 农业农村部 https://kyy.scau.edu.cn/nyncb/list.htm
> - 广东省平台 https://kyy.scau.edu.cn/gdspt/list.htm
> - 市厅局级 https://kyy.scau.edu.cn/tjjkypt/list.htm
> - 自设研究机构 https://kyy.scau.edu.cn/xjkypt/list.htm
> - 地方/企业共建 https://kyy.scau.edu.cn/hnwskjcxzx/list.htm

---

## 7. 群团组织 / 附属单位

| 单位名称 | 官网地址 | 状态 |
|---|---|---|
| 中国教育工会华南农业大学委员会 | http://xgh.scau.edu.cn/ | ✅ |
| 共青团华南农业大学委员会 | https://xtw.scau.edu.cn/ | ✅ |
| 广东华农大资产经营有限公司 | http://zgs.scau.edu.cn/ | ✅ |
| 校医院 | http://xyy.scau.edu.cn/ | ✅ |
| 附属小学 | http://scaufx.scau.edu.cn/ | ✅ |
| 幼儿园 | http://yey.scau.edu.cn/ | ✅ |

### 7.1 省纪委监委驻华南农业大学纪检监察组（校纪委）https://jiwei.scau.edu.cn/

- ⚠️ 首页正文**仅返回一张图片**（模板 792，疑为 JS 渲染/单图首页）；`/main.htm` 同样只有图片；`/index.htm` = **404**
- 旧版入口：**有** —— 页脚「旧版链接」→ http://web.scau.edu.cn/jjjc/ ；旧模板路径前缀 `/_t181/`（模板 181）；旧 ASP 系统入口 http://jiwei.scau.edu.cn/Web/Article.aspx?cid=22
- ⚠️ `https://jiwei.scau.edu.cn/_t181/main.htm`、`http://jiwei.scau.edu.cn/list.htm` 触发重定向环

#### A. 新版（模板 792）

| 栏目名称 | 列表页 URL | 说明 |
|---|---|---|
| 综合信息 | https://jiwei.scau.edu.cn/zhxx/list.htm | 正文空 |
| 廉洁教育 | https://jiwei.scau.edu.cn/ljjy/list.htm | 内容为「廉洁文化路线」 |
| ├ 廉洁文化路线 | https://jiwei.scau.edu.cn/ljwhlx/list.htm | 1 条 |
| ├ 纪法小课 | https://www.ccdi.gov.cn/jfxkn/ | 外链 |
| ├ 最美家风 | https://www.gdjct.gd.gov.cn/zthz/xznyzmjf/index.html | 外链 |
| └ 在线展馆 | https://www.gdjct.gd.gov.cn/wszt/index.html | 外链 |
| 法规制度 | https://jiwei.scau.edu.cn/fgzd/list.htm | 未确认 |
| ├ 校内规章制度 | https://jiwei.scau.edu.cn/xngzzd/list.htm | 未确认 |
| ├ 党内法规制度 | https://www.ccdi.gov.cn/fgk/law_validity_01 | 外链 |
| └ 国家法律法规 | https://www.ccdi.gov.cn/fgk/law_validity_02 | 外链 |
| 专题专栏 | https://jiwei.scau.edu.cn/ztzl/list.htm | 未确认 |
| ├ 权威解读 | https://jiwei.scau.edu.cn/qwjd/list.htm | 未确认 |
| ├ 习近平总书记全面从严治党 | https://people.ccdi.gov.cn/ | 外链 |
| └ 纪检监察干部应知应会 | https://www.gdjct.gd.gov.cn/zthz/jjjcgbyzyh/index.html | 外链 |
| 资料下载 | https://jiwei.scau.edu.cn/2412/list.htm | 未确认 |
| 栏目备份—党纪法规 | https://jiwei.scau.edu.cn/lmbf/list.htm | 未确认 |
| 栏目备份—党纪法规—上级文件 | https://jiwei.scau.edu.cn/2421/list.htm | 未确认 |

#### B. 旧版（模板 181，`/_t181/` 前缀）—— **重点保留**

| 栏目名称 | 列表页 URL | 说明 |
|---|---|---|
| 首页 | http://jiwei.scau.edu.cn/_t181/main.htm | ⚠️ 重定向环 |
| 机构职能 | https://jiwei.scau.edu.cn/_t181/2404/list.htm | 未确认 |
| ├ 工作职责 | https://jiwei.scau.edu.cn/_t181/2415/list.htm | 未确认 |
| ├ 职岗职责 | https://jiwei.scau.edu.cn/_t181/2416/list.htm | 未确认 |
| └ 机构人员 | https://jiwei.scau.edu.cn/_t181/2417/list.htm | 未确认 |
| 新闻动态 | https://jiwei.scau.edu.cn/_t181/2405/list.htm | 未确认 |
| 时政要闻 | https://jiwei.scau.edu.cn/_t181/2406/list.htm | 未确认（另有 ASP 版 `/Web/Article.aspx?cid=22`） |
| 通知公告 | https://jiwei.scau.edu.cn/_t181/2407/list.htm | 子页 `/_t181/2025/0620/c2407a412143/page.psp` ✅ |
| 党纪法规 | https://jiwei.scau.edu.cn/_t181/2408/list.htm | 未确认 |
| ├ 学校文件 | https://jiwei.scau.edu.cn/_t181/2420/list.htm | 未确认 |
| └ 上级文件 | https://jiwei.scau.edu.cn/_t181/2421/list.htm | 未确认 |
| 廉政教育 | https://jiwei.scau.edu.cn/_t181/2409/list.htm | 未确认 |
| 廉洁社团 | https://jiwei.scau.edu.cn/_t181/2410/list.htm | 未确认 |
| 资料下载 | https://jiwei.scau.edu.cn/_t181/2412/list.htm | 未确认 |

**下属系统**：廉控系统 http://fxjh.scau.edu.cn/ ；旧版站点 http://web.scau.edu.cn/jjjc/

---

### 7.2 中国教育工会华南农业大学委员会 https://xgh.scau.edu.cn/

- **旧版入口**：**有** —— 页脚「回顾旧版」→ **https://xgh.scau.edu.cn/_s91/_t221/main.psp**
- 路由风格：新版栏目别名

| 栏目名称 | 列表页 URL（前缀 `https://xgh.scau.edu.cn`） | 说明 |
|---|---|---|
| 工会概况 | /ghgk/list.htm | 未确认 |
| ├ 工会简介 | /ghjj/list.htm | 未确认 |
| ├ 组织机构 | /zzjg/list.htm | 未确认 |
| ├ 工作机构 | /gzjg/list.htm | 未确认 |
| ├ 工作职责 | /gzzz/list.htm | 未确认 |
| ├ 女工委 | /ngw/list.htm | 未确认 |
| └ 青工委 | /qgw/list.htm | 未确认 |
| **工会要闻** | /ghyw/list.htm | **702 条 / 51 页** |
| **通知讲座** | /tzjz/list.htm | **507 条 / 37 页** |
| 融媒头条 | /rmtt/list.htm | 68 条 / 5 页 |
| 部门工会 | /bmgh_14911/list.htm | 356 条 / 26 页 |
| 教工协会 | /jgxh_14912/list.htm | 首页入口 |
| 教工风采 | /jgfc/list.htm | 15 条 / 2 页 |
| 民主管理 | /mzgl/list.htm | 未确认 |
| ├ 教代会 | /jdh/list.htm | 未确认 |
| ├ 工代会 | /gdh/list.htm | 未确认 |
| ├ 提案工作 | /tagz/list.htm | 未确认 |
| └ 信息公开 | /xxgk/list.htm | 未确认 |
| 党建工作 | /djgz/list.htm | 内容为「党建动态」 |
| ├ 党建动态 | /djdt/list.htm | 18 条 / 2 页 |
| ├ 党建专题 | /djzt/list.htm | 未确认 |
| └ 学习资料 | /xxzl/list.htm | 未确认 |
| 宣传教育 | /xcjy/list.htm | 未确认 |
| ├ 师德师风 | /sdsf/list.htm | 未确认 |
| ├ 劳模工匠 | /lmgj/list.htm | 未确认 |
| ├ 理论研究 | /llyj/list.htm | 未确认 |
| ├ 工会刊物 | /ghkw/list.htm | 未确认 |
| └ 工运简史 | /gyjs/list.htm | 未确认 |
| 服务阵地 | /fwzd/list.htm | 未确认 |
| ├ 职工小家 | /zgxj/list.htm | 未确认 |
| ├ 困难帮扶 | /knbf/list.htm | 未确认 |
| ├ 法援中心 | /fyzx/list.htm | 未确认 |
| ├ 心晴家园 | /xqjy/list.htm | 未确认 |
| └ 青工驿站 | /qgyz/list.htm | 未确认 |
| 二级组织 | /ejzz/list.htm | 未确认 |
| ├ 部门工会 | /bmgh/list.htm | 另有 `_14911` 变体 |
| └ 教工协会 | /jgxh/list.htm | 另有 `_14912` 变体 |
| 办事指南 | /bszn/list.htm | 未确认 |
| ├ 规章制度 | /gzzd/list.htm | 未确认 |
| ├ 权益申诉 | /qyss/list.htm | 未确认 |
| ├ 业务咨询 | /ywzx/list.htm | 未确认 |
| └ 下载专区 | /xzzq/list.htm | 未确认 |
| 权益维护/提案工作/会员管理/工会活动 | 文章前缀 c14639 | 未发现独立列表页 |

---

### 7.3 共青团华南农业大学委员会 https://xtw.scau.edu.cn/

- **旧版入口**：**有** —— 顶部 LOGO 指向 **http://202.116.160.8/_s28/_t1387/main.psp**
- 路由风格：新版栏目别名（部分带数字后缀）

| 栏目名称 | 列表页 URL | 说明 |
|---|---|---|
| 新闻中心 | https://xtw.scau.edu.cn/1076/list.htm | 64 条 / 5 页 |
| 通知公告 | https://xtw.scau.edu.cn/tzgg/list.htm | 140 条 / 10 页 |
| 媒体报道 | https://xtw.scau.edu.cn/mtbd/list.htm | 184 条 / 14 页 |
| 学院风采 | https://xtw.scau.edu.cn/xyfc/list.htm | 300 条 / 22 页 |
| 学习路上 | https://xtw.scau.edu.cn/xxls/list.htm | 39 条 / 3 页 |
| 视频剪映 | https://xtw.scau.edu.cn/spzs/list.htm | 14 条 |
| 资料下载 | https://xtw.scau.edu.cn/zlxz/list.htm | 含《场地借用申请表.docx》 |
| 团委概况 | https://xtw.scau.edu.cn/twgk/list.htm | 内容为「成员分工」 |
| ├ 团委职能 | https://xtw.scau.edu.cn/twzn_16210/list.htm | 未确认 |
| ├ 成员分工 | https://xtw.scau.edu.cn/cyfg_16211/list.htm | 7 条 |
| └ 学院团委书记 | https://xtw.scau.edu.cn/xytwsj/list.htm | 未确认 |
| 思想引领 | https://xtw.scau.edu.cn/sxyl/list.htm | 未确认 |
| ├ 理论学习 | https://xtw.scau.edu.cn/llxx_7680/list.htm | 未确认 |
| ├ 青马工程 | https://xtw.scau.edu.cn/qmgc_7681/list.htm | 未确认 |
| └ 学「习」社 | https://xtw.scau.edu.cn/xwxws/list.htm | 未确认 |
| 组织建设 | https://xtw.scau.edu.cn/zzjs/list.htm | 未确认 |
| ├ 智慧团建 | https://xtw.scau.edu.cn/zhtj/list.htm | 未确认 |
| └ 活力在基层 | https://xtw.scau.edu.cn/hlzjc/list.htm | 未确认 |
| 科技创新 | https://xtw.scau.edu.cn/kjcx/list.htm | 未确认 |
| ├ 攀登计划 | https://xtw.scau.edu.cn/pdjh/list.htm | 未确认 |
| ├ 挑战杯 | https://xtw.scau.edu.cn/tzb/list.htm | 未确认 |
| └ 创青春 | https://xtw.scau.edu.cn/cqc/list.htm | 未确认 |
| 社会实践 | https://xtw.scau.edu.cn/shsj/list.htm | 未确认 |
| ├ 社区实践 | https://xtw.scau.edu.cn/sqsj/list.htm | 未确认 |
| ├ 志愿服务 | https://xtw.scau.edu.cn/zyfw/list.htm | 未确认 |
| └ 社会实践 | https://xtw.scau.edu.cn/shsj_7674/list.htm | 未确认 |
| 校园文化 | https://xtw.scau.edu.cn/xywh/list.htm | 未确认 |
| └ 文体艺术 | https://xtw.scau.edu.cn/wtys/list.htm | 未确认 |
| 学生组织 | https://xtw.scau.edu.cn/xszz/list.htm | 未确认 |
| ├ 校团委直属学生部门 | https://xtw.scau.edu.cn/xtwzsxsbm/list.htm | 未确认 |
| ├ 校学生会 | https://xtw.scau.edu.cn/xxsh/list.htm | 未确认 |
| ├ 校研究生会 | https://xtw.scau.edu.cn/yjsh/list.htm | 未确认 |
| ├ 学生社团工作部 | https://xtw.scau.edu.cn/stgzb/list.htm | 未确认 |
| ├ 青年志愿者服务中心 | https://xtw.scau.edu.cn/qnzyzfwzx/list.htm | 未确认 |
| └ 蚂蚁工作室 | https://xtw.scau.edu.cn/mygzs/list.htm | 未确认 |
| 社团风采 | https://xtw.scau.edu.cn/stfc/list.htm | 未确认 |
| ├ 社团工作部 | https://xtw.scau.edu.cn/stlhh/list.htm | 未确认 |
| └ 缤纷社团 | https://xtw.scau.edu.cn/bfst/list.htm | 未确认 |
| 联系我们 | http://xtw.scau.edu.cn/2023/0222/c16397a336610/page.htm | 单篇文章 |
| 组织数据页 | `/2022/1027/c16030a328430/page.htm`、`…a328431`、`…a328432`、`…a328433` | 首页模块 |

**校外业务平台**：智慧团建 https://tuan.12355.net/bg/index.html ；青年之声 https://www.12355.net/ ；I 志愿 https://www.gdzyz.cn/ ；易展翅 https://www.izhanchi.com/

---

### 7.4 广东华农大资产经营有限公司 https://zgs.scau.edu.cn/

- 旧版入口：未发现；部分栏目文章指向 webplus 旧站（`https://webplus.scau.edu.cn/_s94/2025/0424/c19159a407183/page.psp` 领导关怀）
- ⚠️ `/xwzx/`、`/gsdt/`、`/tzgg/`、`/djgz/` 为 **重定向环，无法抓取**

| 栏目名称 | 列表页 URL（前缀 `https://zgs.scau.edu.cn`） | 说明 |
|---|---|---|
| 公司概况 | /gsgk/list.htm | 6 条 |
| ├ 公司领导 | /gsld_14865/list.htm | 未确认 |
| ├ 企业概况 | http://zgs.scau.edu.cn/2021/0827/c13318a288213/page.htm | 单篇 |
| ├ 组织架构 | http://zgs.scau.edu.cn/2021/0827/c13318a288214/page.htm | 单篇 |
| ├ 领导关怀 | https://webplus.scau.edu.cn/_s94/2025/0424/c19159a407183/page.psp | 旧站单篇 |
| ├ 我们的团队 | http://zgs.scau.edu.cn/2021/0827/c13318a288219/page.htm | 单篇 |
| └ 企业文化 | http://zgs.scau.edu.cn/2021/0827/c13318a288223/page.htm | 单篇 |
| 党群工作（一级） | /djgz/list.htm | ⚠️ 重定向环 |
| ├ 党建专题 | /djzt/list.htm | 未确认 |
| ├ 学习动态 | /xxdt/list.htm | 未确认 |
| ├ 党廉建设 | /dljs/list.htm | 未确认 |
| └ 党团工作 | /dtgz/list.htm | 未确认 |
| 新闻中心（一级） | /xwzx/list.htm | ⚠️ 重定向环 |
| └ 公司动态 | /gsdt/list.htm | ⚠️ 重定向环（首页文章前缀 c13921） |
| 通知公告 | /tzgg/list.htm | ⚠️ 重定向环（首页「更多+」，文章前缀 c13212） |
| 产业布局 | http://zgs.scau.edu.cn/qzqy/list.htm | 内容为「全资企业」 |
| ├ 全资企业 | /qzqy/list.htm | 8 条 |
| ├ 参股企业 | /cgqy/list.htm | 未确认 |
| └ 技术入股企业 | /jsrgqy/list.htm | 未确认 |
| 经营管理 | /jygl/list.htm | 正文空 |
| ├ 优质产品 | http://zgs.scau.edu.cn/2021/0827/c13318a288221/page.htm | 单篇 |
| └ 科研资源 | http://zgs.scau.edu.cn/2021/0827/c13318a288215/page.htm | 单篇 |
| 办事指南 | /bszn/list.htm | 内容为「法律法规」 |
| ├ 法律法规 | /flfg/list.htm | 正文空 |
| ├ 政策措施 | /zccs/list.htm | 未确认 |
| ├ 学校发文 | /xxfw/list.htm | 未确认 |
| └ 公司制度 | /gszd/list.htm | 未确认 |
| 产业动态 | http://zgs.scau.edu.cn/cydt/list.htm | 未确认 |
| 文化活动 | http://zgs.scau.edu.cn/whhd/list.htm | 未确认 |

**全资/参股企业**（站内文章，非独立网站）：广州华农大食品科技有限公司、广东省华农正大禽业有限公司、广东华农高科生物药业有限公司、广州市华农大科技园管理有限公司、广州市华农大动物医院有限公司、广州市华农大商业服务有限公司、广州市奇康饮品有限公司、广州华农大工程技术开发有限公司

**旧版站点（站点 ID `_s94`）**：https://webplus.scau.edu.cn/_s94/…

---

### 7.5 校医院、附属小学、幼儿园

| 单位名称 | 官网地址 | 状态 |
|---|---|---|
| 校医院 | http://xyy.scau.edu.cn/ | ✅ |
| 附属小学 | http://scaufx.scau.edu.cn/ | ✅ |
| 幼儿园 | http://yey.scau.edu.cn/ | ✅ |

---

## 8. 招生 / 就业 / 校友 / 捐赠 专题门户

### 8.1 本科招生网 https://zsb.scau.edu.cn/

| 栏目名称 | 列表页 URL |
|---|---|
| 招生快讯—普通类招生 | http://zsb.scau.edu.cn/ptlzs/list.htm |
| 招生快讯—艺术类招生 | http://zsb.scau.edu.cn/yslzs/list.htm |
| 招生快讯—高水平运动队招生 | http://zsb.scau.edu.cn/gspyddzs/list.htm |
| 招生快讯—港澳台招生 | http://zsb.scau.edu.cn/gatzs/list.htm |
| 招生快讯—国际化办学 | https://zsb.scau.edu.cn/gjhrcpyb/list.htm |
| 招生快讯—其它 | http://zsb.scau.edu.cn/qt/list.htm |
| 招生政策 | http://zsb.scau.edu.cn/4284/list.htm |
| 招生政策—招生章程 | http://zsb.scau.edu.cn/4293/list.htm |
| 招生政策—学校政策 | http://zsb.scau.edu.cn/4297/list.htm |
| 招生政策—广东省政策 | http://zsb.scau.edu.cn/4296/list.htm |
| 招生政策—国家政策 | http://zsb.scau.edu.cn/4295/list.htm |
| 招生计划 | https://zsb.scau.edu.cn/gd_20001/list.htm |
| 招生简章 | http://zsb.scau.edu.cn/zsjz/list.htm |
| 历年分数—历年专业录取分数 | http://zsb.scau.edu.cn/lnlqfs/list.htm |
| 历年分数—历年学校投档分数 | http://zsb.scau.edu.cn/lnfs_9044/list.htm |
| 招宣动态 | http://zsb.scau.edu.cn/zsxcdt/list.htm |
| 学子风采 | http://zsb.scau.edu.cn/xzfc/list.htm |
| 视频华农 / 招生宣传视频 | https://zsb.scau.edu.cn/zsxcsp/list.htm |
| 宣传片 | http://zsb.scau.edu.cn/jchn/list.htm |
| 特色班介绍 | http://zsb.scau.edu.cn/tsbjs/list.htm |
| 热点关注 | http://zsb.scau.edu.cn/rdgz/list.htm |
| 四新建设 | http://zsb.scau.edu.cn/xgkxnk/list.htm |
| 校园新闻 | http://zsb.scau.edu.cn/xyxw/list.htm |
| 媒体华农 | http://zsb.scau.edu.cn/mthn/list.htm |
| 学校简介 | http://zsb.scau.edu.cn/xxjj/list.htm |
| 联系我们 | http://zsb.scau.edu.cn/4291/list.htm |
| 本科招生小程序 | http://zsb.scau.edu.cn/bkzsxcx/list.htm |
| 微信公众号 | http://zsb.scau.edu.cn/wxgzh/list.htm |
| 学校微博 | http://zsb.scau.edu.cn/xxwb/list.htm |
| 学校抖音 | http://zsb.scau.edu.cn/xxdy/list.htm |
| 2023 师兄师姐说专业电子书 | http://zsb.scau.edu.cn/2023sxsjszydzs/list.htm |

**下属**：录取查询 https://lqtz.scau.edu.cn/ ；招办 B 站 https://space.bilibili.com/513429163 ；考生常见问题解答 https://zsb.scau.edu.cn/gkzxjd/

### 8.2 研究生招生网

| 项目 | 地址 |
|---|---|
| 官网 | https://yzb.scau.edu.cn/ | 未确认（站内广泛引用） |

### 8.3 就业创业信息网 https://jyzx.scau.edu.cn/

> ⚠️ 该站为云研科技（bysjy.com.cn）第三方平台，栏目以 `?type_id=&menu_id=` 参数寻址，**非 list.htm 形态**。

| 栏目名称 | 地址 |
|---|---|
| 新闻公告—通知公告 | https://jyzx.scau.edu.cn/module/news?type_id=720&menu_id=1006 |
| 新闻公告—新闻快讯 | https://jyzx.scau.edu.cn/module/news?type_id=723&menu_id=1006 |
| 新闻公告—就业质量年报 | https://jyzx.scau.edu.cn/module/news?type_id=3951&menu_id=1006 |
| 招聘信息—招聘快讯 | https://jyzx.scau.edu.cn/module/news?type_id=19870&menu_id=1009 |
| 招聘信息—校内宣讲会 | https://jyzx.scau.edu.cn/module/careers?menu_id=1009 |
| 招聘信息—校外宣讲会 | https://jyzx.scau.edu.cn/module/careers?type=outer&menu_id=1009 |
| 招聘信息—在线招聘 | https://jyzx.scau.edu.cn/module/onlines?menu_id=1009 |
| 招聘信息—双选会 | https://jyzx.scau.edu.cn/module/jobfairs?menu_id=1009 |
| 招聘信息—正式岗位 | https://jyzx.scau.edu.cn/module/jobs?is_practice=0&menu_id=1009 |
| 招聘信息—实习岗位 | https://jyzx.scau.edu.cn/module/jobs?is_practice=1&menu_id=1009 |
| 生源信息—生源速览 | https://jyzx.scau.edu.cn/module/news?type_id=725&menu_id=1016 |
| 生源信息—学院专业 | https://jyzx.scau.edu.cn/module/news?type_id=726&menu_id=1016 |
| 业务指南—政策指南 | https://jyzx.scau.edu.cn/module/news?type_id=20213&menu_id=1057 |
| 业务指南—毕业生办事指南 | https://jyzx.scau.edu.cn/module/news?type_id=741&menu_id=1057 |
| 业务指南—单位服务指南 | https://jyzx.scau.edu.cn/module/news?type_id=727&menu_id=1057 |
| 业务指南—常用下载 | https://jyzx.scau.edu.cn/module/news?type_id=20201&menu_id=1057 |
| 业务指南—其他下载 | https://jyzx.scau.edu.cn/module/news?type_id=20214&menu_id=1057 |
| 宏志助航培训班—基地介绍 | https://jyzx.scau.edu.cn/module/news?type_id=17591&menu_id=36712 |
| 宏志助航培训班—新闻动态 | https://jyzx.scau.edu.cn/module/news?type_id=17592&menu_id=36712 |
| 宏志助航培训班—师资介绍 | https://jyzx.scau.edu.cn/module/news?type_id=17593&menu_id=36712 |
| 宏志助航培训班—学员风采 | https://jyzx.scau.edu.cn/module/news?type_id=17594&menu_id=36712 |
| 学校简介 | https://jyzx.scau.edu.cn/detail/news?id=4732&menu_id=1001 |
| 部门概况 | https://jyzx.scau.edu.cn/detail/news?id=4733&menu_id=1001 |
| 联系我们 | https://jyzx.scau.edu.cn/detail/news?id=4736&menu_id=1022 |
| 生源信息（登录版） | https://jyzx.scau.edu.cn/detail/student_source_info |

### 8.4 校友 / 基金 / 联络

| 名称 | 地址 | 状态 |
|---|---|---|
| 校友会（对外联络处） | https://dwllc.scau.edu.cn/ | ✅ |
| 校友网（新版入口） | https://scauxyh.scau.edu.cn/ | ✅ |
| 教育发展基金会（捐赠） | https://jyjjh.scau.edu.cn/ | ✅ |
| 基金会—动态信息 | https://jyjjh.scau.edu.cn/3544/list8.htm | 未确认 |
| 校友会（旧域名） | http://alumni.scau.edu.cn/ | 未确认 |

### 8.5 国际教育 / 继续教育

| 名称 | 地址 |
|---|---|
| 国际教育学院 | https://cie.scau.edu.cn/ |
| 国际教育学院（英文版） | https://cie.scau.edu.cn/cie_english/ |
| 国际教育学院（英文版旧域名） | http://english.cie.scau.edu.cn/ |
| 广州都柏林国际生命科学与技术学院 | https://gdic.scau.edu.cn/ |
| 广州都柏林国际学院（英文版） | https://gdic.scau.edu.cn/gdicen/ |
| 继续教育学院 | https://jxjy.scau.edu.cn/ |
| 留学生报名系统 | https://scau.at0086.cn/student |
| 国际交流处（港澳台事务办公室） | http://fao.scau.edu.cn/ |

---

## 9. 专题网站 / 业务系统

| 名称 | 地址 |
|---|---|
| 卢永根专题网 | https://lyg.scau.edu.cn/ |
| 华农人物网 | https://hnr.scau.edu.cn/ |
| 115 周年校庆专题网 | https://115.scau.edu.cn/ |
| 「百千万工程」专题网 | https://xcb.scau.edu.cn/bqw/ |
| 树立和践行正确政绩观专题 | https://xcb.scau.edu.cn/xjp/ |
| 本科教学评估专题 | https://jwc.scau.edu.cn/jxpg/ |
| 大学生思政在线 | https://szzx.scau.edu.cn/ |
| 勤工助学 | http://qgzx.scau.edu.cn/ |
| 两学一做专题 | https://lxyz.scau.edu.cn/ |
| 社会服务管理系统 | https://shfw.scau.edu.cn/login |
| 廉洁风险防控（廉控系统） | http://fxjh.scau.edu.cn/ |
| 华农学报（在线投稿/阅读） | http://xuebao.scau.edu.cn/ch/index.aspx |
| 学报（旧域名入口） | http://xuebao.scau.edu.cn/ |
| 电子校报 | https://hnxb.scau.edu.cn/ |
| 招标采购中心 | https://cgglxt.scau.edu.cn/ |
| 知识产权信息服务 | https://ipis.scau.edu.cn/ |
| 华农学术成果库 | https://scholar.scau.edu.cn/ |
| 智慧党建系统 | https://hndj.scau.edu.cn/#/login |
| 党建专题网（人工智能与低空技术学院） | https://dzxy.scau.edu.cn/dzdj/ |
| 兽医党建网（兽医学院） | https://vet.scau.edu.cn/sydj/ |
| 党建工作网（人文与法学学院） | https://rw.scau.edu.cn/dangjian/main.htm |
| 党建工作网（林学与风景园林学院） | https://lf.scau.edu.cn/dangjiangongzuo/ |
| 就业与创新创业服务中心（人文与法学学院） | https://rw.scau.edu.cn/jicengjiuye/ |
| 专业认证专题站（食品学院） | https://spxy.scau.edu.cn/sprz/ |
| 就业与创业信息网（食品学院） | https://spxy.scau.edu.cn/jiuye/ |
| 海洋学院实验教学中心 | https://hy.scau.edu.cn/hysyzx/ |
| 园艺学实验教学中心 | https://yy.scau.edu.cn/syjxsfzx/ |
| 转基因检测中心 | https://swjsxy.scau.edu.cn/ |
| 农学院英文版 | https://nxy.scau.edu.cn/nxyenglish/ |
| 食品学院英文版 | https://spxy.scau.edu.cn/spxy_en/ |
| 动物科学学院英文版 | https://dongke.scau.edu.cn/dongke_en/main.psp |
| 国际教育学院英文版 | https://cie.scau.edu.cn/cie_english/ |
| 广州都柏林国际学院英文版 | https://gdic.scau.edu.cn/gdicen/ |
| 中拉农业教育科技创新联盟 | https://claeria.scau.edu.cn/ |
| 广东农村政策研究中心 | https://rprc.scau.edu.cn/ |
| 节水抗旱稻绿色产业研究院 | https://wdr.scau.edu.cn/ |
| 广东省畜禽种质资源库 | http://www.gdgenebank.scau.edu.cn/gw/ |
| 招生宣传门户（第三方 360eol） | https://gaokaobang.360eol.com/rector/2024/scau/index.html?v=102 |

### 9.1 学校规章 / 信息公开

| 名称 | 地址 |
|---|---|
| 信息公开网 | https://xxgk.scau.edu.cn/ |
| 学校规章 | https://xngk.scau.edu.cn/gzzd/list.htm |
| 网上办事大厅 | https://service.scau.edu.cn/taskcenter-v4-new/workflow/index |

---

## 10. 旧版网站汇总（← 重点保留）

> 华南农业大学站点群经历多轮改版。**识别旧版的方法与已确认入口如下。**

### 10.1 识别旧版站点的实用方法

1. 站点首页右上角 / 页脚查找「返回旧版」「旧版网站」「旧版回顾」链接。
2. URL 中出现 `_t数字`（模板区）或 `_s数字`（站点区）前缀的路径。
3. 栏目使用**纯数字栏目号**（如 `/1234/list.htm`），多为旧版遗留栏目。
4. 正文页以 `page.psp` 结尾的多为旧模板。
5. **最可靠**：访问旧版站群统一门户 `https://webplus.scau.edu.cn/_s{站点ID}/main.psp`。
6. 查询历史快照：`https://web.archive.org/web/*/站点域名/*`。

### 10.2 已确认的旧版入口

| 站点 | 旧版地址 | 状态 / 说明 |
|---|---|---|
| **学校主站** | https://www.scau.edu.cn/_t104/main.htm | ✅ 官网右上角「返回旧版」指向；`_t104` 为旧模板分区 |
| 学校主站（psp 渲染） | https://www.scau.edu.cn/_t104/main.psp | ✅ |
| 学校主站多模板分区（示例） | https://www.scau.edu.cn/_s3/17935/list.psp | ✅ |
| **本科生院（教务处）** | https://jwc.scau.edu.cn/_t291/main.psp | ✅ 站内明确标注「旧版网站」 |
| 本科生院（站点区） | https://jwc.scau.edu.cn/_s124/main.psp | ✅ |
| **公共管理学院** | https://ggglxy.scau.edu.cn/_t206/ | ✅ 站头「旧版网站」 |
| **人工智能与低空技术学院** | https://dzxy.scau.edu.cn/_s156/_t432/main.psp | ✅ 原电子工程学院旧版整站 |
| 人工智能与低空技术学院（旧版英文） | http://dzxy.scau.edu.cn:88 | 未确认 |
| **资源环境学院** | https://webplus.scau.edu.cn/_s82/main.psp | ✅ 站点 ID `_s82`，模板 `_t1734` |
| **海洋学院** | https://webplus.scau.edu.cn/_s125/_t1778/main.psp | ✅ 站点 ID `_s125`，模板 `_t1778` |
| 海洋学院实验教学中心 | http://webplus.scau.edu.cn/_s287/main.psp | ✅ |
| 海洋学院实验教学中心（子目录旧版） | http://webplus.scau.edu.cn/hysyzx/main.psp | 未确认 |
| **生命科学学院** | https://webplus.scau.edu.cn/_s83/main.psp | ✅ 站点 ID `_s83` |
| **马克思主义学院** | http://webplus.scau.edu.cn/_s287/main.psp | 跨协议跳转，未确认 |
| **农学院** | http://nxy.scau.edu.cn/_t1378/main.htm | ❌ 「旧版回顾」链接已失效（重定向循环） |
| 农学院（旧版 webplus 路径） | http://webplus.scau.edu.cn/_s287/_t1693/xyxw/list.psp | 未确认 |
| **林学与风景园林学院** | http://webplus.scau.edu.cn/_s24/_t636/lxxk/list.psp | 未确认（师资名录旧版） |
| 林学与风景园林学院（党建网旧版） | http://webplus.scau.edu.cn/dangjiangongzuo/djxw/list.psp | 未确认 |
| 林学与风景园林学院（旧模板首页） | https://lf.scau.edu.cn/_upload/tpl/02/7c/636/template636/index.htm | 未确认 |
| **财务处** | https://cwc.scau.edu.cn/_s9/main.psp | ✅ 旧版路由前缀 `/_s9/` |
| **兽医学院** | https://vet.scau.edu.cn/_t436/… | ✅ 旧分区（国家级实验室页面） |
| **总务部** | http://webplus.scau.edu.cn/_s287/main.psp ；http://webplus.scau.edu.cn/_s51/_t888/main.psp | 未确认（站内 LOGO 与「网站首页」指向） |
| **校纪委（纪检监察组）** | http://web.scau.edu.cn/jjjc/ | 未确认（页脚「旧版链接」） |
| 校纪委旧模板区 | https://jiwei.scau.edu.cn/_t181/… | 未确认（模板 181） |
| **工会** | https://xgh.scau.edu.cn/_s91/_t221/main.psp | 未确认（页脚「回顾旧版」） |
| **团委** | http://202.116.160.8/_s28/_t1387/main.psp | 未确认（顶部 LOGO 指向） |
| **资产经营有限公司** | https://webplus.scau.edu.cn/_s94/… | 未确认（站点 ID `_s94`） |
| 宣传部专题网 | http://webplus.scau.edu.cn/_s327/main.psp | 未确认 |
| 国际教育学院 | https://cie.scau.edu.cn/cie_english/_t1662/… | 未确认（模板 `_t1662`） |
| 国际教育学院（来华留学旧版） | http://202.116.160.8/_s128/_t1200/… | 未确认（站点 ID `_s128`） |
| **转基因检测中心** | http://202.116.160.8/_s90/… | 未确认 |
| 原重点实验室建设办公室 | http://sysjs.scau.edu.cn/ | 旧站 |
| 原学报编辑部 | http://xuebao.scau.edu.cn/ | 旧入口（现为 `xuebao.scau.edu.cn/ch/index.aspx`） |
| 旧教务系统 | http://jwxtxs.scau.edu.cn/default2.aspx | ⚠️ 需登录 |
| 工程学院旧版遗留栏目 | https://gcxy.scau.edu.cn/{2084…2091}/list.htm | 页脚旧数字栏目 |
| 数学与信息学院「移除栏目备份2020」 | https://info.scau.edu.cn/yclmbf2020/list.htm | 备份栏目父页 |
| 马克思主义学院「栏目备份」 | https://jiwei.scau.edu.cn/lmbf/list.htm | 备份栏目 |
| 人力资源处旧/备用栏目群 | https://hr.scau.edu.cn/{pfck,bsznw,rsgz1,tzgg1,djgz1…}/list.htm | 旧/备用栏目 |
| 信息网络中心旧域名 | http://metc.scau.edu.cn/ | 现用 `inc.scau.edu.cn` |
| 材料与能源学院旧域名 | http://cme.scau.edu.cn/ | 现用 `cmce.scau.edu.cn` |
| 党政办公室旧域名 | http://dwbgs.scau.edu.cn/ | 现用 `dzbgs.scau.edu.cn`（两域名并存可访问） |
| 纪委办、监察处旧域名 | http://jiwei.scau.edu.cn | 现用 `https://jiwei.scau.edu.cn` |
| 科学研究院旧域名 | http://kjc.scau.edu.cn/ | 现用 `kyy.scau.edu.cn` |
| 学生工作部旧 IP 入口 | http://202.116.160.8/login.jsp?inner=1 | 部分站点旧后台 |
| 统一旧后台（全校多数站点） | http://webplus.scau.edu.cn/login.jsp?inner=1 | 全部站点管理入口 |

### 10.3 站点群 ID 对照（用于构造旧版 `.psp` 入口）

| 站点 | 站点 ID | 模板 ID | 旧版入口 |
|---|---|---|---|
| 资源环境学院 | `_s82` | `_t1734` | https://webplus.scau.edu.cn/_s82/main.psp |
| 生命科学学院 | `_s83` | — | https://webplus.scau.edu.cn/_s83/main.psp |
| 转基因检测中心 | `_s90` | — | http://202.116.160.8/_s90/… |
| 财务处 | `_s9` | — | https://cwc.scau.edu.cn/_s9/main.psp |
| 海洋学院 | `_s125` | `_t1778` | https://webplus.scau.edu.cn/_s125/_t1778/main.psp |
| 海洋学院实验教学中心 | `_s287` | — | http://webplus.scau.edu.cn/_s287/main.psp |
| 人工智能与低空技术学院 | `_s156` | `_t432` | https://dzxy.scau.edu.cn/_s156/_t432/main.psp |
| 本科生院 | `_s124` | `_t291` | https://jwc.scau.edu.cn/_s124/main.psp |
| 公共管理学院 | — | `_t206` | https://ggglxy.scau.edu.cn/_t206/ |
| 兽医学院 | — | `_t436` | https://vet.scau.edu.cn/_t436/… |
| 校纪委（纪检监察组） | — | `_t181` | https://jiwei.scau.edu.cn/_t181/… |
| 农学院 | `_s287` | `_t1378` / `_t1693` | http://nxy.scau.edu.cn/_t1378/main.htm ❌ |
| 林学与风景园林学院 | `_s24` | `_t636` | http://webplus.scau.edu.cn/_s24/_t636/lxxk/list.psp |
| 主站 | `_s3` | `_t104` | https://www.scau.edu.cn/_t104/main.htm |
| 宣传部专题网 | `_s327` | — | http://webplus.scau.edu.cn/_s327/main.psp |
| 总务部 | `_s51` | `_t888` | http://webplus.scau.edu.cn/_s51/_t888/main.psp |
| 工会 | `_s91` | `_t221` | https://xgh.scau.edu.cn/_s91/_t221/main.psp |
| 团委 | `_s28` | `_t1387` | http://202.116.160.8/_s28/_t1387/main.psp |
| 资产经营有限公司 | `_s94` | — | https://webplus.scau.edu.cn/_s94/… |
| 国际教育学院 | — | `_t1662` | https://cie.scau.edu.cn/cie_english/_t1662/… |
| 国际教育学院（来华留学） | `_s128` | `_t1200` | http://202.116.160.8/_s128/_t1200/… |
| 马克思主义学院 | `_s287` | — | http://webplus.scau.edu.cn/_s287/main.psp |
| 农学院（教师详情托管） | `_s18` | — | https://webplus.scau.edu.cn/_s18/… |

### 10.4 各站英文版汇总

| 站点 | 英文版地址 | 状态 |
|---|---|---|
| 学校主站 | http://english.scau.edu.cn/ | 未确认 |
| 农学院 | https://nxy.scau.edu.cn/nxyenglish/ | ✅ |
| 食品学院 | https://spxy.scau.edu.cn/spxy_en/ | ✅ |
| 动物科学学院 | https://dongke.scau.edu.cn/dongke_en/main.psp | ✅（内容更新至 2020 年） |
| 国际教育学院 | https://cie.scau.edu.cn/cie_english/ | ✅ |
| 广州都柏林国际学院 | https://gdic.scau.edu.cn/gdicen/ | ✅ |
| 外国语学院 | https://sfs.scau.edu.cn/3291/list.htm | ✅（仅英文简介页） |
| 转基因检测中心 | https://swjsxy.scau.edu.cn/jczx/ | 未确认 |
| 人工智能与低空技术学院 | https://dzxy.scau.edu.cn/dzxyen/ | 未确认 |
| 经济管理学院 | http://cem.scau.edu.cn/cem_en | 未确认 |
| 生命科学学院 | https://life.scau.edu.cn/life_en/ | ❌ 重定向回主站 |
| 工程学院 | https://gcxy.scau.edu.cn/gcxyen/ | ❌ 重定向回主站 |
| 湾区设计与艺术学院 | https://art.scau.edu.cn/arten/ | ❌ 重定向回主站 |
| 园艺学院 | http://yy.scau.edu.cn/yyen | ❌ 重定向回主站 |
| 兽医学院 | https://vet.scau.edu.cn/veten/ | ❌ 重定向回主站 |
| 林学与风景园林学院 | https://lf.scau.edu.cn/lfen/ | ❌ 重定向回主站 |
| 资源环境学院（数学与信息学院） | http://info.scau.edu.cn/info_en/ | ❌ 重定向回主站 |
| 公共管理学院 | https://ggglxy.scau.edu.cn/english/ | ❌ 重定向（`/english/index.htm` 404） |
| 国际教育学院（旧域名） | http://english.cie.scau.edu.cn/ | 未确认 |

---

## 11. 网站群子域名清单（SCAU 域名资产）

> 来源：被动 DNS 数据（HackerTarget hostsearch）与各站点交叉引用，用于核对是否遗漏站点。
> `*.course.scau.edu.cn` 为课程/教学平台集群；解析至 `1.1.1.1` 的多为占位。

### 11.1 已确认为官网/门户的域名

```
www  nxy  zb  lf  yy  vet  dongke  zyhjxy  hy  life  gcxy  spxy  wcce
info  dzxy  cmce  cme(旧)  cfb  mkszyxy  cem  ggglxy  rw  sfs  art
tyb  jxjy  cie  gdic  cxcyxy  scauzhujiang(独立学院)  wdr  rprc
dzbgs  dwbgs(旧)  zzb  dztzb  xcb  xg  bwc  hr  jsgzb  ltx  fzghc
jwc  yjsy  kyy  kjc(旧)  cwc  zcc  hqglc  sjc  fao  xzc  dwllc
jiwei  xgh  xtw  zgs  xyy  scaufx  yey
cgglxt  cszx  inc  metc(旧)  syxl  lib  wbg  gzdus  jd
zsb  yzb  jyzx  scauxyh  alumni  jyjjh  lyg  hnr  115  szzx
xuebao  hnxb  ipis  scholar  sysjs(旧)  cfd  jxpj  cxcygl  xngk
htyzzx  hnszzx  npaac  swjsxy  gdgenebank  claeria  fxjh
```

### 11.2 业务系统 / 平台类子域名

| 子域名 | 用途 |
|---|---|
| portal.scau.edu.cn | 融合门户 |
| cas.scau.edu.cn | 统一身份认证 |
| cas.bigdataxny.scau.edu.cn | 大数据新能源认证节点 |
| service.scau.edu.cn | 网上办事服务大厅 |
| estop.scau.edu.cn | 网上办事（旧） / 书记院长信箱 |
| oa.scau.edu.cn | OA 办公系统 |
| xxgk.scau.edu.cn | 信息公开 |
| xngk.scau.edu.cn | 学校规章 |
| jwzf.scau.edu.cn / jwxt.scau.edu.cn | 教务管理系统 |
| jwxtxs.scau.edu.cn | 旧教务系统 |
| jkpt.jwc.scau.edu.cn | 教学质量监控平台 |
| pgzx.scau.edu.cn | 质量工程网 |
| bkbylw.scau.edu.cn | 毕业论文（设计）系统 |
| kyglxt.scau.edu.cn | 科研管理系统 |
| xgxt.scau.edu.cn | 学生工作系统（迎新 / 综测 / 学籍 / 学工队伍） |
| cxcygl.scau.edu.cn | 学科竞赛管理系统 |
| zp.scau.edu.cn | 招聘系统 |
| hr2.scau.edu.cn | 人力资源管理系统 |
| libopac.scau.edu.cn | 图书馆书目检索 |
| libseat.scau.edu.cn | 图书馆座位/空间预约 |
| lib2.scau.edu.cn | 图书馆电子资源平台 |
| lib-scau-edu-cn-s.vpn.scau.edu.cn | 图书馆校外访问 WebVPN |
| vpn.scau.edu.cn | 校园 VPN |
| mail.scau.edu.cn | 教工邮箱 |
| pay.scau.edu.cn | 统一支付平台 |
| clpt.scau.edu.cn | 智慧差旅平台 |
| hndj.scau.edu.cn | 智慧党建系统 |
| jxpj.scau.edu.cn | 教学质量管理平台 |
| lqtz.scau.edu.cn | 录取查询 |
| qgzx.scau.edu.cn | 勤工助学 |
| szzx.scau.edu.cn | 大学生思政在线 |
| lxyz.scau.edu.cn | 两学一做专题 |
| shfw.scau.edu.cn | 社会服务管理系统 |
| labsra.scau.edu.cn | 实验室安全考试系统 |
| xnfzsyjx.scau.edu.cn | 虚拟仿真实验平台 |
| emrs.scau.edu.cn | 仪器设备报修管理系统 |
| mis2.scau.edu.cn | 大仪共享预约（`/scau-eqmgr`、`/scau-eqmgrb`） |
| asset.scau.edu.cn / 2fasset.scau.edu.cn | 固定资产管理系统 |
| skhysjy.scau.edu.cn | 会议室预约（生命科学学院） |
| tybtcxt.scau.edu.cn | 体质测试系统（体育学院） |
| tybyldpage.scau.edu.cn | 阳光体育（体育学院） |
| acm.scau.edu.cn | 程序设计竞赛 |
| bigdata.scau.edu.cn | 大数据相关 |
| bingo.scau.edu.cn | 业务系统 |
| bksypt.scau.edu.cn | 本科实验平台 |
| cemstu.scau.edu.cn | 经管学生系统 |
| cbsim.scau.edu.cn | 经管仿真 |
| ceol.scau.edu.cn | 在线教育 |
| cjd.scau.edu.cn | 继续教育相关 |
| clyy.scau.edu.cn | 材料与能源相关 |
| bwcx.scau.edu.cn / 110.scau.edu.cn | 保卫处 / 报警 |
| by.scau.edu.cn | 毕业相关 |
| voyage001.scau.edu.cn | AI 应用（华农小研）节点 |
| yjsglxt.scau.edu.cn | 研究生招生目录系统 |
| 202.116.160.8 / 202.116.160.105 / 202.116.162.70 / 202.116.162.93 / 202.116.160.44:8004 / 222.201.224.99:8080 / 222.201.225.29 / 222.201.226.48 / 222.201.228.129 / 210.76.83.199 | IP 直连业务系统（旧后台、财务、科研、心理、林学就业、慧审通、学业导师、内控、智慧实验室、党员管理） |
| *.course.scau.edu.cn | 课程/教学资源集群（bjys、cbx、cpx、dgydzjs、dwx、fjgc、fzshx、gcjcjx、gcllx、gclx、gczj、gdsx、gjmy、gjzwsl、gllsltj、gnspx、hhzpx、jxzzgyx、kcslsh、kjxyl、nyjjx、nyjxx、nykcx、oop 等） |

### 11.3 校外合作 / 第三方平台（非 scau.edu.cn 域名）

| 平台 | 地址 | 用途 |
|---|---|---|
| 招生宣传门户（360eol） | https://gaokaobang.360eol.com/rector/2024/scau/index.html?v=102 | 本科招生宣传 |
| 留学生报名系统 | https://scau.at0086.cn/student | 来华留学申请 |
| 成人教育授课平台（超星） | https://hnnydx.jxjy.chaoxing.com/login | 继续教育 |
| 成人学历教育平台 | https://scaujxjy.o-learn.cn/login.jsp | 继续教育 |
| 继教 OA | https://hnndoa.o-learn.cn/ | 继续教育管理 |
| 成教论文查重 | https://vpcs.fanyu.com/personal/hnndjxjy | 继续教育 |
| 研究生在线课程平台 | https://gsscau.yuketang.cn/pro/portal/home/ | 研究生教学 |
| 图书馆实时馆情 | https://scau.libtop.com/v3/ | 图书馆 |
| 就业创业信息网技术方 | https://jyzx.scau.edu.cn/ （平台：hnnydx.bysjy.com.cn） | 就业 |
| 都柏林大学侧 GDIC 页 | https://www.ucd.ie/gdic/ | 国际合作 |
| 图书馆数据库 | https://www.cnki.net/ 、http://www.webofknowledge.com/ 、http://www.sciencedirect.com/ 等 | 电子资源 |

### 11.4 疑似占位 / 非站点解析

`1.scau.edu.cn`、`123.scau.edu.cn`、`2foa.scau.edu.cn`、`bsd1.scau.edu.cn` 等解析至 `1.1.1.1`，非有效站点。

---

## 12. 内容量最大的列表页（爬取优先级参考）

| 排名 | 站点 | 栏目 | 条数 / 页数 |
|---|---|---|---|
| 1 | 党委宣传部 | 媒体华农 `/380/list.htm` | 4597 条 / 92 页 |
| 2 | 主站 | 媒体华农 `/17864/list.htm` | 4598 条 / 460 页 |
| 3 | 主站 | 学校要闻 `/xxyw/list.htm`（204 页）/ `/17646/list.htm`（285 页） | 2843 条 |
| 4 | 党委宣传部 | 学校要闻 `/xxyw/list.htm` | 2843 条 / 57 页 |
| 5 | 科学研究院 | 通知公告 `/tzgg/list.htm` | 1798 条 / 129 页 |
| 6 | 研究生院 | 通知公告 `/208/list.htm` | 1469 条 / 105 页 |
| 7 | 党委组织部 | 通知公告 `/tzgg/list.htm` | — |
| 8 | 外国语学院 | 公告公示 `/3518/list.htm` | 1375 条 / 99 页 |
| 9 | 研究生院 | 通知公告 `/208/list.htm` | 1469 条 |
| 10 | 公共管理学院 | 学工通知 `/xgtz/list.htm` | 1042 条 / 75 页 |
| 11 | 食品学院 | 学院通告 `/6187/list.htm` | 1335 条 / 96 页 |
| 12 | 党委保卫部 | 通知公告 `/786/list.htm` | 824 条 / 55 页 |
| 13 | 主站 | 学术动态 `/17863/list.htm`（76 页）/ `/17648/list.htm`（54 页） | 756 / 754 条 |
| 14 | 土木与水利工程学院 | 学院动态 `/4274/list.htm` | 184 条 |
| 15 | 公共管理学院 | 学院新闻 `/xyxw_11881/list.htm` | 674 条 / 49 页 |
| 16 | 食品学院 | 学院要闻 `/6186/list.htm` | 869 条 / 63 页 |
| 17 | 海洋学院 | 学院新闻 `/xyxw/list.htm` | 718 条 / 52 页 |
| 18 | 湾区设计与艺术学院 | 招聘信息 `/2555/list.htm` | 711 条 / 51 页 |
| 19 | 湾区设计与艺术学院 | 学院新闻 `/2552/list.htm` | 685 条 / 49 页 |
| 20 | 生命科学学院 | 通知公告 `/tzgg/list.htm` | 645 条 / 47 页 |
| 21 | 公共管理学院 | 公告公示 `/gs/list.htm` | 552 条 / 40 页 |
| 22 | 人力资源处 | 通知公告 `/tzgg/list.htm` | 501 条 / 36 页 |
| 23 | 资源环境学院 | 通知公告 `/tzgg_19902/list.htm` | 422 条 / 31 页 |
| 24 | 人文与法学学院 | 本科生通知 `/bkstz/list.htm` | 405 条 / 29 页 |
| 25 | 外国语学院 | 学生通知 `/xstzcscj/list.htm` | 455 条 / 33 页 |

---

## 13. 使用建议

1. **批量抓取列表页**：本站群统一为 `listN.htm` 分页形态，可按 `栏目列表页 + list2.htm … listN.htm` 顺序抓取；新版站点亦支持部分 `?page=N`。
2. **正文页规律与去重**：
   - 新版站点：`/年/月日/c栏目号a文章号/page.htm`
   - 旧版站点：同形，或 `page.psp`
   - ⚠️ **主站聚合页会同时挂载多个栏目的正文页链接**，同一文章可能有 `c17646`、`c17859`、`c1300` 等多个栏目号副本，抓取时需按「文章号 a{ID}」去重。
3. **跨协议跳转陷阱**：本站群大量站点在 `http://` 与 `https://` 之间存在 301/302 互跳。工具无法跟随时应改用：
   - `https://…/_s{ID}/{栏目}/list.psp`（多数站点旧版路由同时可服务新版栏目）
   - 或 `https://cwc.scau.edu.cn/main.psp` 形式
4. **旧版留存**：建议对第 10 节所列入口逐一做历史快照查询与离线存档；`webplus.scau.edu.cn/_s{ID}/` 门户是集中留存旧版的最佳位置。
5. **登录墙**：第 11.2 节标注业务系统类子域（融合门户、信息公开、教务系统、科研管理系统、学工系统、邮箱、财务平台等）需统一身份认证，非公开列表页。
6. **已失效 / 空栏目**（实测）：`tyb /xwhd`、`tyb /jctyr`、`art /2530`、`cie /zsjz`、`dongke /tzgg`、`cfb /xsjz`、`cfb /kyjz`、`mkszyxy /pxdt`、`rw /3693`、`rw /gs`、`ggglxy /xsdt`（止于 2020）、`dongke /dkzsw/`（重定向）、`life /life_en/`、`gcxy /gcxyen/`、`art /arten/`。

---

*本文档由站点实测整理。所有 URL 均来自实际抓取或抓取到的页面链接；未确认项已如实标注。站点内容与结构可能随时间变动。*
