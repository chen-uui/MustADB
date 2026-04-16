"""
跨文档分析API - 实现陨石数据的统计和关联分析
"""
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Max, Min
from django.db.models.functions import Trunc
import json

from .models import DirectProcessingResult
from meteorite_search.models import Meteorite as MeteoriteDB

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def analyze_meteorite_types(request):
    """
    分析不同类型的陨石中发现了什么
    支持问题：
    - 哪种类型的火星陨石中分别发现了什么？
    - 碳质球粒陨石中检测到哪些有机化合物？
    """
    try:
        data = json.loads(request.body) if request.method == 'POST' else {}
        query_type = data.get('type', 'martian')  # martian, all
        
        # 从DirectProcessingResult查询
        results = DirectProcessingResult.objects.filter(
            status='completed'
        ).exclude(
            meteorite_data={}
        )
        
        # 如果查询火星陨石
        if query_type == 'martian':
            results = results.filter(
                Q(meteorite_data__classification__icontains='martian') |
                Q(meteorite_data__classification__icontains='shergottite') |
                Q(meteorite_data__classification__icontains='nakhlite') |
                Q(meteorite_data__classification__icontains='chassignite') |
                Q(meteorite_data__classification__icontains='SNC')
            )
        
        # 按陨石类型分组
        analysis = {}
        
        for result in results:
            classification = result.meteorite_data.get('classification', 'Unknown')
            meteorite_name = result.meteorite_data.get('name', 'Unknown')
            
            if classification not in analysis:
                analysis[classification] = {
                    'count': 0,
                    'meteorites': [],
                    'organic_compounds': set(),
                    'minerals': set(),
                    'papers': []
                }
            
            analysis[classification]['count'] += 1
            analysis[classification]['meteorites'].append(meteorite_name)
            
            # 提取有机化合物
            organic_data = result.organic_compounds or {}
            compounds = organic_data.get('compounds', '')
            if compounds and compounds != '该论文不包含有机化合物相关内容':
                analysis[classification]['organic_compounds'].add(compounds)
            
            # 提取矿物
            mineral_data = result.mineral_relationships or {}
            minerals = mineral_data.get('minerals', '')
            if minerals and minerals != '该论文不包含矿物相关内容':
                analysis[classification]['minerals'].add(minerals)
            
            # 论文信息
            analysis[classification]['papers'].append({
                'title': result.document_title,
                'meteorite': meteorite_name,
                'confidence': result.confidence_score
            })
        
        # 转换set为list
        for key in analysis:
            analysis[key]['organic_compounds'] = list(analysis[key]['organic_compounds'])
            analysis[key]['minerals'] = list(analysis[key]['minerals'])
        
        return JsonResponse({
            'success': True,
            'data': analysis,
            'total_types': len(analysis),
            'total_results': results.count()
        })
        
    except Exception as e:
        logger.error(f"分析陨石类型失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def analyze_organics_mineral_association(request):
    """
    分析有机质和矿物之间的关系（organics-mineral association）
    """
    try:
        data = json.loads(request.body) if request.method == 'POST' else {}
        
        # 查询所有有有机化合物和矿物数据的记录
        results = DirectProcessingResult.objects.filter(
            status='completed'
        ).exclude(
            organic_compounds={}
        ).exclude(
            mineral_relationships={}
        )
        
        associations = []
        
        for result in results:
            meteorite_name = result.meteorite_data.get('name', 'Unknown')
            classification = result.meteorite_data.get('classification', 'Unknown')
            
            organic_data = result.organic_compounds or {}
            mineral_data = result.mineral_relationships or {}
            
            compounds = organic_data.get('compounds', '')
            minerals = mineral_data.get('minerals', '')
            relationships = mineral_data.get('relationships', '')
            
            # 过滤无效数据
            if (compounds and compounds != '该论文不包含有机化合物相关内容' and
                minerals and minerals != '该论文不包含矿物相关内容'):
                
                associations.append({
                    'meteorite': meteorite_name,
                    'classification': classification,
                    'organic_compounds': compounds,
                    'minerals': minerals,
                    'relationships': relationships,
                    'paper': result.document_title,
                    'confidence': result.confidence_score
                })
        
        # 统计最常见的矿物-有机化合物组合
        mineral_compound_pairs = {}
        for assoc in associations:
            key = f"{assoc['minerals']} + {assoc['organic_compounds']}"
            if key not in mineral_compound_pairs:
                mineral_compound_pairs[key] = {
                    'count': 0,
                    'meteorites': [],
                    'papers': []
                }
            mineral_compound_pairs[key]['count'] += 1
            mineral_compound_pairs[key]['meteorites'].append(assoc['meteorite'])
            mineral_compound_pairs[key]['papers'].append(assoc['paper'])
        
        # 按出现次数排序
        sorted_pairs = sorted(
            mineral_compound_pairs.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        return JsonResponse({
            'success': True,
            'data': {
                'associations': associations,
                'common_pairs': dict(sorted_pairs[:20]),  # 前20个最常见的组合
                'total_associations': len(associations)
            }
        })
        
    except Exception as e:
        logger.error(f"分析有机质-矿物关联失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def get_martian_meteorite_overview(request):
    """
    获取火星陨石概览
    返回所有火星陨石类型的详细对比
    """
    try:
        # 查询所有火星陨石
        results = DirectProcessingResult.objects.filter(
            Q(meteorite_data__classification__icontains='martian') |
            Q(meteorite_data__classification__icontains='shergottite') |
            Q(meteorite_data__classification__icontains='nakhlite') |
            Q(meteorite_data__classification__icontains='chassignite') |
            Q(meteorite_data__classification__icontains='SNC')
        ).filter(
            status='completed'
        )
        
        overview = {
            'total_papers': results.count(),
            'meteorite_types': {},
            'summary': {}
        }
        
        for result in results:
            meteorite_name = result.meteorite_data.get('name', 'Unknown')
            classification = result.meteorite_data.get('classification', 'Unknown')
            
            if classification not in overview['meteorite_types']:
                overview['meteorite_types'][classification] = {
                    'meteorites': set(),
                    'papers': [],
                    'organic_compounds_found': set(),
                    'has_mineral_data': False
                }
            
            overview['meteorite_types'][classification]['meteorites'].add(meteorite_name)
            overview['meteorite_types'][classification]['papers'].append({
                'title': result.document_title,
                'meteorite': meteorite_name
            })
            
            # 有机化合物
            organic = result.organic_compounds.get('compounds', '')
            if organic and organic != '该论文不包含有机化合物相关内容':
                overview['meteorite_types'][classification]['organic_compounds_found'].add(organic)
            
            # 矿物数据
            if result.mineral_relationships:
                overview['meteorite_types'][classification]['has_mineral_data'] = True
        
        # 转换set为list
        for key in overview['meteorite_types']:
            overview['meteorite_types'][key]['meteorites'] = list(overview['meteorite_types'][key]['meteorites'])
            overview['meteorite_types'][key]['organic_compounds_found'] = list(
                overview['meteorite_types'][key]['organic_compounds_found']
            )
        
        # 生成摘要
        overview['summary'] = {
            'total_types': len(overview['meteorite_types']),
            'types_with_organics': sum(
                1 for t in overview['meteorite_types'].values()
                if t['organic_compounds_found']
            ),
            'types_with_minerals': sum(
                1 for t in overview['meteorite_types'].values()
                if t['has_mineral_data']
            )
        }
        
        return JsonResponse({
            'success': True,
            'data': overview
        })
        
    except Exception as e:
        logger.error(f"获取火星陨石概览失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)




