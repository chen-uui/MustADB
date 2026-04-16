"""
Weaviate向量数据库服务
专为大规模PDF文档处理设计
支持高性能语义搜索和问答系统
"""

import os
import uuid
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

import weaviate
from .api_errors import (
    from_pdf_extraction_result,
    pdf_parse_error,
    processing_error_result,
    sanitize_error_detail,
    text_chunk_error,
    vector_index_error,
)

# 导入统一配置
from .pdf_utils import GlobalConfig

# 配置日志
logger = logging.getLogger(__name__)

DEFAULT_WEAVIATE_COLLECTION_NAME = "PDFDocument"


def resolve_collection_name(collection_name: Optional[str] = None) -> str:
    name = str(collection_name or os.getenv("WEAVIATE_COLLECTION_NAME", "")).strip()
    return name or DEFAULT_WEAVIATE_COLLECTION_NAME

@dataclass
class WeaviateConfig:
    """Weaviate配置 - 使用全局配置"""
    url: str = GlobalConfig.WEAVIATE_URL
    collection_name: str = DEFAULT_WEAVIATE_COLLECTION_NAME
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = GlobalConfig.CHUNK_SIZE
    chunk_overlap: int = GlobalConfig.CHUNK_OVERLAP
    batch_size: int = 50  # 减少批处理大小以防止超时
    timeout: int = 120  # 增加超时时间以处理复杂查询
    max_connections: int = 10  # 减少最大连接数以避免资源竞争

