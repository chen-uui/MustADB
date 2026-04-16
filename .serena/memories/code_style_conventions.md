# 代码风格和约定

## Python代码风格 (后端)

### 基本约定
- 使用4个空格缩进，不使用Tab
- 行长度限制为88字符 (Black格式化器标准)
- 使用UTF-8编码，文件头包含编码声明
- 类名使用PascalCase，函数和变量使用snake_case

### 文件头格式
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块描述
功能说明
"""
```

### 导入顺序
```python
# 1. 标准库导入
import os
import sys
from pathlib import Path

# 2. 第三方库导入
import requests
from django.conf import settings

# 3. 本地应用导入
from .models import PDFDocument
from .services import RAGService
```

### 类和函数文档
```python
class RAGService:
    """RAG问答服务类
    
    提供基于向量检索的智能问答功能，集成Weaviate和LLM。
    """
    
    def process_query(self, query: str, limit: int = 5) -> dict:
        """处理用户查询
        
        Args:
            query: 用户问题
            limit: 返回结果数量限制
            
        Returns:
            包含答案和参考文献的字典
            
        Raises:
            ValueError: 查询参数无效时抛出
        """
        pass
```

### 类型提示
- 使用类型提示增强代码可读性
- 复杂类型使用typing模块
```python
from typing import List, Dict, Optional, Union

def format_references(refs: List[Dict[str, str]]) -> Optional[str]:
    """格式化参考文献"""
    pass
```

### 异常处理
```python
try:
    result = weaviate_client.query()
except WeaviateException as e:
    logger.error(f"Weaviate查询失败: {e}")
    raise
except Exception as e:
    logger.error(f"未知错误: {e}")
    return {"error": "系统错误"}
```

## Django特定约定

### 模型定义
```python
class PDFDocument(models.Model):
    """PDF文档模型"""
    
    title = models.CharField(max_length=500, verbose_name="标题")
    file_path = models.CharField(max_length=1000, verbose_name="文件路径")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "PDF文档"
        verbose_name_plural = "PDF文档"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
```

### 视图函数
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_query(request):
    """处理RAG查询请求"""
    try:
        serializer = QuerySerializer(data=request.data)
        if serializer.is_valid():
            # 处理逻辑
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"查询处理失败: {e}")
        return Response(
            {"error": "服务器内部错误"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

## JavaScript/Vue.js代码风格 (前端)

### 基本约定
- 使用2个空格缩进
- 使用单引号字符串
- 组件名使用PascalCase
- 变量和函数使用camelCase

### Vue组件结构
```vue
<template>
  <div class="component-name">
    <!-- 模板内容 -->
  </div>
</template>

<script>
export default {
  name: 'ComponentName',
  props: {
    title: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      isLoading: false,
      results: []
    }
  },
  methods: {
    async fetchData() {
      try {
        this.isLoading = true
        const response = await this.$api.get('/endpoint')
        this.results = response.data
      } catch (error) {
        console.error('获取数据失败:', error)
        this.$message.error('获取数据失败')
      } finally {
        this.isLoading = false
      }
    }
  }
}
</script>

<style scoped>
.component-name {
  /* 组件样式 */
}
</style>
```

### API调用约定
```javascript
// api/index.js
import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

// 响应拦截器
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API请求失败:', error)
    return Promise.reject(error)
  }
)
```

## 命名约定

### 文件命名
- Python文件: `snake_case.py`
- Vue组件: `PascalCase.vue`
- 工具脚本: `kebab-case.py`
- 配置文件: `lowercase.yml`

### 变量命名
```python
# Python
user_query = "用户问题"
pdf_documents = []
is_processing = False
MAX_RESULTS = 10

# JavaScript
const userQuery = '用户问题'
const pdfDocuments = []
const isProcessing = false
const MAX_RESULTS = 10
```

### 函数命名
```python
# Python - 动词开头，描述功能
def process_query():
def format_references():
def validate_input():

# JavaScript - 动词开头，驼峰命名
function processQuery() {}
function formatReferences() {}
function validateInput() {}
```

## 注释约定

### 代码注释
```python
# 单行注释说明代码意图
query_vector = self.get_embedding(query)  # 获取查询向量

"""
多行注释用于复杂逻辑说明
这里处理向量检索和重排序逻辑
"""
```

### TODO标记
```python
# TODO: 优化检索算法性能
# FIXME: 修复并发访问问题
# NOTE: 这里使用了特殊的处理逻辑
# WARNING: 此方法可能消耗大量内存
```

## 日志约定

### 日志级别使用
```python
import logging

logger = logging.getLogger(__name__)

# DEBUG: 详细的调试信息
logger.debug(f"查询向量维度: {vector.shape}")

# INFO: 一般信息
logger.info(f"处理查询: {query[:50]}...")

# WARNING: 警告信息
logger.warning(f"缓存未命中，使用默认值")

# ERROR: 错误信息
logger.error(f"向量检索失败: {e}")

# CRITICAL: 严重错误
logger.critical(f"系统无法连接到Weaviate")
```

## 测试约定

### 测试文件命名
- `test_*.py` - 测试文件
- `*_test.py` - 测试文件 (备选)

### 测试函数命名
```python
class TestRAGService(TestCase):
    def test_process_query_success(self):
        """测试查询处理成功情况"""
        pass
    
    def test_process_query_empty_input(self):
        """测试空输入处理"""
        pass
    
    def test_process_query_invalid_format(self):
        """测试无效格式处理"""
        pass
```