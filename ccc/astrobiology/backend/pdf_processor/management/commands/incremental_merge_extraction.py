"""
增量合并的分布式提取系统
基于现有的一篇篇提取，实现智能数据合并
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from collections import defaultdict
import time
import json
import difflib
from django.core.management.base import BaseCommand
from pdf_processor.rag_meteorite_extractor import RAGMeteoriteExtractor
from meteorite_search.models import Meteorite
from meteorite_search.review_models import PendingMeteorite
from django.db.models import Q

logger = logging.getLogger(__name__)

@dataclass
class IncrementalMergeConfig:
    """增量合并配置"""
    similarity_threshold: float = 0.8  # 相似度阈值
    merge_strategy: str = "intelligent"  # 合并策略: intelligent, conservative, aggressive
    enable_field_level_merge: bool = True  # 启用字段级合并
    enable_confidence_weighting: bool = True  # 启用置信度加权
    save_interval: int = 10  # 每处理10个文档保存一次

class IncrementalMergeExtractor:
    """增量合并提取器"""
    
    def __init__(self, config: IncrementalMergeConfig = None):
        self.config = config or IncrementalMergeConfig()
        self.extractor = RAGMeteoriteExtractor()
        self.preview_only = False
        self.preview_results: List[Dict[str, Any]] = []
        
        # 统计信息
        self.stats = {
            'total_documents': 0,
            'processed_documents': 0,
            'new_extractions': 0,
            'merged_extractions': 0,
            'total_meteorites': 0,
            'start_time': None,
            'end_time': None
        }

        self._last_logged_progress = -10.0
        
        # 现有数据缓存
        self.existing_meteorites = {}
        self._load_existing_data()
    
    def _load_existing_data(self):
        """加载现有的陨石数据"""
        logger.info("加载现有陨石数据...")
        
        # 从已审核的陨石中加载
        approved_meteorites = Meteorite.objects.all()
        for meteorite in approved_meteorites:
            key = self._generate_meteorite_key(meteorite.name, meteorite.classification)
            self.existing_meteorites[key] = {
                'source': 'approved',
                'data': meteorite,
                'confidence': meteorite.confidence_score or 0.5
            }
        
        # 从待审核的陨石中加载
        pending_meteorites = PendingMeteorite.objects.all()
        for meteorite in pending_meteorites:
            key = self._generate_meteorite_key(meteorite.name, meteorite.classification)
            if key not in self.existing_meteorites:  # 避免重复
                self.existing_meteorites[key] = {
                    'source': 'pending',
                    'data': meteorite,
                    'confidence': meteorite.confidence_score or 0.5
                }
        
        logger.info("现有陨石数据加载完成，共 %d 条", len(self.existing_meteorites))

    def _log_progress_summary(self, progress_percentage: float, processed: int, total: int) -> None:
        """输出简洁的进度日志，避免过于频繁的记录"""
        if progress_percentage is None:
            progress_percentage = 0.0

        should_log = False
        if processed <= 1 and self._last_logged_progress < 0:
            should_log = True
        elif progress_percentage - self._last_logged_progress >= 5:
            should_log = True
        elif total and processed >= total:
            should_log = True

        if should_log:
            total_display = total if total else '未知'
            logger.info("提取进度 %.1f%% (%s/%s)", progress_percentage, processed, total_display)
            self._last_logged_progress = progress_percentage
    
    def _generate_meteorite_key(self, name: str, classification: str) -> str:
        """生成陨石唯一标识"""
        # 标准化名称和分类
        normalized_name = name.lower().strip() if name else "unknown"
        normalized_classification = classification.lower().strip() if classification else "unknown"
        
        return f"{normalized_name}|{normalized_classification}"
    
    def extract_and_merge_from_corpus(self, search_query: str = "meteorite",
                                    max_documents: int = None,
                                    relevance_threshold: float = None,
                                    preview_only: bool = False,
                                    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                                    stop_event: Optional[Any] = None,
                                    pause_event: Optional[Any] = None) -> Dict[str, Any]:
        """
        从语料库中提取并增量合并陨石信息
        
        Args:
            search_query: 搜索查询
            max_documents: 最大处理文档数
            
        Returns:
            提取和合并结果统计
        """
        logger.info(f"开始增量合并提取，搜索查询: {search_query}")
        self.stats['start_time'] = time.time()
        self.preview_only = bool(preview_only)
        self.preview_results = []
        self._last_logged_progress = -10.0
        
        # 初始化RAG服务
        if not self.extractor.initialize_services():
            raise Exception("RAG服务初始化失败")
        
        # 获取相关文档
        all_documents = self._get_all_relevant_documents(search_query, max_documents, relevance_threshold)
        self.stats['total_documents'] = len(all_documents)
        
        logger.info("相关文档检索完成，共 %d 篇", len(all_documents))
        
        # 逐个处理文档
        for doc_idx, document in enumerate(all_documents):
            if stop_event and stop_event.is_set():
                logger.info("检测到停止信号，终止提取循环")
                self.stats['stop_requested'] = True
                break

            if pause_event and pause_event.is_set():
                logger.info("检测到暂停信号，进入等待状态")
                if progress_callback:
                    try:
                        progress_callback({
                            'status': 'paused',
                            'progress_percentage': (doc_idx / len(all_documents)) * 100 if len(all_documents) else 0,
                            'total_documents': len(all_documents),
                            'processed_documents': self.stats.get('processed_documents', doc_idx),
                            'successful_extractions': self.stats.get('merged_extractions', 0) + self.stats.get('new_extractions', 0),
                            'failed_extractions': 0,
                            'status_text': '任务已暂停'
                        })
                    except Exception:
                        pass
                while pause_event.is_set():
                    if stop_event and stop_event.is_set():
                        logger.info("暂停期间检测到停止信号，终止提取循环")
                        self.stats['stop_requested'] = True
                        break
                    time.sleep(0.5)
                if stop_event and stop_event.is_set():
                    break
                logger.info("恢复提取，继续处理文档")

            try:
                self._process_document_incremental(document, doc_idx)
                
                # 定期保存进度
                if (doc_idx + 1) % self.config.save_interval == 0:
                    self._save_progress(doc_idx + 1)
                
                # 显示并回调进度
                progress = (doc_idx + 1) / len(all_documents) * 100
                self._log_progress_summary(progress, doc_idx + 1, len(all_documents))
                if progress_callback:
                    try:
                        progress_callback({
                            'current_batch': 1,
                            'total_batches': 1,
                            'progress_percentage': progress,
                            'total_documents': len(all_documents),
                            'processed_documents': self.stats.get('processed_documents', doc_idx + 1),
                            'successful_extractions': self.stats.get('merged_extractions', 0) + self.stats.get('new_extractions', 0),
                            'failed_extractions': 0,
                            'status': 'running',
                            'status_text': f'处理中 {doc_idx + 1}/{len(all_documents)}'
                        })
                    except Exception:
                        pass
                
            except Exception as e:
                logger.error(f"处理文档 {doc_idx} 失败: {e}")
                continue
        
        # 生成最终报告
        self.stats['end_time'] = time.time()
        logger.info(
            "任务结束：处理 %d/%d 篇文档，新增 %d，合并 %d",
            self.stats['processed_documents'],
            self.stats['total_documents'],
            self.stats['new_extractions'],
            self.stats['merged_extractions']
        )
        final_report = self._generate_final_report()
        
        return final_report
    
    def _get_all_relevant_documents(self, search_query: str, max_documents: int = None, relevance_threshold: float = None) -> List[Dict]:
        """获取所有相关文档"""
        # 当 max_documents 为 0/None 时，按批次扩增抓取，直到基本穷尽或达到安全上限
        if not max_documents:
            step = 1000
            hard_cap = 10000  # 安全上限，防止资源耗尽
            filtered_keys = set()
            meteorite_segments = []
            last_count = 0
            while True:
                limit = min(len(meteorite_segments) + step, hard_cap)
                batch = self.extractor._search_meteorite_segments_optimized(search_query, limit)
                # 过滤阈值
                if relevance_threshold is not None:
                    try:
                        thr = float(relevance_threshold)
                        filtered_batch = [s for s in batch if float(s.get('score', 0.0) or 0.0) >= thr]
                        if filtered_batch:
                            batch = filtered_batch
                        else:
                            logger.info("相关性阈值 %.2f 未命中过滤结果，回退到未过滤的搜索结果", thr)
                    except Exception:
                        pass
                # 去重（document_id + chunk_index）
                unique_batch = []
                for s in batch:
                    key = (s.get('document_id', ''), s.get('chunk_index', 0))
                    if key not in filtered_keys:
                        filtered_keys.add(key)
                        unique_batch.append(s)
                meteorite_segments = unique_batch  # 由于每次取的是前 limit 个top结果，这里保持去重后的前缀
                # 终止条件：增长停滞或达到上限
                if len(meteorite_segments) <= last_count or limit >= hard_cap:
                    break
                last_count = len(meteorite_segments)
        else:
            # 固定上限抓取
            limit = max_documents if (isinstance(max_documents, int) and max_documents > 0) else 1000
            meteorite_segments = self.extractor._search_meteorite_segments_optimized(search_query, limit)
            # 应用相关性阈值过滤（如果提供）
            if relevance_threshold is not None:
                try:
                    thr = float(relevance_threshold)
                    filtered_segments = [s for s in meteorite_segments if float(s.get('score', 0.0) or 0.0) >= thr]
                    if filtered_segments:
                        meteorite_segments = filtered_segments
                    else:
                        logger.info("相关性阈值 %.2f 未命中过滤结果，回退到未过滤的搜索结果", thr)
                except Exception:
                    pass
        
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
        
        # 按片段数量排序
        document_list.sort(key=lambda x: x['segment_count'], reverse=True)
        
        if max_documents:
            document_list = document_list[:max_documents]
        
        return document_list
    
    def _process_document_incremental(self, document: Dict, doc_idx: int):
        """增量处理单个文档"""
        doc_id = document['document_id']
        segments = document['segments']
        
        logger.debug("处理文档 %d: %s", doc_idx + 1, doc_id)
        
        # 限制每篇文档的提取数量
        max_extractions = min(len(segments), 3)  # 每文档最多3个提取
        
        for i, segment in enumerate(segments[:max_extractions]):
            try:
                # 执行数据提取
                # 提取管道当前的抽取器需要一个 extraction_options 参数
                # （即使实际未使用），因此传入一个默认的空配置，避免 TypeError
                result = self.extractor.extract_from_segment(segment, {})
                
                # 处理不同的置信度字段名
                confidence = (result.get('confidence_score') or 
                             result.get('confidence') or 
                             result.get('data', {}).get('confidence', 0))
                
                # 确保置信度是数字
                if isinstance(confidence, str) and confidence != 'N/A':
                    try:
                        confidence = float(confidence)
                    except ValueError:
                        confidence = 0
                elif confidence == 'N/A':
                    confidence = 0
                
                if result and isinstance(confidence, (int, float)) and confidence >= 0.6:
                    if self.preview_only:
                        self.preview_results.append(
                            self._build_preview_extraction_entry(document, segment, result, confidence)
                        )
                        self.stats['new_extractions'] += 1
                        logger.debug("preview extraction buffered for document %s", doc_id)
                    else:
                        # 尝试合并到现有数据
                        merged = self._try_merge_with_existing(result)
                        
                        if merged:
                            self.stats['merged_extractions'] += 1
                            logger.debug("成功合并数据: %s", result.get('meteorite_data', {}).get('name', 'Unknown'))
                        else:
                            self.stats['new_extractions'] += 1
                            logger.debug("新增数据: %s", result.get('meteorite_data', {}).get('name', 'Unknown'))
                    
            except Exception as e:
                logger.error(f"提取片段 {i} 失败: {e}")
                continue
        
        self.stats['processed_documents'] += 1

    def _build_preview_extraction_entry(
        self,
        document: Dict,
        segment: Dict[str, Any],
        result: Dict[str, Any],
        confidence: float,
    ) -> Dict[str, Any]:
        payload = result.get('data') or {}
        meteorite_data = payload.get('meteorite_data', payload)
        if not isinstance(meteorite_data, dict):
            meteorite_data = {}

        return {
            'success': True,
            'meteorite_data': meteorite_data,
            'confidence': float(confidence),
            'source_info': {
                'document_id': document.get('document_id', segment.get('document_id', '')),
                'title': segment.get('title', ''),
                'chunk_index': segment.get('chunk_index', 0),
                'score': segment.get('score', 0.0),
            },
        }
    
    def _try_merge_with_existing(self, new_result: Dict) -> bool:
        """尝试将新结果合并到现有数据"""
        # 处理不同的数据结构
        if 'data' in new_result and new_result['data']:
            meteorite_data = new_result['data'].get('meteorite_data', {})
            confidence_score = new_result['data'].get('confidence', 0)
        else:
            meteorite_data = new_result.get('meteorite_data', {})
            confidence_score = new_result.get('confidence_score', 0)
        
        name = meteorite_data.get('name', 'Unknown')
        classification = meteorite_data.get('classification', 'Unknown')
        
        # 生成新数据的键
        new_key = self._generate_meteorite_key(name, classification)
        
        # 查找最相似的现有数据
        best_match = self._find_best_match(new_result)
        
        if best_match:
            # 执行合并
            self._merge_meteorite_data(best_match, new_result)
            return True
        else:
            # 创建新记录
            self._create_new_meteorite(new_result)
            return False
    
    def _find_best_match(self, new_result: Dict) -> Optional[Dict]:
        """查找最相似的现有陨石数据"""
        # 处理不同的数据结构
        if 'data' in new_result and new_result['data']:
            meteorite_data = new_result['data'].get('meteorite_data', {})
        else:
            meteorite_data = new_result.get('meteorite_data', {})

        name = meteorite_data.get('name', 'Unknown') or 'Unknown'
        classification = meteorite_data.get('classification', 'Unknown') or 'Unknown'
        location = meteorite_data.get('discovery_location', meteorite_data.get('location', 'Unknown')) or 'Unknown'
        origin = meteorite_data.get('origin', 'Unknown') or 'Unknown'
        new_refs = self._extract_reference_keys(meteorite_data.get('references', []))

        best_match = None
        best_score = 0.0

        for key, existing in self.existing_meteorites.items():
            existing_data = existing['data']
            existing_name = getattr(existing_data, 'name', 'Unknown') or 'Unknown'
            existing_classification = getattr(existing_data, 'classification', 'Unknown') or 'Unknown'
            existing_location = getattr(existing_data, 'discovery_location', 'Unknown') or 'Unknown'
            existing_origin = getattr(existing_data, 'origin', 'Unknown') or 'Unknown'
            existing_refs = self._extract_reference_keys(getattr(existing_data, 'references', []) or [])

            # 计算多信号相似度
            score = self._multi_signal_similarity(
                (name, classification, location, origin, new_refs),
                (existing_name, existing_classification, existing_location, existing_origin, existing_refs)
            )

            if score > best_score and score >= self.config.similarity_threshold:
                best_score = score
                best_match = existing

        return best_match
    
    def _calculate_similarity(self, name1: str, class1: str, name2: str, class2: str) -> float:
        """计算两个陨石的相似度"""
        # 名称相似度
        name_similarity = difflib.SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
        
        # 分类相似度
        class_similarity = difflib.SequenceMatcher(None, class1.lower(), class2.lower()).ratio()
        
        # 加权平均
        total_similarity = (name_similarity * 0.7 + class_similarity * 0.3)
        
        return total_similarity

    def _normalize_text(self, text: str) -> str:
        return (text or '').strip().lower()

    def _string_similarity(self, a: str, b: str) -> float:
        a_n = self._normalize_text(a)
        b_n = self._normalize_text(b)
        if not a_n or not b_n:
            return 0.0
        return difflib.SequenceMatcher(None, a_n, b_n).ratio()

    def _extract_reference_keys(self, refs: Any) -> Dict[str, set]:
        """抽取参考文献信息的关键集合（doi、title），用于重叠计算。"""
        dois = set()
        titles = set()
        if isinstance(refs, list):
            for r in refs:
                if isinstance(r, dict):
                    doi = self._normalize_text(r.get('doi', ''))
                    title = self._normalize_text(r.get('title', ''))
                    if doi:
                        dois.add(doi)
                    if title:
                        titles.add(title)
                elif isinstance(r, str):
                    titles.add(self._normalize_text(r))
        return {'dois': dois, 'titles': titles}

    def _overlap_ratio(self, a: set, b: set) -> float:
        if not a or not b:
            return 0.0
        inter = len(a & b)
        union = len(a | b)
        return inter / union if union else 0.0

    def _multi_signal_similarity(self, new_tuple, exist_tuple) -> float:
        """多信号综合相似度，兼容主字段缺失的情况。
        new_tuple: (name, class, location, origin, refs_keys)
        exist_tuple: 同上
        """
        n_name, n_class, n_loc, n_origin, n_refs = new_tuple
        e_name, e_class, e_loc, e_origin, e_refs = exist_tuple

        # 计算各项相似度
        name_sim = self._string_similarity(n_name, e_name)
        class_sim = self._string_similarity(n_class, e_class)
        loc_sim = self._string_similarity(n_loc, e_loc)
        origin_sim = self._string_similarity(n_origin, e_origin)
        ref_sim = max(
            self._overlap_ratio(n_refs.get('dois', set()), e_refs.get('dois', set())),
            self._overlap_ratio(n_refs.get('titles', set()), e_refs.get('titles', set()))
        )

        # 权重根据信息缺失自适应调整
        has_name = (self._normalize_text(n_name) not in ['', 'unknown'])
        has_class = (self._normalize_text(n_class) not in ['', 'unknown'])

        # 基础权重
        w_name = 0.5 if has_name else 0.0
        w_class = 0.2 if has_class else 0.0
        w_loc = 0.15
        w_ref = 0.15
        w_origin = 0.05

        # 如果主字段缺失，将权重分摊到其他信号
        residual = 0.7 - (w_name + w_class)
        if residual > 0:
            # 分摊到 loc/ref/origin
            w_loc += residual * 0.6
            w_ref += residual * 0.3
            w_origin += residual * 0.1

        # 归一化以保证总和<=1
        total_w = w_name + w_class + w_loc + w_ref + w_origin
        if total_w == 0:
            return 0.0

        score = (
            w_name * name_sim +
            w_class * class_sim +
            w_loc * loc_sim +
            w_ref * ref_sim +
            w_origin * origin_sim
        ) / total_w

        return score
    
    def _merge_meteorite_data(self, existing: Dict, new_result: Dict):
        """合并陨石数据"""
        existing_data = existing['data']
        
        # 处理不同的数据结构
        if 'data' in new_result and new_result['data']:
            new_data = new_result['data'].get('meteorite_data', {})
            confidence_score = new_result['data'].get('confidence', 0)
        else:
            new_data = new_result.get('meteorite_data', {})
            confidence_score = new_result.get('confidence_score', 0)
        
        # 字段级合并
        if self.config.enable_field_level_merge:
            self._merge_fields(existing_data, new_data, confidence_score)
        
        # 更新置信度
        if self.config.enable_confidence_weighting:
            new_confidence = confidence_score
            existing_confidence = existing['confidence']
            # 加权平均
            existing['confidence'] = (existing_confidence + new_confidence) / 2
        
        # 保存到数据库
        if hasattr(existing_data, 'save'):
            existing_data.save()
    
    def _merge_fields(self, existing_data, new_data: Dict, new_confidence: float):
        """字段级合并"""
        # 合并有机化合物
        if 'organic_compounds' in new_data:
            existing_org = getattr(existing_data, 'organic_compounds', {}) or {}
            new_org = new_data['organic_compounds']
            
            # 合并氨基酸
            if 'amino_acids' in new_org and new_org['amino_acids']:
                existing_amino = existing_org.get('amino_acids', [])
                merged_amino = list(set(existing_amino + new_org['amino_acids']))
                existing_org['amino_acids'] = merged_amino
            
            # 合并其他有机化合物
            for field in ['carboxylic_acids', 'nucleotide_bases', 'aromatic_compounds']:
                if field in new_org and new_org[field]:
                    existing_field = existing_org.get(field, [])
                    merged_field = list(set(existing_field + new_org[field]))
                    existing_org[field] = merged_field
            
            # 更新同位素签名（选择更具体的）
            if 'isotopic_signatures' in new_org:
                existing_iso = existing_org.get('isotopic_signatures', {})
                new_iso = new_org['isotopic_signatures']
                
                for iso_field in ['carbon_isotope_ratio', 'nitrogen_isotope_ratio']:
                    if (iso_field in new_iso and 
                        new_iso[iso_field] != 'Not specified' and
                        existing_iso.get(iso_field) == 'Not specified'):
                        existing_iso[iso_field] = new_iso[iso_field]
                
                existing_org['isotopic_signatures'] = existing_iso
            
            # 保存合并后的有机化合物
            existing_data.organic_compounds = existing_org
        
        # 合并其他字段（选择更具体的值）
        field_mappings = {
            'discovery_location': 'discovery_location',
            'origin': 'origin',
            # references 单独处理
        }
        
        for new_field, existing_field in field_mappings.items():
            if (new_field in new_data and 
                new_data[new_field] not in ['Unknown', 'Not specified', ''] and
                getattr(existing_data, existing_field, '') in ['Unknown', 'Not specified', '']):
                setattr(existing_data, existing_field, new_data[new_field])

        # 参考文献：做列表合并去重（基于 doi 或 标题）
        if 'references' in new_data and new_data['references']:
            try:
                existing_refs = getattr(existing_data, 'references', []) or []
                if not isinstance(existing_refs, list):
                    existing_refs = []
                new_refs = new_data['references'] if isinstance(new_data['references'], list) else []

                def ref_key(r: Any) -> str:
                    if isinstance(r, dict):
                        doi = (r.get('doi') or '').strip().lower()
                        if doi:
                            return f"doi:{doi}"
                        title = (r.get('title') or '').strip().lower()
                        if title:
                            return f"title:{title}"
                        return json.dumps(r, sort_keys=True, ensure_ascii=False)
                    return str(r).strip().lower()

                seen = set(ref_key(r) for r in existing_refs)
                merged = list(existing_refs)
                for r in new_refs:
                    k = ref_key(r)
                    if k and k not in seen:
                        merged.append(r)
                        seen.add(k)
                existing_data.references = merged
            except Exception as e:
                logger.warning(f"参考文献合并失败: {e}")
    
    def _create_new_meteorite(self, result: Dict):
        """创建新的陨石记录"""
        # 处理不同的数据结构
        if 'data' in result and result['data']:
            meteorite_data = result['data'].get('meteorite_data', {})
            confidence_score = result['data'].get('confidence', 0)
        else:
            meteorite_data = result.get('meteorite_data', {})
            confidence_score = result.get('confidence_score', 0)
        
        # 创建待审核记录
        pending_meteorite = PendingMeteorite.objects.create(
            name=meteorite_data.get('name', 'Unknown'),
            classification=meteorite_data.get('classification', 'Unknown'),
            discovery_location=meteorite_data.get('discovery_location', meteorite_data.get('location', 'Unknown')),
            origin=meteorite_data.get('origin', 'Unknown'),
            organic_compounds=meteorite_data.get('organic_compounds', {}),
            references=meteorite_data.get('references', []),
            confidence_score=confidence_score,
            extraction_metadata=result.get('extraction_metadata', {})
        )
        
        # 添加到缓存
        key = self._generate_meteorite_key(
            meteorite_data.get('name', 'Unknown'),
            meteorite_data.get('classification', 'Unknown')
        )
        self.existing_meteorites[key] = {
            'source': 'pending',
            'data': pending_meteorite,
            'confidence': confidence_score
        }
        
        self.stats['total_meteorites'] += 1
    
    def _save_progress(self, processed_count: int):
        """保存进度"""
        progress_data = {
            'processed_count': processed_count,
            'stats': self.stats.copy(),
            'timestamp': time.time()
        }
        
        try:
            with open("incremental_extraction_progress.json", 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            logger.info(f"进度已保存: 已处理 {processed_count} 个文档")
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """生成最终报告"""
        processing_time = self.stats['end_time'] - self.stats['start_time']
        
        report = {
            'processing_stats': {
                'total_documents': self.stats['total_documents'],
                'processed_documents': self.stats['processed_documents'],
                'new_extractions': self.stats['new_extractions'],
                'merged_extractions': self.stats['merged_extractions'],
                'total_meteorites': self.stats['total_meteorites'],
                'processing_time_seconds': processing_time,
                'documents_per_minute': (self.stats['processed_documents'] / processing_time * 60) if processing_time > 0 else 0
            },
            'merge_stats': {
                'merge_rate': (self.stats['merged_extractions'] / max(self.stats['new_extractions'] + self.stats['merged_extractions'], 1)) * 100,
                'total_unique_meteorites': len(self.existing_meteorites),
                'avg_confidence': sum(data['confidence'] for data in self.existing_meteorites.values()) / len(self.existing_meteorites) if self.existing_meteorites else 0
            },
            'quality_metrics': {
                'extraction_efficiency': (self.stats['new_extractions'] + self.stats['merged_extractions']) / max(self.stats['processed_documents'], 1),
                'data_consolidation_rate': self.stats['merged_extractions'] / max(self.stats['new_extractions'] + self.stats['merged_extractions'], 1) * 100
            },
            'extraction_results': list(self.preview_results),
        }
        
        return report


class Command(BaseCommand):
    help = '增量合并的分布式提取系统'

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
            '--similarity-threshold',
            type=float,
            default=0.8,
            help='相似度阈值'
        )
        parser.add_argument(
            '--merge-strategy',
            type=str,
            default='intelligent',
            choices=['intelligent', 'conservative', 'aggressive'],
            help='合并策略'
        )

    def handle(self, *args, **options):
        self.stdout.write("🔄 增量合并的分布式提取系统")
        self.stdout.write("=" * 50)
        
        # 配置参数
        config = IncrementalMergeConfig(
            similarity_threshold=options['similarity_threshold'],
            merge_strategy=options['merge_strategy']
        )
        
        self.stdout.write(f"📊 配置参数:")
        self.stdout.write(f"  搜索查询: {options['search_query']}")
        self.stdout.write(f"  最大文档数: {options['max_documents'] or '全部'}")
        self.stdout.write(f"  相似度阈值: {config.similarity_threshold}")
        self.stdout.write(f"  合并策略: {config.merge_strategy}")
        self.stdout.write(f"  字段级合并: {config.enable_field_level_merge}")
        self.stdout.write(f"  置信度加权: {config.enable_confidence_weighting}")
        
        # 创建提取器
        extractor = IncrementalMergeExtractor(config)
        
        try:
            # 执行增量合并提取
            self.stdout.write(f"\n🔍 开始增量合并提取...")
            report = extractor.extract_and_merge_from_corpus(
                search_query=options['search_query'],
                max_documents=options['max_documents']
            )
            
            # 显示结果
            self._display_results(report)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 增量合并提取失败: {e}"))
            logger.error(f"增量合并提取失败: {e}")
    
    def _display_results(self, report: Dict[str, Any]):
        """显示提取结果"""
        self.stdout.write(f"\n📈 增量合并结果统计:")
        
        # 处理统计
        processing_stats = report['processing_stats']
        self.stdout.write(f"\n  📊 处理统计:")
        self.stdout.write(f"    总文档数: {processing_stats['total_documents']}")
        self.stdout.write(f"    已处理: {processing_stats['processed_documents']}")
        self.stdout.write(f"    新增提取: {processing_stats['new_extractions']}")
        self.stdout.write(f"    合并提取: {processing_stats['merged_extractions']}")
        self.stdout.write(f"    总陨石数: {processing_stats['total_meteorites']}")
        self.stdout.write(f"    处理时间: {processing_stats['processing_time_seconds']:.1f} 秒")
        self.stdout.write(f"    处理速度: {processing_stats['documents_per_minute']:.1f} 文档/分钟")
        
        # 合并统计
        merge_stats = report['merge_stats']
        self.stdout.write(f"\n  🔗 合并统计:")
        self.stdout.write(f"    合并率: {merge_stats['merge_rate']:.1f}%")
        self.stdout.write(f"    唯一陨石数: {merge_stats['total_unique_meteorites']}")
        self.stdout.write(f"    平均置信度: {merge_stats['avg_confidence']:.3f}")
        
        # 质量指标
        quality_metrics = report['quality_metrics']
        self.stdout.write(f"\n  🎯 质量指标:")
        self.stdout.write(f"    提取效率: {quality_metrics['extraction_efficiency']:.1f} 提取/文档")
        self.stdout.write(f"    数据整合率: {quality_metrics['data_consolidation_rate']:.1f}%")
        
        self.stdout.write(self.style.SUCCESS("\n✅ 增量合并提取完成"))
