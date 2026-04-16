from django.core.management.base import BaseCommand
from pdf_processor.pdf_utils import GlobalConfig, PDFUtils
from pdf_processor.weaviate_services import WeaviateVectorService
import weaviate

class Command(BaseCommand):
    help = '分析Weaviate中的文档分块情况'

    def handle(self, *args, **options):
        self.stdout.write("🔍 分析Weaviate中的文档分块情况")
        self.stdout.write("=" * 50)
        
        try:
            # 连接Weaviate
            client = weaviate.Client(url=GlobalConfig.WEAVIATE_URL)
            
            # 获取所有文档块
            query = """
            {
              Get {
                PDFDocument {
                  _additional {
                    id
                  }
                  title
                  content
                  chunk_index
                  total_chunks
                }
              }
            }
            """
            
            result = client.query.raw(query)
            
            if not result or 'data' not in result or 'Get' not in result['data']:
                self.stdout.write(self.style.ERROR("❌ 无法获取Weaviate数据"))
                return
            
            documents = result['data']['Get']['PDFDocument']
            total_chunks = len(documents)
            
            self.stdout.write(f"📊 总文档块数: {total_chunks}")
            
            if total_chunks == 0:
                self.stdout.write(self.style.WARNING("⚠️ 没有找到文档块"))
                return
            
            # 分析分块大小
            chunk_sizes = []
            chunk_lengths = []
            
            for doc in documents:
                content = doc.get('content', '')
                chunk_sizes.append(len(content))
                chunk_lengths.append(len(content.split()))
            
            avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
            avg_chunk_words = sum(chunk_lengths) / len(chunk_lengths)
            min_chunk_size = min(chunk_sizes)
            max_chunk_size = max(chunk_sizes)
            
            self.stdout.write(f"\n📏 分块大小分析:")
            self.stdout.write(f"  平均字符数: {avg_chunk_size:.0f}")
            self.stdout.write(f"  平均单词数: {avg_chunk_words:.0f}")
            self.stdout.write(f"  最小字符数: {min_chunk_size}")
            self.stdout.write(f"  最大字符数: {max_chunk_size}")
            self.stdout.write(f"  当前配置: CHUNK_SIZE={GlobalConfig.CHUNK_SIZE}, CHUNK_OVERLAP={GlobalConfig.CHUNK_OVERLAP}")
            
            # 分析分块质量
            small_chunks = sum(1 for size in chunk_sizes if size < 500)
            medium_chunks = sum(1 for size in chunk_sizes if 500 <= size < 1000)
            large_chunks = sum(1 for size in chunk_sizes if size >= 1000)
            
            self.stdout.write(f"\n📊 分块质量分布:")
            self.stdout.write(f"  小分块 (<500字符): {small_chunks} ({small_chunks/total_chunks*100:.1f}%)")
            self.stdout.write(f"  中分块 (500-1000字符): {medium_chunks} ({medium_chunks/total_chunks*100:.1f}%)")
            self.stdout.write(f"  大分块 (≥1000字符): {large_chunks} ({large_chunks/total_chunks*100:.1f}%)")
            
            # 显示前5个分块的示例
            self.stdout.write(f"\n📋 前5个分块示例:")
            for i, doc in enumerate(documents[:5], 1):
                content = doc.get('content', '')
                title = doc.get('title', 'Unknown')
                chunk_index = doc.get('chunk_index', 'Unknown')
                total_chunks = doc.get('total_chunks', 'Unknown')
                
                self.stdout.write(f"\n  {i}. 标题: {title}")
                self.stdout.write(f"     分块: {chunk_index}/{total_chunks}")
                self.stdout.write(f"     长度: {len(content)} 字符, {len(content.split())} 单词")
                self.stdout.write(f"     内容预览: {content[:200]}...")
            
            # 分析问题
            self.stdout.write(f"\n🎯 问题分析:")
            
            if avg_chunk_size < 700 * 0.8:
                self.stdout.write(self.style.WARNING("  ⚠️ 平均分块大小过小（按字符估算），可能导致信息不完整"))
            
            if small_chunks > total_chunks * 0.3:
                self.stdout.write(self.style.WARNING("  ⚠️ 小分块比例过高，可能影响数据提取质量"))
            
            if max_chunk_size < GlobalConfig.CHUNK_SIZE * PDFUtils._avg_chars_per_token * 0.8:
                self.stdout.write(self.style.WARNING("  ⚠️ 最大分块大小（字符）低于配置对应值，可能存在截断"))
            
            # 建议
            self.stdout.write(f"\n💡 改进建议:")
            
            if avg_chunk_size < 700 * PDFUtils._avg_chars_per_token:
                self.stdout.write("  1. 增加CHUNK_SIZE到900-1100 token")
                self.stdout.write("  2. 增加CHUNK_OVERLAP到100-150 token")
                self.stdout.write("  3. 重新处理PDF文档以生成更大的分块")
            
            self.stdout.write("  4. 考虑使用语义分块而非固定长度分块")
            self.stdout.write("  5. 优化分块边界检测，避免在句子中间截断")
            
            # 检查是否有文档被过度分块
            doc_chunk_counts = {}
            for doc in documents:
                title = doc.get('title', 'Unknown')
                if title not in doc_chunk_counts:
                    doc_chunk_counts[title] = 0
                doc_chunk_counts[title] += 1
            
            over_chunked = {title: count for title, count in doc_chunk_counts.items() if count > 20}
            if over_chunked:
                self.stdout.write(f"\n⚠️ 过度分块的文档:")
                for title, count in over_chunked.items():
                    self.stdout.write(f"  - {title}: {count} 个分块")
            
            self.stdout.write(self.style.SUCCESS("\n✅ 分块分析完成"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 分析失败: {e}"))
            import traceback
            traceback.print_exc()
