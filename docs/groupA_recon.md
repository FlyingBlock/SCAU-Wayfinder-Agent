# SCAU 学院官网侦察报告 — Group A

> 说明：状态码为 `web_fetch` 实际返回。标注「仅见链接」的 URL 来自页面导航/页脚超链接，未逐条抓取；其余均为已实际抓取成功（HTTP 200）的页面。

---

## 农学院
- 官网首页: https://nxy.scau.edu.cn/  (状态: 200)
- 旧版入口: 页面顶部有「旧版回顾」→ http://nxy.scau.edu.cn/_t1378/main.htm （抓取时 http→https→http 重定向循环，未能取得内容，疑似失效）；另发现旧版 webplus 栏目路径 http://webplus.scau.edu.cn/_s287/_t1693/xyxw/list.psp （首页「学院新闻-查看更多」指向）
- 路由风格: 两者都有 — 新版栏目 `/xxx/list.htm`；文章页与旧版数字模板路径混用（`/2026/1013/c14465a448632/page.htm`、`/_upload/tpl/06/9d/1693/template1693/...`）

### 信息发布/列表页面
| 栏目名称 | 列表页URL | 说明 |
|---|---|---|
| 学院新闻 | https://nxy.scau.edu.cn/xyxw/list.htm | 已抓取 200；183 条 / 23 页；列表页支持 /xyxw/list2.htm … listN.htm |
| 通知公告（学院） | https://nxy.scau.edu.cn/tzgg/list.htm | 已抓取 200；191 条 / 24 页 |
| 讲座论坛 | https://nxy.scau.edu.cn/jzltw/list.htm | 已抓取 200；61 条 / 8 页 |
| 党建动态 | https://nxy.scau.edu.cn/djdt/list.htm | 已抓取 200；46 条 / 6 页；面包屑显示上级为「党群动态 /dqdt/list.htm」 |
| 科研进展 | https://nxy.scau.edu.cn/kyjz/list.htm | 已抓取 200；92 条 / 12 页 |
| 工会工作 | https://nxy.scau.edu.cn/ghgz/list.htm | 仅见链接（党建动态页侧栏） |
| 党群动态 | https://nxy.scau.edu.cn/dqdt/list.htm | 仅见链接 |
| 招贤纳士（人才招聘） | https://nxy.scau.edu.cn/zxns/list.htm | 仅见链接（首页轮播图/底部） |
| 学院概况 | https://nxy.scau.edu.cn/xygk_17945/list.htm | 已抓取 200（实为「学院简介」正文页） |
| 学院简介 | https://nxy.scau.edu.cn/xyjj_17955/list.htm | 仅见链接 |
| 现任领导 | https://nxy.scau.edu.cn/xrld_17997/list.htm | 仅见链接 |
| 机构设置 | https://nxy.scau.edu.cn/jgsz/list.htm | 仅见链接 |
| 师资队伍 | https://nxy.scau.edu.cn/szdw_17946/list.htm | 仅见链接 |
| 优秀人才 | https://nxy.scau.edu.cn/yxrc/list.htm | 仅见链接 |
| 在编教师 | https://nxy.scau.edu.cn/jsmlw/list.htm | 仅见链接 |
| 行政教辅人员 | https://nxy.scau.edu.cn/xzjfry/list.htm | 仅见链接 |
| 辅导员 | https://nxy.scau.edu.cn/fdy/list.htm | 仅见链接 |
| 实验中心人员 | https://nxy.scau.edu.cn/syzxry/list.htm | 仅见链接 |
| 博士后 | https://nxy.scau.edu.cn/bsh/list.htm | 仅见链接 |
| 班主任 | https://nxy.scau.edu.cn/bzr/list.htm | 仅见链接 |
| 人才培养 | https://nxy.scau.edu.cn/rcpy_17947/list.htm | 仅见链接 |
| 专业建设 | https://nxy.scau.edu.cn/zyjs_17962/list.htm | 仅见链接 |
| 课程设置 | https://nxy.scau.edu.cn/kcsz/list.htm | 仅见链接 |
| 慕课学习 | https://nxy.scau.edu.cn/mkxx/list.htm | 仅见链接 |
| 教学研究 | https://nxy.scau.edu.cn/jxyj/list.htm | 仅见链接 |
| 实践基地 | https://nxy.scau.edu.cn/sjjd/list.htm | 仅见链接 |
| 招生工作 | https://nxy.scau.edu.cn/zsgz_18654/list.htm | 仅见链接 |
| 研究生教育 | https://nxy.scau.edu.cn/yjsjy_18766/list.htm | 仅见链接 |
| 科学研究 | https://nxy.scau.edu.cn/kxyj_17948/list.htm | 仅见链接 |
| 科研平台 | https://nxy.scau.edu.cn/kypt_17966/list.htm | 仅见链接 |
| 科研成果 | https://nxy.scau.edu.cn/kycg_17968/list.htm | 仅见链接 |
| 社会服务 | https://nxy.scau.edu.cn/shfw/list.htm | 仅见链接 |
| 服务动态 | https://nxy.scau.edu.cn/fwdt/list.htm | 仅见链接 |
| 服务团队 | https://nxy.scau.edu.cn/fwtd/list.htm | 仅见链接 |
| 成果转化 | https://nxy.scau.edu.cn/cgzh/list.htm | 仅见链接 |
| 校地企合作 | https://nxy.scau.edu.cn/xdqhz/list.htm | 仅见链接 |
| 对口支持 | https://nxy.scau.edu.cn/dkzc/list.htm | 仅见链接 |
| 服务需求 | https://nxy.scau.edu.cn/fwxq/list.htm | 仅见链接 |
| 学生工作 | https://nxy.scau.edu.cn/xsgz_17951/list.htm | 仅见链接 |
| 学生工作-通知公告 | https://nxy.scau.edu.cn/tzgg_17977/list.htm | 仅见链接（与学生工作栏目区分） |
| 学生活动 | https://nxy.scau.edu.cn/xshd/list.htm | 仅见链接 |
| 共青团工作 | https://nxy.scau.edu.cn/gqtgz/list.htm | 仅见链接 |
| 学生会工作 | https://nxy.scau.edu.cn/xshgz/list.htm | 仅见链接 |
| 奖助贷工作 | https://nxy.scau.edu.cn/jzdgz/list.htm | 仅见链接 |
| 本科生综合测评及评优实施 | https://nxy.scau.edu.cn/bkszhcpjzyssj/list.htm | 仅见链接（导航中标题被截断） |
| 大事记 | https://nxy.scau.edu.cn/dsj/list.htm | 仅见链接 |
| 服务指南 | https://nxy.scau.edu.cn/fwzn_17953/list.htm | 仅见链接 |
| 办事指引 | https://nxy.scau.edu.cn/bszy_17983/list.htm | 仅见链接 |
| 规章制度 | https://nxy.scau.edu.cn/gzzd_17984/list.htm | 仅见链接 |
| 资料下载 | https://nxy.scau.edu.cn/zlxz_17985/list.htm | 仅见链接 |
| 学科成果信息填报表 | https://nxy.scau.edu.cn/xkcgxxtb/list.htm | 仅见链接（导航中标题被截断） |
| 校友之窗 | https://nxy.scau.edu.cn/xyzc/list.htm | 仅见链接 |
| 校友服务 | https://nxy.scau.edu.cn/xyfw/list.htm | 仅见链接 |
| 校友风采 | https://gaokaobang.360eol.com/rector/2024/scau/department_custom.html?id=19906&custom=%E6%A0%A1%E5%8F%8B%E9%A3%8E%E9%87%87&v=1 | 第三方站点（360eol），仅见链接 |
| 招生宣传（门户） | https://gaokaobang.360eol.com/rector/2024/scau/index.html?v=102 | 第三方站点，仅见链接 |

