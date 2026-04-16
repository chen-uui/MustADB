"""
Weaviate API瑙嗗浘
涓庣幇鏈夊墠绔吋瀹圭殑Weaviate鐗堟湰API
"""

import os
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from typing import Type, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from rest_framework.serializers import Serializer
    from .serializers import PDFDocumentSerializer, PDFUploadSerializer
from django.http import FileResponse

from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
import threading

from .api_errors import (
    build_error_payload,
    clear_document_processing_error,
    database_write_error,
    error_response,
    file_save_error,
    from_pdf_extraction_result,
    from_processing_result,
    remember_document_processing_error,
    sanitize_error_detail,
)
from .models import PDFDocument, DocumentChunk
from .serializers import PDFDocumentSerializer, PDFUploadSerializer
from .services.upload_storage_service import PDF_LIBRARY, UploadStorageService
from .weaviate_services import WeaviateDocumentProcessor
from .pdf_utils import GlobalConfig
from .confidence_calculator import confidence_calculator

# 杩涚▼绾у崟渚嬪鐞嗗櫒锛岄伩鍏嶆瘡璇锋眰閲嶅缓/鍏抽棴杩炴帴
_GLOBAL_PROCESSOR = None
_PROCESSING_LOCK = False
_CANCEL_REQUESTED = False

logger = logging.getLogger(__name__)

