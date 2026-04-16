from django.core.management.base import BaseCommand
from meteorite_search.models import Meteorite
import random

class Command(BaseCommand):
    help = 'Initialize meteorite data for testing'

    def handle(self, *args, **options):
        # 定义测试数据
        classifications = ['Chondrite', 'Achondrite', 'Iron', 'Stony-Iron', 'Martian', 'Lunar', 'Carbonaceous', 'Ordinary']
        analysis_methods = ['XRF', 'SEM', 'ICP-MS', 'Raman', 'FTIR', 'XRD', 'EPMA', 'SIMS']
        material_types = ['Silicate', 'Metal', 'Sulfide', 'Oxide', 'Carbonate', 'Phosphate', 'Organic', 'Ice']
        
        meteorite_names = [
            'Allende', 'Murchison', 'Orgueil', 'Sikhote-Alin', 'Gibeon', 'Campo del Cielo',
            'NWA 869', 'NWA 13188', 'Chelyabinsk', 'Tissint', 'Shergotty', 'Nakhla',
            'ALH 84001', 'Zagami', 'EETA 79001', 'QUE 94201', 'DaG 476', 'Los Angeles',
            'Sayh al Uhaymir', 'Dar al Gani', 'Jiddat al Harasis', 'Dhofar', 'SaU 005',
            'Yamato 000593', 'Yamato 000749', 'Yamato 000802', 'MIL 03346', 'LAR 06319'
        ]
        
        # 创建测试数据
        created_count = 0
        for name in meteorite_names:
            meteorite = Meteorite.objects.create(
                name=name,
                classification=random.choice(classifications),
                analysis_method=random.choice(analysis_methods),
                material_type=random.choice(material_types),
                description=f"{name} is a {random.choice(classifications).lower()} meteorite discovered on Earth.",
                mass=round(random.uniform(0.1, 1000.0), 2),
                age=round(random.uniform(0.5, 4.6), 2),
                origin=f"{random.choice(['Mars', 'Moon', 'Asteroid Belt', 'Comet', 'Kuiper Belt'])}",
                source=f"{random.choice(['NASA', 'JPL', 'Smithsonian', 'Natural History Museum', 'Private Collection'])}",
                created_by='system',
                updated_by='system'
            )
            created_count += 1
            
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} meteorite records')
        )