### 子站点/下属机构
- 英文版：https://nxy.scau.edu.cn/nxyenglish/（已抓取 200）
  - 列表页：/nxyenglish/News1/list.htm（NEWS）、/nxyenglish/Situationw/list.htm（About us）、/nxyenglish/Exploreus/list.htm、/nxyenglish/Overview/list.htm、/nxyenglish/Faculty/list.htm、/nxyenglish/5938/list.htm、/nxyenglish/5939/list.htm（Undergraduate Education）、/nxyenglish/5940/list.htm（Graduate Education）、/nxyenglish/5941/list.htm（Scientific Research）、/nxyenglish/5942/list.htm（International Cooperation）、/nxyenglish/Video/list.htm
  - 教师详情页托管在旧 webplus：https://webplus.scau.edu.cn/_s18/2023/0911/c419a355084/page.psp
- 国家植物航天育种工程技术研究中心：https://htyzzx.scau.edu.cn/
- 植物新品种测试（广州）分中心：https://gzdus.scau.edu.cn/
- 节水抗旱稻绿色产业研究院：https://wdr.scau.edu.cn/
- 生物信息平台：首页为 `javascript:void(0)`（未配置链接）
- 管理后台入口（页脚）：http://webplus.scau.edu.cn/login.jsp?inner=1

---

## 植物保护学院
- 官网首页: https://zb.scau.edu.cn/  (状态: 200)；https://zb.scau.edu.cn/main.htm 亦为 200（同一首页）
- 旧版入口: 未发现（全站未见「旧版/返回旧版」链接）
- 路由风格: 新版栏目（`/xxx/list.htm` + 数字栏目 `/NNNN/list.htm`）；文章页 `/2026/0908/c11919a443482/page.htm`