class WeaviateVectorService:
    """Weaviate向量数据库服务"""
    
    def __init__(self, collection_name: Optional[str] = None):
        # 使用统一的嵌入服务和连接管理
        from .embedding_service import embedding_service
        from .weaviate_connection import weaviate_connection
        
        self.embedding_service = embedding_service
        self.weaviate_connection = weaviate_connection
        self.collection_name = resolve_collection_name(collection_name)
        
    def test_connection(self) -> bool:
        """测试Weaviate连接"""
        return self.weaviate_connection.test_connection()
    
    def create_collection_if_not_exists(self, collection_name: Optional[str] = None):
        """创建集合（如果不存在）"""
        try:
            collection_name = resolve_collection_name(collection_name or self.collection_name)
            client = self.weaviate_connection.get_client()
            if client is None:
                raise RuntimeError("无法获取Weaviate客户端连接")
            
            # 检查集合是否存在
            if client.collections.exists(collection_name):
                logger.info(f"集合 {collection_name} 已存在")
                return
            
            # 创建集合
            client.collections.create(
                name=collection_name,
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
                vector_index_config=weaviate.classes.config.Configure.VectorIndex.hnsw(
                    distance_metric=weaviate.classes.config.VectorDistances.COSINE
                ),
                properties=[
                    weaviate.classes.config.Property(
                        name="content",
                        data_type=weaviate.classes.config.DataType.TEXT
                    ),
                    weaviate.classes.config.Property(
                        name="document_id",
                        data_type=weaviate.classes.config.DataType.TEXT
                    ),
                    weaviate.classes.config.Property(
                        name="title",
                        data_type=weaviate.classes.config.DataType.TEXT
                    ),
                    weaviate.classes.config.Property(
                        name="page_number",
                        data_type=weaviate.classes.config.DataType.INT
                    ),
                    weaviate.classes.config.Property(
                        name="chunk_index",
                        data_type=weaviate.classes.config.DataType.INT
                    ),
                ]
            )
            logger.info(f"成功创建集合: {collection_name}")
            
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            raise
    
    def add_documents_batch(self, documents: List[Dict], collection_name: Optional[str] = None):
        """批量添加文档"""
        try:
            collection_name = resolve_collection_name(collection_name or self.collection_name)
            client = self.weaviate_connection.get_client()
            if client is None:
                raise RuntimeError("无法获取Weaviate客户端连接")
            collection = client.collections.get(collection_name)
            
            # 准备批量数据
            batch_data = []
            texts = [doc['content'] for doc in documents]
            
            # 使用统一的嵌入服务生成向量
            logger.info(f"为 {len(texts)} 个文档生成嵌入向量...")
            embeddings = self.embedding_service.encode(texts)
            
            for doc, embedding in zip(documents, embeddings):
                # 使用DataObject类正确插入带向量的文档
                batch_data.append(weaviate.classes.data.DataObject(
                    properties={
                        "content": doc['content'],
                        "document_id": doc['document_id'],
                        "title": doc.get('title', ''),
                        "page_number": doc.get('page_number', 0),
                        "chunk_index": doc.get('chunk_index', 0),
                    },
                    vector=embedding
                ))
            
            # 批量插入
            logger.info(f"批量插入 {len(batch_data)} 个文档...")
            response = collection.data.insert_many(batch_data)
            
            if response.has_errors:
                for error in response.errors:
                    logger.error(f"插入错误: {error}")
            else:
                logger.info(f"成功插入 {len(batch_data)} 个文档")
                
        except Exception as e:
            logger.error(f"批量添加文档失败: {e}")
            raise
    
    def add_document_batch(self, 
                          chunks: List[Dict[str, Any]], 
                          document_id: str,
                          document_title: str,
                          metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """批量添加单个文档的分块"""
        try:
            client = self.weaviate_connection.get_client()
            if client is None:
                raise RuntimeError("无法获取Weaviate客户端连接")
            collection = client.collections.get(self.collection_name)
            
            # 准备批量数据
            batch_data = []
            texts = [chunk['content'] for chunk in chunks]
            
            # 使用统一的嵌入服务生成向量
            logger.info(f"为文档 {document_id} 的 {len(texts)} 个分块生成嵌入向量...")
            embeddings = self.embedding_service.encode(texts)
            
            chunk_ids = []
            for chunk, embedding in zip(chunks, embeddings):
                chunk_id = f"{document_id}_{chunk.get('chunk_index', 0)}"
                chunk_ids.append(chunk_id)
                
                # 使用DataObject类正确插入带向量的文档
                batch_data.append(weaviate.classes.data.DataObject(
                    properties={
                        "content": chunk['content'],
                        "document_id": document_id,
                        "title": document_title,
                        "page_number": chunk.get('page_number', 0),
                        "chunk_index": chunk.get('chunk_index', 0),
                    },
                    vector=embedding
                ))
            
            # 批量插入
            logger.info(f"批量插入文档 {document_id} 的 {len(batch_data)} 个分块...")
            response = collection.data.insert_many(batch_data)
            
            if response.has_errors:
                for error in response.errors:
                    logger.error(f"插入错误: {error}")
                raise Exception(f"插入文档 {document_id} 失败")
            else:
                logger.info(f"成功插入文档 {document_id} 的 {len(batch_data)} 个分块")
                return chunk_ids
                
        except Exception as e:
            logger.error(f"批量添加文档 {document_id} 失败: {e}")
            raise
    
    def semantic_search(self, query: str, limit: int = 10, collection_name: Optional[str] = None) -> List[Dict]:
        """语义搜索"""
        try:
            # 使用统一的嵌入服务
            query_vector = self.embedding_service.encode([query])[0]
            
            collection_name = resolve_collection_name(collection_name or self.collection_name)
            client = self.weaviate_connection.get_client()
            if client is None:
                raise RuntimeError("无法获取Weaviate客户端连接")
            collection = client.collections.get(collection_name)
            
            response = collection.query.near_vector(
                near_vector=query_vector,
                limit=limit,
                include_vector=True,
                return_metadata=weaviate.classes.query.MetadataQuery(distance=True)
            )
            
            results = []
            for obj in response.objects:
                results.append({
                    'content': obj.properties.get('content', ''),
                    'document_id': obj.properties.get('document_id'),
                    'page_number': obj.properties.get('page_number'),
                    'chunk_index': obj.properties.get('chunk_index'),
                    'distance': obj.metadata.distance if obj.metadata else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return []
    
    def delete_documents_by_id(self, document_id: str, collection_name: Optional[str] = None):
        """根据文档ID删除文档"""
        try:
            collection_name = resolve_collection_name(collection_name or self.collection_name)
            client = self.weaviate_connection.get_client()
            if client is None:
                raise RuntimeError("无法获取Weaviate客户端连接")
            collection = client.collections.get(collection_name)
            
            # 删除指定文档ID的所有分块
            where_filter = weaviate.classes.query.Filter.by_property("document_id").equal(document_id)
            result = collection.data.delete_many(where=where_filter)
            
            logger.info(f"删除文档 {document_id} 的 {result.successful} 个分块")
            
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise
    
    def delete_document(self, document_id: str, collection_name: Optional[str] = None):
        """Backward-compatible alias used by existing maintenance flows."""
        return self.delete_documents_by_id(document_id, collection_name)

    def delete_all_documents(self, collection_name: Optional[str] = None):
        """删除所有文档分块"""
        try:
            collection_name = resolve_collection_name(collection_name or self.collection_name)
            client = self.weaviate_connection.get_client()
            if client is None:
                raise RuntimeError("无法获取Weaviate客户端连接")
            
            # 删除并重建集合是最可靠的方法
            if client.collections.exists(collection_name):
                logger.info(f"删除集合 {collection_name}")
                client.collections.delete(collection_name)
            
            # 重建集合
            logger.info(f"重建集合 {collection_name}")
            self.create_collection_if_not_exists(collection_name)
            
            logger.info(f"成功删除并重建集合 {collection_name}")
            
        except Exception as e:
            logger.error(f"删除所有文档失败: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            client = self.weaviate_connection.get_client()
            if client is None:
                raise RuntimeError("无法获取Weaviate客户端连接")
            collection = client.collections.get(self.collection_name)
            
            # 获取集合中的对象数量
            total_objects = collection.aggregate.over_all(total_count=True).total_count
            
            return {
                "total_chunks": total_objects,
                "collection_name": self.collection_name,
                "weaviate_status": "connected"
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {
                "total_chunks": 0,
                "collection_name": self.collection_name,
                "weaviate_status": "error",
                "error": str(e)
            }
    
    def get_all_chunks(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有分块数据"""
        try:
            client = self.weaviate_connection.get_client()
            if client is None:
                raise RuntimeError("无法获取Weaviate客户端连接")
            collection = client.collections.get(self.collection_name)
            
            # 获取分块数据
            response = collection.query.fetch_objects(
                limit=limit,
                offset=offset
            )
            
            chunks = []
            for obj in response.objects:
                chunks.append({
                    "id": str(obj.uuid),
                    "content": obj.properties.get("content", ""),
                    "document_id": obj.properties.get("document_id", ""),
                    "page_number": obj.properties.get("page_number", 0),
                    "chunk_index": obj.properties.get("chunk_index", 0)
                })
            
            return chunks
        except Exception as e:
            logger.error(f"获取分块数据失败: {e}")
            return []
    
    def get_document_chunks(self, document_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取特定文档的分块数据"""
        try:
            client = self.weaviate_connection.get_client()
            if client is None:
                raise RuntimeError("无法获取Weaviate客户端连接")
            collection = client.collections.get(self.collection_name)
            
            # 查询特定文档的分块
            response = collection.query.fetch_objects(
                filters=weaviate.classes.query.Filter.by_property("document_id").equal(document_id),
                limit=limit,
                offset=offset
            )
            
            chunks = []
            for obj in response.objects:
                chunks.append({
                    "id": str(obj.uuid),
                    "content": obj.properties.get("content", ""),
                    "document_id": obj.properties.get("document_id", ""),
                    "page_number": obj.properties.get("page_number", 0),
                    "chunk_index": obj.properties.get("chunk_index", 0)
                })
            
            return chunks
        except Exception as e:
            logger.error(f"获取文档分块失败: {e}")
            return []
    
    def hybrid_search(self, query: str, limit: int = 10) -> List[Dict]:
        """混合搜索"""
        try:
            # 导入混合搜索服务
            from .hybrid_search_service import hybrid_search_service
            results = hybrid_search_service.hybrid_search(query, limit)
            
            # 转换结果格式
            converted_results = []
            for result in results:
                converted_results.append({
                    'content': result.content,
                    'score': result.score,
                    'document_id': result.document_id,
                    'page_number': result.page,
                    'title': result.title,
                    'chunk_index': result.chunk_index
                })
            return converted_results
        except Exception as e:
            logger.error(f"混合搜索失败: {e}")
            return []
    
    def search_similar(self, query: str, n_results: int = 5) -> List[Dict]:
        """语义搜索"""
        return self.semantic_search(query, n_results)
    
    def close(self):
        """关闭服务"""
        try:
            if hasattr(self.weaviate_connection, 'close_connection'):
                self.weaviate_connection.close_connection()
            elif hasattr(self.weaviate_connection, 'close'):
                self.weaviate_connection.close()
        except Exception as e:
            logger.error(f"关闭服务失败: {e}")

class WeaviateDocumentProcessor:
    """基于Weaviate的文档处理器"""
    
    def __init__(self, config: Optional[WeaviateConfig] = None):
        self.config = config or WeaviateConfig()
        self.config.collection_name = resolve_collection_name(self.config.collection_name)
        self.vector_service = WeaviateVectorService(collection_name=self.config.collection_name)
    
    def add_document_batch(self, 
                          chunks: List[Dict[str, Any]], 
                          document_id: str,
                          document_title: str,
                          metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """批量添加文档"""
        return self.vector_service.add_document_batch(
            chunks=chunks,
            document_id=document_id,
            document_title=document_title,
            metadata=metadata
        )
    
    def process_documents_batch(self, 
                               pdf_paths: List[str],
                               max_workers: int = 2,
                               metadata_list: Optional[List[Dict[str, Any]]] = None,
                               chunk_size: Optional[int] = None,
                               chunk_overlap: Optional[int] = None) -> List[Dict[str, Any]]:
        """批量处理PDF文档
        
        Args:
            pdf_paths: PDF文件路径列表
            max_workers: 最大工作线程数
            metadata_list: 每个文档的元数据列表
            
        Returns:
            处理结果列表
        """
        from .pdf_utils import PDFUtils
        
        results = []
        total_documents = len(pdf_paths)
        processed_documents = 0
        
        logger.info(f"开始批量处理 {total_documents} 个文档")
        
        for i, pdf_path in enumerate(pdf_paths):
            try:
                file_name = os.path.basename(pdf_path)
                logger.info(f"正在处理文档 {i+1}/{total_documents}: {file_name}")
                
                # 获取元数据
                metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
                
                # 提取文本和分块
                # 处理可能为None的参数
                actual_chunk_size = chunk_size if chunk_size is not None else GlobalConfig.CHUNK_SIZE
                actual_chunk_overlap = chunk_overlap if chunk_overlap is not None else GlobalConfig.CHUNK_OVERLAP
                extraction_result = PDFUtils.extract_text_and_chunks(pdf_path, actual_chunk_size, actual_chunk_overlap)
                
                if not extraction_result['success']:
                    error_msg = extraction_result.get('error', '提取失败')
                    logger.error(f"文档 {file_name} 提取失败: {error_msg}")
                    results.append({
                        "status": "error",
                        "error": error_msg,
                        "file_path": pdf_path,
                        "file_name": file_name
                    })
                    processed_documents += 1
                    continue
                
                # 处理分块 - 转换为Weaviate需要的格式
                raw_chunks = extraction_result['chunks']
                document_id = str(metadata.get('id', f"doc_{i}"))
                document_title = metadata.get('title', file_name)
                
                logger.info(f"文档 {file_name} 提取成功，共 {len(raw_chunks)} 个分块")
                
                # 转换chunks格式为Weaviate需要的格式
                weaviate_chunks = []
                for chunk in raw_chunks:
                    weaviate_chunks.append({
                        'content': chunk['chunk_text'],
                        'length': chunk['chunk_length'],
                        'sentences': len(chunk['chunk_text'].split('.')),
                        'page_number': chunk['page_number'],
                        'chunk_index': chunk.get('chunk_index', 0)  # 重要：保留chunk_index用于正确去重
                    })
                
                # 添加文档到Weaviate
                chunk_ids = self.add_document_batch(
                    chunks=weaviate_chunks,
                    document_id=document_id,
                    document_title=document_title,
                    metadata=metadata
                )
                
                results.append({
                    "status": "success",
                    "total_chunks": len(weaviate_chunks),
                    "total_pages": extraction_result.get('total_pages', 0),
                    "file_path": pdf_path,
                    "file_name": file_name,
                    "document_id": document_id
                })
                
                processed_documents += 1
                logger.info(f"文档 {file_name} 处理完成，进度: {processed_documents}/{total_documents}")
                
            except Exception as e:
                file_name = os.path.basename(pdf_path)
                logger.error(f"处理文档 {file_name} 失败: {str(e)}")
                results.append({
                    "status": "error",
                    "error": str(e),
                    "file_path": pdf_path,
                    "file_name": file_name
                })
                processed_documents += 1
        
        logger.info(f"批量处理完成，成功处理 {processed_documents}/{total_documents} 个文档")
        return results
    
    def process_single_document(self, 
                              pdf_path: str,
                              document_id: Optional[str] = None,
                              metadata: Optional[Dict[str, Any]] = None,
                              chunk_size: Optional[int] = None,
                              chunk_overlap: Optional[int] = None) -> Dict[str, Any]:
        """处理单个PDF文档"""
        try:
            from .pdf_utils import PDFUtils, GlobalConfig
            
            # 使用传入的参数，如果没有则使用全局配置
            if chunk_size is None:
                chunk_size = GlobalConfig.CHUNK_SIZE
            if chunk_overlap is None:
                chunk_overlap = GlobalConfig.CHUNK_OVERLAP
            
            # 提取文本和分块
            # 处理可能为None的参数
            actual_chunk_size = chunk_size if chunk_size is not None else GlobalConfig.CHUNK_SIZE
            actual_chunk_overlap = chunk_overlap if chunk_overlap is not None else GlobalConfig.CHUNK_OVERLAP
            extraction_result = PDFUtils.extract_text_and_chunks(pdf_path, actual_chunk_size, actual_chunk_overlap)
            
            if not extraction_result['success']:
                return {
                    "status": "error",
                    "error": extraction_result.get('error', '提取失败')
                }
            
            # 处理分块 - 转换为Weaviate需要的格式
            raw_chunks = extraction_result['chunks']
            doc_id = document_id or str(uuid.uuid4())
            title = metadata.get('title', os.path.basename(pdf_path)) if metadata else os.path.basename(pdf_path)
            
            # 转换chunks格式为Weaviate需要的格式
            weaviate_chunks = []
            for chunk in raw_chunks:
                weaviate_chunks.append({
                        'content': chunk['chunk_text'],
                        'length': chunk['chunk_length'],
                        'sentences': len(chunk['chunk_text'].split('.')),
                        'page_number': chunk['page_number'],
                        'chunk_index': chunk.get('chunk_index', 0)  # 重要：保留chunk_index用于正确去重
                    })
            
            # 添加文档到Weaviate
            chunk_ids = self.add_document_batch(
                chunks=weaviate_chunks,
                document_id=doc_id,
                document_title=title,
                metadata=metadata
            )
            
            return {
                "status": "success",
                "total_chunks": len(weaviate_chunks),
                "total_pages": extraction_result.get('total_pages', 0),
                "document_id": doc_id
            }
            
        except Exception as e:
            logger.error(f"处理单个文档 {pdf_path} 失败: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def search_documents(self, 
                        query: str,
                        n_results: int = 5,
                        search_type: str = "similarity") -> List[Dict[str, Any]]:
        """搜索文档"""
        if search_type == "hybrid":
            return self.vector_service.hybrid_search(query, n_results)
        else:
            return self.vector_service.search_similar(query, n_results)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.vector_service.get_collection_stats()
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            # 获取Weaviate统计
            weaviate_stats = self.vector_service.get_collection_stats()
            
            # 构建系统统计信息
            stats = {
                "weaviate_status": "connected" if weaviate_stats else "disconnected",
                "total_chunks": weaviate_stats.get("total_chunks", 0) if weaviate_stats else 0,
                "collection_name": self.vector_service.collection_name
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取系统统计信息失败: {e}")
            return {
                "weaviate_status": "error",
                "error": str(e),
                "total_chunks": 0,
                "collection_name": self.vector_service.collection_name
            }
    
    def get_all_chunks(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取所有分块数据"""
        return self.vector_service.get_all_chunks(limit=limit, offset=offset)
    
    def get_document_chunks(self, document_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取特定文档的分块数据"""
        return self.vector_service.get_document_chunks(document_id, limit=limit, offset=offset)
    
    def close(self):
        """关闭服务"""
        self.vector_service.close()

# 使用示例
if __name__ == "__main__":
    # 测试Weaviate连接
    try:
        service = WeaviateVectorService()
        stats = service.get_collection_stats()
        print(f"Weaviate统计信息: {stats}")
        
        # 测试搜索
        results = service.semantic_search("测试", limit=2)
        print(f"搜索结果: {len(results)} 条")
        
    except Exception as e:
        print(f"错误: {e}")
