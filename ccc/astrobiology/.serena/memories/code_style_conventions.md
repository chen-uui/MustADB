# 代码风格和约定

## Python代码风格

### 命名约定
- **类名**: PascalCase (如: `RAGService`, `MeteoriteDataExtractor`)
- **函数/方法名**: snake_case (如: `search_meteorite_segments`, `get_client`)
- **变量名**: snake_case (如: `search_results`, `document_id`)
- **常量**: UPPER_SNAKE_CASE (如: `MAX_FILE_SIZE`, `DEFAULT_BATCH_SIZE`)

### 文件结构
- **服务类**: 以 `_service.py` 结尾 (如: `rag_service.py`, `embedding_service.py`)
- **视图类**: 以 `views_` 开头 (如: `views_extraction.py`, `views_enhanced_rag.py`)
- **模型类**: 在 `models.py` 中定义
- **工具类**: 以 `_utils.py` 或功能名结尾

### 导入顺序
```python
# 1. 标准库导入
import os
import json
from typing import List, Dict, Optional

# 2. 第三方库导入
import requests
from django.http import JsonResponse

# 3. 本地应用导入
from .rag_service import RAGService
from .models import PDFDocument
```

### 文档字符串
```python
def search_meteorite_segments(self, query: str, limit: int = 100) -> List[Dict]:
    """
    搜索陨石相关片段
    
    Args:
        query: 搜索查询字符串
        limit: 返回结果数量限制
        
    Returns:
        包含搜索结果的字典列表
        
    Raises:
        ValueError: 当查询字符串为空时
    """
```

## 错误处理约定

### 异常处理模式
```python
try:
    # 主要逻辑
    result = perform_operation()
    return JsonResponse({'success': True, 'data': result})
except SpecificException as e:
    logger.error(f"特定错误: {str(e)}")
    return JsonResponse({'success': False, 'error': '具体错误信息'}, status=400)
except Exception as e:
    logger.error(f"未知错误: {str(e)}")
    return JsonResponse({'success': False, 'error': '系统错误'}, status=500)
```

### 日志记录
```python
import logging
logger = logging.getLogger(__name__)

# 信息日志
logger.info(f"开始处理文档: {document_id}")

# 警告日志
logger.warning(f"配置项缺失，使用默认值: {config_key}")

# 错误日志
logger.error(f"处理失败: {str(e)}")
```

## API响应格式

### 成功响应
```python
{
    "success": True,
    "data": {...},
    "message": "操作成功",
    "timestamp": "2025-01-01T00:00:00Z"
}
```

### 错误响应
```python
{
    "success": False,
    "error": "错误描述",
    "details": "详细错误信息",
    "code": "ERROR_CODE",
    "timestamp": "2025-01-01T00:00:00Z"
}
```

## 配置管理

### 环境变量使用
```python
# 在 settings.py 中定义
WEAVIATE_HOST = get_env_var('WEAVIATE_HOST', 'localhost')
WEAVIATE_PORT = int(get_env_var('WEAVIATE_PORT', '8080'))

# 在代码中使用
from config.settings import WEAVIATE_CONFIG
host = WEAVIATE_CONFIG['HOST']
```

### 配置验证
```python
def validate_config():
    """验证配置完整性"""
    required_vars = ['SECRET_KEY', 'DB_PASSWORD']
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"必需的环境变量 {var} 未设置")
```

## 测试约定

### 测试文件命名
- 测试文件以 `test_` 开头
- 测试类以 `Test` 开头
- 测试方法以 `test_` 开头

### 测试结构
```python
class TestRAGService:
    def setUp(self):
        """测试前准备"""
        self.rag_service = RAGService()
        
    def test_search_functionality(self):
        """测试搜索功能"""
        # 准备测试数据
        # 执行测试
        # 验证结果
        
    def tearDown(self):
        """测试后清理"""
        pass
```