### 信息发布/列表页面
| 栏目名称 | 列表页URL | 说明 |
|---|---|---|
| 学院新闻 | https://zb.scau.edu.cn/xydt/list.htm | 已抓取 200；186 条 / 14 页 |
| 学院通知 | https://zb.scau.edu.cn/jgtz/list.htm | 已抓取 200；326 条 / 24 页 |
| 讲座预告 | https://zb.scau.edu.cn/jzyg_12113/list.htm | 已抓取 200；120 条 / 9 页 |
| 学术进展 | https://zb.scau.edu.cn/xsjz/list.htm | 已抓取 200；82 条 / 6 页 |
| 信息公开 | https://zb.scau.edu.cn/xxgk/list.htm | 已抓取 200；577 条 / 42 页 |
| 媒体植保 | https://zb.scau.edu.cn/mtzb/list.htm | 已抓取 200；232 条 / 17 页 |
| 党政工会 | https://zb.scau.edu.cn/dzgh/list.htm | 已抓取 200；14 条 / 1 页 |
| 本科生通知 | https://zb.scau.edu.cn/bks/list.htm | 已抓取 200；310 条 / 23 页 |
| 研究生通知 | https://zb.scau.edu.cn/yjs/list.htm | 已抓取 200；189 条 / 14 页 |
| 党建动态 | https://zb.scau.edu.cn/djxw/list.htm | 已抓取 200，但列表为空（0 条）；党建内容实际多在「党政工会」/dzgh/list.htm |
| 学院概况 | https://zb.scau.edu.cn/xygk/list.htm | 仅见链接 |
| 学院简介 | https://zb.scau.edu.cn/xyjj/list.htm | 仅见链接 |
| 现任领导 | https://zb.scau.edu.cn/xrld/list.htm | 仅见链接 |
| 机构设置 | https://zb.scau.edu.cn/jgsz/list.htm | 仅见链接 |
| 党群组织 | https://zb.scau.edu.cn/dqzz/list.htm | 仅见链接 |
| 学院标识 | https://zb.scau.edu.cn/xybs/list.htm | 仅见链接 |
| 师资队伍 | https://zb.scau.edu.cn/szdw/list.htm | 仅见链接 |
| 人才招聘 | https://zb.scau.edu.cn/rczp/list.htm | 仅见链接（首页轮播图指向） |
| 师资概况 | https://zb.scau.edu.cn/szgk/list.htm | 仅见链接 |
| 专业教师（总） | https://zb.scau.edu.cn/kcxx/list.htm | 仅见链接 |
| 昆虫学系 | https://zb.scau.edu.cn/kcxx/list.htm | 仅见链接 |
| 农药学系 | https://zb.scau.edu.cn/nyxx/list.htm | 仅见链接 |
| 植物病理学系 | https://zb.scau.edu.cn/zwblxx/list.htm | 仅见链接 |
| 群体微生物研究中心 | https://zb.scau.edu.cn/qtwswyjzx/list.htm | 仅见链接 |
| 实验中心 | https://zb.scau.edu.cn/syzx/list.htm | 仅见链接 |
| 科学研究 | https://zb.scau.edu.cn/kxyj/list.htm | 仅见链接 |
| 科研成果 | https://zb.scau.edu.cn/kycg/list.htm | 仅见链接 |
| 科研团队 | https://zb.scau.edu.cn/kytd/list.htm | 仅见链接 |
| 科研团队（图墙栏目） | https://zb.scau.edu.cn/kytd_12048/list.htm | 仅见链接（首页「科研团队-更多」） |
| 学术交流 | https://zb.scau.edu.cn/xsjl/list.htm | 仅见链接 |
| 实验室建设 | https://zb.scau.edu.cn/sysjs/list.htm | 仅见链接 |
| 本科生培养 | https://zb.scau.edu.cn/bkspy/list.htm | 仅见链接 |
| 专业设置 | https://zb.scau.edu.cn/zysz/list.htm | 仅见链接 |
| 培养方案（本科） | https://zb.scau.edu.cn/pyfa_11956/list.htm | 仅见链接 |
| 教学大纲 | https://zb.scau.edu.cn/jxdg/list.htm | 仅见链接 |
| 文件规定 | https://zb.scau.edu.cn/wjgd/list.htm | 仅见链接 |
| 科普基地 | https://zb.scau.edu.cn/kpjd/list.htm | 仅见链接 |
| 研究生培养 | https://zb.scau.edu.cn/yjspy/list.htm | 仅见链接 |
| 培养方案（研究生） | https://zb.scau.edu.cn/pyfa/list.htm | 仅见链接 |
| 学位工作 | https://zb.scau.edu.cn/xwgz/list.htm | 仅见链接 |
| 办事流程（研究生） | https://zb.scau.edu.cn/bslc/list.htm | 仅见链接 |
| 博士后培养 | https://zb.scau.edu.cn/bshpy/list.htm | 仅见链接 |
| 流动站简介 | https://zb.scau.edu.cn/ldzjj/list.htm | 仅见链接 |
| 合作导师 | https://zb.scau.edu.cn/hzds/list.htm | 仅见链接 |
| 博士后招聘 | https://zb.scau.edu.cn/bshzp/list.htm | 仅见链接 |
| 博士后管理 | https://zb.scau.edu.cn/bshgl/list.htm | 仅见链接 |
| 招生就业 | https://zb.scau.edu.cn/zsjy/list.htm | 仅见链接 |
| 招生专栏 | https://zb.scau.edu.cn/yjszs/list.htm | 仅见链接 |
| 学生工作 | https://zb.scau.edu.cn/xsgz/list.htm | 仅见链接 |
| 学工队伍 | https://zb.scau.edu.cn/xgdw/list.htm | 仅见链接 |
| 学生动态 | https://zb.scau.edu.cn/xsdt/list.htm | 仅见链接 |
| 学生组织 | https://zb.scau.edu.cn/txzz/list.htm | 仅见链接 |
| 团委 | https://zb.scau.edu.cn/tw/list.htm | 仅见链接 |
| 学生会 | https://zb.scau.edu.cn/xsh/list.htm | 仅见链接 |
| 党务管理委员会 | https://zb.scau.edu.cn/dwglwyh/list.htm | 仅见链接 |
| 媒体中心 | https://zb.scau.edu.cn/mtzx/list.htm | 仅见链接 |
| 本科生工作 | https://zb.scau.edu.cn/bksgz/list.htm | 仅见链接 |
| 研究生工作 | https://zb.scau.edu.cn/yjsgz/list.htm | 仅见链接 |
| 资助工作 | https://zb.scau.edu.cn/zzgz/list.htm | 仅见链接 |
| 办事流程（学生工作） | https://zb.scau.edu.cn/bslc_12310/list.htm | 仅见链接 |
| 党建专栏 | https://zb.scau.edu.cn/djzx/list.htm | 仅见链接 |
| 组织架构 | https://zb.scau.edu.cn/zzjg/list.htm | 仅见链接 |
| 支部风采 | https://zb.scau.edu.cn/zbfc/list.htm | 仅见链接 |
| 党务指南 | https://zb.scau.edu.cn/dwzn/list.htm | 仅见链接 |
| 公示情况 | https://zb.scau.edu.cn/gsqk/list.htm | 仅见链接 |
| 学习平台 | https://zb.scau.edu.cn/xzyd/list.htm | 仅见链接 |
| 办事流程（党务） | https://zb.scau.edu.cn/wdxz_12229/list.htm | 仅见链接 |
| 社会服务 | https://zb.scau.edu.cn/shfw/list.htm | 仅见链接 |
| 培训 | https://zb.scau.edu.cn/px/list.htm | 仅见链接 |
| 乡村振兴 | https://zb.scau.edu.cn/xczx/list.htm | 仅见链接 |

### 子站点/下属机构
- 招生就业网：http://zb.scau.edu.cn/zbzs（仅见链接，未抓取）
- 实验教学示范中心：https://zb.scau.edu.cn/syjxzx/（仅见链接，未抓取）
- 校园风光图库栏目参数（模板变量异常，非有效URL）：`/_upload/tpl/04/6b/1131/template1131/V_URL[L:S260:C15028]`
- 管理后台入口（页脚）：http://webplus.scau.edu.cn/login.jsp?inner=1
- 注：页脚「学院网站链接」中「植物保护学院」指向 http://zb.scauzhujiang.cn/ （珠江学院镜像，非本站）

---

## 林学与风景园林学院
- 官网首页: https://lf.scau.edu.cn/  (状态: 200)
- 旧版入口: 未发现「旧版/返回旧版」链接；但存在旧版 webplus 师资名录路径 http://webplus.scau.edu.cn/_s24/_t636/lxxk/list.psp （师资队伍-师资名录指向）；页脚 logo 链向旧模板首页 /_upload/tpl/02/7c/636/template636/index.htm
- 路由风格: 两者都有 — 数字栏目 `/885/`、`/887/`、`/888/` 与命名栏目 `/xxx/list.htm` 并存

