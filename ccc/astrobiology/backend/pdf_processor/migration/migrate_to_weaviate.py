"""
ChromaDB到Weaviate的迁移脚本
将现有PDF文档数据从ChromaDB迁移到Weaviate
"""

import os
import sys
import json
import logging
from pathlib import Path
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
from pdf_processor.models import PDFDocument
from pdf_processor.enhanced_services import EnhancedVectorService, ProcessingConfig
from pdf_processor.weaviate_services import WeaviateVectorService, WeaviateConfig

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChromaToWeaviateMigrator:
    """ChromaDB到Weaviate迁移器"""
    
    def __init__(self):
        # 初始化ChromaDB服务
        self.chroma_service = EnhancedVectorService()
        
        # 初始化Weaviate服务
        self.weaviate_config = WeaviateConfig()
        self.weaviate_service = WeaviateVectorService(self.weaviate_config)
    
    def get_chroma_stats(self) -> dict:
        """获取ChromaDB统计信息"""
        try:
            stats = self.chroma_service.get_collection_stats()
            logger.info(f"ChromaDB统计: {stats}")
            return stats
        except Exception as e:
            logger.error(f"获取ChromaDB统计失败: {e}")
            return {}
    
    def get_weaviate_stats(self) -> dict:
        """获取Weaviate统计信息"""
        try:
            stats = self.weaviate_service.get_collection_stats()
            logger.info(f"Weaviate统计: {stats}")
            return stats
        except Exception as e:
            logger.error(f"获取Weaviate统计失败: {e}")
            return {}
    
    def migrate_all_documents(self) -> dict:
        """迁移所有文档"""
        try:
            # 获取所有已处理的PDF文档
            pdf_docs = PDFDocument.objects.filter(processed=True)
            total_docs = pdf_docs.count()
            
            logger.info(f"开始迁移 {total_docs} 个文档")
            
            if total_docs == 0:
                logger.warning("没有找到已处理的PDF文档")
                return {"status": "no_documents", "count": 0}
            
            # 获取ChromaDB中的所有数据
            chroma_stats = self.get_chroma_stats()
            if chroma_stats.get("total_documents", 0) == 0:
                logger.warning("ChromaDB中没有向量数据")
                return {"status": "no_chroma_data", "count": 0}
            
            # 迁移每个文档
            migrated_count = 0
            failed_count = 0
            
            for doc in pdf_docs:
                try:
                    result = self.migrate_single_document(doc)
                    if result["success"]:
                        migrated_count += 1
                        logger.info(f"[成功] 迁移成功: {doc.title}")
                    else:
                        failed_count += 1
                        logger.error(f"[失败] 迁移失败: {doc.title} - {result['error']}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"[失败] 迁移异常: {doc.title} - {e}")
            
            # 返回迁移结果
            result = {
                "status": "completed",
                "total_documents": total_docs,
                "migrated": migrated_count,
                "failed": failed_count,
                "chroma_stats": chroma_stats,
                "weaviate_stats": self.get_weaviate_stats()
            }
            
            logger.info(f"迁移完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"迁移过程失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def migrate_single_document(self, pdf_doc: PDFDocument) -> dict:
        """迁移单个文档"""
        try:
            # 获取文档的所有分块
            from chromadb import QueryResult
            
            # 构建查询条件
            filter_dict = {"document_id": str(pdf_doc.id)}
            
            # 获取ChromaDB中的数据
            chroma_results = self.chroma_service.search_similar(
                query="",  # 空查询获取所有分块
                n_results=10000,  # 获取所有分块
                filter_dict=filter_dict
            )
            
            if not chroma_results:
                return {"success": False, "error": "没有找到分块数据"}
            
            # 准备迁移数据
            chunks = []
            for result in chroma_results:
                chunk = {
                    "text": result["content"],
                    "length": result["metadata"].get("chunk_length", 0),
                    "sentences": result["metadata"].get("sentences_count", 0)
                }
                chunks.append(chunk)
            
            # 添加到Weaviate
            chunk_ids = self.weaviate_service.add_document_batch(
                chunks=chunks,
                document_id=str(pdf_doc.id),
                document_title=pdf_doc.title,
                metadata={
                    "title": pdf_doc.title,
                    "category": pdf_doc.category,
                    "upload_date": str(pdf_doc.upload_date),
                    "file_path": pdf_doc.file_path,
                    "page_count": pdf_doc.page_count
                }
            )
            
            return {
                "success": True,
                "document_id": str(pdf_doc.id),
                "chunks_migrated": len(chunks),
                "chunk_ids": chunk_ids
            }
            
        except Exception as e:
            logger.error(f"迁移单个文档失败: {e}")
            return {"success": False, "error": str(e)}
    
    def verify_migration(self) -> dict:
        """验证迁移结果"""
        try:
            chroma_stats = self.get_chroma_stats()
            weaviate_stats = self.get_weaviate_stats()
            
            # 比较统计信息
            chroma_total = chroma_stats.get("total_documents", 0)
            weaviate_total = weaviate_stats.get("total_chunks", 0)
            
            # 验证文档数量
            pdf_docs = PDFDocument.objects.filter(processed=True)
            expected_docs = pdf_docs.count()
            
            verification = {
                "status": "verified",
                "chroma_total_chunks": chroma_total,
                "weaviate_total_chunks": weaviate_total,
                "expected_documents": expected_docs,
                "weaviate_unique_docs": weaviate_stats.get("unique_documents", 0),
                "consistency_check": weaviate_stats.get("unique_documents", 0) == expected_docs,
                "data_integrity": chroma_total == weaviate_total
            }
            
            logger.info(f"验证结果: {verification}")
            return verification
            
        except Exception as e:
            logger.error(f"验证失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def cleanup_chroma(self) -> dict:
        """清理ChromaDB数据（可选）"""
        try:
            # 警告：此操作会删除所有ChromaDB数据
            logger.warning("[警告] 准备清理ChromaDB数据...")
            
            # 获取ChromaDB路径
            chroma_path = Path(__file__).parent.parent.parent / "chroma_db"
            
            if chroma_path.exists():
                import shutil
                # 备份ChromaDB
                backup_path = chroma_path.parent / "chroma_db_backup"
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                
                shutil.copytree(chroma_path, backup_path)
                logger.info(f"[成功] ChromaDB已备份到: {backup_path}")
                
                # 清理ChromaDB
                shutil.rmtree(chroma_path)
                logger.info("[成功] ChromaDB已清理")
                
                return {
                    "status": "cleaned",
                    "backup_path": str(backup_path),
                    "original_path": str(chroma_path)
                }
            else:
                logger.warning("ChromaDB目录不存在")
                return {"status": "not_found", "path": str(chroma_path)}
                
        except Exception as e:
            logger.error(f"清理失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """关闭连接"""
        try:
            self.chroma_service.close()
            self.weaviate_service.close()
            logger.info("所有连接已关闭")
        except Exception as e:
            logger.error(f"关闭连接失败: {e}")

def main():
    """主函数"""
    try:
        print("🚀 开始ChromaDB到Weaviate迁移")
        print("=" * 50)
        
        # 创建迁移器
        migrator = ChromaToWeaviateMigrator()
        
        # 显示当前状态
        print("[统计] 当前状态:")
        chroma_stats = migrator.get_chroma_stats()
        weaviate_stats = migrator.get_weaviate_stats()
        
        print(f"   ChromaDB: {chroma_stats.get('total_documents', 0)} 个分块")
        print(f"   Weaviate: {weaviate_stats.get('total_chunks', 0)} 个分块")
        
        # 执行迁移
        result = migrator.migrate_all_documents()
        
        # 显示结果
        print("\n📈 迁移结果:")
        print(f"   总文档数: {result.get('total_documents', 0)}")
        print(f"   成功迁移: {result.get('migrated', 0)}")
        print(f"   失败: {result.get('failed', 0)}")
        
        # 验证迁移
        print("\n🔍 验证迁移结果...")
        verification = migrator.verify_migration()
        
        if verification.get("consistency_check"):
            print("[成功] 文档数量一致性验证通过")
        else:
            print("[警告] 文档数量不一致，请检查")
        
        if verification.get("data_integrity"):
            print("[成功] 数据完整性验证通过")
        else:
            print("[警告] 数据完整性检查失败")
        
        # 询问是否清理ChromaDB
        print("\n🗑️ 是否清理ChromaDB数据？(y/N)")
        response = input().strip().lower()
        
        if response == 'y':
            cleanup_result = migrator.cleanup_chroma()
            print(f"清理结果: {cleanup_result}")
        
        print("\n🎉 迁移完成!")
        
    except KeyboardInterrupt:
        print("\n[失败] 用户中断")
    except Exception as e:
        print(f"\n[失败] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            migrator.close()
        except:
            pass

if __name__ == "__main__":
    main()