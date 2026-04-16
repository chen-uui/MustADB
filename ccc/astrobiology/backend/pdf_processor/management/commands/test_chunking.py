from django.core.management.base import BaseCommand
from pdf_processor.pdf_utils import GlobalConfig, PDFUtils
import os

class Command(BaseCommand):
    help = '测试优化后的分块配置效果'

    def handle(self, *args, **options):
        self.stdout.write("🧪 测试优化后的分块配置效果")
        self.stdout.write("=" * 50)
        
        try:
            # 显示配置
            self.stdout.write(f"📊 当前分块配置 (token):")
            self.stdout.write(f"  CHUNK_SIZE: {GlobalConfig.CHUNK_SIZE}")
            self.stdout.write(f"  CHUNK_OVERLAP: {GlobalConfig.CHUNK_OVERLAP}")
            
            # 测试文档：包含完整陨石信息的论文摘要
            test_text = """
            Abstract: We report the comprehensive analysis of the Martian meteorite NWA 7034, 
            discovered in Northwest Africa in 2011. This meteorite is classified as a Martian 
            shergottite and represents one of the most primitive Martian meteorites known. 
            The meteorite was found in the Sahara Desert and weighs approximately 320 grams. 
            It contains significant amounts of organic compounds including amino acids such as 
            glycine, alanine, and valine, as well as carboxylic acids including formic acid 
            and acetic acid. The meteorite was found to contain 2.3 wt% total organic carbon 
            with δ13C values ranging from -25‰ to -30‰, indicating a terrestrial contamination 
            level of less than 5%. Mineral analysis revealed the presence of olivine, pyroxene, 
            and clay minerals including smectite and chlorite. The organic compounds show 
            strong associations with clay minerals through ionic exchange mechanisms, as 
            evidenced by FTIR spectroscopy showing characteristic absorption bands at 1650 cm-1 
            and 1540 cm-1. This association is significant for understanding the preservation 
            of organic matter on Mars and its potential role in prebiotic chemistry. The 
            meteorite also contains nucleotide bases including adenine and guanine, suggesting 
            the presence of prebiotic molecules. Isotopic analysis reveals δ15N values of 
            +50‰, consistent with Martian atmospheric composition. The discovery of NWA 7034 
            provides crucial evidence for the presence of water and organic matter on early 
            Mars, supporting the hypothesis that Mars may have had conditions suitable for 
            life during its early history.
            """
            
            self.stdout.write(f"\n📄 测试文档长度: {len(test_text)} 字符")
            
            # 分块处理 - 使用uuid_sync中的方法
            from pdf_processor.management.commands.uuid_sync import Command as UUIDSyncCommand
            uuid_sync = UUIDSyncCommand()
            chunks = uuid_sync.chunk_text(test_text)
            
            self.stdout.write(f"\n📦 分块结果:")
            self.stdout.write(f"  分块数量: {len(chunks)}")
            
            # 分析每个分块
            for i, chunk in enumerate(chunks, 1):
                chunk_length = len(chunk)
                chunk_tokens = PDFUtils.count_tokens(chunk)
                chunk_words = len(chunk.split())
                
                self.stdout.write(f"\n  分块 {i}:")
                self.stdout.write(f"    长度: {chunk_length} 字符, {chunk_tokens} token, {chunk_words} 单词")
                self.stdout.write(f"    内容预览: {chunk[:150]}...")
                
                # 检查关键信息是否完整
                key_info = {
                    'NWA 7034': 'NWA 7034' in chunk,
                    'Northwest Africa': 'Northwest Africa' in chunk,
                    '2011': '2011' in chunk,
                    'Martian shergottite': 'Martian shergottite' in chunk,
                    'glycine': 'glycine' in chunk,
                    'alanine': 'alanine' in chunk,
                    'formic acid': 'formic acid' in chunk,
                    '2.3 wt%': '2.3 wt%' in chunk,
                    'δ13C': 'δ13C' in chunk,
                    'olivine': 'olivine' in chunk,
                    'pyroxene': 'pyroxene' in chunk,
                    'clay minerals': 'clay minerals' in chunk,
                    'FTIR': 'FTIR' in chunk,
                    'adenine': 'adenine' in chunk,
                    'δ15N': 'δ15N' in chunk
                }
                
                complete_info = sum(key_info.values())
                total_info = len(key_info)
                completeness = complete_info / total_info * 100
                
                self.stdout.write(f"    信息完整性: {complete_info}/{total_info} ({completeness:.1f}%)")
                
                if completeness >= 80:
                    self.stdout.write(f"    ✅ 信息完整")
                elif completeness >= 60:
                    self.stdout.write(f"    ⚠️ 信息较完整")
                else:
                    self.stdout.write(f"    ❌ 信息不完整")
            
            # 总体评估
            self.stdout.write(f"\n🎯 总体评估:")
            
            # 计算平均完整性
            total_completeness = 0
            for chunk in chunks:
                key_info = {
                    'NWA 7034': 'NWA 7034' in chunk,
                    'Northwest Africa': 'Northwest Africa' in chunk,
                    '2011': '2011' in chunk,
                    'Martian shergottite': 'Martian shergottite' in chunk,
                    'glycine': 'glycine' in chunk,
                    'alanine': 'alanine' in chunk,
                    'formic acid': 'formic acid' in chunk,
                    '2.3 wt%': '2.3 wt%' in chunk,
                    'δ13C': 'δ13C' in chunk,
                    'olivine': 'olivine' in chunk,
                    'pyroxene': 'pyroxene' in chunk,
                    'clay minerals': 'clay minerals' in chunk,
                    'FTIR': 'FTIR' in chunk,
                    'adenine': 'adenine' in chunk,
                    'δ15N': 'δ15N' in chunk
                }
                completeness = sum(key_info.values()) / len(key_info) * 100
                total_completeness += completeness
            
            avg_completeness = total_completeness / len(chunks)
            
            self.stdout.write(f"  平均信息完整性: {avg_completeness:.1f}%")
            
            if avg_completeness >= 80:
                self.stdout.write(self.style.SUCCESS("  ✅ 分块配置优秀，信息完整性很高"))
            elif avg_completeness >= 60:
                self.stdout.write(self.style.WARNING("  ⚠️ 分块配置良好，信息完整性中等"))
            else:
                self.stdout.write(self.style.ERROR("  ❌ 分块配置需要进一步优化"))
            
            # 建议
            self.stdout.write(f"\n💡 建议:")
            if avg_completeness < 80:
                self.stdout.write("  1. 考虑进一步增加CHUNK_SIZE到900-1100 token")
                self.stdout.write("  2. 增加CHUNK_OVERLAP到100-150 token")
                self.stdout.write("  3. 使用语义分块而非固定长度分块")
            else:
                self.stdout.write("  1. 当前配置效果良好，可以用于实际数据提取")
                self.stdout.write("  2. 建议重新处理PDF文档并测试数据提取质量")
            
            self.stdout.write(self.style.SUCCESS("\n✅ 分块配置测试完成"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 测试失败: {e}"))
            import traceback
            traceback.print_exc()
