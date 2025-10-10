# 🎯 AI模型关键词提取系统

这是一个专业的AI模型关键词提取系统，能够从HuggingFace模型数据中智能提取高价值的SEO关键词，用于内容营销和搜索优化。

## ✨ 核心特性

- 📊 **CSV数据处理**: 高效读取和筛选HuggingFace模型数据
- 🤖 **多平台AI支持**: 支持月之暗面、阿里百炼、七牛云、腾讯混元四大AI平台
- 🚀 **分片并发处理**: 类似XXL-Job的分片广播模式，大幅提升处理效率
- 🎯 **多维度分析**: 品牌身份、功能应用、技术创新、社区生态、数据训练、模型标签
- 💾 **批量处理**: 支持大规模数据批量提取
- 📈 **成果输出**: JSON格式存储，便于后续分析
- 🔄 **智能容错**: 自动处理平台失败，确保系统稳定性

## 📁 项目结构

```
modelkeyword/
├── keyword_extractor.py           # 🚀 主程序入口
├── csv_reader.py                  # 📊 CSV数据读取器
├── ai_extractor.py               # 🤖 AI关键词提取模块
├── multi_platform_extractor.py   # 🚀 多平台分片并发提取器
├── hf_scraper.py                 # 🕷️ 网页爬虫模块
├── models.py                     # 🏗️ 数据模型定义
├── requirements.txt              # 📦 项目依赖
├── .env                         # 🔐 环境变量配置
├── .gitignore                   # 🚫 Git忽略规则
├── 需求.md                      # 📋 项目需求文档
├── README.md                    # 📖 项目说明
├── QUICKSTART.md               # ⚡ 快速开始指南
├── huggingface模型数据_202509241526.csv  # 📊 源数据文件
├── output/                      # 📁 输出目录
│   ├── keywords_batch_*.json    # 🎯 关键词提取结果
│   ├── models_*.json            # 📊 模型信息
│   ├── report_*.md              # 📋 分析报告
│   ├── report_*.csv             # 📈 CSV导出
│   └── report_*_keywords.txt    # 📝 关键词列表
└── venv/                        # 🐍 Python虚拟环境
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo>
cd modelkeyword

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# 多平台AI模型配置

# 月之暗面 (Moonshot) - 必需
MOONSHOT_API_KEY=your_moonshot_api_key_here
MOONSHOT_BASE_URL=https://api.moonshot.cn/v1

# 阿里百炼 (DashScope) - 推荐
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen3-max

# 七牛云 - 可选
QINIU_API_KEY=your_qiniu_api_key_here
QINIU_BASE_URL=https://openai.qiniu.com/v1
QINIU_MODEL=gpt-oss-120b

# 腾讯混元 - 可选
HUNYUAN_API_KEY=your_hunyuan_api_key_here
HUNYUAN_BASE_URL=https://api.hunyuan.cloud.tencent.com/v1
HUNYUAN_MODEL=hunyuan-turbos-latest
```

### 3. 运行系统

```bash
# 基础运行（处理前10个模型，自动检测平台）
python keyword_extractor.py

# 批量处理（指定数量，自动检测平台）
python keyword_extractor.py --max-models 50

# 大批量处理（自动启用多平台分片并发）
python keyword_extractor.py --max-models 80

# 小批量处理（自动选择最优策略）
python keyword_extractor.py --max-models 8

# 强制重新爬取模型信息
python keyword_extractor.py --max-models 10 --force-crawl

# 使用认证token
python keyword_extractor.py --max-models 10 --token "your_bearer_token"

# 查看帮助
python keyword_extractor.py --help
```

### 4. 智能平台检测

系统会自动检测可用的API平台数量：

- **1个平台**: 自动使用单平台模式
- **2+个平台**: 自动启用多平台分片并发模式

无需手动指定`--multi-platform`参数，系统会根据配置自动选择最优策略。

## 📊 数据说明

### 输入数据

- **源文件**: `huggingface模型数据_202509241526.csv`
- **筛选条件**: 审核状态=2 且 是否公开=1
- **符合条件**: 82个模型

### 输出结果

- **关键词文件**: `output/keywords_batch_*.json`
- **模型信息**: `output/models_*.json`
- **分析报告**: `output/report_*.md`
- **CSV导出**: `output/report_*.csv`
- **关键词列表**: `output/report_*_keywords.txt`

### 关键词维度

1. **品牌与身份**: 官方名称、开发机构、版本标识
2. **功能与应用**: 核心场景、任务类型、应用领域  
3. **技术与创新**: 算法特色、技术亮点、前沿概念
4. **社区与生态**: 开源特性、社区热度、合作伙伴
5. **数据与训练**: 数据类型、训练方式、参数规模
6. **模型标签**: 模型类型、部署方式、性能特色

