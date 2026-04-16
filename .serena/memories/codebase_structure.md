# 代码库结构说明

## 项目根目录结构
```
d:\workspace\123\
├── .serena/                    # Serena配置目录
├── .venv/                      # Python虚拟环境
├── ccc/astrobiology/          # 主项目目录
├── ASTROBIOLOGY_RAG_SYSTEM.md # 系统说明文档
├── ASTROBIOLOGY_RAG_TEST_QUESTIONS.md # 测试问题集
├── SYSTEM_FILE_DESCRIPTIONS.md # 文件结构说明
└── Git-installer.exe          # Git安装程序
```

## 核心项目结构 (ccc/astrobiology/)

### 根目录文件
```
ccc/astrobiology/
├── start_astrobiology_system.py  # 系统启动脚本
├── docker-compose.yml           # Docker服务配置
├── debug_task.py               # 调试任务脚本
├── OPTIMIZATION_SUMMARY.md     # 优化总结
├── SYSTEM_OPTIMIZATION_PLAN.md # 系统优化计划
├── backend/                    # Django后端
├── astro_frontend/            # Vue.js前端
└── data/                      # 数据目录
```

## 后端结构 (backend/)

### 核心配置
```
backend/
├── manage.py                  # Django管理脚本
├── requirements.txt           # Python依赖
├── .env                      # 环境变量配置
├── db.sqlite3               # SQLite数据库
├── logging_config.py        # 日志配置
├── start_backend.bat        # Windows启动脚本
└── config/                  # Django配置包
    ├── __init__.py
    ├── settings.py          # Django设置
    ├── urls.py             # URL路由
    └── wsgi.py             # WSGI配置
```

### 应用模块
```
backend/
├── pdf_processor/           # PDF处理核心模块
│   ├── models.py           # 数据模型
│   ├── views.py            # API视图
│   ├── serializers.py      # 数据序列化
│   ├── services.py         # 业务逻辑服务
│   ├── urls.py             # URL路由
│   └── management/         # Django管理命令
│       └── commands/
│           ├── sync_pdfs.py
│           └── init_vector_db.py
├── astro_data/             # 天体生物学数据模块
│   ├── models.py           # 数据模型
│   ├── views.py            # API视图
│   ├── serializers.py      # 序列化器
│   └── migrations/         # 数据库迁移
└── meteorite_search/       # 陨石搜索模块
    ├── models.py           # 陨石数据模型
    ├── views.py            # 搜索API
    ├── rag_service.py      # RAG服务核心
    ├── performance_test.py # 性能测试
    └── postgresql_optimizer.py # 数据库优化
```

### 工具和脚本
```
backend/
├── scripts/                # 工具脚本目录
│   ├── clear_all_cache.py  # 清理缓存
│   ├── performance_dashboard.py # 性能监控
│   └── diagnose.py         # 系统诊断
├── clear_database.py       # 清理数据库
└── create_dev_user.py      # 创建开发用户
```

### 静态文件和媒体
```
backend/
├── static/                 # 静态文件
├── media/                  # 媒体文件
└── models/                 # 模型文件存储
```

## 前端结构 (astro_frontend/)

### 项目配置
```
astro_frontend/
├── package.json            # Node.js依赖配置
├── package-lock.json       # 依赖锁定文件
├── vite.config.js         # Vite构建配置
├── jsconfig.json          # JavaScript配置
├── index.html             # HTML入口文件
├── start_frontend.bat     # Windows启动脚本
└── .gitignore             # Git忽略文件
```

### 源代码结构
```
astro_frontend/src/
├── main.js                # 应用入口
├── App.vue               # 根组件
├── router/               # 路由配置
├── components/           # 可复用组件
├── views/               # 页面组件
├── assets/              # 静态资源
├── services/            # API服务
└── utils/               # 工具函数
```

### 构建输出
```
astro_frontend/
├── dist/                 # 构建输出目录
└── node_modules/         # Node.js依赖
```

## 数据目录结构 (data/)

### 文献库组织
```
data/
├── astrobiology_papers/   # 天体生物学论文
├── meteorite_studies/     # 陨石研究文献
├── exoplanet_research/    # 系外行星研究
├── biosignatures/         # 生物标志研究
└── astrobiology_reviews/  # 综述文献
```

## 关键入口点

### 系统启动
- **主启动脚本**: `start_astrobiology_system.py`
- **后端启动**: `backend/manage.py runserver`
- **前端启动**: `astro_frontend/npm run dev`
- **Docker启动**: `docker-compose up -d`

### API入口点
- **主API**: `http://localhost:8000/api/`
- **RAG查询**: `http://localhost:8000/api/rag/query/`
- **PDF处理**: `http://localhost:8000/api/pdf/`
- **陨石搜索**: `http://localhost:8000/api/meteorite/`

### 前端入口
- **开发服务器**: `http://localhost:5173/`
- **生产构建**: `astro_frontend/dist/index.html`

## 配置文件位置

### 环境配置
- **Django设置**: `backend/config/settings.py`
- **环境变量**: `backend/.env`
- **Docker配置**: `docker-compose.yml`
- **前端配置**: `astro_frontend/vite.config.js`

### 日志配置
- **后端日志**: `backend/logging_config.py`
- **系统日志**: 输出到控制台和文件

## 数据库和存储

### 数据库文件
- **SQLite**: `backend/db.sqlite3`
- **向量数据库**: Weaviate (Docker容器)
- **缓存**: Redis (可选)

### 文件存储
- **PDF文档**: `data/` 目录下按类别存储
- **模型缓存**: `backend/models/`
- **静态文件**: `backend/static/`
- **媒体文件**: `backend/media/`

## 重要的配置和约定

### 端口分配
- **Django后端**: 8000
- **Vue前端**: 5173
- **Weaviate**: 8080
- **Transformers**: 9090
- **Ollama**: 11434

### 环境要求
- **Python**: 3.11+
- **Node.js**: 16+
- **Docker**: 最新版本
- **Git**: 2.x
- **内存**: 8GB+ (推荐16GB)
- **GPU**: 可选，用于加速推理