# 建议的系统命令

## Windows系统命令
由于项目运行在Windows环境，以下是常用的系统命令：

### 文件和目录操作
- `dir` - 列出目录内容 (等同于Unix的ls)
- `cd` - 切换目录
- `mkdir` - 创建目录
- `rmdir /s` - 删除目录及其内容
- `copy` - 复制文件
- `move` - 移动/重命名文件
- `del` - 删除文件

### 进程管理
- `tasklist` - 查看运行进程 (等同于Unix的ps)
- `taskkill /PID <pid>` - 终止进程
- `netstat -an` - 查看网络连接

### 文本搜索
- `findstr "pattern" file.txt` - 在文件中搜索文本 (等同于Unix的grep)
- `findstr /r "pattern" *.py` - 使用正则表达式搜索

## 项目启动命令

### 一键启动系统
```bash
# 启动完整系统 (推荐)
python start_astrobiology_system.py

# 或使用Docker Compose
docker-compose up -d
```

### 分步启动
```bash
# 1. 启动Docker服务 (Weaviate + Transformers)
docker-compose up -d

# 2. 启动Django后端
cd backend
python manage.py runserver 8000

# 3. 启动Vue前端
cd astro_frontend
npm run dev
```

## 开发命令

### 后端开发 (Django)
```bash
cd backend

# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 运行开发服务器
python manage.py runserver 8000

# Django Shell
python manage.py shell

# 收集静态文件
python manage.py collectstatic
```

### 前端开发 (Vue.js)
```bash
cd astro_frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

## 系统维护命令

### 诊断和监控
```bash
# 系统诊断
python diagnose.py

# 性能监控
python backend/performance_dashboard.py

# 检查GPU状态
python check_gpu.py
```

### 缓存管理
```bash
# 清理所有缓存
python backend/clear_all_cache.py

# 清理特定缓存
python backend/manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

### 数据库管理
```bash
# 清理数据库
python backend/clear_database.py

# 初始化向量数据库
python backend/manage.py init_vector_db

# 同步PDF文档
python backend/manage.py sync_pdfs
```

## Docker命令

### 容器管理
```bash
# 查看运行中的容器
docker ps

# 查看所有容器
docker ps -a

# 查看容器日志
docker logs <container_name>

# 进入容器
docker exec -it <container_name> bash

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart
```

### 镜像管理
```bash
# 查看镜像
docker images

# 删除未使用的镜像
docker image prune

# 构建镜像
docker build -t image_name .
```

## 测试命令

### 运行测试
```bash
cd backend

# 运行所有测试
python manage.py test

# 运行特定应用测试
python manage.py test pdf_processor

# 运行特定测试文件
python manage.py test pdf_processor.tests.TestRAGService
```

### 性能测试
```bash
# RAG系统性能测试
python backend/meteorite_search/performance_test.py

# 数据库性能测试
python backend/meteorite_search/postgresql_optimizer.py
```

## 故障排除命令

### 端口检查
```bash
# 检查端口占用
netstat -an | findstr :8000
netstat -an | findstr :5173
netstat -an | findstr :8080

# 终止占用端口的进程
taskkill /F /PID <pid>
```

### 服务状态检查
```bash
# 检查Weaviate状态
curl http://localhost:8080/v1/.well-known/ready

# 检查Ollama状态
curl http://localhost:11434/api/tags

# 检查后端API
curl http://localhost:8000/api/health/
```

## Git命令 (版本控制)
```bash
# 查看状态
git status

# 添加文件
git add .

# 提交更改
git commit -m "commit message"

# 推送到远程
git push origin main

# 拉取最新代码
git pull origin main

# 查看提交历史
git log --oneline
```