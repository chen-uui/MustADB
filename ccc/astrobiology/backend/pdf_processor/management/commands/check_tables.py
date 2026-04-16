from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = '检查数据库表'

    def handle(self, *args, **options):
        self.stdout.write("🔍 检查数据库表")
        
        try:
            cursor = connection.cursor()
            
            # 检查所有表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            
            tables = cursor.fetchall()
            self.stdout.write("📋 所有表:")
            for table in tables:
                self.stdout.write(f"  {table[0]}")
            
            # 检查陨石相关表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%meteorite%'
                ORDER BY table_name;
            """)
            
            meteorite_tables = cursor.fetchall()
            self.stdout.write("\n📋 陨石相关表:")
            for table in meteorite_tables:
                self.stdout.write(f"  {table[0]}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 检查失败: {e}"))
            import traceback
            traceback.print_exc()
