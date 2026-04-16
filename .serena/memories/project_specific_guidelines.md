# 项目特定指南和最佳实践

## 天体生物学RAG系统特定指南

### 核心业务逻辑理解

#### RAG工作流程
1. **查询预处理**: 用户输入 → 查询清理和标准化
2. **向量检索**: 查询向量化 → Weaviate相似性搜索
3. **文档重排序**: 基于相关性和权重的结果排序
4. **上下文构建**: 选择最相关的文档片段
5. **LLM生成**: 使用Llama 3.1生成答案
6. **后处理**: 格式化答案和参考文献

#### 关键组件交互
```python
# 典型的RAG查询流程
def process_rag_query(query: str) -> dict:
    # 1. 查询预处理
    cleaned_query = preprocess_query(query)
    
    # 2. 向量检索
    query_vector = get_embedding(cleaned_query)
    search_results = weaviate_client.query(query_vector)
    
    # 3. 重排序和过滤
    ranked_results = rerank_results(search_results, query)
    
    # 4. 构建上下文
    context = build_context(ranked_results)
    
    # 5. LLM生成
    answer = llm_generate(query, context)
    
    # 6. 格式化输出
    return format_response(answer, ranked_results)
```

### 数据处理最佳实践

#### PDF文档处理
```python
# PDF处理管道
class PDFProcessor:
    def process_document(self, pdf_path: str):
        # 1. 文本提取
        text = self.extract_text(pdf_path)
        
        # 2. 文档分块
        chunks = self.chunk_document(text)
        
        # 3. 向量化
        vectors = self.vectorize_chunks(chunks)
        
        # 4. 存储到Weaviate
        self.store_vectors(vectors, metadata)
        
        # 5. 更新数据库记录
        self.update_database(pdf_path, status='processed')
```

#### 文档分块策略
- **固定长度分块**: 每块500-1000字符
- **语义分块**: 基于段落和句子边界
- **重叠分块**: 块之间50-100字符重叠
- **元数据保留**: 保留标题、作者、页码等信息

### 性能优化指南

#### 向量检索优化
```python
# 优化Weaviate查询
def optimized_vector_search(query_vector, limit=10):
    return (
        weaviate_client.query
        .get("Document", ["title", "content", "metadata"])
        .with_near_vector({
            "vector": query_vector,
            "certainty": 0.7  # 设置相似度阈值
        })
        .with_limit(limit)
        .with_additional(["certainty", "distance"])
        .do()
    )
```

#### 缓存策略
```python
# Redis缓存实现
import redis
from django.core.cache import cache

def cached_embedding(text: str):
    cache_key = f"embedding:{hash(text)}"
    embedding = cache.get(cache_key)
    
    if embedding is None:
        embedding = compute_embedding(text)
        cache.set(cache_key, embedding, timeout=3600)  # 1小时缓存
    
    return embedding
```

#### 数据库查询优化
```python
# Django ORM优化
class PDFDocument(models.Model):
    # 添加数据库索引
    title = models.CharField(max_length=500, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['title', 'created_at']),
            models.Index(fields=['status']),
        ]

# 查询优化
def get_recent_documents():
    return (
        PDFDocument.objects
        .select_related('category')  # 减少数据库查询
        .prefetch_related('tags')    # 预取相关对象
        .filter(status='processed')
        .order_by('-created_at')[:10]
    )
```

### 错误处理和监控

#### 异常处理模式
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RAGServiceError(Exception):
    """RAG服务基础异常"""
    pass

class VectorSearchError(RAGServiceError):
    """向量搜索异常"""
    pass

def safe_vector_search(query: str) -> Optional[dict]:
    try:
        result = vector_search(query)
        return result
    except WeaviateException as e:
        logger.error(f"Weaviate搜索失败: {e}")
        raise VectorSearchError(f"向量搜索失败: {e}")
    except Exception as e:
        logger.error(f"未知搜索错误: {e}")
        return None
```

#### 性能监控
```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} 执行时间: {execution_time:.2f}秒")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败 ({execution_time:.2f}秒): {e}")
            raise
    return wrapper

@monitor_performance
def process_rag_query(query: str):
    # RAG查询处理逻辑
    pass