class WeaviatePDFViewSet(viewsets.ModelViewSet):
    """Weaviate PDF澶勭悊API瑙嗗浘"""
    
    serializer_class = PDFDocumentSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [AllowAny]  # 鍏佽鍖垮悕璁块棶鏂囨。绠＄悊鍔熻兘
    queryset = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        global _GLOBAL_PROCESSOR
        if _GLOBAL_PROCESSOR is None:
            _GLOBAL_PROCESSOR = WeaviateDocumentProcessor()
        self.processor = _GLOBAL_PROCESSOR
        
    def get_queryset(self):
        """鍔ㄦ€佽幏鍙栨煡璇㈤泦"""
        return self._get_all_documents()
    
    # 绉婚櫎閫愯姹傚叧闂紝缁熶竴鍦ㄨ繘绋嬬粨鏉熸椂鐢辫В閲婂櫒鍥炴敹
    
    def get_serializer_class(self):  # type: ignore
        if self.action == 'upload':
            return PDFUploadSerializer
        return PDFDocumentSerializer
    
    
    def _get_document_by_id(self, doc_id):
        """鏍规嵁ID鑾峰彇鏂囨。"""
        return self._filter_documents(id=doc_id).first()
    
    def _get_document_does_not_exist_exception(self):
        """Return the PDFDocument DoesNotExist exception."""
        return PDFDocument.DoesNotExist
    
    def _get_all_documents(self):
        """Return all PDF documents."""
        return PDFDocument.objects.all()
    
    def _filter_documents(self, **kwargs):
        """杩囨护鏂囨。"""
        return PDFDocument.objects.filter(**kwargs)
    
    def _get_document_count(self):
        """鑾峰彇鏂囨。璁℃暟"""
        return PDFDocument.objects.count()
    
    def _order_documents_by(self, *args, **kwargs):
        """Order PDF documents by the given fields."""
        return PDFDocument.objects.order_by(*args, **kwargs)
    
    def _aggregate_documents(self, *args, **kwargs):
        """鑱氬悎鏂囨。缁熻淇℃伅"""
        return PDFDocument.objects.aggregate(*args, **kwargs)
    
    def _values_documents(self, *args, **kwargs):
        """Return document values for the given fields."""
        return PDFDocument.objects.values(*args, **kwargs)
    
    def _create_document(self, **kwargs):
        """鍒涘缓鏂囨。"""
        return PDFDocument.objects.create(**kwargs)
    
    def _get_or_create_document(self, filter_kwargs, defaults=None):
        """Get or create a PDF document."""
        if defaults is None:
            defaults = {}
        return PDFDocument.objects.get_or_create(**filter_kwargs, defaults=defaults)

    def _build_document_processing_metadata(self, doc):
        return {
            "title": doc.title,
            "authors": doc.authors or '',
            "year": doc.year or '',
            "journal": doc.journal or '',
            "doi": doc.doi or '',
            "category": doc.category,
            "upload_date": str(doc.upload_date),
        }

    def _mark_document_processed(self, doc, result):
        doc.processed = True
        doc.page_count = result.get("total_pages", 0)
        doc.save()
        clear_document_processing_error(getattr(doc, "id", None))

    def _record_document_processing_failure(self, doc, result_or_detail):
        error_info = from_processing_result(result_or_detail if isinstance(result_or_detail, dict) else {"error": result_or_detail})
        remember_document_processing_error(
            document_id=getattr(doc, "id", None),
            error_code=error_info.error_code,
            message=error_info.message,
            detail=error_info.detail,
        )
        return error_info

    def _warn_orphan_duplicate_child(self, doc, warning_token):
        canonical_doc = UploadStorageService.resolve_content_document(doc)
        canonical_id = getattr(canonical_doc, "id", None)
        canonical_path = getattr(canonical_doc, "file_path", None)
        if canonical_doc is None or canonical_id is None or not canonical_path or not os.path.exists(canonical_path):
            logger.warning(
                "%s document_id=%s duplicate_of=%s file_path=%s",
                warning_token,
                getattr(doc, "id", None),
                getattr(getattr(doc, "duplicate_of", None), "id", None),
                canonical_path,
            )
            return True
        return False
    
    def _only_documents(self, *fields):
        """Limit document fields for the query."""
        return PDFDocument.objects.only(*fields)
    
    def _get_first_document(self, queryset=None):
        """Return the first document from a queryset."""
        if queryset is None:
            return self._get_all_documents().first()
        return queryset.first()
    
    def _get_document_or_none(self, **kwargs):
        """鑾峰彇鏂囨。鎴栬繑鍥濶one"""
        try:
            return self._filter_documents(**kwargs).first()
        except self._get_document_does_not_exist_exception():
            return None
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """涓嬭浇鎸囧畾PDF鏂囦欢锛屼緵鍓嶇鏌ョ湅/涓嬭浇"""
        try:
            document = self.get_object()
            if not document.file_path or not os.path.exists(document.file_path):
                return error_response(
                    error_code="FILE_NOT_FOUND",
                    message="文件不存在",
                    detail=f"file_path={document.file_path}",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            # FileResponse will close the underlying file handle after the response finishes.
            response = FileResponse(
                open(document.file_path, 'rb'),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'inline; filename="{os.path.basename(document.file_path)}"'
            return response
        except Exception as e:
            logger.exception("下载文件失败")
            return error_response(
                error_code="FILE_DOWNLOAD_FAILED",
                message="文件下载失败",
                detail=e,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process a single document and build vector chunks."""
        try:
            document = self.get_object()
            result = self.processor.process_single_document(
                pdf_path=document.file_path,
                document_id=str(document.id),
                metadata={
                    "title": document.title,
                    "authors": document.authors or '',
                    "year": document.year or '',
                    "journal": document.journal or '',
                    "doi": document.doi or '',
                    "category": document.category,
                    "upload_date": str(document.upload_date)
                }
            )

            if result.get("status") == "success":
                self._mark_document_processed(document, result)
                return Response({
                    "success": True,
                    "message": "文档处理完成",
                    "total_chunks": result.get("total_chunks", 0),
                    "total_pages": result.get("total_pages", 0)
                })
            else:
                error_info = self._record_document_processing_failure(document, result)
                logger.error(
                    "文档处理失败: document_id=%s error_code=%s detail=%s",
                    document.id,
                    error_info.error_code,
                    error_info.detail,
                )
                return error_response(
                    error_code=error_info.error_code,
                    message=error_info.message,
                    detail=error_info.detail,
                    status_code=error_info.status_code,
                    extra={"document_id": str(document.id)},
                )

        except Exception as e:
            logger.exception("处理单个文档失败")
            error_info = self._record_document_processing_failure(document, {"error": e}) if 'document' in locals() else None
            return error_response(
                error_code=error_info.error_code if error_info else "PDF_PROCESS_FAILED",
                message=error_info.message if error_info else "PDF 处理失败",
                detail=error_info.detail if error_info else e,
                status_code=error_info.status_code if error_info else status.HTTP_500_INTERNAL_SERVER_ERROR,
                extra={"document_id": str(document.id)} if 'document' in locals() else None,
            )

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """涓婁紶PDF鏂囦欢"""
        try:
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                return error_response(
                    error_code="VALIDATION_ERROR",
                    message="上传参数校验失败",
                    detail=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            
            # 淇濆瓨鏂囦欢
            pdf_file = serializer.validated_data['file']
            title = serializer.validated_data.get('title', pdf_file.name)
            category = serializer.validated_data.get('category', 'general')

            duplicate_inspection = UploadStorageService.inspect_uploaded_file(pdf_file)
            UploadStorageService.log_duplicate_inspection(logger, 'weaviate_upload', duplicate_inspection)
            
            # 妫€鏌ユ槸鍚﹀凡瀛樺湪鍚屽悕鏂囦欢
            existing_doc = self._filter_documents(filename=pdf_file.name).first()
            if existing_doc:
                # Weaviate upload can safely short-circuit to the existing
                # content record because it does not create a separate review
                # action the way user uploads do.
                logger.info(
                    "weaviate_existing_hit reason=same_filename incoming=%s existing_document_id=%s existing_filename=%s",
                    pdf_file.name,
                    existing_doc.id,
                    existing_doc.filename,
                )
                clear_document_processing_error(existing_doc.id)
                return Response({
                    "success": True,
                    "message": "文件已存在，跳过上传",
                    "document_id": str(existing_doc.id),
                    "filename": pdf_file.name,
                    "existing": True,
                    "title": existing_doc.title,
                    "upload_date": existing_doc.upload_date.isoformat()
                }, status=status.HTTP_200_OK)

            if duplicate_inspection.duplicate_detected and duplicate_inspection.duplicate_document_id:
                duplicate_doc = self._get_document_or_none(id=duplicate_inspection.duplicate_document_id)
                if duplicate_doc:
                    logger.info(
                        "weaviate_existing_hit reason=duplicate_content incoming=%s duplicate_document_id=%s existing_filename=%s",
                        pdf_file.name,
                        duplicate_doc.id,
                        getattr(duplicate_doc, 'filename', ''),
                    )
                    clear_document_processing_error(duplicate_doc.id)
                    return Response({
                        "success": True,
                        "message": "文件内容已存在，跳过上传",
                        "document_id": str(duplicate_doc.id),
                        "filename": pdf_file.name,
                        "existing": True,
                        "title": duplicate_doc.title,
                        "upload_date": duplicate_doc.upload_date.isoformat()
                    }, status=status.HTTP_200_OK)
            
            try:
                stored_upload = UploadStorageService.save_uploaded_file(
                    pdf_file,
                    storage_key=PDF_LIBRARY,
                    naming_strategy='original',
                    precomputed_inspection=duplicate_inspection,
                )
            except Exception as exc:
                logger.exception("保存上传文件失败: %s", pdf_file.name)
                error_info = file_save_error(exc)
                return error_response(
                    error_code=error_info.error_code,
                    message=error_info.message,
                    detail=error_info.detail,
                    status_code=error_info.status_code,
                )
            file_path = stored_upload.file_path
            
            # 楠岃瘉鏂囦欢鏄惁涓烘湁鏁堢殑PDF
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                page_count = len(doc)
                doc.close()
                logger.info(f"鏂囦欢楠岃瘉鎴愬姛: {pdf_file.name} ({page_count} 椤?")
            except Exception as e:
                # 鍒犻櫎鏃犳晥鏂囦欢
                if os.path.exists(file_path):
                    os.remove(file_path)
                logger.exception("上传 PDF 校验失败: %s", pdf_file.name)
                return error_response(
                    error_code="INVALID_PDF",
                    message="文件格式不支持或 PDF 已损坏",
                    detail=e,
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            
            from .pdf_utils import PDFUtils
            extraction_result = PDFUtils.extract_text_and_metadata(file_path)
            if not extraction_result.get("success"):
                if os.path.exists(file_path):
                    os.remove(file_path)
                error_info = from_pdf_extraction_result(extraction_result)
                logger.error(
                    "上传后提取 PDF 元数据失败: filename=%s error_code=%s detail=%s",
                    pdf_file.name,
                    error_info.error_code,
                    error_info.detail,
                )
                return error_response(
                    error_code=error_info.error_code,
                    message=error_info.message,
                    detail=error_info.detail,
                    status_code=error_info.status_code,
                )
            
            # 浣跨敤鎻愬彇鐨勫厓鏁版嵁
            metadata = extraction_result.get('metadata', {})
            title = metadata.get('title') or title
            authors = metadata.get('authors', '')
            year_str = metadata.get('year', '')
            year = int(year_str) if year_str and year_str.isdigit() else None
            journal = metadata.get('journal', '')
            doi = metadata.get('doi', '')
            abstract = metadata.get('abstract', '')
            keywords = metadata.get('keywords', '')
            
            # 淇濆瓨鍒版暟鎹簱
            try:
                pdf_document = self._create_document(
                    title=title,
                    authors=authors,
                    year=year,
                    journal=journal,
                    doi=doi,
                    filename=pdf_file.name,
                    file_path=file_path,
                    file_size=pdf_file.size,
                    category=category,
                    processed=False,
                    sha1=stored_upload.sha1,
                )
            except Exception as exc:
                logger.exception("写入上传文档记录失败: %s", pdf_file.name)
                error_info = database_write_error(exc)
                return error_response(
                    error_code=error_info.error_code,
                    message=error_info.message,
                    detail=error_info.detail,
                    status_code=error_info.status_code,
                )
            clear_document_processing_error(pdf_document.id)
            
            # 寮傛澶勭悊鏂囨。

            from threading import Thread
            
            def process_document_async():
                try:
                    result = self.processor.process_single_document(
                        pdf_document.file_path,
                        document_id=str(pdf_document.id),
                        metadata={
                            "title": title,
                            "authors": authors,
                            "year": year,
                            "journal": journal,
                            "doi": doi,
                            "category": category,
                            "upload_date": str(pdf_document.upload_date)
                        }
                    )
                    
                    if result.get("status") == "success":
                        self._mark_document_processed(pdf_document, result)
                        logger.info("文档处理完成: %s", title)
                    else:
                        pdf_document.processed = False
                        pdf_document.save()
                        error_info = self._record_document_processing_failure(pdf_document, result)
                        logger.error(
                            "文档处理失败: title=%s error_code=%s detail=%s",
                            title,
                            error_info.error_code,
                            error_info.detail,
                        )
                        
                except Exception as e:
                    logger.exception("异步处理上传文档失败: %s", title)
                    if 'pdf_document' in locals():
                        self._record_document_processing_failure(pdf_document, {"error": e})
            
            # 鍚姩寮傛澶勭悊
            Thread(target=process_document_async, daemon=True).start()
            
            return Response({
                "success": True,
                "message": "文件上传成功，正在处理中",
                "document_id": str(pdf_document.id),
                "filename": pdf_file.name
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.exception("文件上传失败")
            return error_response(
                error_code="UPLOAD_FAILED",
                message="文件上传失败",
                detail=e,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'])
    def search(self, request):
        """鎼滅储鏂囨。鍐呭"""
        try:
            query = request.query_params.get('q', '').strip()
            if not query:
                return Response({
                    "success": False,
                    "error": "请提供搜索查询"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            n_results = int(request.query_params.get('limit', 5))
            search_type = request.query_params.get('type', 'similarity')
            
            # 鎵ц鎼滅储
            results = self.processor.search_documents(
                query=query,
                n_results=min(n_results, 20),  # 闄愬埗鏈€澶х粨鏋滄暟
                search_type=search_type
            )
            
            documents = {}
            for result in results:
                doc_id = result["metadata"]["document_id"]
                if doc_id not in documents:
                    doc = self._get_document_or_none(id=doc_id)
                    if not doc:
                        logger.warning(f"鎼滅储缁撴灉鍏宠仈鐨勬枃妗ｄ笉瀛樺湪鎴栧凡鍒犻櫎: {doc_id}")
                        continue
                    documents[doc_id] = {
                        "document": PDFDocumentSerializer(doc).data,
                        "chunks": []
                    }
                
                documents[doc_id]["chunks"].append({
                    "content": result["content"],
                    "score": result["score"],
                    "metadata": result["metadata"]
                })
            
            return Response({
                "success": True,
                "query": query,
                "total_results": len(results),
                "documents": list(documents.values())
            })
            
        except Exception as e:
            logger.error(f"鎼滅储澶辫触: {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """鑾峰彇绯荤粺缁熻淇℃伅"""
        try:
            cache_key = 'pdf_stats'
            cached_stats = cache.get(cache_key)
            if cached_stats:
                logger.info("返回缓存的统计信息")
                return Response({
                    "success": True,
                    **cached_stats
                })
            
            # 鑾峰彇Weaviate缁熻淇℃伅
            stats = self.processor.get_system_stats()
            
            # 璁＄畻鏈湀涓婁紶鏁伴噺
            current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_upload = PDFDocument.objects.filter(
                upload_date__gte=current_month
            ).count()
            
            from django.db.models import Count, Q

            stats_query = PDFDocument.objects.aggregate(
                total_docs=Count('id'),
                processed_docs=Count('id', filter=Q(processed=True))
            )
            
            total_docs = stats_query['total_docs']
            processed_docs = stats_query['processed_docs']
            pending_docs = total_docs - processed_docs
            
            processing_rate = 0
            if total_docs > 0:
                processing_rate = int((processed_docs / total_docs) * 100)
            
            # 鑾峰彇鏂囨。绫诲瀷鍒嗗竷
            category_counts = dict(PDFDocument.objects.values('category').annotate(
                count=Count('id')
            ).values_list('category', 'count'))
            
            chunk_count = stats.get("total_chunks", 0) if stats else 0
            if chunk_count == 0:
                chunk_count = DocumentChunk.objects.count()
            
            # 杩斿洖鏇存湁浠峰€肩殑缁熻淇℃伅
            response_data = {
                "total_documents": total_docs,
                "processed_documents": processed_docs,
                "pending_documents": pending_docs,
                "processing_rate": processing_rate,
                "monthly_upload": monthly_upload,
                "total_chunks": chunk_count,
                "categories": list(category_counts.keys()),
                "category_counts": category_counts,
                "weaviate_status": stats.get("weaviate_status", "unknown")
            }
            
            # 缂撳瓨缁熻淇℃伅10鍒嗛挓
            cache.set(cache_key, response_data, 600)
            
            return Response({
                "success": True,
                **response_data
            })
            
        except Exception as e:
            logger.error(f"鑾峰彇缁熻淇℃伅澶辫触: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def processing_status(self, request):
        """杩斿洖澶勭悊杩涘害锛歱rocessed/pending/total"""
        try:
            qs = self._get_all_documents()
            total = qs.count()
            processed = qs.filter(processed=True).count()
            pending = max(0, total - processed)
            failed = qs.filter(processed=False).exclude(file_path__isnull=True).count() if total > 0 else 0
            
            current_doc = None
            if pending > 0:
                current_doc = self._filter_documents(processed=False).order_by('upload_date').first()
            
            last_doc = self._order_documents_by('-upload_date').first()
            last_file = last_doc.title if last_doc else ''
            current_file = current_doc.title if current_doc else ''
            
            finished = (pending == 0 and total > 0)
            
            return Response({
                "success": True,
                "total": total,
                "processed": processed,
                "pending": pending,
                "failed": failed,
                "finished": finished,
                "last_file": last_file,
                "current_file": current_file,
                "progress_percentage": round((processed / total * 100) if total > 0 else 0, 1)
            })
        except Exception as e:
            logger.exception("获取处理状态失败")
            return error_response(
                error_code="PROCESSING_STATUS_FAILED",
                message="获取处理状态失败",
                detail=e,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    def _collect_pending_candidates(self):
        """Collect canonical content records that still need pending processing."""
        candidates = []
        seen_ids = set()

        def add_candidate(doc):
            doc_id = str(getattr(doc, "id", ""))
            if not doc_id or doc_id in seen_ids:
                return
            seen_ids.add(doc_id)
            candidates.append(doc)

        canonical_pending_qs = self._filter_documents(
            processed=False,
            duplicate_of__isnull=True,
        ).order_by("upload_date")
        for doc in canonical_pending_qs:
            add_candidate(doc)

        # Duplicate child rows keep review/action semantics. Their content
        # pending state is derived from the canonical parent instead of being
        # treated as independent processing candidates.
        duplicate_children_qs = self._filter_documents(
            processed=False,
            duplicate_of__isnull=False,
        ).order_by("upload_date")
        for doc in duplicate_children_qs:
            self._warn_orphan_duplicate_child(doc, "process_pending_orphan_child")

        return candidates

    def process_pending(self, request):
        """Process pending canonical documents in the background."""
        try:
            global _PROCESSING_LOCK, _CANCEL_REQUESTED
            if _PROCESSING_LOCK:
                return error_response(
                    error_code="PROCESSING_BUSY",
                    message="系统正在处理其他任务，请稍后再试",
                    detail="当前已有后台处理任务在运行",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            _PROCESSING_LOCK = True
            _CANCEL_REQUESTED = False
            pending_docs = self._collect_pending_candidates()
            count = len(pending_docs)
            
            if count == 0:
                _PROCESSING_LOCK = False
                return Response({
                    "success": True,
                    "message": "没有待处理的文档"
                })
            
            def process_async():
                try:
                    successful = 0
                    for i, doc in enumerate(pending_docs):
                        if _CANCEL_REQUESTED:
                            logger.info("Pending processing cancelled before completion")
                            break
                        try:
                            # Process one canonical content record at a time.
                            result = self.processor.process_single_document(
                                doc.file_path,
                                document_id=str(doc.id),
                                metadata=self._build_document_processing_metadata(doc)
                            )
                            
                            if result.get("status") == "success":
                                self._mark_document_processed(doc, result)
                                successful += 1
                                logger.info("Pending processing completed: %s (%s/%s)", doc.title, i + 1, count)
                            else:
                                error_info = self._record_document_processing_failure(doc, result)
                                logger.error(
                                    "Pending processing failed: document_id=%s error_code=%s detail=%s",
                                    doc.id,
                                    error_info.error_code,
                                    error_info.detail,
                                )
                            # Keep the loop structure explicit so progress updates
                            # can be reintroduced without revisiting candidate logic.
                            if (i + 1) % 1 == 0:
                                pass
                                
                        except Exception as e:
                            logger.exception("Pending processing exception for %s", doc.title)
                            self._record_document_processing_failure(doc, {"error": e})
                            continue
                    
                    logger.info(f"批量处理完成，成功处理 {successful}/{count} 个文档")
                    
                except Exception as e:
                    logger.exception("Pending processing loop error")
                finally:
                    globals()['_PROCESSING_LOCK'] = False
            
            # Start the worker thread after candidate collection is complete.
            from threading import Thread
            Thread(target=process_async, daemon=True).start()
            
            return Response({
                "success": True,
                "message": f"开始批量处理 {count} 个文档",
                "total": count,
                "status": "processing"
            })
            
        except Exception as e:
            globals()['_PROCESSING_LOCK'] = False
            logger.exception("Failed to start pending processing")
            return error_response(
                error_code="PROCESS_PENDING_FAILED",
                message="启动批量处理失败",
                detail=e,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    @action(
        detail=False,
        methods=['post'],
        parser_classes=[JSONParser, MultiPartParser, FormParser],
    )
    def reprocess_all(self, request):
        """Reprocess all documents behind an explicit safety gate."""
        try:
            global _PROCESSING_LOCK, _CANCEL_REQUESTED
            if _PROCESSING_LOCK:
                return error_response(
                    error_code="PROCESSING_BUSY",
                    message="系统正在处理其他任务，请稍后再试",
                    detail="当前已有后台处理任务在运行",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            def _flag(value):
                if isinstance(value, bool):
                    return value
                if value is None:
                    return False
                return str(value).strip().lower() in {"1", "true", "yes", "on"}

            all_docs = self._get_all_documents()
            count = all_docs.count()
            
            if count == 0:
                return Response({
                    "success": True,
                    "message": "没有文档需要重新处理"
                })

            confirm = _flag(request.data.get("confirm"))
            dry_run = _flag(request.data.get("dry_run"))

            preview_payload = {
                "success": True,
                "dry_run": dry_run,
                "requires_confirmation": not confirm and not dry_run,
                "total": count,
                "would_reset_processed": True,
                "would_delete_all_vectors": True,
                "message": f"Reprocess-all will reset {count} documents and rebuild all vectors",
            }

            if dry_run:
                return Response(preview_payload)

            if not confirm:
                preview_payload["success"] = False
                preview_payload["error"] = "confirm=true is required before reprocess_all can run"
                return Response(preview_payload, status=status.HTTP_400_BAD_REQUEST)

            _PROCESSING_LOCK = True
            _CANCEL_REQUESTED = False
            
            # 棣栧厛灏嗘墍鏈夋枃妗ｆ爣璁颁负鏈鐞嗙姸鎬侊紝杩欐牱鐘舵€丄PI鑳芥纭窡韪繘搴?            logger.info(f"姝ｅ湪灏?{count} 涓枃妗ｆ爣璁颁负鏈鐞嗙姸鎬?..")
            all_docs.update(processed=False)
            logger.warning("reprocess_all confirmed: resetting %s documents and deleting all vectors", count)
            
            # 寮傛澶勭悊鍑芥暟
            def reprocess_async():
                try:
                    # 瀵煎叆PDFUtils
                    from .pdf_utils import PDFUtils
                    
                    logger.info(f"开始异步重新处理 {count} 个文档")
                    
                    # 鍒犻櫎鎵€鏈夌幇鏈夊垎鍧楁暟鎹?                    logger.info("姝ｅ湪鍒犻櫎鎵€鏈夌幇鏈夊垎鍧楁暟鎹?..")
                    self.processor.vector_service.delete_all_documents()
                    
                    pdf_paths = [doc.file_path for doc in all_docs]
                    metadata_list = []
                    
                    for doc in all_docs:
                        try:
                            extraction_result = PDFUtils.extract_text_and_metadata(doc.file_path)
                            if extraction_result.get('success'):
                                meta = extraction_result.get('metadata', {})
                                metadata_list.append({
                                    "id": str(doc.id),
                                    "title": meta.get('title', doc.title),
                                    "authors": meta.get('authors', doc.authors or ''),
                                    "year": meta.get('year', doc.year or ''),
                                    "journal": meta.get('journal', doc.journal or ''),
                                    "doi": meta.get('doi', doc.doi or ''),
                                    "category": doc.category,
                                    "upload_date": str(doc.upload_date)
                                })
                                
                                # 鏇存柊鏁版嵁搴撲腑鐨勫厓鏁版嵁
                                if meta.get('title') and meta.get('title') != doc.title:
                                    doc.title = meta.get('title')
                                    doc.save()
                                
                                logger.info(f"閲嶆柊鎻愬彇鍏冩暟鎹? {doc.filename} -> {meta.get('title', 'No title')}")
                            else:
                                # 濡傛灉鎻愬彇澶辫触锛屼娇鐢ㄥ師鏈夊厓鏁版嵁
                                metadata_list.append({
                                    "id": str(doc.id),
                                    "title": doc.title,
                                    "authors": doc.authors or '',
                                    "year": doc.year or '',
                                    "journal": doc.journal or '',
                                    "doi": doc.doi or '',
                                    "category": doc.category,
                                    "upload_date": str(doc.upload_date)
                                })
                        except Exception as e:
                            logger.error(f"閲嶆柊鎻愬彇鍏冩暟鎹け璐?{doc.filename}: {e}")
                            metadata_list.append({
                                "id": str(doc.id),
                                "title": doc.title,
                                "authors": doc.authors or '',
                                "year": doc.year or '',
                                "journal": doc.journal or '',
                                "doi": doc.doi or '',
                                "category": doc.category,
                                "upload_date": str(doc.upload_date)
                            })
                    
                    results = []
                    for idx, doc in enumerate(all_docs):
                        if _CANCEL_REQUESTED:
                            logger.info("閲嶆柊澶勭悊琚彇娑堬紝鎻愬墠缁撴潫")
                            break
                        result = self.processor.process_single_document(
                            pdf_path=doc.file_path,
                            document_id=str(doc.id),
                            metadata=metadata_list[idx],
                            chunk_size=GlobalConfig.CHUNK_SIZE,   # token鍒嗗潡
                            chunk_overlap=GlobalConfig.CHUNK_OVERLAP
                        )
                        results.append(result)
                        try:
                            if result.get("status") == "success":
                                doc.processed = True
                                doc.page_count = result.get("total_pages", 0)
                            else:
                                doc.processed = False
                            doc.save()
                        except Exception:
                            pass
                    
                    successful = 0
                    for doc, result in zip(all_docs, results):
                        if result.get("status") == "success":
                            doc.processed = True
                            doc.page_count = result.get("total_pages", 0)
                            doc.save()
                            successful += 1
                        else:
                            doc.processed = False
                            doc.save()
                    
                    logger.info(f"异步重新处理完成，成功处理 {successful}/{count} 个文档")
                    
                except Exception as e:
                    logger.error(f"寮傛閲嶆柊澶勭悊澶辫触: {e}")
                    # 鍑洪敊鏃跺皢鎵€鏈夋枃妗ｆ爣璁颁负澶勭悊澶辫触
                    all_docs.update(processed=False)
                finally:
                    globals()['_PROCESSING_LOCK'] = False
            
            # 鍚姩寮傛澶勭悊
            from threading import Thread
            Thread(target=reprocess_async, daemon=True).start()
            # 绔嬪嵆杩斿洖鍚姩淇℃伅
            return Response({
                "success": True,
                "message": f"开始重新处理 {count} 个文档",
                "total": count,
                "status": "processing",
                "dry_run": False,
            })
            
        except Exception as e:
            globals()['_PROCESSING_LOCK'] = False
            logger.error(f"閲嶆柊澶勭悊澶辫触: {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def cancel_processing(self, request):
        """Cancel the current processing task."""
        try:
            global _CANCEL_REQUESTED
            _CANCEL_REQUESTED = True
            return Response({"success": True, "message": "宸茶姹傚彇娑堬紝姝ｅ湪鍋滄..."})
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=500)

    def _document_has_other_file_references(self, document) -> bool:
        if not document.file_path:
            return False
        return PDFDocument.objects.filter(file_path=document.file_path).exclude(id=document.id).exists()

    def _delete_physical_file_if_unshared(self, document) -> None:
        # Shared duplicate chains can legitimately reuse the same file_path.
        # Only delete the physical file when this record is the final
        # remaining reference.
        if (
            document.file_path
            and not self._document_has_other_file_references(document)
            and os.path.exists(document.file_path)
        ):
            os.remove(document.file_path)
    
    @action(detail=True, methods=['delete'])
    def delete_document(self, request, pk=None):
        """Delete a document record and its vector data."""
        try:
            document = self.get_object()
            
            # Remove vector data before deleting the row.
            self.processor.vector_service.delete_document(str(document.id))

            self._delete_physical_file_if_unshared(document)
            
            document.delete()
            
            return Response({
                "success": True,
                "message": "鏂囨。鍒犻櫎鎴愬姛"
            })
            
        except Exception as e:
            logger.error("Failed to delete document %s: %s", pk, e)
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def chunks(self, request):
        """鑾峰彇鏂囨。鍒嗗潡淇℃伅"""
        try:
            document_id = request.query_params.get('document_id')
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
            
            if document_id:
                try:
                    document = self._get_document_by_id(document_id)
                    chunks = self.processor.get_document_chunks(
                        document_id=str(document_id),
                        limit=limit,
                        offset=offset
                    )
                    
                    return Response({
                        "success": True,
                        "document": PDFDocumentSerializer(document).data,
                        "chunks": chunks,
                        "total": len(chunks)
                    })
                    
                except self._get_document_does_not_exist_exception():
                    return Response({
                        "success": False,
                        "error": "文档不存在"
                    }, status=status.HTTP_404_NOT_FOUND)
            
            else:
                # 鑾峰彇鎵€鏈夊垎鍧楋紙甯﹀垎椤碉級
                chunks = self.processor.get_all_chunks(
                    limit=limit,
                    offset=offset
                )
                
                return Response({
                    "success": True,
                    "chunks": chunks,
                    "total": len(chunks),
                    "limit": limit,
                    "offset": offset
                })
                
        except Exception as e:
            logger.error(f"鑾峰彇鍒嗗潡淇℃伅澶辫触: {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _normalize_sync_path(self, raw_path):
        return UploadStorageService.normalize_sync_path(raw_path)

    def _collect_sync_folder_files(self, pdf_dir):
        """Build a canonical file-system view keyed by normalized file_path."""
        folder_files = {}
        for file_path in pdf_dir.rglob('*'):
            try:
                if file_path.is_file() and file_path.suffix.lower() == '.pdf':
                    normalized_path = self._normalize_sync_path(file_path)
                    if normalized_path:
                        folder_files[normalized_path] = file_path
            except Exception:
                continue
        return folder_files

    def _collect_sync_canonical_records(self, pdf_dir):
        """Collect canonical records for sync; duplicate child rows stay transparent."""
        db_files = {}
        orphan_children = []
        ignored_paths = set()

        documents = self._get_all_documents().select_related('duplicate_of').only(
            'id',
            'filename',
            'file_path',
            'file_size',
            'sha1',
            'duplicate_of',
        )

        for doc in documents:
            if getattr(doc, 'duplicate_of', None) is not None:
                canonical_doc = UploadStorageService.resolve_content_document(doc)
                canonical_id = getattr(canonical_doc, 'id', None)
                canonical_path = self._normalize_sync_path(getattr(canonical_doc, 'file_path', None))
                child_path = self._normalize_sync_path(getattr(doc, 'file_path', None))

                if canonical_doc is doc or canonical_doc is None or canonical_id is None or not canonical_path:
                    orphan_children.append(doc)
                    if child_path:
                        ignored_paths.add(child_path)
                    continue

                if not UploadStorageService.is_sync_managed_path(canonical_path, pdf_dir):
                    if child_path:
                        ignored_paths.add(child_path)
                continue

            canonical_path = self._normalize_sync_path(getattr(doc, 'file_path', None))
            if not canonical_path or not UploadStorageService.is_sync_managed_path(canonical_path, pdf_dir):
                continue

            db_files.setdefault(
                canonical_path,
                {
                    'id': doc.id,
                    'filename': doc.filename,
                    'file_path': getattr(doc, 'file_path', ''),
                    'file_size': getattr(doc, 'file_size', 0),
                    'sha1': getattr(doc, 'sha1', None),
                },
            )

        return db_files, orphan_children, ignored_paths

    @action(detail=False, methods=['post'])
    def sync_files(self, request):
        """鍚屾鏂囦欢澶逛腑鐨凱DF鏂囦欢"""
        try:
            from pathlib import Path
            from django.conf import settings
            
            # 鑾峰彇PDF鏂囦欢澶硅矾寰勶紙浼樺厛浣跨敤鍏ㄥ眬璁剧疆锛岀‘淇濅竴鑷达級
            pdf_dir = Path(getattr(settings, 'PDF_STORAGE_PATH', Path(settings.BASE_DIR).parent / 'data' / 'pdfs')).resolve()
            
            if not pdf_dir.exists():
                return Response({
                    "success": False,
                    "error": f"PDF鏂囦欢澶逛笉瀛樺湪: {pdf_dir}"
                }, status=status.HTTP_404_NOT_FOUND)

            folder_files = self._collect_sync_folder_files(pdf_dir)
            db_files, orphan_children, ignored_folder_paths = self._collect_sync_canonical_records(pdf_dir)

            for orphan_child in orphan_children:
                logger.warning(
                    "sync_files_orphan_child document_id=%s duplicate_of=%s file_path=%s",
                    getattr(orphan_child, 'id', None),
                    getattr(getattr(orphan_child, 'duplicate_of', None), 'id', None),
                    getattr(orphan_child, 'file_path', None),
                )
            
            added_count = 0
            removed_count = 0
            added_files = []
            removed_files = []
            error_count = 0
            first_error = None
            
            from django.db import transaction
            
            with transaction.atomic():  # type: ignore
                for file_key, file_path in folder_files.items():
                    if file_key in ignored_folder_paths:
                        continue

                    if file_key in db_files:
                        continue
                    
                    try:
                        filename = file_path.name
                        
                        try:
                            doc, created = self._get_or_create_document(
                                {'filename': filename},
                                defaults=UploadStorageService.build_sync_document_defaults(file_path)
                            )
                            if created:
                                added_count += 1
                                added_files.append(filename)
                                logger.info(f'娣诲姞鏂版枃浠? {filename}')
                            else:
                                updated = False
                                if doc.file_path != str(file_path):
                                    doc.file_path = str(file_path)
                                    updated = True
                                size_now = file_path.stat().st_size
                                if not doc.file_size or doc.file_size != size_now:
                                    doc.file_size = size_now
                                    updated = True
                                # 璁＄畻sha1鐢ㄤ簬鏇寸ǔ鍋ョ殑鍘婚噸
                                try:
                                    import hashlib
                                    h = hashlib.sha1()
                                    with open(file_path, 'rb') as fh:
                                        for chunk in iter(lambda: fh.read(1024 * 1104), b''):
                                            h.update(chunk)
                                    sha1 = h.hexdigest()
                                    if not getattr(doc, 'sha1', None) or doc.sha1 != sha1:
                                        doc.sha1 = sha1
                                        updated = True
                                except Exception:
                                    pass
                                if updated:
                                    doc.save()
                                    logger.info(f'鏇存柊鏂囦欢璁板綍: {filename}')
                        except Exception as e:
                            error_count += 1
                            if first_error is None:
                                first_error = str(e)
                            logger.error(f'娣诲姞鏂囦欢澶辫触 {filename}: {str(e)}')
                        
                    except Exception as e:
                        logger.error(f'娣诲姞鏂囦欢澶辫触 {filename}: {str(e)}')
            
            files_to_delete = [
                (file_key, doc)
                for file_key, doc in db_files.items()
                if file_key not in folder_files
            ]
            
            if files_to_delete:
                # 鎵归噺鑾峰彇瑕佸垹闄ょ殑鏂囨。ID
                doc_ids_to_delete = [doc['id'] for _, doc in files_to_delete]
                
                # 鎵归噺鍒犻櫎鍚戦噺鏁版嵁
                for doc_id in doc_ids_to_delete:
                    try:
                        self.processor.vector_service.delete_document(str(doc_id))  # type: ignore
                    except Exception as e:
                        logger.warning(f'鍒犻櫎鍚戦噺鏁版嵁澶辫触 {doc_id}: {str(e)}')
                
                with transaction.atomic():  # type: ignore
                    deleted_count = self._filter_documents(id__in=doc_ids_to_delete).delete()[0]
                    removed_count = deleted_count
                    removed_files = [doc['filename'] for _, doc in files_to_delete]
                
                logger.info(f'批量删除 {removed_count} 个文件记录')
            
            message = f"同步完成：新增 {added_count} 个文件，删除 {removed_count} 个文件"
            if added_count == 0 and removed_count == 0:
                message = "鏂囦欢宸插悓姝ワ紝鏃犻渶鏇存柊"
            
            return Response({
                "success": True,
                "message": message,
                "pdf_dir": str(pdf_dir),
                "scanned_files": len(folder_files),
                "db_count_before": len(db_files),
                "db_count_after": self._get_document_count(),
                "error_count": error_count,
                "first_error": first_error,
                "added_count": added_count,
                "removed_count": removed_count,
                "added_files": added_files,
                "removed_files": removed_files
            })
            
        except Exception as e:
            logger.error(f"鍚屾鏂囦欢澶辫触: {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request, *args, **kwargs):
        """鑾峰彇鏂囨。鍒楄〃锛堟敮鎸佸垎椤碉級"""
        try:
            # 鑾峰彇鍒嗛〉鍙傛暟
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # 楠岃瘉鍙傛暟
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 20
                
            offset = (page - 1) * page_size
            
            # 鑾峰彇鎬绘枃妗ｆ暟 - 鐩存帴浣跨敤PDFDocument.objects
            total_docs = PDFDocument.objects.count()
            
            # 鑾峰彇鍒嗛〉鏁版嵁 - 鐩存帴浣跨敤PDFDocument.objects
            documents = PDFDocument.objects.only(
                'id', 'title', 'filename', 'file_size', 'upload_date', 
                'processed', 'category', 'authors', 'year'
            ).order_by('-upload_date')[offset:offset + page_size]
            
            serializer = self.get_serializer(documents, many=True)
            
            # 璁＄畻鎬婚〉鏁帮紝纭繚鑷冲皯涓?
            total_pages = max(1, (total_docs + page_size - 1) // page_size) if total_docs > 0 else 1
            
            if page > total_pages:
                page = total_pages
                offset = (page - 1) * page_size
                documents = PDFDocument.objects.only(
                    'id', 'title', 'filename', 'file_size', 'upload_date', 
                    'processed', 'category', 'authors', 'year'
                ).order_by('-upload_date')[offset:offset + page_size]
                serializer = self.get_serializer(documents, many=True)
            
            return Response({
                "success": True,
                "documents": serializer.data,
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_documents": total_docs,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            })
            
        except ValueError as e:
            return Response({
                "success": False,
                "error": f"鍒嗛〉鍙傛暟閿欒: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"鑾峰彇鏂囨。鍒楄〃澶辫触: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _collect_stale_candidates(self):
        """Collect canonical content records that need stale repair."""
        candidates = []
        seen_ids = set()

        def add_candidate(doc):
            doc_id = str(getattr(doc, 'id', ''))
            if not doc_id or doc_id in seen_ids:
                return
            seen_ids.add(doc_id)
            candidates.append(doc)

        # Only canonical content records become independent stale candidates.
        canonical_unprocessed_qs = self._filter_documents(
            processed=False,
            duplicate_of__isnull=True,
        ).order_by('upload_date')
        for doc in canonical_unprocessed_qs:
            add_candidate(doc)

        # Duplicate child rows keep review semantics only. Their content
        # availability is derived from the canonical parent, so they should not
        # be repaired independently here.
        duplicate_children_qs = self._filter_documents(duplicate_of__isnull=False)
        for doc in duplicate_children_qs:
            self._warn_orphan_duplicate_child(doc, "process_stale_orphan_child")

        processed_canonicals = self._filter_documents(
            processed=True,
            duplicate_of__isnull=True,
        )
        for doc in processed_canonicals:
            try:
                if not self.processor.vector_service.has_document_vectors(str(doc.id)):  # type: ignore
                    add_candidate(doc)
            except Exception:
                continue

        return candidates

    def process_stale(self, request):
        """Process stale documents that need content/vector recovery."""
        try:
            global _PROCESSING_LOCK, _CANCEL_REQUESTED
            if _PROCESSING_LOCK:
                return error_response(
                    error_code="PROCESSING_BUSY",
                    message="系统正在处理其他任务，请稍后再试",
                    detail="当前已有后台处理任务在运行",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            _PROCESSING_LOCK = True
            _CANCEL_REQUESTED = False

            # Collect stale repair candidates once. Canonical content records
            # remain eligible; duplicate child rows delegate stale/content
            # semantics to their canonical parent.
            candidates = self._collect_stale_candidates()

            if len(candidates) == 0:
                _PROCESSING_LOCK = False
                return Response({"success": True, "message": "没有需要修复的文档"})

            def process_async():
                try:
                    successful = 0
                    total = len(candidates)
                    for index, doc in enumerate(candidates):
                        if _CANCEL_REQUESTED:
                            logger.info("Stale recovery cancelled before completion")
                            break
                        try:
                            result = self.processor.process_single_document(
                                doc.file_path,
                                document_id=str(doc.id),
                                metadata=self._build_document_processing_metadata(doc)
                            )
                            if result.get("status") == "success":
                                self._mark_document_processed(doc, result)
                                successful += 1
                                logger.info(f"[STALE] Recovery completed: {doc.title} ({index+1}/{total})")
                            else:
                                error_info = self._record_document_processing_failure(doc, result)
                                logger.error(
                                    "[STALE] Recovery failed: document_id=%s error_code=%s detail=%s",
                                    doc.id,
                                    error_info.error_code,
                                    error_info.detail,
                                )
                        except Exception as e:
                            logger.exception("[STALE] Recovery exception for %s", doc.title)
                            self._record_document_processing_failure(doc, {"error": e})
                            continue
                except Exception as e:
                    logger.exception("[STALE] Recovery loop error")
                finally:
                    globals()['_PROCESSING_LOCK'] = False

            t = threading.Thread(target=process_async, daemon=True)
            t.start()
            return Response({
                "success": True,
                "message": f"开始增量修复 {len(candidates)} 个文档",
                "total": len(candidates),
                "status": "processing",
            })
        except Exception as e:
            globals()['_PROCESSING_LOCK'] = False
            logger.exception("Failed to start stale processing")
            return error_response(
                error_code="PROCESS_STALE_FAILED",
                message="启动增量修复失败",
                detail=e,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'])
    def analyze_confidence(self, request):
        """鍒嗘瀽鎼滅储缁撴灉鐨勭疆淇″害"""
        try:
            query = request.data.get('query', '').strip()
            if not query:
                return Response({
                    "success": False,
                    "error": "请提供搜索查询"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 鎵ц鎼滅储
            search_results = self.processor.search_documents(
                query=query,
                n_results=10,
                search_type='hybrid'
            )
            
            if not search_results:
                return Response({
                    "success": True,
                    "query": query,
                    "confidence_analysis": {
                        "overall_confidence": 0.0,
                        "message": "娌℃湁鎵惧埌鐩稿叧缁撴灉"
                    }
                })
            
            # 杞崲涓篠earchResult鏍煎紡
            from pdf_processor.rag_service import SearchResult
            search_result_objects = []
            for result in search_results:
                search_result_objects.append(SearchResult(
                    content=result["content"],
                    score=result["score"],
                    metadata=result["metadata"],
                    document_id=result["metadata"]["document_id"],
                    page=result["metadata"].get("page_number", 0),
                    title=result["metadata"].get("title", "鏈煡鏂囨。"),
                    chunk_index=result["metadata"].get("chunk_index", -1)
                ))
            
            confidence_metrics = confidence_calculator.calculate_dynamic_confidence(
                search_result_objects, query, use_rerank=True
            )
            
            return Response({
                "success": True,
                "query": query,
                "confidence_analysis": {
                    "overall_confidence": confidence_metrics.overall_confidence,
                    "relevance_confidence": confidence_metrics.relevance_confidence,
                    "completeness_confidence": confidence_metrics.completeness_confidence,
                    "consistency_confidence": confidence_metrics.consistency_confidence,
                    "quality_confidence": confidence_metrics.quality_confidence,
                    "details": confidence_metrics.details
                }
            })
            
        except Exception as e:
            logger.error(f"缃俊搴﹀垎鏋愬け璐? {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def confidence_settings(self, request):
        """Return current confidence settings."""
        try:
            min_threshold, max_threshold = confidence_calculator.get_confidence_thresholds()
            return Response({
                "success": True,
                "settings": {
                    "min_confidence_threshold": min_threshold,
                    "max_confidence_threshold": max_threshold,
                    "historical_accuracy": confidence_calculator.historical_accuracy
                }
            })
        except Exception as e:
            logger.error(f"鑾峰彇缃俊搴﹁缃け璐? {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def update_confidence_settings(self, request):
        """Update confidence settings."""
        try:
            min_threshold = request.data.get('min_threshold')
            max_threshold = request.data.get('max_threshold')
            historical_accuracy = request.data.get('historical_accuracy')
            
            if min_threshold is not None and max_threshold is not None:
                confidence_calculator.set_confidence_thresholds(min_threshold, max_threshold)
            
            if historical_accuracy is not None:
                confidence_calculator.update_historical_accuracy(historical_accuracy)
            
            return Response({
                "success": True,
                "message": "缃俊搴﹁缃凡鏇存柊"
            })
            
        except Exception as e:
            logger.error(f"鏇存柊缃俊搴﹁缃け璐? {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """Delete the document and keep vector cleanup delegated."""
        return self.delete_document(request, pk=kwargs.get('pk'))
    
    def __del__(self):
        """閬垮厤鍏抽棴鍏ㄥ眬鍗曚緥澶勭悊鍣紝闃叉澶勭悊涓€旇鏂紑"""
        return
