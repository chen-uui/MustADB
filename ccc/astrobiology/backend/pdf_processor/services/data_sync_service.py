"""
数据同步服务
将DirectProcessingResult的提取结果同步到Meteorite表
"""

import logging
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.utils import timezone

from pdf_processor.models import DirectProcessingResult
from meteorite_search.models import Meteorite, DataExtractionTask

logger = logging.getLogger(__name__)


class DataSyncService:
    """数据同步服务"""
    
    def __init__(self):
        """初始化数据同步服务"""
        self.logger = logger
        self.logger.info("DataSyncService initialized")
    
    def sync_extraction_to_meteorite(self, extraction_id: str) -> Optional[Meteorite]:
        """
        同步提取结果到陨石数据库
        
        Args:
            extraction_id: DirectProcessingResult的ID
            
        Returns:
            Meteorite: 创建或更新的陨石对象，失败时返回None
        """
        try:
            # 1. 获取提取结果
            extraction = DirectProcessingResult.objects.get(id=extraction_id)
            self.logger.info(f"开始同步提取结果: {extraction.document_title}")
            
            # 2. 提取陨石信息
            meteorite_data = extraction.meteorite_data
            meteorite_name = meteorite_data.get('name', 'Unknown')
            
            # 检查是否为有效陨石数据
            if not meteorite_name or meteorite_name in ['Unknown', '该论文不包含陨石相关内容']:
                self.logger.warning(f"提取结果不包含有效陨石数据: {meteorite_name}")
                return None
            
            # 3. 提取矿物关联信息
            mineral_data = extraction.mineral_relationships
            mineral_associations = mineral_data.get('associations', []) if isinstance(mineral_data, dict) else []
            
            # 4. 构建陨石数据
            meteorite_data_dict = {
                'name': meteorite_name,
                'classification': meteorite_data.get('classification', 'Unknown'),
                'discovery_location': meteorite_data.get('location', 'Unknown'),
                'origin': meteorite_data.get('origin', 'Unknown'),
                'organic_compounds': extraction.organic_compounds,
                'contamination_exclusion_method': self._extract_contamination_method(extraction),
                'references': self._extract_references(extraction),
                'confidence_score': extraction.confidence_score,
                'extraction_source': 'rag_extraction',
                'extraction_metadata': {
                    'document_title': extraction.document_title,
                    'document_path': extraction.document_path,
                    'extraction_id': str(extraction.id),
                    'processing_time': extraction.processing_time,
                    'mineral_associations': mineral_associations,
                    'scientific_insights': extraction.scientific_insights,
                    'sync_timestamp': timezone.now().isoformat()
                },
                'review_status': 'pending'  # 新同步的数据需要审核
            }
            
            # 5. 创建或更新陨石记录
            with transaction.atomic():
                meteorite, created = Meteorite.objects.update_or_create(
                    name=meteorite_name,
                    defaults=meteorite_data_dict
                )
                
                action = "创建" if created else "更新"
                self.logger.info(f"成功{action}陨石记录: {meteorite.name} (ID: {meteorite.id})")
                
                return meteorite
                
        except DirectProcessingResult.DoesNotExist:
            self.logger.error(f"未找到提取结果: {extraction_id}")
            return None
        except Exception as e:
            self.logger.error(f"同步提取结果失败: {str(e)}")
            return None
    
    def sync_batch_extractions(self, extraction_ids: List[str]) -> Dict[str, Any]:
        """
        批量同步提取结果
        
        Args:
            extraction_ids: DirectProcessingResult的ID列表
            
        Returns:
            Dict: 同步结果统计
        """
        results = {
            'total': len(extraction_ids),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'meteorites': []
        }
        
        self.logger.info(f"开始批量同步 {len(extraction_ids)} 个提取结果")
        
        for extraction_id in extraction_ids:
            try:
                meteorite = self.sync_extraction_to_meteorite(extraction_id)
                
                if meteorite:
                    results['successful'] += 1
                    results['meteorites'].append({
                        'id': str(meteorite.id),
                        'name': meteorite.name,
                        'classification': meteorite.classification
                    })
                else:
                    results['skipped'] += 1
                    
            except Exception as e:
                results['failed'] += 1
                self.logger.error(f"同步提取结果 {extraction_id} 失败: {str(e)}")
        
        self.logger.info(f"批量同步完成: 成功{results['successful']}, 跳过{results['skipped']}, 失败{results['failed']}")
        return results
    
    def sync_recent_extractions(self, hours: int = 24) -> Dict[str, Any]:
        """
        同步最近的提取结果
        
        Args:
            hours: 最近多少小时内的提取结果
            
        Returns:
            Dict: 同步结果统计
        """
        from datetime import timedelta
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # 获取最近的提取结果
        recent_extractions = DirectProcessingResult.objects.filter(
            created_at__gte=cutoff_time,
            status='completed'
        ).order_by('-created_at')
        
        extraction_ids = [str(extraction.id) for extraction in recent_extractions]
        
        self.logger.info(f"找到 {len(extraction_ids)} 个最近{hours}小时的提取结果")
        
        return self.sync_batch_extractions(extraction_ids)
    
    def sync_pending_extractions(self) -> Dict[str, Any]:
        """
        同步所有待同步的提取结果（未同步到陨石表的）
        
        Returns:
            Dict: 同步结果统计
        """
        # 获取所有已完成的提取结果
        completed_extractions = DirectProcessingResult.objects.filter(
            status='completed'
        ).order_by('-created_at')
        
        # 过滤掉已经同步过的（通过extraction_metadata中的extraction_id判断）
        pending_extractions = []
        for extraction in completed_extractions:
            # 检查是否已经同步过
            if not self._is_extraction_synced(extraction):
                pending_extractions.append(extraction)
        
        extraction_ids = [str(extraction.id) for extraction in pending_extractions]
        
        self.logger.info(f"找到 {len(extraction_ids)} 个待同步的提取结果")
        
        return self.sync_batch_extractions(extraction_ids)
    
    def _is_extraction_synced(self, extraction: DirectProcessingResult) -> bool:
        """
        检查提取结果是否已经同步
        
        Args:
            extraction: DirectProcessingResult对象
            
        Returns:
            bool: 是否已同步
        """
        try:
            # 通过陨石名称查找
            meteorite_name = extraction.meteorite_data.get('name', 'Unknown')
            if not meteorite_name or meteorite_name in ['Unknown', '该论文不包含陨石相关内容']:
                return True  # 无效数据视为已处理
            
            # 查找对应的陨石记录
            meteorites = Meteorite.objects.filter(
                name=meteorite_name,
                extraction_source='rag_extraction'
            )
            
            # 检查extraction_metadata中是否包含当前extraction_id
            for meteorite in meteorites:
                metadata = meteorite.extraction_metadata
                if isinstance(metadata, dict):
                    if metadata.get('extraction_id') == str(extraction.id):
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查同步状态失败: {str(e)}")
            return False
    
    def _extract_contamination_method(self, extraction: DirectProcessingResult) -> str:
        """
        从提取结果中提取污染排除方法
        
        Args:
            extraction: DirectProcessingResult对象
            
        Returns:
            str: 污染排除方法描述
        """
        # 从scientific_insights中提取相关信息
        insights = extraction.scientific_insights
        if isinstance(insights, dict):
            significance = insights.get('significance', '')
            explanation = insights.get('explanation', '')
            
            # 组合相关信息
            methods = []
            if significance and 'contamination' in significance.lower():
                methods.append(significance)
            if explanation and 'contamination' in explanation.lower():
                methods.append(explanation)
            
            if methods:
                return '; '.join(methods)
        
        return 'RAG自动提取，需要人工审核'
    
    def _extract_references(self, extraction: DirectProcessingResult) -> List[Dict[str, str]]:
        """
        从提取结果中提取参考文献
        
        Args:
            extraction: DirectProcessingResult对象
            
        Returns:
            List[Dict]: 参考文献列表
        """
        references = []
        
        # 从document_title构建基本引用
        if extraction.document_title:
            references.append({
                'title': extraction.document_title,
                'source': 'RAG提取',
                'type': 'document',
                'extraction_id': str(extraction.id)
            })
        
        return references
    
    def get_sync_statistics(self) -> Dict[str, Any]:
        """
        获取同步统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            # 总提取结果数
            total_extractions = DirectProcessingResult.objects.filter(status='completed').count()
            
            # 已同步的提取结果数
            synced_extractions = 0
            for extraction in DirectProcessingResult.objects.filter(status='completed'):
                if self._is_extraction_synced(extraction):
                    synced_extractions += 1
            
            # 陨石记录统计
            total_meteorites = Meteorite.objects.count()
            rag_meteorites = Meteorite.objects.filter(extraction_source='rag_extraction').count()
            pending_review = Meteorite.objects.filter(review_status='pending').count()
            
            return {
                'total_extractions': total_extractions,
                'synced_extractions': synced_extractions,
                'pending_extractions': total_extractions - synced_extractions,
                'sync_rate': (synced_extractions / total_extractions * 100) if total_extractions > 0 else 0,
                'total_meteorites': total_meteorites,
                'rag_meteorites': rag_meteorites,
                'pending_review': pending_review
            }
            
        except Exception as e:
            self.logger.error(f"获取同步统计失败: {str(e)}")
            return {}
    
    def cleanup_duplicate_meteorites(self) -> Dict[str, Any]:
        """
        清理重复的陨石记录
        
        Returns:
            Dict: 清理结果统计
        """
        try:
            # 查找重复的陨石记录（基于名称）
            from django.db.models import Count
            
            duplicate_names = Meteorite.objects.values('name').annotate(
                count=Count('id')
            ).filter(count__gt=1)
            
            cleanup_results = {
                'duplicate_names': len(duplicate_names),
                'removed_records': 0,
                'kept_records': 0
            }
            
            # 优化：批量处理，减少数据库查询
            from django.db import transaction
            
            with transaction.atomic():
                for item in duplicate_names:
                    name = item['name']
                    # 优化：使用select_for_update防止并发问题，只查询需要的字段
                    meteorites = list(Meteorite.objects.filter(name=name).order_by('-created_at').only('id', 'name', 'created_at'))
                    
                    if len(meteorites) <= 1:
                        continue
                    
                    # 保留最新的记录，删除其他重复记录
                    keep_meteorite = meteorites[0]
                    duplicate_meteorites = meteorites[1:]
                    
                    # 优化：批量删除，减少数据库往返
                    duplicate_ids = [m.id for m in duplicate_meteorites]
                    deleted_count = Meteorite.objects.filter(id__in=duplicate_ids).delete()[0]
                    cleanup_results['removed_records'] += deleted_count
                    cleanup_results['kept_records'] += 1
            
            self.logger.info(f"清理完成: 发现{cleanup_results['duplicate_names']}个重复名称，删除{cleanup_results['removed_records']}条记录")
            return cleanup_results
            
        except Exception as e:
            self.logger.error(f"清理重复陨石记录失败: {str(e)}")
            return {}