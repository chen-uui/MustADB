import os
import uuid
import json
import logging
from pathlib import Path
import requests
from typing import List, Dict, Any
from django.core.management.base import BaseCommand
from pdf_processor.models import PDFDocument

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '使用UUID同步所有PDF文档到Weaviate'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verify-only',
            action='store_true',
            help='仅验证同步结果'
        )

    def handle(self, *args, **options):
        # 使用统一配置
        from pdf_processor.pdf_utils import GlobalConfig
        
        self.weaviate_url = GlobalConfig.WEAVIATE_URL
        self.class_name = "PDFDocument"
        self.headers = {"Content-Type": "application/json"}
        
        if options['verify_only']:
            self.verify_sync()
            return
            
        self.sync_all_documents()

    def clear_weaviate_documents(self) -> bool:
        """清除Weaviate中的所有文档"""
        try:
            # 获取所有文档的UUID
            query = {
                "query": f"""
                {{
                    Get {{
                        {self.class_name} {{
                            _additional {{ id }}
                        }}
                    }}
                }}
                """
            }
            
            response = requests.post(
                f"{self.weaviate_url}/v1/graphql",
                json=query,
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get("data", {}).get("Get", {}).get(self.class_name, [])
                
                # 删除每个文档
                for doc in documents:
                    doc_id = doc.get("_additional", {}).get("id")
                    if doc_id:
                        delete_url = f"{self.weaviate_url}/v1/objects/{self.class_name}/{doc_id}"
                        requests.delete(delete_url)
                        
                self.stdout.write(
                    self.style.SUCCESS(f'已清除 {len(documents)} 个Weaviate文档')
                )
                return True
            else:
                self.stdout.write(
                    self.style.WARNING('Weaviate中没有文档需要清除')
                )
                return True
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'清除Weaviate文档失败: {e}')
            )
            return False

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """从PDF提取文本 - 使用统一的PyMuPDF处理"""
        try:
            # 使用统一的PDF处理工具
            from pdf_processor.pdf_utils import PDFUtils
            
            extraction_result = PDFUtils.extract_text_and_metadata(pdf_path)
            
            if extraction_result['success']:
                total_pages = extraction_result['metadata'].get('total_pages', 0)
                self.stdout.write(
                    self.style.SUCCESS(f'  成功处理 {total_pages} 页')
                )
                return extraction_result['text']
            else:
                self.stdout.write(
                    self.style.ERROR(f'PDF处理失败: {extraction_result.get("error", "未知错误")}')
                )
                return ""
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'提取PDF文本失败 {pdf_path}: {e}')
            )
            return ""

    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """按token分块（优先tiktoken，否则字符近似）。"""
        from pdf_processor.pdf_utils import GlobalConfig, PDFUtils
        if chunk_size is None:
            chunk_size = GlobalConfig.CHUNK_SIZE
        if overlap is None:
            overlap = GlobalConfig.CHUNK_OVERLAP
        if not text:
            return []

        # 限制文本长度，避免超大文件导致内存问题（按字符截断）
        max_text_length = 1000000
        if len(text) > max_text_length:
            self.stdout.write(
                self.style.WARNING(f'  文本过长，截断到 {max_text_length} 字符')
            )
            text = text[:max_text_length]

        return PDFUtils.chunk_plain_text(text, chunk_size=chunk_size, overlap=overlap)

    def upload_document_chunks(self, document: PDFDocument, text: str, chunks: List[str]) -> bool:
        """上传文档分块到Weaviate"""
        try:
            # 使用Django文档的UUID作为document_id
            document_uuid = str(document.id)
            
            # 批量上传
            batch_objects = []
            
            for i, chunk_text in enumerate(chunks):
                chunk_uuid = str(uuid.uuid4())
                
                obj_data = {
                    "class": self.class_name,
                    "id": chunk_uuid,
                    "properties": {
                        "chunk_text": chunk_text,
                        "document_id": document_uuid,
                        "document_title": document.title,
                        "chunk_index": i,
                        "metadata": json.dumps({
                            "filename": document.filename,
                            "title": document.title,
                            "authors": document.authors or '',
                            "year": str(document.year) if document.year else '',
                            "journal": document.journal or '',
                            "doi": document.doi or '',
                            "abstract": document.abstract or '',
                            "keywords": document.keywords or '',
                            "category": document.category,
                            "upload_date": str(document.upload_date),
                            "file_size": document.file_size
                        })
                    }
                }
                
                batch_objects.append(obj_data)
            
            # 使用批量API上传
            batch_url = f"{self.weaviate_url}/v1/batch/objects"
            response = requests.post(
                batch_url,
                json={"objects": batch_objects},
                headers=self.headers
            )
            
            if response.status_code in [200, 201]:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'成功上传文档 {document.title} 的 {len(chunks)} 个分块'
                    )
                )
                return True
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'上传文档分块失败: {response.status_code} - {response.text}'
                    )
                )
                return False
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'上传文档分块异常: {e}')
            )
            return False

    def sync_all_documents(self):
        """同步所有文档到Weaviate"""
        try:
            self.stdout.write(self.style.SUCCESS('[恢复] 开始同步文档到Weaviate...'))
            
            # 清除现有文档
            self.clear_weaviate_documents()
            
            # 获取所有PDF文档
            documents = PDFDocument.objects.all()
            total_docs = documents.count()
            
            if total_docs == 0:
                self.stdout.write(
                    self.style.WARNING('没有找到PDF文档')
                )
                return
            
            self.stdout.write(
                self.style.SUCCESS(f'开始同步 {total_docs} 个文档到Weaviate...')
            )
            
            success_count = 0
            total_chunks = 0
            
            # 设置文件大小限制（50MB）
            max_file_size = 50 * 1024 * 1024  # 50MB
            
            for idx, doc in enumerate(documents, 1):
                try:
                    self.stdout.write(
                        self.style.SUCCESS(f'\n正在处理文档 {idx}/{total_docs}: {doc.filename}')
                    )
                    
                    # 检查文件是否存在和大小
                    if not os.path.exists(doc.file_path):
                        self.stdout.write(
                            self.style.WARNING(f'  文件不存在: {doc.file_path}')
                        )
                        continue
                    
                    # 检查文件大小
                    file_size = os.path.getsize(doc.file_path)
                    if file_size > max_file_size:
                        self.stdout.write(
                            self.style.WARNING(f'  文件过大({file_size//1024//1024}MB)，跳过: {doc.filename}')
                        )
                        continue
                    
                    # 提取文本
                    text = self.extract_text_from_pdf(doc.file_path)
                    if not text:
                        self.stdout.write(
                            self.style.WARNING(f'  无法从文档提取文本: {doc.filename}')
                        )
                        continue
                    
                    # 分块
                    chunks = self.chunk_text(text)
                    if not chunks:
                        self.stdout.write(
                            self.style.WARNING(f'  无法为文档生成分块: {doc.filename}')
                        )
                        continue
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'  生成了 {len(chunks)} 个分块')
                    )
                    
                    # 上传到Weaviate
                    if self.upload_document_chunks(doc, text, chunks):
                        success_count += 1
                        total_chunks += len(chunks)
                        
                        # 更新处理状态
                        doc.processed = True
                        doc.processing_error = None
                        doc.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'  [成功] 文档处理完成')
                        )
                    else:
                        doc.processed = False
                        doc.processing_error = "Weaviate同步失败"
                        doc.save()
                        
                        self.stdout.write(
                            self.style.ERROR(f'  [失败] 文档处理失败')
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  [失败] 处理文档 {doc.filename} 失败: {e}')
                    )
                    doc.processed = False
                    doc.processing_error = str(e)
                    doc.save()
                
                # 每处理完一个文档清理内存
                import gc
                gc.collect()
                self.stdout.flush()
            
            self.stdout.write(
                self.style.SUCCESS(f'\n🎉 同步完成!')
            )
            self.stdout.write(
                self.style.SUCCESS(f'[统计] 总文档数: {total_docs}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'[成功] 成功文档: {success_count}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'[文档] 总分块数: {total_chunks}')
            )
            
            # 验证同步结果
            self.verify_sync()
            
            # 最终内存清理
            import gc
            gc.collect()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'同步过程失败: {e}')
            )

    def verify_sync(self):
        """验证同步结果"""
        try:
            # 查询Weaviate中的文档统计
            query = {
                "query": f"""
                {{
                    Aggregate {{
                        {self.class_name} {{
                            meta {{
                                count
                            }}
                        }}
                    }}
                }}
                """
            }
            
            response = requests.post(
                f"{self.weaviate_url}/v1/graphql",
                json=query,
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                count = data.get("data", {}).get("Aggregate", {}).get(self.class_name, [{}])[0].get("meta", {}).get("count", 0)
                
                django_count = PDFDocument.objects.count()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Weaviate总分块数: {count}')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Django总文档数: {django_count}')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'同步验证: {"成功" if count > 0 else "失败"}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('无法连接到Weaviate')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'验证失败: {e}')
            )
