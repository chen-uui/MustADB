#!/usr/bin/env python3
"""
测试数据同步服务
"""

import os
import sys
import django
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

from pdf_processor.services.data_sync_service import DataSyncService
from pdf_processor.models import DirectProcessingResult
from meteorite_search.models import Meteorite

def test_data_sync_service():
    """测试数据同步服务"""
    print("=== 测试数据同步服务 ===")
    
    try:
        # 初始化服务
        sync_service = DataSyncService()
        print("[OK] DataSyncService初始化成功")
        
        # 测试获取同步统计
        statistics = sync_service.get_sync_statistics()
        print(f"[OK] 获取同步统计成功: {statistics}")
        
        # 测试清理重复记录
        cleanup_results = sync_service.cleanup_duplicate_meteorites()
        print(f"[OK] 清理重复记录: {cleanup_results}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {str(e)}")
        return False

def test_sync_with_sample_data():
    """使用样本数据测试同步功能"""
    print("\n=== 测试样本数据同步 ===")
    
    try:
        # 创建样本DirectProcessingResult
        sample_extraction = DirectProcessingResult.objects.create(
            document_path="test/sample.pdf",
            document_title="测试文档",
            processing_time=10.5,
            confidence_score=0.85,
            meteorite_data={
                "name": "Murchison",
                "classification": "CM2",
                "location": "Australia",
                "date": "1969"
            },
            organic_compounds={
                "compounds": ["glycine", "alanine", "proline"],
                "concentration": "10-100 ppm",
                "explanation": "检测到多种氨基酸"
            },
            mineral_relationships={
                "minerals": ["clay minerals", "olivine"],
                "associations": [
                    {
                        "mineral": "clay minerals",
                        "organic_compounds": ["glycine", "alanine"],
                        "association_type": "ionic exchange",
                        "description": "氨基酸通过离子交换与粘土矿物结合",
                        "evidence": "FTIR spectra showed characteristic bands at 1650 cm-1",
                        "significance": "protects organic molecules from degradation"
                    }
                ],
                "explanation": "论文中分析了矿物与有机质的相互作用"
            },
            scientific_insights={
                "significance": "为理解生命起源提供重要信息",
                "explanation": "该研究为理解小行星表面有机物质的来源和分布提供了重要信息"
            },
            status='completed'
        )
        
        print(f"[OK] 创建样本提取结果: {sample_extraction.id}")
        
        # 测试同步
        sync_service = DataSyncService()
        meteorite = sync_service.sync_extraction_to_meteorite(str(sample_extraction.id))
        
        if meteorite:
            print(f"[OK] 同步成功: {meteorite.name} (ID: {meteorite.id})")
            print(f"   分类: {meteorite.classification}")
            print(f"   置信度: {meteorite.confidence_score}")
            print(f"   数据来源: {meteorite.extraction_source}")
            
            # 检查矿物关联信息
            metadata = meteorite.extraction_metadata
            if isinstance(metadata, dict):
                mineral_associations = metadata.get('mineral_associations', [])
                print(f"   矿物关联数量: {len(mineral_associations)}")
                
                if mineral_associations:
                    first_assoc = mineral_associations[0]
                    print(f"   第一个关联: {first_assoc.get('mineral')} - {first_assoc.get('association_type')}")
            
            return True
        else:
            print("[ERROR] 同步失败")
            return False
            
    except Exception as e:
        print(f"[ERROR] 测试失败: {str(e)}")
        return False

def test_batch_sync():
    """测试批量同步"""
    print("\n=== 测试批量同步 ===")
    
    try:
        # 获取最近的几个提取结果
        recent_extractions = DirectProcessingResult.objects.filter(
            status='completed'
        ).order_by('-created_at')[:3]
        
        if not recent_extractions:
            print("[WARNING] 没有找到提取结果进行测试")
            return True
        
        extraction_ids = [str(extraction.id) for extraction in recent_extractions]
        print(f"[INFO] 找到 {len(extraction_ids)} 个提取结果")
        
        # 测试批量同步
        sync_service = DataSyncService()
        results = sync_service.sync_batch_extractions(extraction_ids)
        
        print(f"[OK] 批量同步结果: {results}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 批量同步测试失败: {str(e)}")
        return False

def test_recent_sync():
    """测试最近提取结果同步"""
    print("\n=== 测试最近提取结果同步 ===")
    
    try:
        sync_service = DataSyncService()
        results = sync_service.sync_recent_extractions(hours=24)
        
        print(f"[OK] 最近24小时同步结果: {results}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 最近同步测试失败: {str(e)}")
        return False

def analyze_existing_data():
    """分析现有数据"""
    print("\n=== 分析现有数据 ===")
    
    try:
        # 分析DirectProcessingResult
        total_extractions = DirectProcessingResult.objects.count()
        completed_extractions = DirectProcessingResult.objects.filter(status='completed').count()
        
        print(f"[INFO] 总提取结果: {total_extractions}")
        print(f"[INFO] 已完成提取: {completed_extractions}")
        
        # 分析Meteorite
        total_meteorites = Meteorite.objects.count()
        rag_meteorites = Meteorite.objects.filter(extraction_source='rag_extraction').count()
        pending_review = Meteorite.objects.filter(review_status='pending').count()
        
        print(f"[INFO] 总陨石记录: {total_meteorites}")
        print(f"[INFO] RAG提取陨石: {rag_meteorites}")
        print(f"[INFO] 待审核陨石: {pending_review}")
        
        # 分析矿物关联数据
        meteorites_with_associations = 0
        for meteorite in Meteorite.objects.filter(extraction_source='rag_extraction'):
            metadata = meteorite.extraction_metadata
            if isinstance(metadata, dict):
                associations = metadata.get('mineral_associations', [])
                if associations:
                    meteorites_with_associations += 1
        
        print(f"[INFO] 包含矿物关联的陨石: {meteorites_with_associations}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 数据分析失败: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        success_count = 0
        total_tests = 5
        
        if test_data_sync_service():
            success_count += 1
        
        if test_sync_with_sample_data():
            success_count += 1
        
        if test_batch_sync():
            success_count += 1
        
        if test_recent_sync():
            success_count += 1
        
        if analyze_existing_data():
            success_count += 1
        
        print(f"\n=== 测试完成 ===")
        print(f"[INFO] 成功: {success_count}/{total_tests}")
        
        if success_count == total_tests:
            print("[OK] 所有测试通过")
        else:
            print("[WARNING] 部分测试失败")
        
    except Exception as e:
        print(f"[ERROR] 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
