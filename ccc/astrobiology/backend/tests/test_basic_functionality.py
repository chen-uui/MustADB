#!/usr/bin/env python3
"""
快速功能测试脚本
"""

import os
import sys
import django

# 设置环境变量
os.environ['SECRET_KEY'] = 'django-insecure-test-key-for-development-only'
os.environ['JWT_SECRET'] = 'jwt-secret-key-for-development-only'

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

def test_basic_functionality():
    """测试基本功能"""
    print("🚀 增强RAG系统功能测试")
    print("=" * 50)
    
    # 1. 测试数据库连接
    try:
        from pdf_processor.models import PDFDocument
        doc_count = PDFDocument.objects.count()
        print(f"✅ 数据库连接正常 - 可用文档: {doc_count}")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False
    
    # 2. 测试问题分类器
    try:
        from pdf_processor.question_classifier import QuestionClassifier
        classifier = QuestionClassifier()
        
        test_questions = [
            "不同陨石类型分别发现了什么？",
            "矿物与有机质是如何关联的？", 
            "Murchison陨石的详细信息是什么？"
        ]
        
        print("\n🧠 问题分类测试:")
        for question in test_questions:
            classification = classifier.classify(question)
            print(f"  ❓ {question}")
            print(f"     -> {classification}")
        
        print("✅ 问题分类器功能正常")
    except Exception as e:
        print(f"❌ 问题分类器测试失败: {e}")
        return False
    
    # 3. 测试数据同步服务
    try:
        from pdf_processor.services.data_sync_service import DataSyncService
        sync_service = DataSyncService()
        print("✅ 数据同步服务可用")
    except Exception as e:
        print(f"❌ 数据同步服务测试失败: {e}")
        return False
    
    # 4. 测试专门答案生成器
    try:
        from pdf_processor.specialized_answer_generator import SpecializedAnswerGenerator
        generator = SpecializedAnswerGenerator()
        print("✅ 专门答案生成器可用")
    except Exception as e:
        print(f"❌ 专门答案生成器测试失败: {e}")
        return False
    
    return True

def show_next_steps():
    """显示下一步建议"""
    print("\n🎯 下一步建议")
    print("=" * 50)
    
    print("1. 🚀 启动服务:")
    print("   # 设置环境变量")
    print("   $env:SECRET_KEY='django-insecure-test-key-for-development-only'")
    print("   $env:JWT_SECRET='jwt-secret-key-for-development-only'")
    print()
    print("   # 启动后端")
    print("   python manage.py runserver")
    print()
    print("   # 启动前端 (另一个终端)")
    print("   cd ../astro_frontend")
    print("   npm run dev")
    print()
    
    print("2. 🧪 小规模测试:")
    print("   - 访问 http://localhost:5173")
    print("   - 选择2-3篇论文进行提取")
    print("   - 验证矿物关联信息提取")
    print("   - 测试问答功能")
    print()
    
    print("3. 📊 评估结果:")
    print("   - 检查提取质量")
    print("   - 验证数据同步")
    print("   - 测试问答准确性")
    print()
    
    print("4. 🎯 决定下一步:")
    print("   - 如果测试通过 → 可以运行大规模提取")
    print("   - 如果发现问题 → 先修复问题")

if __name__ == "__main__":
    success = test_basic_functionality()
    
    if success:
        print("\n🎉 所有基本功能测试通过！")
        show_next_steps()
    else:
        print("\n⚠️ 部分功能测试失败，请检查系统配置")
    
    sys.exit(0 if success else 1)
