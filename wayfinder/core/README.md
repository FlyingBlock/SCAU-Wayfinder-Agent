# wayfinder/core/ — 配置与基础设施

只做「配置模型与 .env 读写」，不写业务、不发网络请求。

## 文件

| 文件 | 作用 |
|---|---|
| `config.py` | 路径常量、`.env` 加载、`LLMSettings` / `SearchSettings` / `CrawlSettings` / `OCRSettings` / `AuthSettings` / `Settings`、`.env` 读写函数 |
| `urls.py` | URL 归一化纯函数（`normalize_url` / `is_loopback`），供采集、附件、问答共用 |

## 关键约定

- `ROOT` 是仓库根（`wayfinder/core/config.py` 往上两级），所有默认路径都相对它。
- 密钥优先级：真实环境变量 > 根目录 `.env` > 上级工作区 `.env`。
- 环境变量前缀为 `WAYFINDER_*`，同时兼容旧的 `HARNESS_*`（见 `env_compat()`）。
- `Settings` 是唯一配置源：OCR / 登录配置也在 `Settings.ocr` / `Settings.auth`，
  `documents.ocr` 与 `crawl.auth` 只保留指向同一对象的兼容别名。
- 本模块**不负责写盘校验**：设置面板的保存、验证与运行时生效在
  [`wayfinder/settings/`](../settings/README.md)（`commands.py` 用例 +
  `service.py` 底层）。

## 扩展

新增配置项时：

1. 在对应 dataclass 加字段；
2. 在 `from_env()` / `load()` 里用 `getenv()` 或 `env_compat()` 读取；
3. 在根 `.env.example` 写一行注释与默认值；
4. 不要在领域模块里散落 `os.environ[...]`。
