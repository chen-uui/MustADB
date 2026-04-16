from django.db import connection
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch
from typing import List, Dict, Any
import time
import logging
from .models import Meteorite

logger = logging.getLogger(__name__)

class MeteoriteQueryOptimizer:
    """陨石查询优化器"""
    
    @staticmethod
    def search_with_optimization(filters: Dict[str, Any], page: int = 1, page_size: int = 20) -> Dict:
        """优化的搜索方法"""
        start_time = time.time()
        
        # 构建基础查询
        queryset = Meteorite.objects.select_related().filter(is_active=True)
        
        # 应用过滤器
        if filters.get('name'):
            queryset = queryset.filter(name__icontains=filters['name'])
        
        if filters.get('classification'):
            queryset = queryset.filter(classification__icontains=filters['classification'])
        
        if filters.get('origin'):
            queryset = queryset.filter(origin__icontains=filters['origin'])
        
        if filters.get('discovery_location'):
            queryset = queryset.filter(discovery_location__icontains=filters['discovery_location'])
        
        # 有机化合物搜索优化
        if filters.get('organic_compound'):
            compound = filters['organic_compound']
            queryset = queryset.filter(
                organic_compounds__icontains=compound
            )
        
        # 使用values减少数据传输
        results = queryset.values(
            'id', 'name', 'classification', 'origin', 'discovery_location',
            'organic_compounds', 'created_at'
        )
        
        # 分页
        paginator = Paginator(results, page_size)
        page_obj = paginator.get_page(page)
        
        # 计算统计信息
        total_count = paginator.count
        
        execution_time = time.time() - start_time
        
        # 记录查询性能
        logger.info(f"Search executed in {execution_time:.2f}s, found {total_count} results")
        
        return {
            'results': list(page_obj),
            'total_count': total_count,
            'page': page,
            'total_pages': paginator.num_pages,
            'execution_time': execution_time,
            'query': str(queryset.query)
        }
    
    @staticmethod
    def get_statistics() -> Dict:
        """获取数据库统计信息"""
        # 使用模型表名，避免硬编码
        from .models import Meteorite
        table = Meteorite._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT classification) as unique_classifications,
                    AVG(LENGTH(organic_compounds::text)) as avg_organic_data_size,
                    COUNT(CASE WHEN organic_compounds != '[]' THEN 1 END) as with_organics
                FROM {table}
                WHERE is_active = true
            """)
            
            result = cursor.fetchone()
            
        return {
            'total_records': result[0],
            'unique_classifications': result[1],
            'avg_organic_data_size': result[2],
            'meteorites_with_organics': result[3]
        }
    
    @staticmethod
    def analyze_query_performance(query: str) -> Dict:
        """分析查询性能"""
        with connection.cursor() as cursor:
            cursor.execute(f"EXPLAIN ANALYZE {query}")
            plan = cursor.fetchall()
            
        return {
            'execution_plan': plan,
            'suggestions': MeteoriteQueryOptimizer._get_optimization_suggestions(plan)
        }
    
    @staticmethod
    def _get_optimization_suggestions(plan: List) -> List[str]:
        """基于执行计划提供优化建议"""
        suggestions = []
        plan_text = '\n'.join([row[0] for row in plan])
        
        if 'Seq Scan' in plan_text and 'meteorites' in plan_text:
            suggestions.append("考虑在搜索字段上添加索引")
        
        if 'Sort' in plan_text and 'external merge' in plan_text:
            suggestions.append("结果集过大，考虑增加内存限制或优化排序")
        
        if 'Nested Loop' in plan_text:
            suggestions.append("考虑使用JOIN优化")
            
        return suggestions
