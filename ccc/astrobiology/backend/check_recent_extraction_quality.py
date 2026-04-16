"""
检查最近提取的数据质量
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

from meteorite_search.review_models import PendingMeteorite
from django.utils import timezone
from datetime import timedelta
import json

# 获取最近1小时内的数据
recent = PendingMeteorite.objects.filter(
    created_at__gte=timezone.now() - timedelta(hours=1)
).order_by('-created_at')[:50]

print(f"=" * 80)
print(f"最近1小时内的待审核数据: {recent.count()} 条")
print(f"=" * 80)

if recent.count() == 0:
    print("没有找到最近的数据，尝试查看最近的数据...")
    recent = PendingMeteorite.objects.order_by('-created_at')[:50]
    print(f"最新的50条数据:")
    print(f"=" * 80)

quality_stats = {
    'total': recent.count(),
    'has_name': 0,
    'has_classification': 0,
    'has_location': 0,
    'has_origin': 0,
    'has_organic': 0,
    'valid_names': [],  # 存储看起来像真正陨石名称的
    'invalid_names': [],  # 存储看起来像论文标题的
    'low_confidence': 0,  # 置信度 < 0.5
    'high_confidence': 0,  # 置信度 >= 0.7
}

for i, p in enumerate(recent):
    print(f"\n{i+1}. ID: {p.id}")
    print(f"   名称: {p.name[:80] if p.name else '(无)'}")
    print(f"   分类: {p.classification[:50] if p.classification else '(无)'}")
    print(f"   发现地点: {p.discovery_location[:50] if p.discovery_location else '(无)'}")
    print(f"   来源: {p.origin[:50] if p.origin else '(无)'}")
    # 处理有机化合物（可能是JSON格式）
    if isinstance(p.organic_compounds, dict) and 'details' in p.organic_compounds:
        organic_str = str(p.organic_compounds.get('details', ''))[:100]
    elif isinstance(p.organic_compounds, list):
        organic_str = ', '.join(map(str, p.organic_compounds[:5]))[:100]
    else:
        organic_str = str(p.organic_compounds)[:100] if p.organic_compounds else '(无)'
    print(f"   有机化合物: {organic_str}")
    conf_score = p.confidence_score if p.confidence_score is not None else 0
    print(f"   置信度: {conf_score:.3f}")
    
    # 检查metadata
    if p.extraction_metadata:
        try:
            metadata = json.loads(p.extraction_metadata) if isinstance(p.extraction_metadata, str) else p.extraction_metadata
            segment_count = metadata.get('segment_count', 0)
            print(f"   来源片段数: {segment_count}")
        except:
            pass
    
    # 统计
    if p.name and p.name.strip():
        quality_stats['has_name'] += 1
        # 简单判断名称是否像论文标题
        name = p.name.strip()
        if (len(name) > 100 or 
            any(word in name.lower() for word in ['exploring', 'investigation', 'analysis', 'assessment', 'study', 'research', 'paper', 'article']) or
            name.count(' ') > 15):
            quality_stats['invalid_names'].append(name[:60])
        else:
            quality_stats['valid_names'].append(name[:60])
    
    if p.classification and p.classification.strip() and p.classification.strip() != 'Unknown':
        quality_stats['has_classification'] += 1
    if p.discovery_location and p.discovery_location.strip() and p.discovery_location.strip() != 'Unknown':
        quality_stats['has_location'] += 1
    if p.origin and p.origin.strip() and p.origin.strip() != 'Unknown':
        quality_stats['has_origin'] += 1
    # 检查有机化合物（可能是JSON格式）
    has_organic = False
    if isinstance(p.organic_compounds, dict) and 'details' in p.organic_compounds:
        has_organic = bool(p.organic_compounds.get('details', '').strip())
    elif isinstance(p.organic_compounds, list):
        has_organic = len(p.organic_compounds) > 0
    else:
        has_organic = bool(p.organic_compounds and str(p.organic_compounds).strip())
    if has_organic:
        quality_stats['has_organic'] += 1
    
    if p.confidence_score:
        if p.confidence_score < 0.5:
            quality_stats['low_confidence'] += 1
        elif p.confidence_score >= 0.7:
            quality_stats['high_confidence'] += 1

print(f"\n{'=' * 80}")
print("数据质量统计:")
print(f"{'=' * 80}")
print(f"总数: {quality_stats['total']}")
print(f"有名称: {quality_stats['has_name']} ({quality_stats['has_name']/quality_stats['total']*100:.1f}%)")
print(f"有分类: {quality_stats['has_classification']} ({quality_stats['has_classification']/quality_stats['total']*100:.1f}%)")
print(f"有发现地点: {quality_stats['has_location']} ({quality_stats['has_location']/quality_stats['total']*100:.1f}%)")
print(f"有来源: {quality_stats['has_origin']} ({quality_stats['has_origin']/quality_stats['total']*100:.1f}%)")
print(f"有有机化合物: {quality_stats['has_organic']} ({quality_stats['has_organic']/quality_stats['total']*100:.1f}%)")
print(f"低置信度(<0.5): {quality_stats['low_confidence']}")
print(f"高置信度(>=0.7): {quality_stats['high_confidence']}")

print(f"\n有效名称示例 ({len(quality_stats['valid_names'])} 个):")
for name in quality_stats['valid_names'][:10]:
    print(f"  - {name}")

if quality_stats['invalid_names']:
    print(f"\n疑似论文标题的名称 ({len(quality_stats['invalid_names'])} 个):")
    for name in quality_stats['invalid_names'][:10]:
        print(f"  - {name}")

