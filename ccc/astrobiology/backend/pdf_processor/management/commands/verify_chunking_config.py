from django.core.management.base import BaseCommand
from pdf_processor.pdf_utils import GlobalConfig
from pdf_processor.rag_meteorite_extractor import RAGMeteoriteExtractor
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '验证分块配置是否生效并测试数据提取'

    def handle(self, *args, **options):
        self.stdout.write("🔍 验证分块配置是否生效")
        self.stdout.write("=" * 50)
        
        try:
            # 检查当前配置
            self.stdout.write(f"📊 当前分块配置:")
            self.stdout.write(f"  CHUNK_SIZE: {GlobalConfig.CHUNK_SIZE}")
            self.stdout.write(f"  CHUNK_OVERLAP: {GlobalConfig.CHUNK_OVERLAP}")
            
            # 检查配置是否正确
            if GlobalConfig.CHUNK_SIZE == 700 and GlobalConfig.CHUNK_OVERLAP == 80:
                self.stdout.write(self.style.SUCCESS("  ✅ 分块配置正确 (token)"))
            else:
                self.stdout.write(self.style.ERROR("  ❌ 分块配置不正确"))
                return
            
            # 初始化RAG服务
            self.stdout.write(f"\n🔧 初始化RAG服务...")
            extractor = RAGMeteoriteExtractor()
            if not extractor.initialize_services():
                self.stdout.write(self.style.ERROR("❌ RAG服务初始化失败"))
                return
            
            self.stdout.write(self.style.SUCCESS("✅ RAG服务初始化成功"))
            
            # 执行小规模测试
            self.stdout.write(f"\n🧪 执行小规模数据提取测试...")
            task = extractor.extract_from_existing_documents(
                search_query="meteorite",
                max_documents=3,  # 只测试3个文档
                preview_only=False
            )
            
            self.stdout.write(f"📊 提取任务状态: {task.status}")
            
            if task.status == "completed":
                self.stdout.write(self.style.SUCCESS("✅ 数据提取完成"))
                
                # 检查提取结果
                from meteorite_search.models import Meteorite
                recent_meteorites = Meteorite.objects.filter(
                    extraction_source='rag_extraction'
                ).order_by('-created_at')[:5]
                
                self.stdout.write(f"\n📋 最新提取的5条数据:")
                for i, meteorite in enumerate(recent_meteorites, 1):
                    self.stdout.write(f"\n  {i}. ID: {meteorite.id}")
                    self.stdout.write(f"     名称: {meteorite.name}")
                    self.stdout.write(f"     分类: {meteorite.classification}")
                    self.stdout.write(f"     地点: {meteorite.discovery_location}")
                    self.stdout.write(f"     来源: {meteorite.origin}")
                    self.stdout.write(f"     置信度: {meteorite.confidence_score:.3f}")
                    
                    # 检查是否有"Unknown"
                    unknown_fields = []
                    if meteorite.name in ['Unknown', '该论文不包含陨石相关内容']:
                        unknown_fields.append('名称')
                    if meteorite.classification in ['Unknown', '该论文不包含陨石相关内容']:
                        unknown_fields.append('分类')
                    if meteorite.discovery_location in ['Unknown', '该论文不包含陨石相关内容']:
                        unknown_fields.append('地点')
                    
                    if unknown_fields:
                        self.stdout.write(f"     ⚠️ Unknown字段: {', '.join(unknown_fields)}")
                    else:
                        self.stdout.write(f"     ✅ 无Unknown字段")
                
                # 统计Unknown字段
                total_meteorites = recent_meteorites.count()
                unknown_name = sum(1 for m in recent_meteorites if m.name in ['Unknown', '该论文不包含陨石相关内容'])
                unknown_classification = sum(1 for m in recent_meteorites if m.classification in ['Unknown', '该论文不包含陨石相关内容'])
                unknown_location = sum(1 for m in recent_meteorites if m.discovery_location in ['Unknown', '该论文不包含陨石相关内容'])
                
                self.stdout.write(f"\n📊 Unknown字段统计:")
                self.stdout.write(f"  陨石名称: {unknown_name}/{total_meteorites} ({unknown_name/total_meteorites*100:.1f}%)")
                self.stdout.write(f"  分类信息: {unknown_classification}/{total_meteorites} ({unknown_classification/total_meteorites*100:.1f}%)")
                self.stdout.write(f"  发现地点: {unknown_location}/{total_meteorites} ({unknown_location/total_meteorites*100:.1f}%)")
                
                # 评估改进效果
                if unknown_name < total_meteorites * 0.3:  # 少于30%的Unknown
                    self.stdout.write(self.style.SUCCESS("  ✅ 陨石名称提取质量良好"))
                else:
                    self.stdout.write(self.style.WARNING("  ⚠️ 陨石名称提取质量仍需改进"))
                
                if unknown_classification < total_meteorites * 0.3:
                    self.stdout.write(self.style.SUCCESS("  ✅ 分类信息提取质量良好"))
                else:
                    self.stdout.write(self.style.WARNING("  ⚠️ 分类信息提取质量仍需改进"))
                
                if unknown_location < total_meteorites * 0.5:  # 地点信息相对宽松
                    self.stdout.write(self.style.SUCCESS("  ✅ 发现地点提取质量良好"))
                else:
                    self.stdout.write(self.style.WARNING("  ⚠️ 发现地点提取质量仍需改进"))
                
            else:
                self.stdout.write(self.style.ERROR(f"❌ 数据提取失败: {task.error_message}"))
            
            self.stdout.write(self.style.SUCCESS("\n✅ 配置验证完成"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 验证失败: {e}"))
            import traceback
            traceback.print_exc()
