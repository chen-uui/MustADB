"""
性能测试脚本
用于测试系统在大数据量下的表现
"""

import time
import random
import string
from django.core.management.base import BaseCommand
from meteorite_search.models import Meteorite
from meteorite_search.query_optimizer import MeteoriteQueryOptimizer

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.test_data_count = 10000
        
    def generate_test_data(self):
        """生成测试数据"""
        print("🧪 生成测试数据...")
        
        classifications = ['CV3', 'CM2', 'CI1', 'C2-ungrouped', 'CR2', 'CH3', 'CB3']
        origins = ['小行星带', '彗星', '火星', '月球', '外太阳系']
        locations = ['南极', '非洲', '澳大利亚', '加拿大', '美国', '中国', '俄罗斯']
        
        # 有机化合物模板
        organic_compounds_template = [
            {"name": "氨基酸", "formula": "C2H5NO2", "abundance": 0.1},
            {"name": "核苷酸", "formula": "C10H13N5O4", "abundance": 0.05},
            {"name": "脂肪酸", "formula": "C16H32O2", "abundance": 0.2},
            {"name": "糖", "formula": "C6H12O6", "abundance": 0.15},
        ]
        
        batch_size = 1000
        for i in range(0, self.test_data_count, batch_size):
            batch = []
            for j in range(batch_size):
                if i + j >= self.test_data_count:
                    break
                    
                meteorite = Meteorite(
                    name=f"测试陨石_{i+j}",
                    classification=random.choice(classifications),
                    discovery_location=f"{random.choice(locations)} 地区",
                    origin=random.choice(origins),
                    organic_compounds=[
                        {
                            **random.choice(organic_compounds_template),
                            "concentration": random.uniform(0.001, 1.0)
                        }
                        for _ in range(random.randint(1, 5))
                    ],
                    contamination_exclusion_method="标准清洁协议",
                    references=[
                        {
                            "url": f"https://doi.org/10.1003/test_{i+j}",
                            "title": f"测试文献 {i+j}"
                        }
                    ]
                )
                batch.append(meteorite)
            
            Meteorite.objects.bulk_create(batch)
            print(f"✅ 已创建 {min(i+batch_size, self.test_data_count)} 条记录")
    
    def run_search_performance_test(self):
        """运行搜索性能测试"""
        print("\n🔍 运行搜索性能测试...")
        
        test_cases = [
            {"name": "Allende"},
            {"classification": "CV3"},
            {"origin": "小行星带"},
            {"organic_compound": "氨基酸"},
            {"name": "测试", "classification": "CV3"}
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            
            result = MeteoriteQueryOptimizer.search_with_optimization(
                test_case, page=1, page_size=20
            )
            
            elapsed_time = time.time() - start_time
            
            print(f"搜索 {test_case}: {result['total_count']} 结果, "
                  f"耗时 {elapsed_time:.3f}s, "
                  f"查询: {result['query'][:100]}...")
    
    def run_database_stats(self):
        """运行数据库统计"""
        print("\n📊 数据库统计信息:")
        stats = MeteoriteQueryOptimizer.get_statistics()
        
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    def cleanup_test_data(self):
        """清理测试数据"""
        print("\n🧹 清理测试数据...")
        deleted_count = Meteorite.objects.filter(name__startswith="测试陨石_").delete()[0]
        print(f"已删除 {deleted_count} 条测试记录")

class Command(BaseCommand):
    help = '运行性能测试'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--generate',
            action='store_true',
            help='生成测试数据'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='运行性能测试'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='显示统计信息'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='清理测试数据'
        )
    
    def handle(self, *args, **options):
        tester = PerformanceTester()
        
        if options['generate']:
            tester.generate_test_data()
        
        if options['test']:
            tester.run_search_performance_test()
        
        if options['stats']:
            tester.run_database_stats()
        
        if options['cleanup']:
            tester.cleanup_test_data()
        
        if not any([options['generate'], options['test'], options['stats'], options['cleanup']]):
            print("请指定操作: --generate, --test, --stats, --cleanup")