"""
现实的批量提取系统
基于Ollama单实例限制，采用智能串行处理策略
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import time
import json
from django.core.management.base import BaseCommand
from pdf_processor.rag_meteorite_extractor import RAGMeteoriteExtractor
from pdf_processor.semantic_chunker import SemanticChunker
from pdf_processor.cross_document_aggregator import CrossDocumentAggregator

logger = logging.getLogger(__name__)

@dataclass
class RealisticBatchConfig:
    """现实的批量提取配置"""
    batch_size: int = 10  # 每批处理的文档数（减少内存压力）
    min_confidence_threshold: float = 0.6  # 最小置信度阈值
    max_extraction_per_document: int = 3  # 每篇文档最大提取数
    enable_semantic_chunking: bool = True  # 启用语义分块
    enable_cross_document_aggregation: bool = True  # 启用跨文档聚合
    save_progress_interval: int = 5  # 每处理5个文档保存一次进度
    memory_cleanup_interval: int = 10  # 每处理10个文档清理一次内存

class RealisticBatchExtractor:
    """现实的批量提取器 - 串行处理，内存优化"""
    
    def __init__(self, config: RealisticBatchConfig = None):
        self.config = config or RealisticBatchConfig()
        self.extractor = RAGMeteoriteExtractor()
        self.chunker = SemanticChunker()
        self.aggregator = CrossDocumentAggregator()
        
        # 统计信息
        self.stats = {
            'total_documents': 0,
            'processed_documents': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'aggregated_meteorites': 0,
            'start_time': None,
            'end_time': None,
            'memory_cleanups': 0
        }
        
        # 进度保存
        self.progress_file = "batch_extraction_progress.json"
        self.extraction_results = []
    
    def extract_from_large_corpus(self, search_query: str = "meteorite", 
                                 max_documents: int = None) -> Dict[str, Any]:
        """
        从大型语料库中智能提取陨石信息 - 串行处理版本
        
        Args:
            search_query: 搜索查询
            max_documents: 最大处理文档数（None表示处理所有）
            
        Returns:
            提取结果统计
        """
        logger.info(f"开始现实批量提取，搜索查询: {search_query}")
        self.stats['start_time'] = time.time()
        
        # 第一步：初始化RAG服务
        if not self.extractor.initialize_services():
            raise Exception("RAG服务初始化失败")
        
        # 第二步：获取所有相关文档
        all_documents = self._get_all_relevant_documents(search_query, max_documents)
        self.stats['total_documents'] = len(all_documents)
        
        logger.info(f"找到 {len(all_documents)} 个相关文档")
        
        # 第三步：串行处理文档（内存优化）
        all_extraction_results = []
        batches = self._create_batches(all_documents)
        
        for batch_idx, batch in enumerate(batches):
            logger.info(f"处理批次 {batch_idx + 1}/{len(batches)}")
            batch_results = self._process_batch_serial(batch, batch_idx)
            all_extraction_results.extend(batch_results)
            
            # 定期保存进度
            if (batch_idx + 1) % self.config.save_progress_interval == 0:
                self._save_progress(all_extraction_results, batch_idx + 1)
            
            # 定期清理内存
            if (batch_idx + 1) % self.config.memory_cleanup_interval == 0:
                self._cleanup_memory()
            
            # 显示进度
            progress = (batch_idx + 1) / len(batches) * 100
            logger.info(f"进度: {progress:.1f}% ({batch_idx + 1}/{len(batches)} 批次)")
        
        # 第四步：跨文档聚合
        if self.config.enable_cross_document_aggregation and all_extraction_results:
            logger.info("开始跨文档信息聚合...")
            aggregated_meteorites = self.aggregator.aggregate_meteorite_info(all_extraction_results)
            self.stats['aggregated_meteorites'] = len(aggregated_meteorites)
        else:
            aggregated_meteorites = []
        
        # 第五步：生成最终报告
        self.stats['end_time'] = time.time()
        final_report = self._generate_final_report(all_extraction_results, aggregated_meteorites)
        
        # 清理进度文件
        self._cleanup_progress_file()
        
        return final_report
    
    def _get_all_relevant_documents(self, search_query: str, max_documents: int = None) -> List[Dict]:
        """获取所有相关文档"""
        # 使用RAG服务搜索所有相关文档
        meteorite_segments = self.extractor._search_meteorite_segments_optimized(max_documents or 0)
        
        # 按文档ID分组
        documents = defaultdict(list)
        for segment in meteorite_segments:
            doc_id = segment.get('document_id', 'unknown')
            documents[doc_id].append(segment)
        
        # 转换为文档列表
        document_list = []
        for doc_id, segments in documents.items():
            document_list.append({
                'document_id': doc_id,
                'segments': segments,
                'segment_count': len(segments)
            })
        
        # 按片段数量排序（片段多的文档优先处理）
        document_list.sort(key=lambda x: x['segment_count'], reverse=True)
        
        if max_documents:
            document_list = document_list[:max_documents]
        
        return document_list
    
    def _create_batches(self, documents: List[Dict]) -> List[List[Dict]]:
        """创建处理批次"""
        batches = []
        batch_size = self.config.batch_size
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batches.append(batch)
        
        return batches
    
    def _process_batch_serial(self, batch: List[Dict], batch_idx: int) -> List[Dict]:
        """串行处理单个批次"""
        batch_results = []
        
        for doc_idx, doc in enumerate(batch):
            try:
                result = self._process_single_document(doc, batch_idx, doc_idx)
                if result:
                    batch_results.extend(result)
                    self.stats['successful_extractions'] += len(result)
                else:
                    self.stats['failed_extractions'] += 1
                    
            except Exception as e:
                logger.error(f"处理文档 {doc['document_id']} 失败: {e}")
                self.stats['failed_extractions'] += 1
        
        self.stats['processed_documents'] += len(batch)
        return batch_results
    
    def _process_single_document(self, document: Dict, batch_idx: int, doc_idx: int) -> List[Dict]:
        """处理单个文档"""
        doc_id = document['document_id']
        segments = document['segments']
        
        logger.info(f"处理文档 {doc_idx + 1}/{len(document)}: {doc_id}")
        
        extraction_results = []
        
        # 限制每篇文档的提取数量
        max_extractions = min(len(segments), self.config.max_extraction_per_document)
        
        for i, segment in enumerate(segments[:max_extractions]):
            try:
                # 使用语义分块优化文本
                if self.config.enable_semantic_chunking:
                    text = segment.get('content', '')
                    chunks = self.chunker.chunk_text_semantic(text, target_size=3000, overlap=800)
                    
                    # 选择最佳分块进行提取
                    best_chunk = self._select_best_chunk(chunks)
                    if best_chunk:
                        segment['content'] = best_chunk
                
                # 执行数据提取（串行）
                result = self.extractor.extract_from_segment(segment)
                
                if result and result.get('confidence_score', 0) >= self.config.min_confidence_threshold:
                    # 添加文档信息
                    result['extraction_metadata'] = {
                        'document_id': doc_id,
                        'batch_idx': batch_idx,
                        'doc_idx': doc_idx,
                        'segment_idx': i,
                        'total_segments': len(segments)
                    }
                    extraction_results.append(result)
                    
            except Exception as e:
                logger.error(f"提取片段 {i} 失败: {e}")
                continue
        
        return extraction_results
    
    def _select_best_chunk(self, chunks: List[str]) -> Optional[str]:
        """选择最佳分块"""
        if not chunks:
            return None
        
        # 评分标准：陨石关键词密度
        meteorite_keywords = [
            'meteorite', 'chondrite', 'achondrite', 'shergottite',
            'amino acid', 'organic compound', 'carbonaceous',
            'classification', 'discovered', 'found', 'recovered'
        ]
        
        best_chunk = None
        best_score = 0
        
        for chunk in chunks:
            score = 0
            chunk_lower = chunk.lower()
            
            for keyword in meteorite_keywords:
                score += chunk_lower.count(keyword)
            
            # 长度奖励（避免过短的分块）
            length_bonus = min(len(chunk) / 1000, 1.0)
            total_score = score + length_bonus
            
            if total_score > best_score:
                best_score = total_score
                best_chunk = chunk
        
        return best_chunk
    
    def _save_progress(self, results: List[Dict], batch_count: int):
        """保存进度"""
        progress_data = {
            'batch_count': batch_count,
            'results_count': len(results),
            'timestamp': time.time(),
            'stats': self.stats.copy()
        }
        
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            logger.info(f"进度已保存: 批次 {batch_count}, 结果 {len(results)}")
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
    
    def _cleanup_memory(self):
        """清理内存"""
        import gc
        gc.collect()
        self.stats['memory_cleanups'] += 1
        logger.info(f"内存清理完成 (第 {self.stats['memory_cleanups']} 次)")
    
    def _cleanup_progress_file(self):
        """清理进度文件"""
        try:
            import os
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
                logger.info("进度文件已清理")
        except Exception as e:
            logger.error(f"清理进度文件失败: {e}")
    
    def _generate_final_report(self, extraction_results: List[Dict], 
                             aggregated_meteorites: List) -> Dict[str, Any]:
        """生成最终报告"""
        processing_time = self.stats['end_time'] - self.stats['start_time']
        
        report = {
            'processing_stats': {
                'total_documents': self.stats['total_documents'],
                'processed_documents': self.stats['processed_documents'],
                'successful_extractions': self.stats['successful_extractions'],
                'failed_extractions': self.stats['failed_extractions'],
                'processing_time_seconds': processing_time,
                'documents_per_minute': (self.stats['processed_documents'] / processing_time * 60) if processing_time > 0 else 0,
                'memory_cleanups': self.stats['memory_cleanups']
            },
            'extraction_stats': {
                'total_extractions': len(extraction_results),
                'unique_meteorites': len(set(r.get('meteorite_data', {}).get('name', 'Unknown') for r in extraction_results)),
                'avg_confidence': sum(r.get('confidence_score', 0) for r in extraction_results) / len(extraction_results) if extraction_results else 0,
                'high_confidence_extractions': sum(1 for r in extraction_results if r.get('confidence_score', 0) >= 0.8)
            },
            'aggregation_stats': {
                'aggregated_meteorites': self.stats['aggregated_meteorites'],
                'aggregation_report': self.aggregator.generate_aggregation_report(aggregated_meteorites) if aggregated_meteorites else {}
            },
            'quality_metrics': {
                'extraction_success_rate': (self.stats['successful_extractions'] / max(self.stats['processed_documents'], 1)) * 100,
                'avg_extractions_per_document': self.stats['successful_extractions'] / max(self.stats['processed_documents'], 1),
                'processing_efficiency': self.stats['processed_documents'] / processing_time if processing_time > 0 else 0
            }
        }
        
        return report


class Command(BaseCommand):
    help = '现实的批量提取系统 - 串行处理，内存优化'

    def add_arguments(self, parser):
        parser.add_argument(
            '--search-query',
            type=str,
            default='meteorite',
            help='搜索查询词'
        )
        parser.add_argument(
            '--max-documents',
            type=int,
            default=None,
            help='最大处理文档数（None表示处理所有）'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='每批处理的文档数'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.6,
            help='最小置信度阈值'
        )

    def handle(self, *args, **options):
        self.stdout.write("🚀 现实的批量提取系统")
        self.stdout.write("=" * 50)
        
        # 配置参数
        config = RealisticBatchConfig(
            batch_size=options['batch_size'],
            min_confidence_threshold=options['min_confidence']
        )
        
        self.stdout.write(f"📊 配置参数:")
        self.stdout.write(f"  搜索查询: {options['search_query']}")
        self.stdout.write(f"  最大文档数: {options['max_documents'] or '全部'}")
        self.stdout.write(f"  批次大小: {config.batch_size}")
        self.stdout.write(f"  最小置信度: {config.min_confidence_threshold}")
        self.stdout.write(f"  进度保存间隔: {config.save_progress_interval}")
        self.stdout.write(f"  内存清理间隔: {config.memory_cleanup_interval}")
        
        # 创建提取器
        extractor = RealisticBatchExtractor(config)
        
        try:
            # 执行批量提取
            self.stdout.write(f"\n🔍 开始现实批量提取...")
            report = extractor.extract_from_large_corpus(
                search_query=options['search_query'],
                max_documents=options['max_documents']
            )
            
            # 显示结果
            self._display_results(report)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 批量提取失败: {e}"))
            logger.error(f"批量提取失败: {e}")
    
    def _display_results(self, report: Dict[str, Any]):
        """显示提取结果"""
        self.stdout.write(f"\n📈 提取结果统计:")
        
        # 处理统计
        processing_stats = report['processing_stats']
        self.stdout.write(f"\n  📊 处理统计:")
        self.stdout.write(f"    总文档数: {processing_stats['total_documents']}")
        self.stdout.write(f"    已处理: {processing_stats['processed_documents']}")
        self.stdout.write(f"    成功提取: {processing_stats['successful_extractions']}")
        self.stdout.write(f"    失败提取: {processing_stats['failed_extractions']}")
        self.stdout.write(f"    处理时间: {processing_stats['processing_time_seconds']:.1f} 秒")
        self.stdout.write(f"    处理速度: {processing_stats['documents_per_minute']:.1f} 文档/分钟")
        self.stdout.write(f"    内存清理次数: {processing_stats['memory_cleanups']}")
        
        # 提取统计
        extraction_stats = report['extraction_stats']
        self.stdout.write(f"\n  🔍 提取统计:")
        self.stdout.write(f"    总提取数: {extraction_stats['total_extractions']}")
        self.stdout.write(f"    唯一陨石数: {extraction_stats['unique_meteorites']}")
        self.stdout.write(f"    平均置信度: {extraction_stats['avg_confidence']:.3f}")
        self.stdout.write(f"    高置信度提取: {extraction_stats['high_confidence_extractions']}")
        
        # 聚合统计
        aggregation_stats = report['aggregation_stats']
        self.stdout.write(f"\n  🔗 聚合统计:")
        self.stdout.write(f"    聚合陨石数: {aggregation_stats['aggregated_meteorites']}")
        
        # 质量指标
        quality_metrics = report['quality_metrics']
        self.stdout.write(f"\n  🎯 质量指标:")
        self.stdout.write(f"    提取成功率: {quality_metrics['extraction_success_rate']:.1f}%")
        self.stdout.write(f"    平均每文档提取数: {quality_metrics['avg_extractions_per_document']:.1f}")
        self.stdout.write(f"    处理效率: {quality_metrics['processing_efficiency']:.1f} 文档/秒")
        
        self.stdout.write(self.style.SUCCESS("\n✅ 现实批量提取完成"))
