"""
批量提取服务
实现按文档数量分批处理的陨石数据提取
"""

import logging
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from django.utils import timezone

from pdf_processor.models import PDFDocument
from pdf_processor.rag_meteorite_extractor import rag_meteorite_extractor
from meteorite_search.models import DataExtractionTask, Meteorite

if TYPE_CHECKING:
    from django.db.models.manager import Manager as DjangoManager
    PDFDocument.objects: "DjangoManager[PDFDocument]"
    DataExtractionTask.objects: "DjangoManager[DataExtractionTask]"
    Meteorite.objects: "DjangoManager[Meteorite]"

logger = logging.getLogger(__name__)

class BatchExtractionService:
    """批量提取服务"""
    
    def __init__(self):
        self.processed_doc_ids = set()
        self.extraction_log = []
        self.query_sleep_seconds = self._get_sleep_setting(
            'BATCH_EXTRACTION_QUERY_SLEEP_SECONDS',
            0.1,
        )
        self.batch_sleep_seconds = self._get_sleep_setting(
            'BATCH_EXTRACTION_BATCH_SLEEP_SECONDS',
            0.5,
        )

    def _get_sleep_setting(self, env_name: str, default_value: float) -> float:
        """Read throttling sleep settings from env with a safe fallback."""
        raw_value = os.getenv(env_name)
        if raw_value is None:
            return default_value
        try:
            parsed_value = float(raw_value)
        except (TypeError, ValueError):
            logger.warning("%s=%r is invalid; using default %s", env_name, raw_value, default_value)
            return default_value
        return max(0.0, parsed_value)
    
    def log_progress(self, task_id: str, message: str):
        """记录进度日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        logger.info(f"Task {task_id}: {log_entry}")
        self.extraction_log.append(log_entry)
    
    def reset_batch_extraction_state(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """重置批量提取状态，清除所有已处理文档记录和检查点"""
        from .task_checkpoint_manager import checkpoint_manager
        
        try:
            # 清除已处理文档ID集合
            processed_count = len(self.processed_doc_ids)
            self.processed_doc_ids.clear()
            
            # 清除提取日志
            log_count = len(self.extraction_log)
            self.extraction_log.clear()
            
            # 如果提供了task_id，清除所有检查点
            checkpoint_cleared = False
            if task_id:
                try:
                    checkpoint_cleared = checkpoint_manager.clear_checkpoints(task_id)
                    logger.info(f"已清除任务 {task_id} 的所有检查点")
                except Exception as e:
                    logger.warning(f"清除检查点失败: {str(e)}")
            
            # 记录重置操作
            reset_message = f"批量提取状态已重置 - 清除了 {processed_count} 个已处理文档记录和 {log_count} 条日志"
            if checkpoint_cleared:
                reset_message += "，以及所有检查点"
            logger.info(reset_message)
            
            return {
                'success': True,
                'message': reset_message,
                'cleared_documents': processed_count,
                'cleared_logs': log_count,
                'checkpoints_cleared': checkpoint_cleared,
                'reset_time': timezone.now().isoformat()
            }
            
        except Exception as e:
            error_message = f"重置批量提取状态失败: {str(e)}"
            logger.error(error_message)
            return {
                'success': False,
                'error': error_message
            }
    
    def get_comprehensive_search_terms(self) -> List[str]:
        """获取全面的搜索词列表"""
        return [
            # 基础陨石词汇
            "meteorite", "meteor", "asteroid", "comet",
            
            # 陨石分类
            "chondrite", "achondrite", "carbonaceous chondrite",
            "ordinary chondrite", "enstatite chondrite",
            "iron meteorite", "stony-iron meteorite",
            
            # 特殊陨石类型
            "martian meteorite", "lunar meteorite", "SNC meteorite",
            "eucrite", "diogenite", "howardite", "ureilite",
            
            # 陨石特征
            "fusion crust", "chondrules", "CAI", "refractory inclusions",
            "shock veins", "impact melt",
            
            # 有机化合物相关
            "organic compounds meteorite", "amino acids meteorite",
            "polycyclic aromatic hydrocarbons", "PAH meteorite",
            "prebiotic chemistry", "astrobiology meteorite",
            
            # 著名陨石
            "Allende", "Murchison", "ALH84001", "Tagish Lake",
            "Orgueil", "Murray", "Cold Bokkeveld"
        ]
    
    def get_default_search_terms(self) -> List[str]:
        """Return a smaller high-value default subset for batch extraction."""
        return [
            "meteorite",
            "chondrite",
            "carbonaceous chondrite",
            "achondrite",
            "martian meteorite",
            "lunar meteorite",
            "organic compounds meteorite",
            "amino acids meteorite",
        ]

    def update_task_progress(self, task_id: str, **kwargs):
        """更新任务进度"""
        try:
            task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
            update_fields = set()
            progress_keys = {
                'total_documents',
                'processed_documents',
                'successful_extractions',
                'failed_extractions',
                'progress_percentage',
                'status_text',
            }
            latest_progress = dict((task.results or {}).get('latest_progress', {}) or {})

            for key, value in kwargs.items():
                if key == 'results_update':
                    continue
                if hasattr(task, key):
                    setattr(task, key, value)
                    update_fields.add(key)
                if key in progress_keys and value is not None:
                    latest_progress[key] = value
            
            # 更新结果数据
            if 'results_update' in kwargs:
                if not task.results:
                    task.results = {}
                task.results.update(kwargs['results_update'])
                for key in ('current_batch', 'total_batches', 'status_text'):
                    if kwargs['results_update'].get(key) is not None:
                        latest_progress[key] = kwargs['results_update'][key]

            if latest_progress:
                if not task.results:
                    task.results = {}
                task.results['latest_progress'] = latest_progress
                update_fields.add('results')

            if update_fields:
                task.save(update_fields=list(update_fields))
            
        except DataExtractionTask.DoesNotExist:  # type: ignore
            logger.error(f"任务 {task_id} 不存在")
        except Exception as e:
            logger.error(f"更新任务进度失败: {str(e)}")
    
    def extract_from_document_batch(self, task_id: str, documents: List[PDFDocument],
                                   search_queries: List[str], *,
                                   batch_num: int = 0,
                                   total_batches: int = 0,
                                   total_docs: int = 0,
                                   processed_before_batch: int = 0,
                                   successful_before_batch: int = 0,
                                   failed_before_batch: int = 0) -> int:
        """从一批文档中提取陨石数据"""
        doc_titles = [str(doc.title)[:50] + "..." if len(str(doc.title)) > 50 else str(doc.title) for doc in documents]
        
        self.log_progress(task_id, f"处理文档批次: {len(documents)} 篇")
        for i, title in enumerate(doc_titles, 1):
            self.log_progress(task_id, f"  {i}. {title}")
        
        batch_extracted = 0
        batch_failed = 0
        
        # 对每个搜索词进行提取
        allowed_document_ids = {str(doc.id) for doc in documents}
        successfully_processed_doc_ids = set()
        extraction_attempt_cache: Dict[str, Dict[str, Any]] = {}
        max_failed_attempts_per_document = 3
        for query_idx, query in enumerate(search_queries, 1):
            self.log_progress(task_id, f"  使用搜索词 [{query_idx}/{len(search_queries)}]: '{query}'")
            
            try:
                remaining_allowed_document_ids = allowed_document_ids - successfully_processed_doc_ids
                if not remaining_allowed_document_ids:
                    self.log_progress(task_id, "    [skip] all documents in this batch already extracted successfully")
                    break
                # 使用特定查询词搜索这批文档
                task = rag_meteorite_extractor.extract_from_existing_documents(
                    search_query=query,
                    max_documents=len(remaining_allowed_document_ids),
                    preview_only=False,
                    allowed_document_ids=remaining_allowed_document_ids,
                    extraction_attempt_cache=extraction_attempt_cache,
                    max_failed_attempts_per_document=max_failed_attempts_per_document,
                )
                
                if task.get("status") == "completed":
                    skipped_attempts = int(task.get("skipped_attempts", 0) or 0)
                    would_skip_attempts = int(task.get("would_skip_attempts", 0) or 0)
                    would_skip_successes = int(task.get("would_skip_successes", 0) or 0)
                    if skipped_attempts > 0:
                        self.log_progress(
                            task_id,
                            f"    [skip] 查询 '{query}' 跳过了 {skipped_attempts} 个已尝试上下文/超过失败上限的文档候选",
                        )
                    if would_skip_attempts > 0:
                        self.log_progress(
                            task_id,
                            f"    [shadow] 查询 '{query}' 命中 {would_skip_attempts} 个 high-overlap low-novelty 候选（其中 {would_skip_successes} 个实际抽取成功）",
                        )
                    # 统计本次提取的成功数量
                    results = task.get("results", [])
                    successful_extractions = [r for r in results if r.get("success", False)]
                    batch_extracted += len(successful_extractions)
                    successful_doc_ids = {
                        str(result.get("document_id"))
                        for result in successful_extractions
                        if result.get("document_id")
                    }
                    successfully_processed_doc_ids.update(successful_doc_ids)
                    
                    # 优化：批量获取文档信息，避免N+1查询
                    doc_ids = [r.get("document_id") for r in successful_extractions if r.get("document_id")]
                    if doc_ids:
                        # 一次性查询所有文档
                        docs_dict = {
                            str(doc.id): doc 
                            for doc in PDFDocument.objects.filter(id__in=doc_ids).only('id', 'title')  # type: ignore
                        }
                        
                        # 记录提取的文档信息
                        for result in successful_extractions:
                            document_id = result.get("document_id")
                            if document_id:
                                self.processed_doc_ids.add(document_id)
                                # 从预加载的字典中获取文档标题
                                doc = docs_dict.get(str(document_id))
                                if doc:
                                    self.log_progress(task_id, f"    [成功] 从 '{doc.title[:30]}...' 提取成功")
                                else:
                                    self.log_progress(task_id, f"    [成功] 从文档ID {document_id} 提取成功")
                else:
                    batch_failed += 1
                    self.log_progress(task_id, f"    [失败] 查询 '{query}' 失败: {task.get('error_message', '未知错误')}")
                
                # 短暂休息
                if total_docs > 0 and search_queries:
                    query_progress = query_idx / len(search_queries)
                    in_batch_processed = max(1, round(len(documents) * query_progress)) if documents else 0
                    processed_estimate = min(total_docs, processed_before_batch + in_batch_processed)
                    progress_percentage = (processed_estimate / total_docs) * 100
                    self.update_task_progress(
                        task_id,
                        status='running',
                        processed_documents=processed_estimate,
                        successful_extractions=successful_before_batch + batch_extracted,
                        failed_extractions=failed_before_batch + batch_failed,
                        progress_percentage=progress_percentage,
                        status_text=f'running batch {batch_num + 1}/{total_batches} query {query_idx}/{len(search_queries)}',
                        results_update={
                            'current_batch': batch_num + 1,
                            'total_batches': total_batches,
                            'processed_doc_ids': list(self.processed_doc_ids),
                            'extraction_log': self.extraction_log[-30:]
                        }
                    )
                if self.query_sleep_seconds > 0:
                    time.sleep(self.query_sleep_seconds)
                
            except Exception as e:
                batch_failed += 1
                if total_docs > 0 and search_queries:
                    query_progress = query_idx / len(search_queries)
                    in_batch_processed = max(1, round(len(documents) * query_progress)) if documents else 0
                    processed_estimate = min(total_docs, processed_before_batch + in_batch_processed)
                    progress_percentage = (processed_estimate / total_docs) * 100
                    self.update_task_progress(
                        task_id,
                        status='running',
                        processed_documents=processed_estimate,
                        successful_extractions=successful_before_batch + batch_extracted,
                        failed_extractions=failed_before_batch + batch_failed,
                        progress_percentage=progress_percentage,
                        status_text=f'running batch {batch_num + 1}/{total_batches} query {query_idx}/{len(search_queries)}',
                        results_update={
                            'current_batch': batch_num + 1,
                            'total_batches': total_batches,
                            'processed_doc_ids': list(self.processed_doc_ids),
                            'extraction_log': self.extraction_log[-30:]
                        }
                    )
                self.log_progress(task_id, f"    [失败] 查询 '{query}' 出错: {str(e)}")
                continue
        
        return batch_extracted
    
    def resume_batch_extraction(self, task_id: str) -> bool:
        """恢复批量提取任务"""
        from .task_checkpoint_manager import checkpoint_manager
        
        try:
            # 获取任务信息
            task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
            
            if task.status not in ['paused', 'failed']:
                logger.error(f"任务 {task_id} 状态为 {task.status}，无法恢复")
                return False
            
            self.log_progress(task_id, "[恢复] 恢复批量提取任务")
            
            # 优先从检查点恢复状态
            checkpoint_data = checkpoint_manager.load_latest_checkpoint(task_id)
            
            if checkpoint_data:
                self.log_progress(task_id, "💾 从检查点恢复任务状态")
                
                # 从检查点恢复状态
                self.processed_doc_ids = set(checkpoint_data.get('processed_doc_ids', []))
                self.extraction_log = checkpoint_data.get('extraction_log', [])
                
                # 获取检查点中的参数
                batch_info = checkpoint_data.get('current_batch', {})
                progress_info = checkpoint_data.get('progress', {})
                additional_data = checkpoint_data.get('additional_data', {})
                
                # 从检查点或任务参数获取配置
                search_queries = additional_data.get('search_queries') or task.parameters.get('search_queries', [])
                extraction_options = additional_data.get('extraction_options') or task.parameters.get('extraction_options', {})
                batch_size = batch_info.get('batch_size') or task.parameters.get('batch_size', 10)
                
                self.log_progress(task_id, f"📋 从检查点恢复: {len(self.processed_doc_ids)} 个已处理文档")
                self.log_progress(task_id, f"[统计] 恢复进度: {progress_info.get('progress_percentage', 0):.1f}%")
                
            else:
                self.log_progress(task_id, "[警告] 未找到检查点，从任务结果恢复")
                
                # 从任务参数中获取配置
                parameters = task.parameters or {}
                batch_size = parameters.get('batch_size', 10)
                search_queries = parameters.get('search_queries', [])
                extraction_options = parameters.get('extraction_options', {})
                
                # 恢复已处理文档记录（从任务结果中恢复状态）
                if task.results and 'processed_doc_ids' in task.results:
                    self.processed_doc_ids = set(task.results['processed_doc_ids'])
                    self.log_progress(task_id, f"📋 恢复已处理文档记录: {len(self.processed_doc_ids)} 个")
                
                # 恢复提取日志
                if task.results and 'extraction_log' in task.results:
                    self.extraction_log = task.results['extraction_log'][-20:]  # 保留最近20条日志
                    self.log_progress(task_id, "📋 恢复提取日志记录")
            
            # 更新任务状态为运行中
            self.update_task_progress(task_id, 
                                    status='running',
                                    results_update={
                                        'resumed_at': timezone.now().isoformat(),
                                        'processed_doc_ids': list(self.processed_doc_ids),
                                        'extraction_log': self.extraction_log,
                                        'resume_method': 'checkpoint' if checkpoint_data else 'task_results'
                                    })
            
            # 继续执行批量提取（从中断点开始）
            return self.execute_batch_extraction(task_id, batch_size, search_queries, extraction_options, resume=True)
            
        except DataExtractionTask.DoesNotExist:  # type: ignore
            logger.error(f"任务 {task_id} 不存在")
            return False
        except Exception as e:
            logger.error(f"恢复批量提取任务失败: {str(e)}")
            
            # 记录恢复失败的错误
            try:
                self.update_task_progress(task_id,
                                        status='failed',
                                        results_update={
                                            'resume_error': str(e),
                                            'resume_failed_at': timezone.now().isoformat()
                                        })
            except:
                pass
            
            return False

    def execute_batch_extraction(self, task_id: str, batch_size: int, 
                               search_queries: List[str], extraction_options: Dict[str, Any], resume: bool = False, stop_event=None):
        """执行完整的批量提取"""
        from .task_checkpoint_manager import checkpoint_manager
        
        try:
            if resume:
                self.log_progress(task_id, "[恢复] 恢复批量提取陨石数据")
            else:
                self.log_progress(task_id, "🚀 开始批量提取陨石数据")
            
            # 更新任务状态（只在非恢复模式下设置started_at）
            update_data = {'status': 'running'}
            if not resume:
                update_data['started_at'] = timezone.now().isoformat()
            
            self.update_task_progress(task_id, **update_data)
            
            # 初始化服务
            if not rag_meteorite_extractor.initialize_services():
                self.log_progress(task_id, "[失败] 服务初始化失败")
                self.update_task_progress(task_id, 
                                        status='failed',
                                        completed_at=timezone.now())
                return False
            
            # 如果没有提供搜索词，使用默认的全面搜索词
            if not search_queries:
                search_queries = self.get_default_search_terms()
                self.log_progress(task_id, f"使用默认搜索词列表: {len(search_queries)} 个")
            
            # 优化批次大小
            batch_size = min(batch_size, 20)  # 减少批次大小以提高效率
            
            # 获取所有文档
            all_documents = list(PDFDocument.objects.all().order_by('id'))  # type: ignore  # type: ignore
            total_docs = len(all_documents)
            total_batches = (total_docs + batch_size - 1) // batch_size
            
            self.log_progress(task_id, f"[文档] 总文档数: {total_docs}")
            self.log_progress(task_id, f"📦 批次大小: {batch_size}")
            self.log_progress(task_id, f"🔢 总批次数: {total_batches}")
            
            # 如果是恢复模式，跳过已处理的文档
            if resume:
                remaining_docs = [doc for doc in all_documents if doc.id not in self.processed_doc_ids]
                self.log_progress(task_id, f"📋 跳过已处理文档: {len(self.processed_doc_ids)} 个")
                self.log_progress(task_id, f"[文档] 剩余待处理文档: {len(remaining_docs)} 个")
                all_documents = remaining_docs
                total_docs = len(all_documents)
                total_batches = (total_docs + batch_size - 1) // batch_size if total_docs > 0 else 0
            
            # 更新任务信息
            self.update_task_progress(task_id,
                                    total_documents=total_docs,  # 始终更新总文档数
                                    results_update={
                                        'total_batches': total_batches,
                                        'current_batch': 0,
                                        'search_queries_count': len(search_queries)
                                    })
            
            # 记录初始状态
            initial_count = Meteorite.objects.count()  # type: ignore  # type: ignore
            self.log_progress(task_id, f"[统计] 提取前数据库中有 {initial_count} 条陨石记录")
            
            total_extracted = 0
            
            # 分批处理
            for batch_num in range(total_batches):
                # 优先检查停止事件（直接停止）
                if stop_event and stop_event.is_set():
                    self.log_progress(task_id, "🛑 收到停止信号，立即停止执行")
                    return True
                
                # 检查任务状态，如果被停止或暂停则退出
                try:
                    current_task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
                    # 刷新数据库对象以获取最新状态
                    current_task.refresh_from_db()
                    if current_task.status in ['cancelled', 'paused']:
                        self.log_progress(task_id, f"🛑 任务状态已变更为 {current_task.status}，停止执行")
                        return True  # 正常退出，不标记为失败
                except DataExtractionTask.DoesNotExist:  # type: ignore
                    self.log_progress(task_id, "[失败] 任务已被删除，停止执行")
                    return False
                
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total_docs)
                batch_docs = all_documents[start_idx:end_idx]
                
                self.log_progress(task_id, f"\n[恢复] [{batch_num + 1}/{total_batches}] 处理批次 {batch_num + 1}")
                self.log_progress(task_id, f"[文档] 文档范围: {start_idx + 1} - {end_idx}")
                
                # 更新当前批次
                self.update_task_progress(task_id,
                                        results_update={'current_batch': batch_num + 1})
                
                try:
                    batch_extracted = self.extract_from_document_batch(
                        task_id,
                        batch_docs,
                        search_queries,
                        batch_num=batch_num,
                        total_batches=total_batches,
                        total_docs=total_docs,
                        processed_before_batch=start_idx,
                        successful_before_batch=total_extracted,
                    )
                    total_extracted += batch_extracted
                    
                    # 更新进度
                    processed_docs = (batch_num + 1) * batch_size
                    if processed_docs > total_docs:
                        processed_docs = total_docs
                    
                    self.update_task_progress(task_id,
                                            processed_documents=processed_docs,
                                            successful_extractions=total_extracted,
                                            results_update={
                                                'processed_doc_ids': list(self.processed_doc_ids),
                                                'extraction_log': self.extraction_log[-30:]  # 保存最近30条日志
                                            })
                    
                    self.log_progress(task_id, f"[成功] 批次 {batch_num + 1} 完成，提取 {batch_extracted} 条记录")
                    
                    # 显示总体进度
                    progress = ((batch_num + 1) / total_batches) * 100
                    self.log_progress(task_id, f"📈 总体进度: {progress:.1f}% ({batch_num + 1}/{total_batches})")
                    
                    # 保存检查点（每处理完一个批次）
                    if checkpoint_manager.should_save_checkpoint(len(self.processed_doc_ids)):
                        checkpoint_data = checkpoint_manager.create_checkpoint_data(
                            processed_doc_ids=list(self.processed_doc_ids),
                            extraction_log=self.extraction_log[-50:],  # 保存最近50条日志
                            current_batch={
                                'batch_num': batch_num + 1,
                                'total_batches': total_batches,
                                'batch_size': batch_size
                            },
                            progress={
                                'processed_documents': processed_docs,
                                'total_documents': total_docs,
                                'successful_extractions': total_extracted,
                                'progress_percentage': progress
                            },
                            additional_data={
                                'search_queries': search_queries,
                                'extraction_options': extraction_options
                            }
                        )
                        
                        if checkpoint_manager.save_checkpoint(task_id, checkpoint_data):
                            self.log_progress(task_id, f"💾 检查点已保存 (批次 {batch_num + 1})")
                    
                    # 批次间休息
                    if batch_num < total_batches - 1:  # 不是最后一批
                        self.log_progress(task_id, "⏸️ 批次间休息 3 秒...")
                        time.sleep(self.batch_sleep_seconds)
                    
                except Exception as e:
                    self.log_progress(task_id, f"[失败] 批次 {batch_num + 1} 处理出错: {str(e)}")
                    continue
            
            # 最终统计
            final_count = Meteorite.objects.count()  # type: ignore
            new_records = final_count - initial_count
            unique_docs_processed = len(self.processed_doc_ids)
            
            self.log_progress(task_id, f"\n🎉 批量提取完成!")
            self.log_progress(task_id, f"[统计] 最终统计:")
            self.log_progress(task_id, f"  • 新增陨石记录: {new_records}")
            self.log_progress(task_id, f"  • 处理的文档批次: {total_batches}")
            self.log_progress(task_id, f"  • 成功提取的唯一文档: {unique_docs_processed}")
            self.log_progress(task_id, f"  • 数据库总记录数: {final_count}")
            self.log_progress(task_id, f"  • 提取成功率: {(unique_docs_processed/total_docs)*100:.1f}%")
            
            # 清除检查点（任务完成后）
            checkpoint_manager.clear_checkpoints(task_id)
            self.log_progress(task_id, "🗑️ 已清除任务检查点")
            
            # 更新最终状态
            self.update_task_progress(task_id,
                                    status='completed',
                                    completed_at=timezone.now(),
                                    successful_extractions=new_records,
                                    results_update={
                                        'final_statistics': {
                                            'new_records': new_records,
                                            'unique_docs_processed': unique_docs_processed,
                                            'success_rate': (unique_docs_processed/total_docs)*100,
                                            'extraction_log': self.extraction_log[-50:]  # 保存最后50条日志
                                        },
                                        'processed_doc_ids': list(self.processed_doc_ids)  # 保存最终的已处理文档ID
                                    })
            
            return True
            
        except Exception as e:
            self.log_progress(task_id, f"💥 批量提取过程出错: {str(e)}")
            
            # 保存错误检查点
            try:
                checkpoint_data = checkpoint_manager.create_checkpoint_data(
                    processed_doc_ids=list(self.processed_doc_ids),
                    extraction_log=self.extraction_log[-30:],
                    current_batch={'error': True},
                    progress={
                        'processed_documents': len(self.processed_doc_ids),
                        'error_occurred': True
                    },
                    additional_data={'error_message': str(e)}
                )
                checkpoint_manager.save_checkpoint(task_id, checkpoint_data)
                self.log_progress(task_id, "💾 错误检查点已保存")
            except:
                pass  # 忽略检查点保存错误
            
            self.update_task_progress(task_id,
                                    status='failed',
                                    completed_at=timezone.now(),
                                    results_update={
                                        'error_message': str(e),
                                        'extraction_log': self.extraction_log[-20:]  # 保存最后20条日志
                                    })
            return False