### 信息发布/列表页面
| 栏目名称 | 列表页URL | 说明 |
|---|---|---|
| 学院新闻 | https://lf.scau.edu.cn/885/list.htm | 已抓取 200；518 条 / 37 页 |
| 教工通知 | https://lf.scau.edu.cn/887/list.htm | 已抓取 200；317 条 / 23 页 |
| 学生通知 | https://lf.scau.edu.cn/888/list.htm | 已抓取 200；851 条 / 61 页 |
| 学术报告 | https://lf.scau.edu.cn/xsbg/list.htm | 已抓取 200；62 条 / 5 页 |
| 党建动态 | https://lf.scau.edu.cn/djdt/list.htm | 已抓取 200；203 条 / 15 页 |
| 学生培养 | https://lf.scau.edu.cn/xspy/list.htm | 已抓取 200；93 条 / 7 页 |
| 师资队伍（师资名录） | https://lf.scau.edu.cn/lxxk/list.htm | 已抓取 200 |
| 师资-正高职称 | https://lf.scau.edu.cn/zg/list.htm | 仅见链接（/lxxk/ 页内） |
| 师资-副高职称 | https://lf.scau.edu.cn/fg/list.htm | 仅见链接 |
| 师资-中级、初级职称 | https://lf.scau.edu.cn/zjwqt/list.htm | 仅见链接 |
| 师资名录（旧版 .psp） | http://webplus.scau.edu.cn/_s24/_t636/lxxk/list.psp | 仅见链接 |
| 林学学科 | https://lf.scau.edu.cn/lxxk/list.htm | 仅见链接 |
| 风景园林学科 | https://lf.scau.edu.cn/fjylxk/list.htm | 仅见链接 |
| 草学学科 | https://lf.scau.edu.cn/cykxxk/list.htm | 仅见链接 |
| 实验中心（师资） | https://lf.scau.edu.cn/jxsyzx_9315/list.htm | 仅见链接 |
| 博士后之家 | https://lf.scau.edu.cn/ldzjs/list.htm | 仅见链接 |
| 博士后-流动站介绍 | https://lf.scau.edu.cn/ldzjs/list.htm | 仅见链接 |
| 博士后-合作导师简介 | https://lf.scau.edu.cn/hzdsjj/list.htm | 仅见链接 |
| 博士后-通知公告 | https://lf.scau.edu.cn/tzgg_10882/list.htm | 仅见链接 |
| 人事服务 | https://lf.scau.edu.cn/rsfw/list.htm | 仅见链接 |
| 学院概况 | https://lf.scau.edu.cn/xygkw/list.htm | 仅见链接 |
| 学院简介 | https://lf.scau.edu.cn/xyjj_9776/list.htm | 仅见链接 |
| 院徽院训 | https://lf.scau.edu.cn/yhyx_9777/list.htm | 仅见链接 |
| 治理架构 | https://lf.scau.edu.cn/zljg/list.htm | 仅见链接 |
| 党委委员 | https://lf.scau.edu.cn/dwwy/list.htm | 仅见链接 |
| 领导班子 | https://lf.scau.edu.cn/ldbz/list.htm | 仅见链接 |
| 学术委员会 | https://lf.scau.edu.cn/xswyh/list.htm | 仅见链接 |
| 学位委员会 | https://lf.scau.edu.cn/xwwyh/list.htm | 仅见链接 |
| 隶属机构及其负责人 | https://lf.scau.edu.cn/yltxgzxz/list.htm | 仅见链接 |
| 院务公开 | https://lf.scau.edu.cn/ywgk/list.htm | 仅见链接 |
| 基本信息 | https://lf.scau.edu.cn/jbxx/list.htm | 仅见链接 |
| 招生考试信息 | https://lf.scau.edu.cn/zsksxx/list.htm | 仅见链接 |
| 财务、资产及收费信息 | https://lf.scau.edu.cn/cwwzcjsfxx/list.htm | 仅见链接 |
| 人事师资信息 | https://lf.scau.edu.cn/rsszxx/list.htm | 仅见链接 |
| 教学质量信息 | https://lf.scau.edu.cn/jxzlxx/list.htm | 仅见链接 |
| 学生管理服务信息 | https://lf.scau.edu.cn/xsglfwxx/list.htm | 仅见链接 |
| 学风建设信息 | https://lf.scau.edu.cn/xfjsxx/list.htm | 仅见链接 |
| 学位、学科信息 | https://lf.scau.edu.cn/xwwxkxx/list.htm | 仅见链接 |
| 对外交流与合作信息 | https://lf.scau.edu.cn/dwjlyhzxx/list.htm | 仅见链接 |
| 综合安全治理 | https://lf.scau.edu.cn/zhaqzl/list.htm | 仅见链接 |
| 党建思政 | https://lf.scau.edu.cn/djsz/list.htm | 仅见链接 |
| 院务公开-其他 | https://lf.scau.edu.cn/qt/list.htm | 仅见链接 |
| 联系我们 | https://lf.scau.edu.cn/lxwm/list.htm | 仅见链接 |
| 人才培养 | https://lf.scau.edu.cn/rcpyw/list.htm | 仅见链接 |
| 本科教育教学审核评估 | https://lf.scau.edu.cn/bkjyjxshpg/list.htm | 仅见链接 |
| 专业建设 | https://lf.scau.edu.cn/zyjs_9785/list.htm | 仅见链接 |
| 课程建设 | https://lf.scau.edu.cn/kcjs/list.htm | 仅见链接 |
| 本科生教育 | https://lf.scau.edu.cn/bksjy/list.htm | 仅见链接 |
| 研究生教育 | https://lf.scau.edu.cn/yjsjy/list.htm | 仅见链接 |
| 学位点质量年报 | https://lf.scau.edu.cn/xwdzlnb/list.htm | 仅见链接 |
| 学位点年报-风景园林 | https://lf.scau.edu.cn/fjyl/list.htm | 仅见链接 |
| 学位点年报-林学 | https://lf.scau.edu.cn/lx/list.htm | 仅见链接 |
| 学位点年报-林业 | https://lf.scau.edu.cn/ly/list.htm | 仅见链接 |
| 学位点年报-草学 | https://lf.scau.edu.cn/cx/list.htm | 仅见链接 |
| 教学实习 | https://lf.scau.edu.cn/jxsx/list.htm | 仅见链接 |
| 科学研究 | https://lf.scau.edu.cn/kxyjw/list.htm | 仅见链接 |
| 学科介绍 | https://lf.scau.edu.cn/kytd/list.htm | 仅见链接 |
| 科研平台 | https://lf.scau.edu.cn/ptjd/list.htm | 仅见链接 |
| 重点实验室 | https://lf.scau.edu.cn/kypt/list.htm | 仅见链接 |
| 教学实验中心 | https://lf.scau.edu.cn/kyjd/list.htm | 仅见链接 |
| 科研动态 | https://lf.scau.edu.cn/kydt/list.htm | 仅见链接 |
| 科研成果 | https://lf.scau.edu.cn/kycg/list.htm | 仅见链接 |
| 实验室管理 | https://lf.scau.edu.cn/sysgl/list.htm | 仅见链接 |
| 党群工作 | https://lf.scau.edu.cn/dqgz/list.htm | 仅见链接 |
| 教工之家 | https://lf.scau.edu.cn/jgzj/list.htm | 仅见链接 |
| 离退休工作 | https://lf.scau.edu.cn/ltxgz/list.htm | 仅见链接 |
| 学生工作 | https://lf.scau.edu.cn/xsgzw/list.htm | 仅见链接 |
| 辅导员信息 | https://lf.scau.edu.cn/fdyxx/list.htm | 仅见链接 |
| 班主任信息 | https://lf.scau.edu.cn/bzrxx/list.htm | 仅见链接 |
| 学生组织 | https://lf.scau.edu.cn/xszz_9800/list.htm | 仅见链接 |
| 学生动态 | https://lf.scau.edu.cn/xsdt/list.htm | 仅见链接 |
| 招生就业 | https://lf.scau.edu.cn/zsjyw/list.htm | 仅见链接 |
| 本科生招生信息 | https://lf.scau.edu.cn/bkszsxx/list.htm | 仅见链接 |
| 招生-学院介绍 | https://lf.scau.edu.cn/xyjs/list.htm | 仅见链接 |
| 招生-专业介绍 | https://lf.scau.edu.cn/zyjs_10878/list.htm | 仅见链接 |
| 招生-学子风采 | https://lf.scau.edu.cn/xzfc_11101/list.htm | 仅见链接 |
| 招生-招生计划 | https://lf.scau.edu.cn/zsjh_11102/list.htm | 仅见链接 |
| 研究生招生信息 | https://lf.scau.edu.cn/yjszsxx/list.htm | 仅见链接 |
| 招生简章 | https://lf.scau.edu.cn/zsjz/list.htm | 仅见链接 |
| 招生目录 | https://lf.scau.edu.cn/zsml/list.htm | 仅见链接 |
| 招生宣讲 | https://lf.scau.edu.cn/zsxj/list.htm | 仅见链接 |
| 对外交流 | https://lf.scau.edu.cn/dwjlw/list.htm | 仅见链接 |
| 国际交流 | https://lf.scau.edu.cn/gjjl/list.htm | 仅见链接 |
| 社会服务 | https://lf.scau.edu.cn/shfw/list.htm | 仅见链接 |
| 校友之家 | https://lf.scau.edu.cn/xyzjw/list.htm | 仅见链接 |
| 校友活动 | https://lf.scau.edu.cn/xyh/list.htm | 仅见链接 |
| 预约返校 | https://lf.scau.edu.cn/yyfx/list.htm | 仅见链接 |
| 饮水思源 | https://lf.scau.edu.cn/yssy/list.htm | 仅见链接 |
| 学院教育发展基金 | https://lf.scau.edu.cn/yjyfzjj/list.htm | 仅见链接 |
| 善境基金 | https://lf.scau.edu.cn/sjjj/list.htm | 仅见链接 |
| 捐赠项目 | https://lf.scau.edu.cn/jzxm/list.htm | 仅见链接 |
| 捐赠鸣谢 | https://lf.scau.edu.cn/jzmx/list.htm | 仅见链接 |
| 校友服务 | https://lf.scau.edu.cn/xyfw/list.htm | 仅见链接 |
| 办事指南 | https://lf.scau.edu.cn/bszn/list.htm | 仅见链接 |
| 常用模板 | https://lf.scau.edu.cn/bszn_14642/list.htm | 仅见链接 |
| 办事流程 | https://lf.scau.edu.cn/bslc/list.htm | 仅见链接 |

