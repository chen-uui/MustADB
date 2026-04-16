后端开发常用命令：
- 依赖安装：cd ccc/astrobiology/backend && pip install -r requirements.txt
- 启动开发服务：python manage.py runserver
- 应用数据库迁移：python manage.py migrate
- 创建direct-processing相关表：python manage.py create_direct_processing_tables
- 初始化直接处理服务：python manage.py init_direct_processing_system
- 单元测试：python manage.py test pdf_processor.tests.test_direct_processing
- 集成测试：python manage.py test pdf_processor.tests.test_integration
- 性能测试：python manage.py test pdf_processor.tests.test_performance

前端开发常用命令：
- 依赖安装：cd ccc/astrobiology/astro_frontend && npm install
- 启动开发服务器：npm run dev
- 构建生产包：npm run build

其它：
- 日志查看（后端）：tail -f ccc/astrobiology/backend/logs/astrobiology.log
- 系统状态检查（后端）：python manage.py check_system_status
- 日志查错、API调试：curl、Postman等工具