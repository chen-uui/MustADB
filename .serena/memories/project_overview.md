# 天体生物学RAG系统项目概览

## 项目目的
这是一个专门为天体生物学研究设计的智能问答系统，结合了先进的检索增强生成(RAG)技术和学术级文献管理能力。系统能够从天体生物学文献库中检索相关信息，并生成基于真实学术文献的高质量回答。

## 核心功能
- 🔍 智能文献检索：基于Weaviate向量数据库的语义搜索
- 📚 学术级文献管理：自动格式化参考文献，支持DOI去重
- 🤖 多模型支持：集成Llama 3.1 8B Instruct等开源大模型
- 📊 性能监控：实时系统状态监控和性能分析
- 🌐 现代化Web界面：Vue.js前端，支持实时交互
- 🔄 多轮对话：支持上下文保持的连续问答

## 技术栈
- **前端**: Vue.js 3 + Vite + Bootstrap 5
- **后端**: Django REST Framework + Django Channels
- **向量数据库**: Weaviate
- **大模型**: Llama 3.1 8B Instruct (q4_K_M量化) - 支持128K tokens超长上下文
- **PDF处理**: PyMuPDF + pdfplumber
- **缓存**: Redis + Django Cache
- **部署**: Docker + Docker Compose

## 项目结构
```
ccc/astrobiology/
├── astro_frontend/          # Vue.js前端应用
├── backend/                 # Django后端服务
│   ├── config/             # Django配置
│   ├── pdf_processor/      # RAG核心服务
│   ├── astro_data/         # 天体数据模型
│   └── meteorite_search/   # 陨石搜索功能
├── data/                   # 数据存储
└── docker-compose.yml      # Docker服务编排
```

## 文献库内容
系统包含14篇高质量天体生物学PDF文献，涵盖：
- 🪐 火星生命探索
- 🌙 谷神星研究
- 🦠 极端微生物学
- 🔬 技术方法

## 系统特点
- 学术严谨性：确保回答符合学术标准，引用真实文献
- 智能去重：基于DOI的精确去重和LLM过滤虚假参考文献
- 多级缓存：查询结果、向量嵌入、模型响应缓存
- 异步处理：支持并发请求处理