### 子站点/下属机构
- 党建工作网：https://lf.scau.edu.cn/dangjiangongzuo/（已抓取 200）
  - 列表页：`/dangjiangongzuo/8604/list.htm`（党委概况）、`/8605/list.htm`（机构设置）、`/dangjiangongzuo/djxw/list.htm`（党建新闻）、`/dangjiangongzuo/zbfc/list.htm`（支部风采）、`/8607/list.htm`（党校培训）、`/8608/list.htm`（工作通知）、`/8609/list.htm`（公示专栏）、`/8610/list.htm`（党务指南）、`/8611/list.htm`（下载中心）
  - 旧版 .psp：http://webplus.scau.edu.cn/dangjiangongzuo/djxw/list.psp
- 英文版：https://lf.scau.edu.cn/lfen/ — 抓取失败：https→http://lf.scau.edu.cn 跨协议重定向，未能取得内容（反向 http→https 同样循环）
- 卢永根专题网站：https://lyg.scau.edu.cn/（仅见链接）
- 就业信息网（就业一点通）：http://202.116.160.44:8004/linxuejob/（仅见链接，独立 IP:端口）
- 管理后台入口（页脚）：http://webplus.scau.edu.cn/login.jsp?inner=1

---

## 园艺学院
- 官网首页: https://yy.scau.edu.cn/  (状态: 200)
- 旧版入口: 未发现
- 路由风格: 两者都有 — 数字栏目 `/2447/`、`/2448/`、`/2449/`、`/2165/`、`/2167/`、`/2430/`、`/2433/`、`/2438/`、`/2439/`、`/2440/`、`/2185/`、`/2429/`、`/2189/` 与命名栏目同时使用；文章页 `/2026/0929/c2447a447595/page.htm`

