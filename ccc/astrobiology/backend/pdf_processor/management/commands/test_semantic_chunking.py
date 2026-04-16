from django.core.management.base import BaseCommand
from pdf_processor.semantic_chunker import SemanticChunker
from pdf_processor.pdf_utils import GlobalConfig
import json

class Command(BaseCommand):
    help = '测试语义分块效果'

    def handle(self, *args, **options):
        self.stdout.write("🧠 测试语义分块效果")
        self.stdout.write("=" * 50)
        
        chunker = SemanticChunker()
        
        # 测试文本 - 包含陨石信息的复杂文档
        test_text = """
        The Winchcombe meteorite is a CM chondrite that fell in the UK on February 28, 2021. 
        It was recovered from a driveway in Gloucestershire and represents one of the most 
        pristine meteorite falls ever recorded. The meteorite is classified as CM2 chondrite 
        and originated from a carbonaceous asteroid in the outer solar system.
        
        Analysis of the Winchcombe meteorite revealed the presence of various organic compounds 
        including amino acids such as glycine and alanine. The meteorite also contains 
        nucleobases including adenine, guanine, cytosine, and uracil. These findings provide 
        important insights into the prebiotic chemistry of the early solar system.
        
        The Tagish Lake meteorite, discovered in Canada in 2000, is another carbonaceous 
        chondrite that has been extensively studied. This meteorite contains complex organic 
        molecules and has been preserved in cold conditions, making it an excellent sample 
        for studying primitive solar system materials.
        
        Both meteorites demonstrate the rich organic chemistry present in carbonaceous 
        chondrites and their potential role in delivering prebiotic molecules to early Earth.
        """
        
        self.stdout.write(f"📄 测试文档长度: {len(test_text)} 字符")
        
        # 测试不同的分块策略
        strategies = [
            {"name": "固定长度分块", "target_size": 300, "overlap": 80},
            {"name": "语义分块", "target_size": 300, "overlap": 80},
        ]
        
        for strategy in strategies:
            self.stdout.write(f"\n🔧 {strategy['name']}:")
            self.stdout.write("-" * 30)
            
            if strategy['name'] == "固定长度分块":
                # 模拟固定长度分块
                chunks = self._fixed_length_chunking(test_text, strategy['target_size'], strategy['overlap'])
            else:
                # 语义分块
                chunks = chunker.chunk_text_semantic(test_text, strategy['target_size'], strategy['overlap'])
            
            # 分析分块质量
            analysis = chunker.analyze_chunk_quality(chunks)
            
            self.stdout.write(f"📊 分块统计:")
            self.stdout.write(f"  总分块数: {analysis['total_chunks']}")
            self.stdout.write(f"  平均大小: {analysis['avg_size']:.1f} 字符")
            self.stdout.write(f"  大小范围: {analysis['size_range'][0]}-{analysis['size_range'][1]} 字符")
            self.stdout.write(f"  陨石相关分块: {analysis['meteorite_chunks']}/{analysis['total_chunks']}")
            self.stdout.write(f"  完整句子分块: {analysis['complete_sentences']}/{analysis['total_chunks']}")
            self.stdout.write(f"  质量分数: {analysis['quality_score']:.1f}/100")
            
            # 显示前3个分块
            self.stdout.write(f"\n📋 前3个分块预览:")
            for i, chunk in enumerate(chunks[:3]):
                self.stdout.write(f"\n  分块 {i+1} ({len(chunk)} 字符):")
                self.stdout.write(f"    {chunk[:100]}...")
                
                # 检查是否包含关键信息
                keywords = ["Winchcombe", "Tagish Lake", "meteorite", "chondrite", "amino acids"]
                found_keywords = [kw for kw in keywords if kw.lower() in chunk.lower()]
                if found_keywords:
                    self.stdout.write(f"    ✅ 包含关键词: {', '.join(found_keywords)}")
                else:
                    self.stdout.write(f"    ❌ 未包含关键陨石信息")
        
        self.stdout.write(f"\n🎯 语义分块的优势:")
        self.stdout.write(f"  1. ✅ 保持语义完整性 - 不会在句子中间切断")
        self.stdout.write(f"  2. ✅ 识别陨石边界 - 优先在陨石相关信息处分割")
        self.stdout.write(f"  3. ✅ 提高信息密度 - 每个分块包含更完整的上下文")
        self.stdout.write(f"  4. ✅ 减少信息丢失 - 避免关键信息被分割到不同分块")
        
        self.stdout.write(f"\n💡 建议:")
        self.stdout.write(f"  - 将语义分块集成到PDF处理流程中")
        self.stdout.write(f"  - 针对陨石文献优化语义边界识别")
        self.stdout.write(f"  - 结合固定长度分块作为备选方案")
        
        self.stdout.write(self.style.SUCCESS("\n✅ 语义分块测试完成"))
    
    def _fixed_length_chunking(self, text: str, chunk_size: int, overlap: int) -> list:
        """模拟固定长度分块"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:].strip())
                break
            
            # 寻找最近的句号
            last_period = text.rfind('.', start, end)
            if last_period > start + chunk_size * 0.7:  # 如果句号在70%位置之后
                end = last_period + 1
            
            chunks.append(text[start:end].strip())
            start = end - overlap
        
        return chunks
