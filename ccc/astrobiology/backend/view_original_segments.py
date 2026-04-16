"""
查看提取数据的原始片段内容，分析是文档质量问题还是提取逻辑问题
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
from pdf_processor.weaviate_connection import weaviate_connection
import weaviate

# 获取最近的数据，重点关注问题案例
recent = PendingMeteorite.objects.filter(
    created_at__gte=timezone.now() - timedelta(hours=1)
).order_by('-created_at')

# 如果有更多数据，增加到50条
total_count = recent.count()
if total_count > 20:
    recent = recent[:50]
    print(f"=" * 80)
    print(f"分析最近{total_count}条中的50条提取数据的原始片段（优先问题案例）")
    print(f"=" * 80)
else:
    recent = list(recent[:total_count])
    print(f"=" * 80)
    print(f"分析最近{len(recent)}条提取数据的原始片段")
    print(f"=" * 80)

# 连接到Weaviate
try:
    client = weaviate_connection.get_client()
    collection = client.collections.get("PDFDocument")
    print("[OK] 已连接到Weaviate\n")
except Exception as e:
    print(f"[ERROR] 连接Weaviate失败: {e}")
    sys.exit(1)

# 优先分析问题案例
problem_cases_list = []
normal_cases_list = []
problem_cases_summary = []  # 用于最后汇总

for p in recent:
    is_problem = False
    problem_reasons = []
    
    # 检查名称是否像论文标题或文档ID
    if p.name:
        name = p.name.strip()
        if (len(name) > 80 or 
            '0004-637X' in name or
            any(word in name.lower() for word in ['exploring', 'investigation', 'analysis', 'assessment', 'synthesis of', 'concerns of'])):
            is_problem = True
            problem_reasons.append(f"名称可疑")
    
    # 检查字段完整性
    empty_fields = []
    if not p.classification or p.classification.strip() == 'Unknown':
        empty_fields.append('分类')
    if not p.discovery_location or p.discovery_location.strip() == 'Unknown':
        empty_fields.append('发现地点')
    if not p.origin or p.origin.strip() == 'Unknown':
        empty_fields.append('来源')
    
    if len(empty_fields) >= 2:
        is_problem = True
        problem_reasons.append(f"缺少{len(empty_fields)}个字段")
    
    conf_score = p.confidence_score if p.confidence_score is not None else 0
    if conf_score < 0.4:
        is_problem = True
        problem_reasons.append(f"低置信度({conf_score:.3f})")
    
    if is_problem:
        problem_cases_list.append((p, problem_reasons))
    else:
        normal_cases_list.append(p)

# 先分析问题案例，再分析正常案例
all_cases = problem_cases_list + [(p, []) for p in normal_cases_list]

print(f"\n统计: 问题案例 {len(problem_cases_list)} 个, 正常案例 {len(normal_cases_list)} 个")
print(f"将详细分析前 {min(30, len(all_cases))} 个案例（优先问题案例）\n")

for i, (p, problem_reasons) in enumerate(all_cases[:30]):
    print(f"\n{'=' * 80}")
    print(f"案例 {i+1}: ID={p.id} {'[问题案例]' if problem_reasons else '[正常案例]'}")
    if problem_reasons:
        print(f"问题标记: {', '.join(problem_reasons)}")
    print(f"{'=' * 80}")
    print(f"提取结果:")
    print(f"  名称: {p.name[:100] if p.name else '(无)'}")
    print(f"  分类: {p.classification[:50] if p.classification else '(无)'}")
    print(f"  发现地点: {p.discovery_location[:50] if p.discovery_location else '(无)'}")
    print(f"  来源: {p.origin[:50] if p.origin else '(无)'}")
    conf_score = p.confidence_score if p.confidence_score is not None else 0
    print(f"  置信度: {conf_score:.3f}")
    
    # 判断是否为问题案例
    is_problem = False
    problem_reasons = []
    
    # 检查名称是否像论文标题或文档ID
    if p.name:
        name = p.name.strip()
        if (len(name) > 80 or 
            '0004-637X' in name or
            any(word in name.lower() for word in ['exploring', 'investigation', 'analysis', 'assessment', 'synthesis of', 'concerns of'])):
            is_problem = True
            problem_reasons.append(f"名称可疑: {name[:60]}")
    
    # 检查字段完整性
    empty_fields = []
    if not p.classification or p.classification.strip() == 'Unknown':
        empty_fields.append('分类')
    if not p.discovery_location or p.discovery_location.strip() == 'Unknown':
        empty_fields.append('发现地点')
    if not p.origin or p.origin.strip() == 'Unknown':
        empty_fields.append('来源')
    
    if len(empty_fields) >= 2:
        is_problem = True
        problem_reasons.append(f"缺少字段: {', '.join(empty_fields)}")
    
    if conf_score < 0.4:
        is_problem = True
        problem_reasons.append(f"低置信度: {conf_score:.3f}")
    
    if is_problem:
        problem_cases_summary.append({
            'pending_id': p.id,
            'name': p.name,
            'reasons': problem_reasons,
            'confidence': conf_score
        })
    
    # 获取segment信息
    if p.extraction_metadata:
        try:
            metadata = json.loads(p.extraction_metadata) if isinstance(p.extraction_metadata, str) else p.extraction_metadata
            segment_ids = metadata.get('segment_ids', [])
            segment_count = metadata.get('segment_count', 0)
            
            print(f"\n  来源片段数: {segment_count}")
            print(f"  片段IDs: {segment_ids[:5]}...") if len(segment_ids) > 5 else print(f"  片段IDs: {segment_ids}")
            
            # 尝试从Weaviate获取第一个片段的内容
            if segment_ids:
                first_segment_id = segment_ids[0]
                print(f"\n  正在获取片段内容: {first_segment_id}")
                
                try:
                    # segment_id格式: document_id:chunk_index
                    if ':' in first_segment_id:
                        doc_id, chunk_idx_str = first_segment_id.split(':', 1)
                        try:
                            chunk_idx = int(chunk_idx_str)
                        except ValueError:
                            chunk_idx = -1
                    else:
                        doc_id = first_segment_id
                        chunk_idx = -1
                    
                    # 直接使用collection查询，使用BM25搜索document_id
                    try:
                        # 使用BM25搜索来查找包含document_id的chunks
                        response = collection.query.bm25(
                            query=doc_id,  # 使用document_id作为查询
                            limit=200,
                            return_properties=['content', 'title', 'page_number', 'chunk_index', 'document_id']
                        )
                        
                        # 在结果中查找匹配的chunk_index和document_id
                        matching_obj = None
                        for obj in response.objects:
                            if (obj.properties.get('document_id') == doc_id and 
                                obj.properties.get('chunk_index') == chunk_idx):
                                matching_obj = obj
                                break
                        
                        if not matching_obj:
                            # 如果BM25没找到，尝试遍历所有结果
                            print(f"    [WARNING] BM25未直接匹配，尝试其他方法...")
                            # 改用获取所有chunks并过滤
                            all_chunks = []
                            offset = 0
                            while len(all_chunks) < 500:  # 最多获取500个chunks
                                batch_response = collection.query.fetch_objects(
                                    limit=100,
                                    offset=offset,
                                    return_properties=['content', 'title', 'page_number', 'chunk_index', 'document_id']
                                )
                                if not batch_response.objects:
                                    break
                                
                                for obj in batch_response.objects:
                                    if (obj.properties.get('document_id') == doc_id and 
                                        obj.properties.get('chunk_index') == chunk_idx):
                                        matching_obj = obj
                                        break
                                
                                if matching_obj:
                                    break
                                    
                                offset += 100
                                if offset >= 1000:  # 防止无限循环
                                    break
                        
                        if not matching_obj:
                            print(f"    [ERROR] 未找到片段 (document_id={doc_id}, chunk_index={chunk_idx})")
                            continue
                        
                        content = matching_obj.properties.get('content', '')
                        title = matching_obj.properties.get('title', '未知文档')
                        page = matching_obj.properties.get('page_number', 0)
                        
                    except Exception as query_error:
                        print(f"    [ERROR] 查询失败: {query_error}")
                        continue
                    
                    print(f"\n  片段详情:")
                    print(f"    文档: {title[:80]}")
                    print(f"    页码: {page}")
                    print(f"    内容长度: {len(content)} 字符")
                    print(f"\n  片段内容预览 (前500字符):")
                    print(f"    {'-' * 70}")
                    # 只输出ASCII字符，避免编码错误
                    try:
                        content_preview = content[:500].encode('ascii', errors='ignore').decode('ascii')
                        print(f"    {content_preview}")
                    except:
                        print(f"    {content[:500]}")
                    print(f"    {'-' * 70}")
                    
                    # 分析片段质量
                    print(f"\n  片段质量分析:")
                    
                    # 检查是否包含标题/作者信息
                    lines = content.split('\n')[:10]
                    has_title_pattern = any(
                        any(word in line.lower() for word in ['exploring', 'investigation', 'analysis', 'synthesis', 'received:', 'revised:', 'published:'])
                        for line in lines
                    )
                    
                    # 检查是否包含陨石名称
                    meteorite_keywords = ['meteorite', 'chondrite', 'ALH', 'EETA', 'Murchison', 'Tissint', 'Nakhla', 'Orgueil', 'Allende', 'Tagish', 'Winchcombe']
                    has_meteorite_info = any(keyword.lower() in content.lower() for keyword in meteorite_keywords)
                    
                    # 检查是否包含数据（分类、地点等）
                    has_classification = any(
                        keyword.lower() in content.lower() 
                        for keyword in ['CM2', 'CR2', 'CI', 'H5', 'L6', 'classification', 'chondrite', 'shergottite']
                    )
                    has_location = any(
                        keyword.lower() in content.lower() 
                        for keyword in ['Antarctica', 'Australia', 'Morocco', 'discovered in', 'fell in', 'found in']
                    )
                    has_organic = any(
                        keyword.lower() in content.lower() 
                        for keyword in ['amino acid', 'organic', 'PAH', 'compound', 'carboxylic']
                    )
                    
                    print(f"    包含标题模式: {'是' if has_title_pattern else '否'}")
                    print(f"    包含陨石信息: {'是' if has_meteorite_info else '否'}")
                    print(f"    包含分类信息: {'是' if has_classification else '否'}")
                    print(f"    包含地点信息: {'是' if has_location else '否'}")
                    print(f"    包含有机化合物: {'是' if has_organic else '否'}")
                    
                    # 判断片段质量
                    quality_score = sum([
                        1 if has_meteorite_info else 0,
                        1 if has_classification else 0,
                        1 if has_location else 0,
                        1 if has_organic else 0,
                        -2 if has_title_pattern else 0
                    ])
                    
                    print(f"    片段质量评分: {quality_score}/4")
                    
                    if quality_score <= 0:
                        print(f"    [WARNING] 片段质量较差，可能不包含足够的陨石数据")
                    elif quality_score <= 2:
                        print(f"    [WARNING] 片段质量一般，信息不完整")
                    else:
                        print(f"    [OK] 片段质量较好")
                        
                except Exception as e:
                    print(f"    [ERROR] 获取片段失败: {e}")
            else:
                print(f"  无segment_ids信息")
                
        except Exception as e:
            print(f"  解析metadata失败: {e}")

print(f"\n{'=' * 80}")
print(f"问题案例总结 ({len(problem_cases_summary)} 个):")
print(f"{'=' * 80}")
for case in problem_cases_summary[:20]:
    print(f"\nID={case['pending_id']}: {case['name'][:60] if case['name'] else '(无名称)'}")
    print(f"  问题: {', '.join(case['reasons'])}")
    print(f"  置信度: {case['confidence']:.3f}")