```

### 前端开发指南

#### API调用最佳实践
```javascript
// api/rag.js
import axios from 'axios'

class RAGService {
  constructor() {
    this.api = axios.create({
      baseURL: 'http://localhost:8000/api',
      timeout: 30000  // 30秒超时
    })
  }

  async queryRAG(question, options = {}) {
    try {
      const response = await this.api.post('/rag/query/', {
        query: question,
        limit: options.limit || 5,
        include_references: options.includeReferences !== false
      })
      
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      console.error('RAG查询失败:', error)
      return {
        success: false,
        error: error.response?.data?.error || '查询失败'
      }
    }
  }
}

export default new RAGService()
```

#### 状态管理
```javascript
// store/rag.js (Vuex示例)
export default {
  namespaced: true,
  state: {
    currentQuery: '',
    results: [],
    isLoading: false,
    error: null
  },
  
  mutations: {
    SET_LOADING(state, loading) {
      state.isLoading = loading
    },
    SET_RESULTS(state, results) {
      state.results = results
    },
    SET_ERROR(state, error) {
      state.error = error
    }
  },
  
  actions: {
    async searchRAG({ commit }, query) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      
      try {
        const result = await RAGService.queryRAG(query)
        if (result.success) {
          commit('SET_RESULTS', result.data)
        } else {
          commit('SET_ERROR', result.error)
        }
      } catch (error) {
        commit('SET_ERROR', '系统错误')
      } finally {
        commit('SET_LOADING', false)
      }
    }
  }
}
```

### 部署和运维指南

#### Docker优化
```dockerfile
# 多阶段构建优化
FROM python:3.11-slim as backend-builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM node:18-alpine as frontend-builder
WORKDIR /app
COPY astro_frontend/package*.json ./
RUN npm ci --only=production

FROM python:3.11-slim as production
WORKDIR /app
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=frontend-builder /app/node_modules ./node_modules
COPY . .
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

#### 环境配置管理
```python
# config/settings.py
import os
from pathlib import Path

# 环境变量配置
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')

# Weaviate配置
WEAVIATE_URL = os.getenv('WEAVIATE_URL', 'http://localhost:8080')
WEAVIATE_API_KEY = os.getenv('WEAVIATE_API_KEY', '')

# Ollama配置
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b-instruct-q4_K_M')

# Redis配置
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
```

### 测试策略

#### 集成测试
```python
# tests/test_integration.py
class TestRAGIntegration(TestCase):
    def setUp(self):
        # 设置测试数据
        self.test_document = PDFDocument.objects.create(
            title="测试文档",
            file_path="/test/doc.pdf"
        )
    
    def test_end_to_end_query(self):
        """端到端查询测试"""
        query = "什么是天体生物学？"
        
        # 模拟完整的RAG流程
        response = self.client.post('/api/rag/query/', {
            'query': query
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('answer', data)
        self.assertIn('references', data)
        self.assertTrue(len(data['references']) > 0)
```

#### 性能测试
```python
# tests/test_performance.py
import time
from django.test import TestCase

class TestPerformance(TestCase):
    def test_query_response_time(self):
        """测试查询响应时间"""
        query = "火星上的生命迹象"
        
        start_time = time.time()
        response = self.client.post('/api/rag/query/', {'query': query})
        end_time = time.time()
        
        response_time = end_time - start_time
        self.assertLess(response_time, 5.0)  # 响应时间应小于5秒
        self.assertEqual(response.status_code, 200)
```

### 安全考虑

#### API安全
```python
# 输入验证和清理
from django.utils.html import escape
import re

def sanitize_query(query: str) -> str:
    # 移除潜在的恶意字符
    query = re.sub(r'[<>"\']', '', query)
    # HTML转义
    query = escape(query)
    # 长度限制
    return query[:1000]

# 速率限制
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='10/m', method='POST')
def rag_query_view(request):
    # RAG查询处理
    pass
```

#### 数据隐私
```python
# 敏感信息过滤
def filter_sensitive_content(text: str) -> str:
    # 移除邮箱地址
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    # 移除电话号码
    text = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', text)
    return text
```