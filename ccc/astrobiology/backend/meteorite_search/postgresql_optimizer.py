from django.db import models, connection
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .models import Meteorite
import time
import logging

logger = logging.getLogger(__name__)

class PostgreSQLMeteoriteOptimizer:
    """PostgreSQL版本的陨石查询优化器"""
    
    @staticmethod
    def search_with_postgresql_optimization(filters: dict, page: int = 1, page_size: int = 20) -> dict:
        """PostgreSQL优化的搜索方法"""
        start_time = time.time()
        
        # 构建基础查询
        queryset = Meteorite.objects.filter(is_active=True)
        
        # 应用过滤器
        if filters.get('name'):
            queryset = queryset.filter(name__icontains=filters['name'])
        
        if filters.get('classification'):
            queryset = queryset.filter(classification__icontains=filters['classification'])
        
        if filters.get('origin'):
            queryset = queryset.filter(origin__icontains=filters['origin'])
        
        if filters.get('discovery_location'):
            queryset = queryset.filter(discovery_location__icontains=filters['discovery_location'])
        
        # PostgreSQL全文搜索
        if filters.get('search_text'):
            search_vector = SearchVector('name', weight='A') + SearchVector('classification', weight='B') + SearchVector('origin', weight='C')
            search_query = SearchQuery(filters['search_text'])
            
            queryset = queryset.annotate(
                search=search_vector,
                rank=SearchRank(search_vector, search_query)
            ).filter(search=search_query).order_by('-rank')
        
        # PostgreSQL JSON字段搜索
        if filters.get('organic_compound'):
            compound = filters['organic_compound']
            queryset = queryset.filter(
                organic_compounds__icontains=compound
            )
        
        # 获取总数
        total_count = queryset.count()
        
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        
        # 优化查询：使用select_related和only
        results = queryset.select_related().only(
            'id', 'name', 'classification', 'origin', 'discovery_location',
            'organic_compounds', 'references', 'created_at'
        )[start:end]
        
        # 处理结果
        processed_results = []
        for meteorite in results:
            processed_results.append({
                'id': meteorite.id,
                'name': meteorite.name,
                'classification': meteorite.classification,
                'origin': meteorite.origin,
                'discovery_location': meteorite.discovery_location,
                'organic_compounds': meteorite.organic_compounds,
                'references': meteorite.references,
                'organic_compound_count': len(meteorite.organic_compounds) if meteorite.organic_compounds else 0,
                'reference_count': len(meteorite.references) if meteorite.references else 0,
                'created_at': meteorite.created_at.isoformat()
            })
        
        execution_time = time.time() - start_time
        
        logger.info(f"PostgreSQL search executed in {execution_time:.3f}s, found {total_count} results")
        
        return {
            'results': processed_results,
            'total_count': total_count,
            'page': page,
            'total_pages': (total_count + page_size - 1) // page_size,
            'execution_time': execution_time,
        }
    
    @staticmethod
    def get_postgresql_statistics() -> dict:
        """获取PostgreSQL数据库统计"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT classification) as unique_classifications,
                    AVG(pg_column_size(organic_compounds)) as avg_organic_data_size,
                    COUNT(CASE WHEN organic_compounds != '[]'::jsonb THEN 1 END) as with_organics,
                    COUNT(CASE WHEN references != '[]'::jsonb THEN 1 END) as with_references
                FROM meteorites
                WHERE is_active = true
            """)
            
            result = cursor.fetchone()
            
        return {
            'total_records': result[0],
            'unique_classifications': result[1],
            'avg_organic_data_size': result[2] or 0,
            'meteorites_with_organics': result[3],
            'meteorites_with_references': result[4]
        }
    
    @staticmethod
    def update_search_vectors():
        """更新全文搜索向量"""
        if not hasattr(Meteorite, 'search_vector'):
            logger.warning("模型未定义 search_vector 字段，跳过全文索引更新")
            return
        
        Meteorite.objects.filter(is_active=True).update(
            search_vector=SearchVector('name', weight='A') + 
                         SearchVector('classification', weight='B') + 
                         SearchVector('origin', weight='C') + 
                         SearchVector('discovery_location', weight='D')
        )
        logger.info("全文搜索向量更新完成")
    
    @staticmethod
    def analyze_postgresql_performance():
        """分析PostgreSQL性能"""
        with connection.cursor() as cursor:
            cursor.execute("""
                EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 
                SELECT * FROM meteorites 
                WHERE is_active = true AND name ILIKE '%Allende%'
            """)
            
            plan = cursor.fetchone()[0]
            
        return {
            'execution_plan': plan,
            'suggestions': [
                "确保已创建适当的索引",
                "考虑使用GIN索引优化JSON搜索",
                "监控查询执行时间"
            ]
        }
