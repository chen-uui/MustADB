from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = '手动创建meteorite_review_logs_new表'

    def handle(self, *args, **options):
        self.stdout.write("🔧 手动创建meteorite_review_logs_new表")
        
        try:
            cursor = connection.cursor()
            
            # 检查表是否存在
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'meteorite_review_logs_new'
                );
            """)
            
            exists = cursor.fetchone()[0]
            self.stdout.write(f"🔍 表存在状态: {exists}")
            
            if not exists:
                self.stdout.write("🔧 创建表...")
                
                # 创建表
                cursor.execute("""
                    CREATE TABLE meteorite_review_logs_new (
                        id SERIAL PRIMARY KEY,
                        pending_meteorite_id INTEGER,
                        approved_meteorite_id INTEGER,
                        rejected_meteorite_id INTEGER,
                        reviewer_id INTEGER NOT NULL,
                        action VARCHAR(30) NOT NULL,
                        previous_status VARCHAR(30) NOT NULL,
                        new_status VARCHAR(30) NOT NULL,
                        notes TEXT,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        review_details JSONB DEFAULT '{}'::jsonb,
                        CONSTRAINT fk_pending_meteorite FOREIGN KEY (pending_meteorite_id) REFERENCES pending_meteorites(id) ON DELETE CASCADE,
                        CONSTRAINT fk_approved_meteorite FOREIGN KEY (approved_meteorite_id) REFERENCES approved_meteorites(id) ON DELETE CASCADE,
                        CONSTRAINT fk_rejected_meteorite FOREIGN KEY (rejected_meteorite_id) REFERENCES rejected_meteorites(id) ON DELETE CASCADE,
                        CONSTRAINT fk_reviewer FOREIGN KEY (reviewer_id) REFERENCES auth_user(id) ON DELETE CASCADE
                    );
                """)
                
                # 创建索引
                cursor.execute("""
                    CREATE INDEX idx_meteorite_review_logs_new_pending_timestamp 
                    ON meteorite_review_logs_new (pending_meteorite_id, timestamp);
                """)
                
                cursor.execute("""
                    CREATE INDEX idx_meteorite_review_logs_new_approved_timestamp 
                    ON meteorite_review_logs_new (approved_meteorite_id, timestamp);
                """)
                
                cursor.execute("""
                    CREATE INDEX idx_meteorite_review_logs_new_rejected_timestamp 
                    ON meteorite_review_logs_new (rejected_meteorite_id, timestamp);
                """)
                
                cursor.execute("""
                    CREATE INDEX idx_meteorite_review_logs_new_reviewer_timestamp 
                    ON meteorite_review_logs_new (reviewer_id, timestamp);
                """)
                
                cursor.execute("""
                    CREATE INDEX idx_meteorite_review_logs_new_action 
                    ON meteorite_review_logs_new (action);
                """)
                
                self.stdout.write(self.style.SUCCESS("✅ 表创建成功"))
            else:
                self.stdout.write("✅ 表已存在")
            
            # 最终检查
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'meteorite_review_logs_new'
                );
            """)
            
            exists_final = cursor.fetchone()[0]
            self.stdout.write(f"🔍 最终检查 - 表存在: {exists_final}")
            
            if exists_final:
                self.stdout.write(self.style.SUCCESS("🎉 meteorite_review_logs_new表创建成功！"))
            else:
                self.stdout.write(self.style.ERROR("❌ 表创建失败"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 创建表失败: {e}"))
            import traceback
            traceback.print_exc()
