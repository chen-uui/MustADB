开发任务完成后：
1. 后端提交需通过pytest测试、flake8静态检查、black格式化（如有CI建议配置自动检查）。
2. 前端建议npm run lint、npm run build，确保无ESLint报错。
3. 检查相关API端点（如 /api/direct-processing/process/）是否响应正常。
4. 本地联调建议配合前后端各自日志和健康检查（如 curl http://localhost:8000/api/pdf/health/、前端http://localhost:5174/页面访问）。
5. 测试主要流程，如上传PDF、查看分析结果、导出等。