### 信息发布/列表页面
| 栏目名称 | 列表页URL | 说明 |
|---|---|---|
| 新闻中心（学院新闻） | https://yy.scau.edu.cn/2447/list.htm | 已抓取 200；309 条 / 23 页 |
| 通知公告 | https://yy.scau.edu.cn/2448/list.htm | 已抓取 200；1083 条 / 78 页 |
| 学术报告（学术活动） | https://yy.scau.edu.cn/2449/list.htm | 已抓取 200；108 条 / 8 页 |
| 新闻公告（父栏目） | https://yy.scau.edu.cn/xwgg/list.htm | 仅见链接（面包屑） |
| 业内新闻 | https://yy.scau.edu.cn/ynxw/list.htm | 仅见链接（首页） |
| 媒体园艺 | https://yy.scau.edu.cn/mtyy/list.htm | 仅见链接（首页） |
| 学院概况 | https://yy.scau.edu.cn/xygk_/list.htm | 仅见链接 |
| 学院简介 | https://yy.scau.edu.cn/xyjj/list.htm | 仅见链接 |
| 现任领导 | https://yy.scau.edu.cn/ldjs/list.htm | 仅见链接 |
| 机构设置 | https://yy.scau.edu.cn/xsfwyh/list.htm | 仅见链接 |
| 大事记 | https://yy.scau.edu.cn/dsj/list.htm | 仅见链接 |
| 联系我们 | https://yy.scau.edu.cn/lxwm/list.htm | 仅见链接 |
| 师资队伍 | https://yy.scau.edu.cn/szdw_/list.htm | 仅见链接 |
| 师资概况 | https://yy.scau.edu.cn/szgk/list.htm | 仅见链接 |
| 教师名录 | https://yy.scau.edu.cn/gsxx01/list.htm | 仅见链接 |
| 客座教授 | https://yy.scau.edu.cn/kzjs/list.htm | 仅见链接 |
| 校外导师 | https://yy.scau.edu.cn/xwds/list.htm | 仅见链接 |
| 博士后之家 | https://yy.scau.edu.cn/bszp/list.htm | 仅见链接 |
| 人才培养 | https://yy.scau.edu.cn/2165/list.htm | 仅见链接 |
| 一流专业 | https://yy.scau.edu.cn/ylzy/list.htm | 仅见链接 |
| 本科生 | https://yy.scau.edu.cn/2185/list.htm | 仅见链接 |
| 研究生 | https://yy.scau.edu.cn/2429/list.htm | 仅见链接 |
| 国际教育 | https://yy.scau.edu.cn/gjjy/list.htm | 仅见链接 |
| 教学成果 | https://yy.scau.edu.cn/jxcg/list.htm | 仅见链接 |
| 基地建设 | https://yy.scau.edu.cn/2189/list.htm | 仅见链接 |
| 科学研究 | https://yy.scau.edu.cn/2167/list.htm | 仅见链接 |
| 学科建设 | https://yy.scau.edu.cn/gjzdxk/list.htm | 仅见链接 |
| 科研平台 | https://yy.scau.edu.cn/kypt/list.htm | 仅见链接 |
| 科研成果 | https://yy.scau.edu.cn/kyxm/list.htm | 仅见链接 |
| 党群工作 | https://yy.scau.edu.cn/2430/list.htm | 仅见链接 |
| 党建工作 | https://yy.scau.edu.cn/2430/list.htm | 仅见链接（栏目 id 12145 为其文章前缀） |
| 工会工作 | https://yy.scau.edu.cn/2433/list.htm | 仅见链接 |
| 党团活动 | https://yy.scau.edu.cn/dthd/list.htm | 仅见链接 |
| 理论学习 | https://yy.scau.edu.cn/llxx/list.htm | 仅见链接 |
| 学生工作 | https://yy.scau.edu.cn/2438/list.htm | 仅见链接 |
| 学生组织 | https://yy.scau.edu.cn/2438/list.htm | 仅见链接 |
| 学生动态 | https://yy.scau.edu.cn/2439/list.htm | 仅见链接 |
| 创新创业 | https://yy.scau.edu.cn/2440/list.htm | 仅见链接 |
| 学生风采 | https://yy.scau.edu.cn/xsfc/list.htm | 仅见链接 |
| 院务公开 | https://yy.scau.edu.cn/xygz_9184/list.htm | 仅见链接 |
| 学院规章 | https://yy.scau.edu.cn/xygz_9184/list.htm | 仅见链接 |
| 党政联席会 | https://yy.scau.edu.cn/dzlxh/list.htm | 仅见链接 |
| 院内公告 | https://yy.scau.edu.cn/yngs/list.htm | 仅见链接（首页亦有「更多」） |
| 校友工作 | https://yy.scau.edu.cn/xygz/list.htm | 仅见链接 |
| 校友工作机构 | https://yy.scau.edu.cn/xylsh/list.htm | 仅见链接 |
| 校友名录 | https://yy.scau.edu.cn/xyml/list.htm | 仅见链接 |
| 校友风采 | https://yy.scau.edu.cn/xyfc/list.htm | 仅见链接 |
| 园艺文化 | https://yy.scau.edu.cn/yywh/list.htm | 仅见链接 |
| 历史沿革 | https://yy.scau.edu.cn/lsyg_9166/list.htm | 仅见链接 |
| 历届领导 | https://yy.scau.edu.cn/ljld_9168/list.htm | 仅见链接 |
| 园艺人物 | https://yy.scau.edu.cn/lsrw/list.htm | 仅见链接 |
| 教学科研（动态） | https://yy.scau.edu.cn/jxky/list.htm | 仅见链接（首页「教学科研-更多」，文章前缀 c9052） |
| 招生就业 | https://yy.scau.edu.cn/zscy/list.htm | 仅见链接（文章前缀 c9050） |
| 视听园艺 | https://yy.scau.edu.cn/xjlmcs/list.htm | 仅见链接（文章前缀 c14341） |

