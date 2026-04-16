# 技术栈和依赖

## 开发环境要求
- Python 3.11+ (当前使用 3.11.13)
- Node.js 16+ (当前使用 v22.14.0)
- Docker & Docker Compose (当前使用 28.3.2)
- Git (当前使用 2.51.0.windows.1)
- 8GB+ RAM (推荐16GB)
- NVIDIA GPU (可选，用于加速推理)

## 后端技术栈 (Django)
### 核心框架
- Django==5.2.1
- djangorestframework==3.15.2
- django-cors-headers==4.7.0

### 向量数据库和嵌入
- weaviate-client==4.16.7
- sentence-transformers==2.7.0

### 大语言模型集成
- openai==1.99.9
- langchain==0.3.27
- langchain-openai==0.3.12
- langchain-community==0.3.27

### PDF处理
- PyMuPDF==1.24.3
- python-multipart==0.0.20

### 数据处理
- numpy==2.2.6
- pandas==2.2.3
- scipy==1.15.3

### 缓存和性能
- redis==5.2.1

## 前端技术栈 (Vue.js)
### 核心框架
- vue: ^3.5.18
- vue-router: ^4.5.1
- vite: ^4.5.14

### UI框架
- bootstrap: ^5.3.7
- bootstrap-icons: ^1.13.1

### 工具库
- axios: ^1.11.0 (HTTP客户端)
- marked: ^16.2.1 (Markdown解析)
- aos: ^2.3.4 (动画库)

## Docker服务
### Weaviate向量数据库
- Image: semitechnologies/weaviate:1.23.7
- Ports: 8080:8080, 50051:50051

### Transformers推理服务
- Image: semitechnologies/transformers-inference:sentence-transformers-multi-qa-MiniLM-L6-cos-v1
- Port: 9090:8080

## 外部服务依赖
### Ollama (大语言模型服务)
- URL: http://localhost:11434
- 模型: llama3.1:8b-instruct-q4_K_M
- 上下文长度: 128K tokens

### Redis (缓存服务)
- 用于查询结果缓存
- 向量嵌入缓存
- 模型响应缓存