## 📈 成果展示

### 处理统计

- ✅ **数据源**: 229个HuggingFace模型记录
- 🎯 **符合条件**: 82个模型（审核状态=2且公开=1）
- 🤖 **成功提取**: 8个模型关键词（分片并发测试）
- 📊 **成功率**: 100%
- 💡 **平均产出**: 每模型6-8个关键词
- 🚀 **处理效率**: 分片并发比原版并发快4倍

### 关键词示例

```json
{
  "keyword": "InternLM大模型",
  "dimension": "热门模型品牌",
  "reason": "知名开源大模型系列，用户在CSDN等平台高频搜索其最新版本，具有强品牌引流效应"
}
```

### 分片并发示例

```
📊 分片策略: 8 个模型，4 个平台
📋 可用平台: 月之暗面, 阿里百炼, 七牛云, 腾讯混元
📈 分片分配: 每个平台负责 2 个模型，剩余 0 个模型
📦 月之暗面 负责模型 1-2 (共2个)
📦 阿里百炼 负责模型 3-4 (共2个)
📦 七牛云 负责模型 5-6 (共2个)
📦 腾讯混元 负责模型 7-8 (共2个)
```

### 性能对比

| 策略 | 8个模型耗时 | 成本 | 质量 | 推荐场景 |
|------|-------------|------|------|----------|
| **单平台** | ~19秒 | 8个API调用 | 稳定 | 小批量测试 |
| **原版并发** | ~136秒 | 32个API调用 | 最高 | 小批量高质量 |
| **分片并发** | ~12秒 | 8个API调用 | 高 | 大批量生产 |

## 🔧 核心模块

### `keyword_extractor.py`
- 主程序入口和流程控制
- 命令行参数处理
- 结果统计和报告
- 支持单平台和多平台模式

### `csv_reader.py`
- CSV数据读取和筛选
- 数据验证和清洗
- 模型信息格式化
- 集成网页爬虫功能

### `ai_extractor.py`  
- 单平台AI接口调用
- 专业Prompt设计
- 响应解析和处理

### `multi_platform_extractor.py`
- 多平台AI支持（月之暗面、阿里百炼、七牛云、腾讯混元）
- 分片并发处理（类似XXL-Job分片广播）
- 智能容错和结果聚合
- 异步并发优化

### `hf_scraper.py`
- 网页爬虫模块
- 支持JavaScript渲染页面
- 自动提取模型README和标签
- 支持Bearer token认证

### `models.py`
- 数据结构定义
- JSON序列化/反序列化
- 类型验证

## ⚙️ 依赖包

```txt
openai==1.35.0
python-dotenv==1.0.1
httpx==0.25.0
beautifulsoup4==4.12.3
requests==2.31.0
tqdm==4.66.2
playwright==1.55.0
aiohttp>=3.8.0
```

## 🛠️ 开发指南

### 添加新的数据源

1. 在 `csv_reader.py` 中添加新的读取逻辑
2. 在 `models.py` 中定义对应的数据结构
3. 在 `keyword_extractor.py` 中集成新的数据源

### 自定义关键词维度

1. 修改 `ai_extractor.py` 中的Prompt模板
2. 更新提取逻辑以适应新的维度
3. 调整输出格式验证

### 扩展AI模型支持

1. 在 `multi_platform_extractor.py` 中添加新的平台配置
2. 修改环境变量配置
3. 更新Prompt以适应不同模型的特性
4. 支持分片并发和单平台模式

### 分片并发优化

1. 调整分片策略以适应不同的模型数量
2. 优化平台分配算法
3. 增强容错机制
4. 监控平台性能

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

**项目状态**: ✅ 生产就绪  
**最后更新**: 2025-01-10  
**版本**: 2.0.0

## 🚀 新版本特性

### v2.0.0 (2025-01-10)
- ✨ **多平台AI支持**: 新增月之暗面、阿里百炼、七牛云、腾讯混元四大平台
- 🚀 **分片并发处理**: 实现类似XXL-Job的分片广播模式，处理效率提升4倍
- 🕷️ **网页爬虫集成**: 自动爬取模型README和标签信息
- 🔄 **智能容错机制**: 自动处理平台失败，确保系统稳定性
- 📊 **丰富输出格式**: 支持JSON、CSV、Markdown、TXT多种输出格式
- 🎯 **SEO优化**: 针对CSDN博客和GitCode网站引流优化关键词提取

### v1.0.0 (2025-09-24)
- 🎯 **基础关键词提取**: 使用Moonshot AI提取专业关键词
- 📊 **CSV数据处理**: 高效读取和筛选HuggingFace模型数据
- 💾 **批量处理**: 支持大规模数据批量提取
- 📈 **JSON输出**: 结构化存储提取结果