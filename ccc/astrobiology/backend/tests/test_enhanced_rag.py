#!/usr/bin/env python3
"""
测试增强RAG功能
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

from pdf_processor.question_classifier import QuestionClassifier, QuestionType
from pdf_processor.specialized_answer_generator import SpecializedAnswerGenerator
from pdf_processor.enhanced_rag_service import EnhancedRAGService

def test_question_classifier():
    """测试问题分类器"""
    print("=== 测试问题分类器 ===")
    
    try:
        classifier = QuestionClassifier()
        
        # 测试问题
        test_questions = [
            "不同陨石类型分别发现了什么？",
            "Murchison陨石中检测到了哪些有机化合物？",
            "矿物与有机质是如何关联的？",
            "这些发现有什么科学意义？",
            "数据库中有多少陨石记录？",
            "什么是天体生物学？",
            "Murchison陨石的详细信息是什么？",
            "氨基酸是如何与粘土矿物结合的？"
        ]
        
        print(f"测试 {len(test_questions)} 个问题:")
        
        for i, question in enumerate(test_questions, 1):
            question_type, confidence, details = classifier.classify(question)
            print(f"{i}. {question}")
            print(f"   类型: {question_type.value}")
            print(f"   置信度: {confidence:.2f}")
            print(f"   匹配模式: {details.get('matched_patterns', {}).get('keyword_count', 0)} 个关键词, {details.get('matched_patterns', {}).get('phrase_count', 0)} 个短语")
            print()
        
        # 测试批量分类
        batch_results = classifier.batch_classify(test_questions)
        
        # 统计结果
        type_counts = {}
        confidence_scores = []
        
        for result in batch_results:
            question_type = result['primary_type']
            type_counts[question_type] = type_counts.get(question_type, 0) + 1
            confidence_scores.append(result['confidence'])
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        print("分类统计:")
        print(f"  平均置信度: {avg_confidence:.2f}")
        print(f"  类型分布: {type_counts}")
        print(f"  高置信度问题: {len([c for c in confidence_scores if c >= 0.7])}")
        print(f"  低置信度问题: {len([c for c in confidence_scores if c < 0.3])}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 问题分类器测试失败: {str(e)}")
        return False

def test_specialized_answer_generator():
    """测试专门答案生成器"""
    print("\n=== 测试专门答案生成器 ===")
    
    try:
        generator = SpecializedAnswerGenerator()
        
        # 测试不同类型的问题
        test_cases = [
            {
                'question': "不同陨石类型分别发现了什么？",
                'type': QuestionType.METEORITE_TYPE_COMPARISON
            },
            {
                'question': "矿物与有机质是如何关联的？",
                'type': QuestionType.ORGANICS_MINERAL_ASSOCIATION
            },
            {
                'question': "检测到了哪些有机化合物？",
                'type': QuestionType.ORGANIC_COMPOUNDS
            },
            {
                'question': "这些发现有什么科学意义？",
                'type': QuestionType.SCIENTIFIC_SIGNIFICANCE
            },
            {
                'question': "数据库中有多少陨石记录？",
                'type': QuestionType.STATISTICAL_QUERY
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            question = test_case['question']
            question_type = test_case['type']
            
            print(f"{i}. 测试问题: {question}")
            print(f"   类型: {question_type.value}")
            
            result = generator.generate_answer(question, question_type, 0.8)
            
            print(f"   答案类型: {result.get('answer_type', 'unknown')}")
            print(f"   数据源: {result.get('data_source', 'unknown')}")
            print(f"   置信度: {result.get('confidence', 0.0):.2f}")
            
            # 显示答案摘要
            answer = result.get('answer', '')
            if answer:
                answer_preview = answer[:200] + '...' if len(answer) > 200 else answer
                print(f"   答案预览: {answer_preview}")
            
            print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 专门答案生成器测试失败: {str(e)}")
        return False

def test_enhanced_rag_service():
    """测试增强RAG服务"""
    print("\n=== 测试增强RAG服务 ===")
    
    try:
        service = EnhancedRAGService()
        
        # 初始化服务
        if not service.initialize():
            print("[ERROR] 增强RAG服务初始化失败")
            return False
        
        print("[OK] 增强RAG服务初始化成功")
        
        # 测试问题分析
        test_question = "不同陨石类型分别发现了什么？"
        print(f"\n测试问题分析: {test_question}")
        
        analysis = service.get_question_analysis(test_question)
        print(f"分析结果: {json.dumps(analysis, indent=2, ensure_ascii=False)}")
        
        # 测试问答
        print(f"\n测试问答: {test_question}")
        
        answer_result = service.ask_question(test_question)
        
        print(f"答案类型: {answer_result.get('answer_type', 'unknown')}")
        print(f"使用的方法: {answer_result.get('method_used', 'unknown')}")
        print(f"置信度: {answer_result.get('confidence', 0.0):.2f}")
        
        # 显示答案
        answer = answer_result.get('answer', '')
        if answer:
            answer_preview = answer[:300] + '...' if len(answer) > 300 else answer
            print(f"答案预览: {answer_preview}")
        
        # 测试服务统计
        print("\n测试服务统计:")
        statistics = service.get_service_statistics()
        print(f"服务状态: {statistics.get('service_status', 'unknown')}")
        
        db_stats = statistics.get('database_stats', {})
        print(f"陨石记录数: {db_stats.get('total_meteorites', 0)}")
        print(f"提取结果数: {db_stats.get('total_extractions', 0)}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 增强RAG服务测试失败: {str(e)}")
        return False

def test_classification_accuracy():
    """测试分类准确性"""
    print("\n=== 测试分类准确性 ===")
    
    try:
        classifier = QuestionClassifier()
        
        # 已知答案的测试问题
        test_cases = [
            {
                'question': "不同陨石类型分别发现了什么？",
                'expected_type': QuestionType.METEORITE_TYPE_COMPARISON,
                'expected_confidence': 0.7
            },
            {
                'question': "矿物与有机质是如何关联的？",
                'expected_type': QuestionType.ORGANICS_MINERAL_ASSOCIATION,
                'expected_confidence': 0.7
            },
            {
                'question': "Murchison陨石的详细信息是什么？",
                'expected_type': QuestionType.METEORITE_DETAILS,
                'expected_confidence': 0.6
            },
            {
                'question': "检测到了哪些有机化合物？",
                'expected_type': QuestionType.ORGANIC_COMPOUNDS,
                'expected_confidence': 0.7
            },
            {
                'question': "数据库中有多少陨石记录？",
                'expected_type': QuestionType.STATISTICAL_QUERY,
                'expected_confidence': 0.6
            }
        ]
        
        correct_predictions = 0
        high_confidence_predictions = 0
        
        for i, test_case in enumerate(test_cases, 1):
            question = test_case['question']
            expected_type = test_case['expected_type']
            expected_confidence = test_case['expected_confidence']
            
            question_type, confidence, details = classifier.classify(question)
            
            is_correct = question_type == expected_type
            is_high_confidence = confidence >= expected_confidence
            
            if is_correct:
                correct_predictions += 1
            if is_high_confidence:
                high_confidence_predictions += 1
            
            print(f"{i}. {question}")
            print(f"   预期类型: {expected_type.value}")
            print(f"   实际类型: {question_type.value}")
            print(f"   类型正确: {'是' if is_correct else '否'}")
            print(f"   置信度: {confidence:.2f} (预期: {expected_confidence:.2f})")
            print(f"   置信度达标: {'是' if is_high_confidence else '否'}")
            print()
        
        accuracy = correct_predictions / len(test_cases) * 100
        confidence_rate = high_confidence_predictions / len(test_cases) * 100
        
        print(f"分类准确性: {accuracy:.1f}% ({correct_predictions}/{len(test_cases)})")
        print(f"高置信度率: {confidence_rate:.1f}% ({high_confidence_predictions}/{len(test_cases)})")
        
        return accuracy >= 80  # 期望至少80%的准确性
        
    except Exception as e:
        print(f"[ERROR] 分类准确性测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        success_count = 0
        total_tests = 4
        
        print("开始增强RAG功能测试...\n")
        
        if test_question_classifier():
            success_count += 1
        
        if test_specialized_answer_generator():
            success_count += 1
        
        if test_enhanced_rag_service():
            success_count += 1
        
        if test_classification_accuracy():
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
