"""
统一的嵌入服务模块
整合SentenceTransformer初始化和模型管理逻辑
"""
import os
import logging
from typing import List, Optional
from sentence_transformers import SentenceTransformer
import torch
from django.conf import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """统一的嵌入服务，管理SentenceTransformer模型"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            # 设置设备
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self._initialize_model()
    
    def _initialize_model(self):
        """初始化嵌入模型"""
        model_name = settings.EMBEDDING_CONFIG['MODEL_NAME']
        cache_dir = settings.EMBEDDING_CONFIG['CACHE_DIR']
        
        # 处理模型名称，提取实际模型名
        if '/' in model_name:
            actual_model_name = model_name.split('/')[-1]  # 提取 'all-mpnet-base-v2'
        else:
            actual_model_name = model_name
            
        model_path = os.path.join(cache_dir, actual_model_name)
        
        try:
            # 尝试从本地加载模型
            if os.path.exists(model_path):
                logger.info(f"从本地路径加载嵌入模型: {model_path}")
                self._model = SentenceTransformer(model_path, device=self.device)
            else:
                logger.info(f"本地模型不存在，从在线下载: {model_name}")
                self._model = SentenceTransformer(model_name, device=self.device)
                
                # 保存模型到本地
                os.makedirs(cache_dir, exist_ok=True)
                self._model.save(model_path)
                logger.info(f"模型已保存到本地: {model_path}")
                
        except Exception as e:
            logger.error(f"嵌入模型初始化失败: {e}")
            raise
    
    def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
        """编码文本为向量"""
        if self._model is None:
            raise RuntimeError("嵌入模型未初始化")
        
        try:
            embeddings = self._model.encode(texts, **kwargs)
            # 检查embeddings是否有tolist方法，如果没有则转换为列表格式
            # 使用类型检查来避免类型错误
            if hasattr(embeddings, 'tolist') and callable(getattr(embeddings, 'tolist', None)):
                # 如果是numpy数组，使用tolist()方法
                try:
                    result = embeddings.tolist()  # type: ignore
                except:
                    # 如果tolist()失败，尝试手动转换
                    if isinstance(embeddings, (list, tuple)):
                        result = [list(row) if isinstance(row, (list, tuple)) else [float(x) for x in row] for row in embeddings]
                    else:
                        result = [[float(x) for x in embeddings]]
            else:
                # 如果embeddings是列表或其他可迭代对象，转换为列表
                result = []
                if isinstance(embeddings, (list, tuple)):
                    # 如果是二维数组，需要转换为二维列表
                    for row in embeddings:
                        if hasattr(row, 'tolist') and callable(getattr(row, 'tolist', None)):
                            try:
                                result.append(row.tolist())  # type: ignore
                            except:
                                if isinstance(row, (list, tuple)):
                                    result.append(list(row))
                                else:
                                    result.append([float(x) for x in row])
                        elif isinstance(row, (list, tuple)):
                            result.append(list(row))
                        else:
                            result.append([float(x) for x in row])
                else:
                    # 如果是单个向量，包装在列表中
                    result = [[float(x) for x in embeddings]]
            
            # 确保返回的数据类型正确
            final_result = []
            for row in result:
                if isinstance(row, (list, tuple)):
                    final_result.append([float(x) for x in row])
                else:
                    final_result.append([float(row)])
            return final_result
        except Exception as e:
            logger.error(f"文本编码失败: {e}")
            raise
    
    def get_model(self) -> SentenceTransformer:
        """获取模型实例"""
        if self._model is None:
            raise RuntimeError("嵌入模型未初始化")
        return self._model

# 全局单例实例
embedding_service = EmbeddingService()