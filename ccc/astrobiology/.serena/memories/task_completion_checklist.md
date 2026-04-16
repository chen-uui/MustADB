# 任务完成检查清单

## 代码修改后必须执行的检查

### 1. 代码质量检查
```bash
# 代码格式化
black backend/pdf_processor/

# 代码检查
flake8 backend/pdf_processor/

# 类型检查（如果配置了mypy）
mypy backend/pdf_processor/
```

### 2. 功能测试
```bash
# 运行相关测试
python manage.py test pdf_processor.tests

# 系统集成测试
python test_e2e_system.py

# 特定功能测试
python test_enhanced_rag.py
```

### 3. 数据库检查
```bash
# 检查迁移状态
python manage.py showmigrations

# 应用新迁移（如果有）
python manage.py migrate

# 检查数据库连接
python check_db.py
```

### 4. 外部服务检查
```bash
# 检查Weaviate连接
python check_weaviate.py

# 检查Ollama服务
curl http://localhost:11434/api/tags

# 检查系统整体状态
python debug_status_check.py
```

### 5. 日志检查
```bash
# 查看错误日志
grep -i error logs/astrobiology.log

# 查看警告日志
grep -i warning logs/astrobiology.log

# 检查最新日志
tail -f logs/astrobiology.log
```

## 部署前检查

### 1. 配置验证
- [ ] 环境变量设置正确
- [ ] 数据库连接正常
- [ ] 外部服务可访问
- [ ] 文件路径存在且可写

### 2. 性能检查
- [ ] 内存使用正常
- [ ] CPU使用率合理
- [ ] 磁盘空间充足
- [ ] 网络连接稳定

### 3. 安全检查
- [ ] 敏感信息已加密
- [ ] API端点有适当权限控制
- [ ] 输入验证完整
- [ ] 错误信息不泄露敏感信息

## 常见问题排查

### 1. 搜索功能异常
```bash
# 检查Weaviate数据
python -c "from pdf_processor.weaviate_connection import weaviate_connection; print(weaviate_connection.test_connection())"

# 检查嵌入服务
python -c "from pdf_processor.embedding_service import embedding_service; print(embedding_service.is_available())"
```

### 2. 数据提取失败
```bash
# 检查任务状态
python manage.py shell -c "from pdf_processor.models import ProcessingTask; print(ProcessingTask.objects.filter(status='failed').count())"

# 清理失败任务
python manage.py shell -c "from pdf_processor.views_task_cleanup import cleanup_stale_tasks; cleanup_stale_tasks(None)"
```

### 3. 前端连接问题
```bash
# 检查CORS设置
grep -i cors backend/config/settings.py

# 检查API端点
curl http://localhost:8000/api/pdf/health/
```

## 回滚计划

### 1. 代码回滚
```bash
# 使用Git回滚到上一个稳定版本
git log --oneline -10
git checkout <commit_hash>

# 重新部署
python manage.py migrate
python manage.py collectstatic
```

### 2. 数据库回滚
```bash
# 回滚数据库迁移
python manage.py migrate <app_name> <previous_migration_number>

# 恢复数据备份（如果有）
pg_restore -d astrobiology_db backup_file.sql
```

### 3. 配置回滚
```bash
# 恢复配置文件
cp .env.backup .env

# 重启服务
systemctl restart astrobiology-backend
```