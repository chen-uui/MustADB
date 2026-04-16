"""
调试增量合并系统的Django管理命令
"""
import logging
from django.core.management.base import BaseCommand
from pdf_processor.rag_meteorite_extractor import RAGMeteoriteExtractor
from pdf_processor.management.commands.incremental_merge_extraction import IncrementalMergeExtractor, IncrementalMergeConfig

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '调试增量合并系统的问题'

    def handle(self, *args, **options):
        self.stdout.write("🔍 调试增量合并系统...")
        
        # 1. 测试RAG提取器
        self.stdout.write("\n1️⃣ 测试RAG提取器...")
        extractor = RAGMeteoriteExtractor()
        if not extractor.initialize_services():
            self.stdout.write(self.style.ERROR("❌ RAG服务初始化失败"))
            return
        
        self.stdout.write(self.style.SUCCESS("✅ RAG服务初始化成功"))
        
        # 2. 测试搜索功能
        self.stdout.write("\n2️⃣ 测试搜索功能...")
        segments = extractor._search_meteorite_segments_optimized(3)
        self.stdout.write(f"找到 {len(segments)} 个片段")
        
        if not segments:
            self.stdout.write(self.style.ERROR("❌ 没有找到任何片段"))
            return
        
        # 3. 测试单个片段提取
        self.stdout.write("\n3️⃣ 测试单个片段提取...")
        test_segment = segments[0]
        content_preview = test_segment.get('content', '')[:100]
        self.stdout.write(f"测试片段: {content_preview}...")
        
        result = extractor.extract_from_segment(test_segment)
        self.stdout.write(f"提取结果类型: {type(result)}")
        
        if result:
            self.stdout.write(f"完整结果结构: {result}")
            
            # 检查不同的置信度字段
            confidence_score = result.get('confidence_score', 'N/A')
            confidence = result.get('confidence', 'N/A')
            data_confidence = result.get('data', {}).get('confidence', 'N/A') if result.get('data') else 'N/A'
            
            self.stdout.write(f"confidence_score: {confidence_score}")
            self.stdout.write(f"confidence: {confidence}")
            self.stdout.write(f"data.confidence: {data_confidence}")
            
            meteorite_data = result.get('meteorite_data', {})
            if not meteorite_data and result.get('data'):
                meteorite_data = result['data'].get('meteorite_data', {})
            
            self.stdout.write(f"陨石数据: {meteorite_data}")
            
            # 检查置信度阈值
            final_confidence = confidence_score if confidence_score != 'N/A' else (confidence if confidence != 'N/A' else data_confidence)
            if isinstance(final_confidence, (int, float)) and final_confidence >= 0.6:
                self.stdout.write(self.style.SUCCESS("✅ 置信度检查通过"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ 置信度检查失败: {final_confidence} < 0.6"))
        else:
            self.stdout.write(self.style.ERROR("❌ 提取失败"))
            return
        
        # 4. 测试增量合并系统
        self.stdout.write("\n4️⃣ 测试增量合并系统...")
        config = IncrementalMergeConfig(
            similarity_threshold=0.5,  # 降低阈值
            merge_strategy='intelligent'
        )
        
        merge_extractor = IncrementalMergeExtractor(config)
        
        # 测试合并逻辑
        if result and isinstance(result.get('confidence_score'), (int, float)) and result.get('confidence_score', 0) >= 0.5:
            self.stdout.write(self.style.SUCCESS("✅ 置信度检查通过"))
            
            # 测试合并
            merged = merge_extractor._try_merge_with_existing(result)
            self.stdout.write(f"合并结果: {merged}")
            
            if merged:
                self.stdout.write(self.style.SUCCESS("✅ 数据已合并"))
            else:
                self.stdout.write(self.style.SUCCESS("✅ 数据已新增"))
        else:
            confidence = result.get('confidence_score', 'N/A') if result else 'N/A'
            self.stdout.write(self.style.ERROR(f"❌ 置信度检查失败: {confidence}"))
        
        # 5. 检查统计计算
        self.stdout.write("\n5️⃣ 检查统计计算...")
        self.stdout.write(f"新增提取数: {merge_extractor.stats['new_extractions']}")
        self.stdout.write(f"合并提取数: {merge_extractor.stats['merged_extractions']}")
        self.stdout.write(f"处理文档数: {merge_extractor.stats['processed_documents']}")
        
        self.stdout.write(self.style.SUCCESS("✅ 调试完成"))