### 子站点/下属机构
- 实验教学中心（园艺学实验教学中心）：https://yy.scau.edu.cn/syjxsfzx/（已抓取 200）
  - 列表页：`/syjxsfzx/zxjs/list.htm`（中心介绍）、`/syjxsfzx/zxdt/list.htm`（中心动态，文章前缀 c11020）、`/syjxsfzx/jsdw/list.htm`、`/syjxsfzx/jxcg/list.htm`、`/syjxsfzx/syjx/list.htm`（实验教学，前缀 c11022）、`/syjxsfzx/sysxxgjc/list.htm`、`/syjxsfzx/cddsyjxxm/list.htm`、`/syjxsfzx/yqsb/list.htm`（仪器设备，前缀 c11011）、`/syjxsfzx/sbyy/list.htm`、`/syjxsfzx/wxgzhyy/list.htm`、`/syjxsfzx/gzzd/list.htm`（规章制度，前缀 c11013）、`/syjxsfzx/dxyqggptglzd/list.htm`、`/syjxsfzx/tsycg/list.htm`、`/syjxsfzx/cdkyxm/list.htm`、`/syjxsfzx/sdpz/list.htm`、`/syjxsfzx/hjqk/list.htm`、`/syjxsfzx/sqzl/list.htm`、`/syjxsfzx/fbkylwwzww/list.htm`、`/syjxsfzx/fbkylwwyww/list.htm`、`/syjxsfzx/sysaq/list.htm`（安全生产）
  - 外部预约系统：http://222.201.228.129/login.html（实验室预约）、http://iot.enzyun.com/scau-eqmgrb/login（大型仪器设备预约）
- 园艺学院招生网：https://yy.scau.edu.cn/zs/（仅见链接）
- http://yy.scau.edu.cn/yysys（仅见链接，疑为实验室/所站点）
- 英文版：http://yy.scau.edu.cn/yyen — 抓取失败：https↔http 跨协议重定向循环，未能取得内容
- 校内关联站点：卢永根专题 https://lyg.scau.edu.cn/ ；http://nz.scau.edu.cn/ （仅见链接）
- 管理后台入口（页脚）：http://webplus.scau.edu.cn/login.jsp?inner=1

---

## 兽医学院
- 官网首页: http://vet.scau.edu.cn/ → 301 至 https://vet.scau.edu.cn/  (状态: 200)；https://vet.scau.edu.cn/main.htm 亦为 200
- 旧版入口: 未发现
- 路由风格: 两者都有 — 数字栏目 `/814/`、`/860/`、`/863/`、`/802/`、`/803/`、`/822/`、`/827/`、`/828/`、`/804/`、`/846/`、`/847/`、`/849/`、`/845/`、`/807/`、`/862/`、`/829/`、`/848/`、`/844/`、`/855/`、`/856/`、`/809/`、`/857/`、`/858/`、`/859/`、`/939/` 与命名栏目 `/xxx/list.htm` 并用；文章页 `/2026/1010/c860a448361/page.htm`

