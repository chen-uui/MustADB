from django.core.management.base import BaseCommand
from meteorite_search.models import Meteorite
import json

class Command(BaseCommand):
    help = '将陨石数据更新为英文版本，保持一致性'

    def handle(self, *args, **options):
        # 定义英文数据映射
        english_data = {
            1: {
                'name': 'Allende',
                'classification': 'CV3',
                'discovery_location': 'Mexico',
                'origin': 'Asteroid Belt',
                'organic_compounds': [
                    {'name': 'Amino Acids', 'formula': 'C2H5NO2', 'concentration': 0.15},
                    {'name': 'Polycyclic Aromatic Hydrocarbons', 'formula': 'C10H8', 'concentration': 0.08},
                    {'name': 'Nucleobases', 'formula': 'C5H5N5', 'concentration': 0.03}
                ]
            },
            2: {
                'name': 'Murchison',
                'classification': 'CM2',
                'discovery_location': 'Australia',
                'origin': 'Comet',
                'organic_compounds': [
                    {'name': 'Amino Acids', 'formula': 'C2H5NO2', 'concentration': 0.17},
                    {'name': 'Carboxylic Acids', 'formula': 'CH2O2', 'concentration': 0.12},
                    {'name': 'Sugar Alcohols', 'formula': 'C2H6O2', 'concentration': 0.05}
                ]
            },
            3: {
                'name': 'Tissint',
                'classification': 'Shergottite',
                'discovery_location': 'Morocco',
                'origin': 'Mars',
                'organic_compounds': [
                    {'name': 'Organic Carbon', 'formula': 'C', 'concentration': 0.10},
                    {'name': 'Methane', 'formula': 'CH4', 'concentration': 0.02}
                ]
            },
            4: {
                'name': 'Zagami',
                'classification': 'Shergottite',
                'discovery_location': 'Nigeria',
                'origin': 'Mars',
                'organic_compounds': [
                    {'name': 'Organic Matter', 'formula': 'C2H4O', 'concentration': 0.08},
                    {'name': 'Sulfur Compounds', 'formula': 'CH4S', 'concentration': 0.03}
                ]
            },
            5: {
                'name': 'ALH 84001',
                'classification': 'Orthopyroxenite',
                'discovery_location': 'Antarctica',
                'origin': 'Mars',
                'organic_compounds': [
                    {'name': 'Polycyclic Aromatic Hydrocarbons', 'formula': 'C16H10', 'concentration': 0.06},
                    {'name': 'Carbonate Minerals', 'formula': 'CaCO3', 'concentration': 0.01}
                ]
            },
            6: {
                'name': 'NWA 869',
                'classification': 'L4-6',
                'discovery_location': 'Northwest Africa',
                'origin': 'Asteroid Belt',
                'organic_compounds': [
                    {'name': 'Aromatic Hydrocarbons', 'formula': 'C7H8', 'concentration': 0.09},
                    {'name': 'Aliphatic Compounds', 'formula': 'C3H8', 'concentration': 0.04}
                ]
            },
            7: {
                'name': 'Sikhote-Alin',
                'classification': 'Iron Meteorite',
                'discovery_location': 'Siberia',
                'origin': 'Asteroid Belt',
                'organic_compounds': [
                    {'name': 'Organic Compounds', 'formula': 'C2H6O', 'concentration': 0.07},
                    {'name': 'Graphite Inclusions', 'formula': 'C', 'concentration': 0.02}
                ]
            },
            8: {
                'name': 'Gibeon',
                'classification': 'Chondrite',
                'discovery_location': 'Namibia',
                'origin': 'Main Belt Asteroid',
                'organic_compounds': [
                    {'name': 'Organic Carbon', 'formula': 'C3H8O', 'concentration': 0.05},
                    {'name': 'Silicate Minerals', 'formula': 'SiO2', 'concentration': 0.03}
                ]
            },
            9: {
                'name': 'Campo del Cielo',
                'classification': 'Carbonaceous',
                'discovery_location': 'Argentina',
                'origin': 'Asteroid Belt',
                'organic_compounds': [
                    {'name': 'Organic Carbon', 'formula': 'CH2O2', 'concentration': 0.11}
                ]
            },
            10: {
                'name': 'NWA 13188',
                'classification': 'Achondrite',
                'discovery_location': 'Morocco',
                'origin': 'Main Belt Asteroid',
                'organic_compounds': [
                    {'name': 'Organic Compounds', 'formula': 'C6H4O2', 'concentration': 0.08},
                    {'name': 'Hydrocarbons', 'formula': 'C4H8', 'concentration': 0.05},
                    {'name': 'Oxygenated Species', 'formula': 'C4H11O', 'concentration': 0.03}
                ]
            }
        }

        updated_count = 0
        for meteorite_id, data in english_data.items():
            try:
                meteorite = Meteorite.objects.get(id=meteorite_id)
                meteorite.name = data['name']
                meteorite.classification = data['classification']
                meteorite.discovery_location = data['discovery_location']
                meteorite.origin = data['origin']
                meteorite.organic_compounds = data['organic_compounds']
                meteorite.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'已更新: {meteorite.name} ({meteorite.classification})')
                )
            except Meteorite.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'未找到ID为{meteorite_id}的陨石')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n成功更新了 {updated_count} 条陨石数据为英文版本')
        )