# 开发任务指南

## 代码质量工具

### Python代码格式化和检查 (后端)

#### Black - 代码格式化
```bash
cd backend

# 格式化所有Python文件
black .

# 检查格式但不修改
black --check .

# 格式化特定文件
black manage.py
```

#### Flake8 - 代码风格检查
```bash
cd backend

# 检查所有Python文件
flake8 .

# 检查特定文件
flake8 pdf_processor/

# 生成报告
flake8 --format=html --htmldir=flake8_report .
```

#### 配置文件示例
```ini
# setup.cfg 或 .flake8
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = 
    .git,
    __pycache__,
    migrations,
    .venv,
    node_modules
```

### JavaScript/Vue代码格式化 (前端)

#### ESLint - 代码检查
```bash
cd astro_frontend

# 安装ESLint (如果未安装)
npm install --save-dev eslint @vue/eslint-config-recommended

# 检查代码
npm run lint

# 自动修复可修复的问题
npm run lint -- --fix
```

#### Prettier - 代码格式化
```bash
cd astro_frontend

# 安装Prettier
npm install --save-dev prettier

# 格式化所有文件
npx prettier --write "src/**/*.{js,vue,css,html}"

# 检查格式
npx prettier --check "src/**/*.{js,vue,css,html}"
```

## 测试指南

### 后端测试 (Django)

#### 单元测试
```bash
cd backend

# 运行所有测试
python manage.py test

# 运行特定应用测试
python manage.py test pdf_processor

# 运行特定测试类
python manage.py test pdf_processor.tests.TestRAGService

# 运行特定测试方法
python manage.py test pdf_processor.tests.TestRAGService.test_process_query

# 生成覆盖率报告
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # 生成HTML报告
```

#### 测试文件结构
```
backend/pdf_processor/
├── tests/
│   ├── __init__.py
│   ├── test_models.py      # 模型测试
│   ├── test_views.py       # 视图测试
│   ├── test_services.py    # 服务测试
│   └── test_utils.py       # 工具函数测试
```

#### 测试示例
```python
# pdf_processor/tests/test_services.py
from django.test import TestCase
from unittest.mock import patch, MagicMock
from ..services import RAGService

class TestRAGService(TestCase):
    def setUp(self):
        self.rag_service = RAGService()
    
    def test_process_query_success(self):
        """测试成功处理查询"""
        query = "什么是天体生物学？"
        result = self.rag_service.process_query(query)
        
        self.assertIn('answer', result)
        self.assertIn('references', result)
        self.assertIsInstance(result['references'], list)
    
    @patch('pdf_processor.services.weaviate_client')
    def test_process_query_weaviate_error(self, mock_client):
        """测试Weaviate连接错误"""
        mock_client.query.side_effect = Exception("连接失败")
        
        query = "测试查询"
        result = self.rag_service.process_query(query)
        
        self.assertIn('error', result)
```

### 前端测试 (Vue.js)

#### 安装测试工具
```bash
cd astro_frontend

# 安装Jest和Vue测试工具
npm install --save-dev @vue/test-utils jest vue-jest babel-jest
```

#### 运行测试
```bash
cd astro_frontend

# 运行所有测试
npm test

# 监视模式运行测试
npm test -- --watch

# 生成覆盖率报告
npm test -- --coverage
```

## 构建和部署

### 开发环境构建

#### 后端开发环境
```bash
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver 8000
```

#### 前端开发环境
```bash
cd astro_frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

### 生产环境构建

#### Docker构建
```bash
# 构建并启动所有服务
docker-compose up -d --build

# 仅构建特定服务
docker-compose build backend
docker-compose build frontend

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f backend
```

#### 手动部署准备
```bash
# 后端生产配置
cd backend
pip install gunicorn
python manage.py collectstatic --noinput
python manage.py migrate

# 前端生产构建
cd astro_frontend
npm run build
# 将dist/目录内容部署到Web服务器
```

## 性能优化

### 后端性能优化
```bash
cd backend

# 数据库查询优化
python manage.py shell
>>> from django.db import connection
>>> print(connection.queries)  # 查看SQL查询

# 缓存性能测试
python meteorite_search/performance_test.py

# 数据库优化
python meteorite_search/postgresql_optimizer.py

# 内存使用分析
pip install memory-profiler
python -m memory_profiler your_script.py
```

### 前端性能优化
```bash
cd astro_frontend

# 构建分析
npm run build -- --analyze

# 包大小分析
npx webpack-bundle-analyzer dist/static/js/*.js

# 性能审计
npm install -g lighthouse
lighthouse http://localhost:5173 --output html --output-path ./lighthouse-report.html
```

## 调试工具

### 后端调试
```bash
cd backend

# Django调试工具栏
pip install django-debug-toolbar

# 系统诊断脚本
python scripts/diagnose.py

# 性能监控面板
python scripts/performance_dashboard.py

# 数据库查询调试
python manage.py shell
>>> import logging
>>> logging.getLogger('django.db.backends').setLevel(logging.DEBUG)
```

### 前端调试
```bash
cd astro_frontend

# Vue开发者工具
# 在浏览器中安装Vue Devtools扩展

# 源码映射调试
npm run dev  # 自动启用source maps

# 网络请求调试
# 使用浏览器开发者工具的Network面板
```

## 代码质量检查流程

### 提交前检查清单
```bash
# 1. 代码格式化
cd backend && black .
cd astro_frontend && npm run lint -- --fix

# 2. 运行测试
cd backend && python manage.py test
cd astro_frontend && npm test

# 3. 代码风格检查
cd backend && flake8 .
cd astro_frontend && npm run lint

# 4. 类型检查 (如果使用TypeScript)
cd astro_frontend && npm run type-check

# 5. 构建测试
cd astro_frontend && npm run build
```

### Git钩子设置
```bash
# 安装pre-commit
pip install pre-commit

# 创建.pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
EOF

# 安装钩子
pre-commit install
```

## 监控和日志

### 应用监控
```bash
# 系统资源监控
python scripts/performance_dashboard.py

# 日志分析
tail -f logs/django.log
grep "ERROR" logs/django.log

# 数据库性能监控
python manage.py shell
>>> from django.db import connection
>>> print(len(connection.queries))
```

### 错误追踪
```bash
# 安装Sentry (可选)
pip install sentry-sdk

# 配置错误报告
# 在settings.py中添加Sentry配置
```