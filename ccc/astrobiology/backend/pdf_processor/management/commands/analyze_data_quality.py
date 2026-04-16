from django.core.management.base import BaseCommand
from meteorite_search.review_models import PendingMeteorite

class Command(BaseCommand):
    help = '分析提取的陨石数据质量'

    def handle(self, *args, **options):
        self.stdout.write("🔍 分析提取的陨石数据质量")
        self.stdout.write("=" * 60)
        
        try:
            # 获取所有待审核数据
            pending_meteorites = PendingMeteorite.objects.all()
            total_count = pending_meteorites.count()
            
            self.stdout.write(f"📊 总数据量: {total_count} 条")
            
            if total_count == 0:
                self.stdout.write(self.style.ERROR("❌ 没有找到待审核数据"))
                return
            
            # 分析各字段质量
            self.stdout.write(f"\n📋 字段质量分析:")
            
            # 分析name字段
            unknown_names = pending_meteorites.filter(name__in=['Unknown', '', None]).count()
            valid_names = total_count - unknown_names
            self.stdout.write(f"  陨石名称: {valid_names}/{total_count} ({valid_names/total_count*100:.1f}% 有效)")
            
            # 分析classification字段
            unknown_classifications = pending_meteorites.filter(classification__in=['Unknown', '', None]).count()
            valid_classifications = total_count - unknown_classifications
            self.stdout.write(f"  分类信息: {valid_classifications}/{total_count} ({valid_classifications/total_count*100:.1f}% 有效)")
            
            # 分析discovery_location字段
            unknown_locations = pending_meteorites.filter(discovery_location__in=['Unknown', '', None]).count()
            valid_locations = total_count - unknown_locations
            self.stdout.write(f"  发现地点: {valid_locations}/{total_count} ({valid_locations/total_count*100:.1f}% 有效)")
            
            # 分析origin字段
            unknown_origins = pending_meteorites.filter(origin__in=['Unknown', '', None]).count()
            valid_origins = total_count - unknown_origins
            self.stdout.write(f"  来源信息: {valid_origins}/{total_count} ({valid_origins/total_count*100:.1f}% 有效)")
            
            # 分析organic_compounds字段
            empty_compounds = 0
            valid_compounds = 0
            for meteorite in pending_meteorites:
                compounds = meteorite.organic_compounds
                if not compounds or compounds == [] or compounds == {}:
                    empty_compounds += 1
                else:
                    valid_compounds += 1
            
            self.stdout.write(f"  有机化合物: {valid_compounds}/{total_count} ({valid_compounds/total_count*100:.1f}% 有效)")
            
            # 分析references字段
            empty_references = 0
            valid_references = 0
            for meteorite in pending_meteorites:
                refs = meteorite.references
                if not refs or refs == [] or refs == {}:
                    empty_references += 1
                else:
                    valid_references += 1
            
            self.stdout.write(f"  参考文献: {valid_references}/{total_count} ({valid_references/total_count*100:.1f}% 有效)")
            
            # 分析置信度分数
            avg_confidence = sum(m.confidence_score for m in pending_meteorites) / total_count
            high_confidence = pending_meteorites.filter(confidence_score__gte=0.8).count()
            medium_confidence = pending_meteorites.filter(confidence_score__gte=0.6, confidence_score__lt=0.8).count()
            low_confidence = pending_meteorites.filter(confidence_score__lt=0.6).count()
            
            self.stdout.write(f"\n📈 置信度分析:")
            self.stdout.write(f"  平均置信度: {avg_confidence:.3f}")
            self.stdout.write(f"  高置信度 (≥0.8): {high_confidence} ({high_confidence/total_count*100:.1f}%)")
            self.stdout.write(f"  中置信度 (0.6-0.8): {medium_confidence} ({medium_confidence/total_count*100:.1f}%)")
            self.stdout.write(f"  低置信度 (<0.6): {low_confidence} ({low_confidence/total_count*100:.1f}%)")
            
            # 显示前10条数据的详细信息
            self.stdout.write(f"\n📋 前10条数据详情:")
            for i, meteorite in enumerate(pending_meteorites[:10], 1):
                self.stdout.write(f"\n  {i}. ID: {meteorite.id}")
                self.stdout.write(f"     名称: {meteorite.name}")
                self.stdout.write(f"     分类: {meteorite.classification}")
                self.stdout.write(f"     地点: {meteorite.discovery_location}")
                self.stdout.write(f"     来源: {meteorite.origin}")
                self.stdout.write(f"     置信度: {meteorite.confidence_score:.3f}")
                self.stdout.write(f"     有机化合物: {meteorite.organic_compounds}")
                self.stdout.write(f"     参考文献: {meteorite.references}")
            
            # 质量评估
            self.stdout.write(f"\n🎯 数据质量评估:")
            
            # 计算整体质量分数
            quality_score = (
                valid_names/total_count * 0.2 +
                valid_classifications/total_count * 0.2 +
                valid_locations/total_count * 0.15 +
                valid_origins/total_count * 0.15 +
                valid_compounds/total_count * 0.15 +
                valid_references/total_count * 0.15
            ) * 100
            
            self.stdout.write(f"  整体质量分数: {quality_score:.1f}/100")
            
            if quality_score >= 80:
                self.stdout.write(self.style.SUCCESS("  ✅ 数据质量: 优秀"))
            elif quality_score >= 60:
                self.stdout.write(self.style.WARNING("  ⚠️  数据质量: 良好"))
            elif quality_score >= 40:
                self.stdout.write(self.style.WARNING("  ⚠️  数据质量: 一般"))
            else:
                self.stdout.write(self.style.ERROR("  ❌ 数据质量: 较差"))
            
            # 建议
            self.stdout.write(f"\n💡 改进建议:")
            if unknown_names > total_count * 0.3:
                self.stdout.write("  - 陨石名称提取率较低，需要改进prompt模板")
            if unknown_classifications > total_count * 0.3:
                self.stdout.write("  - 分类信息提取率较低，需要改进分类识别逻辑")
            if empty_compounds > total_count * 0.5:
                self.stdout.write("  - 有机化合物信息缺失较多，需要改进化合物提取逻辑")
            if avg_confidence < 0.7:
                self.stdout.write("  - 整体置信度较低，需要改进LLM提示词和验证逻辑")
            
            self.stdout.write(self.style.SUCCESS("\n✅ 分析完成"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 分析失败: {e}"))
            import traceback
            traceback.print_exc()