### 信息发布/列表页面
| 栏目名称 | 列表页URL | 说明 |
|---|---|---|
| 新闻动态 | https://vet.scau.edu.cn/860/list.htm | 已抓取 200；455 条 / 33 页 |
| 学院动态（父栏目） | https://vet.scau.edu.cn/814/list.htm | 仅见链接（面包屑） |
| 社会服务与企业合作 | https://vet.scau.edu.cn/863/list.htm | 已抓取 200；26 条 / 1 页（每页 30 条） |
| 通知公告 | https://vet.scau.edu.cn/tzgg/list.htm | 抓取失败：https→http://vet.scau.edu.cn 跨协议重定向循环；http 版反向循环。文章ID前缀 c18287（栏目 id 18287）。https://vet.scau.edu.cn/18287/list.htm 与 https://vet.scau.edu.cn/tzgg/ 同样失败 |
| 学术活动公告 | https://vet.scau.edu.cn/939/list.htm | 仅见链接（首页「学术活动公告-更多」，文章前缀 c939） |
| 联系我们 | http://vet.scau.edu.cn/2020/0516/c803a229476/page.htm | 仅见链接（单篇文章） |
| 学院概况 | https://vet.scau.edu.cn/802/list.htm | 仅见链接 |
| 学院介绍 | https://vet.scau.edu.cn/xygk/list.htm | 仅见链接 |
| 机构设置 | https://vet.scau.edu.cn/803/list.htm | 仅见链接 |
| 领导班子 | https://vet.scau.edu.cn/822/list.htm | 仅见链接 |
| 历史沿革 | https://vet.scau.edu.cn/827/list.htm | 仅见链接 |
| 党建引领 | https://vet.scau.edu.cn/djyl/list.htm | 仅见链接 |
| 形象标识 | https://vet.scau.edu.cn/828/list.htm | 仅见链接 |
| 师资队伍 | https://vet.scau.edu.cn/804/list.htm | 仅见链接 |
| 博士生上岗导师 | https://vet.scau.edu.cn/846/list.htm | 仅见链接（导航标题被截断） |
| 硕士生上岗导师 | https://vet.scau.edu.cn/847/list.htm | 仅见链接（导航标题被截断） |
| 兽医药理学与毒理学 | https://vet.scau.edu.cn/syylxydlx/list.htm | 仅见链接（导航标题被截断） |
| 动物解剖学、组织胚胎学与病理学 | https://vet.scau.edu.cn/dwjpxwzzptxyblx/list.htm | 仅见链接（导航标题被截断） |
| 兽医传染病学 | https://vet.scau.edu.cn/sycrbx/list.htm | 仅见链接 |
| 兽医微生物学 | https://vet.scau.edu.cn/sywswx/list.htm | 仅见链接 |
| 兽医寄生虫学 | https://vet.scau.edu.cn/syjscx/list.htm | 仅见链接 |
| 兽医内科学、诊断学与中兽医学 | https://vet.scau.edu.cn/synkxwzdxyzsyx/list.htm | 仅见链接（导航标题被截断） |
| 兽医外科学与临床科学 | https://vet.scau.edu.cn/sywkxyckx/list.htm | 仅见链接（导航标题被截断） |
| 兽医学实验教学中心 | https://vet.scau.edu.cn/syxsyjxzx/list.htm | 仅见链接（导航标题被截断） |
| 动物医院 | https://vet.scau.edu.cn/dwyy/list.htm | 仅见链接 |
| 农业部畜禽产品质量监督检验测试中心（广州） | https://vet.scau.edu.cn/nybcqcpzljdjczxwgzw/list.htm | 仅见链接（导航标题被截断） |
| 人才培养 | https://vet.scau.edu.cn/rcpy_9750/list.htm | 仅见链接 |
| 教学动态 | https://vet.scau.edu.cn/jxdt/list.htm | 仅见链接 |
| 本科生培养 | https://vet.scau.edu.cn/849/list.htm | 仅见链接 |
| 研究生培养 | https://vet.scau.edu.cn/845/list.htm | 仅见链接 |
| 博士后之家 | https://vet.scau.edu.cn/bshzj/list.htm | 仅见链接 |
| 精品课程 | https://vet.scau.edu.cn/jpkc/list.htm | 仅见链接 |
| 教学成果奖 | https://vet.scau.edu.cn/jxcgj/list.htm | 仅见链接 |
| 教学研究与改革 | https://vet.scau.edu.cn/jxyjygg/list.htm | 仅见链接（导航标题被截断） |
| 教学平台 | https://vet.scau.edu.cn/jxpt/list.htm | 仅见链接 |
| 科学研究 | https://vet.scau.edu.cn/807/list.htm | 仅见链接 |
| 学术交流 | https://vet.scau.edu.cn/xsjl/list.htm | 仅见链接 |
| 科研进展 | https://vet.scau.edu.cn/862/list.htm | 仅见链接 |
| 科研团队 | https://vet.scau.edu.cn/kytd/list.htm | 仅见链接 |
| 研究平台 | https://vet.scau.edu.cn/829/list.htm | 仅见链接 |
| 实验室建设 | https://vet.scau.edu.cn/sysjs/list.htm | 仅见链接 |
| 下载专区 | https://vet.scau.edu.cn/xzzq/list.htm | 仅见链接 |
| 招生就业 | https://vet.scau.edu.cn/zsjy/list.htm | 仅见链接 |
| 本科生招生简章 | https://vet.scau.edu.cn/848/list.htm | 仅见链接（导航标题被截断） |
| 研究生招生简章 | https://vet.scau.edu.cn/844/list.htm | 仅见链接（导航标题被截断） |
| 就业工作 | https://vet.scau.edu.cn/855/list.htm | 仅见链接 |
| 就业信息 | https://vet.scau.edu.cn/856/list.htm | 仅见链接 |
| 学生成果 | https://vet.scau.edu.cn/xscg/list.htm | 仅见链接 |
| 学生风采 | https://vet.scau.edu.cn/xsfc/list.htm | 仅见链接 |
| 学生工作 | https://vet.scau.edu.cn/809/list.htm | 仅见链接 |
| 学生动态 | https://vet.scau.edu.cn/857/list.htm | 仅见链接 |
| 资料下载（学生工作） | https://vet.scau.edu.cn/858/list.htm | 仅见链接 |
| 奖助学金 | https://vet.scau.edu.cn/859/list.htm | 仅见链接 |
| 校友之家 | https://vet.scau.edu.cn/xyzj/list.htm | 仅见链接 |
| 校友分会 | https://vet.scau.edu.cn/xyfh/list.htm | 仅见链接 |
| 校友动态 | https://vet.scau.edu.cn/xydt/list.htm | 仅见链接（文章前缀 c19601） |
| 信息公开 | https://vet.scau.edu.cn/ywgk/list.htm | 仅见链接 |
| 院务公开 | https://vet.scau.edu.cn/gzzd_12422/list.htm | 仅见链接 |
| 党务公开 | https://vet.scau.edu.cn/dzlxh/list.htm | 仅见链接 |

### 子站点/下属机构
- 党建专题网「华南农业大学兽医党建网」：https://vet.scau.edu.cn/sydj/（已抓取 200）
  - 列表页：`/sydj/jgsz/list.htm`（机构设置）、`/sydj/xydwgk/list.htm`（党委概况）、`/sydj/zbjj/list.htm`（支部风采）、`/sydj/djdt/list.htm`（党建动态）、`/sydj/djxw/list.htm`（党建新闻）、`/sydj/zbdt/list.htm`（支部动态）、`/sydj/szxx/list.htm`（单周学习）、`/sydj/xydx/list.htm`（学院党校，文章前缀 c12918）、`/sydj/dwgk/list.htm`（党务公开）、`/sydj/bgjs/list.htm`（党建“双创”，文章前缀 c7976）
- 英文版：https://vet.scau.edu.cn/veten/ — 抓取失败：https→http://vet.scau.edu.cn 跨协议重定向，未能取得内容
- 首页「链接」图标指向：学科大模型 https://5wmhafdxzfc4o.ok.kimi.link/ ；安全生产专题、实验教学中心、实验动物中心、《养禽与禽病防治》均使用 `/_redirect?siteId=25&columnId=7715&articleId=...` 形式的内部跳转（未解析出目标URL）
- 管理后台入口（页脚）：http://webplus.scau.edu.cn/login.jsp?inner=1

---

## 横向观察（仅记录事实）
- 5 个站点全部为 webplus CMS，页脚均含 `http://webplus.scau.edu.cn/login.jsp?inner=1` 管理登录入口。
- 文章详情页统一为 `/YYYY/MMDD/c<栏目标识>a<文章ID>/page.htm`。
- 分页统一为 `<列表页>/list2.htm`、`list3.htm` …，末页可由列表页「尾页」链接确定。
- 各站首页/内页大量使用 `http://` 绝对链接，导致 `web_fetch` 出现跨协议重定向；已按 https 版本重新抓取。
- 旧版 webplus 路径仅在两处实际出现：农学院（`http://webplus.scau.edu.cn/_s287/_t1693/xyxw/list.psp`）、林学院（`http://webplus.scau.edu.cn/_s24/_t636/lxxk/list.psp`、`http://webplus.scau.edu.cn/dangjiangongzuo/djxw/list.psp`）。
- 明确标注「旧版回顾」链接的只有农学院，且该链接当前重定向循环、不可用。
