"""
检测文档库中的扫描版PDF

使用方法:
    python manage.py detect_scanned_pdfs [options]

选项:
    --min-confidence: 最小置信度阈值 (默认 0.7)
    --limit: 限制处理的PDF数量
    --update-db: 更新数据库标记扫描版PDF
    --export: 导出结果到CSV文件
"""

import os
import sys
import django
from django.core.management.base import BaseCommand
from django.db import transaction
from pathlib import Path
import csv

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

from pdf_processor.ocr_service import is_scanned_pdf
from pdf_processor.models import PDFDocument
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '检测文档库中的扫描版PDF'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.7,
            help='最小置信度阈值 (0-1)，默认 0.7'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='限制处理的PDF数量'
        )
        parser.add_argument(
            '--update-db',
            action='store_true',
            help='更新数据库标记扫描版PDF'
        )
        parser.add_argument(
            '--export',
            type=str,
            default=None,
            help='导出结果到CSV文件'
        )
        parser.add_argument(
            '--pdf-dir',
            type=str,
            default=None,
            help='指定PDF目录（覆盖默认路径）'
        )

    def handle(self, *args, **options):
        min_confidence = options['min_confidence']
        limit = options['limit']
        update_db = options['update_db']
        export_path = options['export']
        pdf_dir = options['pdf_dir']
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('开始检测扫描版PDF'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        # 获取PDF文件列表
        if pdf_dir:
            pdf_dir = Path(pdf_dir)
        else:
            # 默认路径
            base_dir = Path(__file__).parent.parent.parent.parent.parent
            pdf_dir = base_dir / 'data' / 'pdfs'
        
        if not pdf_dir.exists():
            self.stdout.write(self.style.ERROR(f'PDF目录不存在: {pdf_dir}'))
            return
        
        # 获取所有PDF文件
        pdf_files = list(pdf_dir.glob('*.pdf'))
        
        if limit:
            pdf_files = pdf_files[:limit]
        
        self.stdout.write(f'\n找到 {len(pdf_files)} 个PDF文件')
        self.stdout.write(f'置信度阈值: {min_confidence}\n')
        
        scanned_pdfs = []
        normal_pdfs = []
        error_pdfs = []
        
        # 处理每个PDF
        for i, pdf_file in enumerate(pdf_files, 1):
            self.stdout.write(f'\n[{i}/{len(pdf_files)}] 处理: {pdf_file.name}')
            
            try:
                result = is_scanned_pdf(str(pdf_file))
                
                if result.get('error'):
                    self.stdout.write(self.style.ERROR(f'  错误: {result["error"]}'))
                    error_pdfs.append({
                        'file': str(pdf_file),
                        'name': pdf_file.name,
                        'error': result['error']
                    })
                    continue
                
                is_scanned = result['is_scanned']
                confidence = result['confidence']
                text_ratio = result['text_ratio']
                
                status = "扫描版" if is_scanned else "正常"
                style = self.style.WARNING if is_scanned else self.style.SUCCESS
                
                self.stdout.write(style(
                    f'  结果: {status} (置信度: {confidence:.2%}, '
                    f'文本比例: {text_ratio:.2%}, '
                    f'平均字符/页: {result.get("avg_chars_per_page", 0):.0f})'
                ))
                
                if is_scanned and confidence >= min_confidence:
                    scanned_pdfs.append({
                        'file': str(pdf_file),
                        'name': pdf_file.name,
                        'confidence': confidence,
                        'text_ratio': text_ratio,
                        'text_pages': result.get('text_pages', 0),
                        'sample_pages': result.get('sample_pages', 0),
                        'total_pages': result.get('total_pages', 0),
                        'avg_chars_per_page': result.get('avg_chars_per_page', 0)
                    })
                else:
                    normal_pdfs.append({
                        'file': str(pdf_file),
                        'name': pdf_file.name,
                        'confidence': confidence,
                        'text_ratio': text_ratio
                    })
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  处理失败: {str(e)}'))
                error_pdfs.append({
                    'file': str(pdf_file),
                    'name': pdf_file.name,
                    'error': str(e)
                })
        
        # 输出统计
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('检测结果统计'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(f'总计: {len(pdf_files)}')
        self.stdout.write(self.style.WARNING(f'扫描版PDF: {len(scanned_pdfs)} ({len(scanned_pdfs)/len(pdf_files)*100:.1f}%)'))
        self.stdout.write(self.style.SUCCESS(f'正常PDF: {len(normal_pdfs)} ({len(normal_pdfs)/len(pdf_files)*100:.1f}%)'))
        if error_pdfs:
            self.stdout.write(self.style.ERROR(f'错误: {len(error_pdfs)}'))
        
        # 导出结果
        if export_path:
            self.export_to_csv(export_path, scanned_pdfs, normal_pdfs, error_pdfs)
            self.stdout.write(self.style.SUCCESS(f'\n结果已导出到: {export_path}'))
        
        # 更新数据库
        if update_db and scanned_pdfs:
            self.stdout.write(f'\n更新数据库标记 {len(scanned_pdfs)} 个扫描版PDF...')
            self.update_database(scanned_pdfs)
        
        # 显示扫描版PDF列表
        if scanned_pdfs:
            self.stdout.write(self.style.WARNING('\n扫描版PDF列表:'))
            for pdf_info in scanned_pdfs[:20]:  # 只显示前20个
                self.stdout.write(f"  - {pdf_info['name']} (置信度: {pdf_info['confidence']:.2%})")
            if len(scanned_pdfs) > 20:
                self.stdout.write(f"  ... 还有 {len(scanned_pdfs) - 20} 个")
        
        self.stdout.write(self.style.SUCCESS('\n检测完成！'))
        
        # 建议
        if scanned_pdfs:
            self.stdout.write(self.style.WARNING(
                f'\n建议: 发现 {len(scanned_pdfs)} 个扫描版PDF，建议使用OCR处理。'
            ))
            self.stdout.write('  运行: python manage.py process_ocr --pdf-dir <目录>')

    def export_to_csv(self, export_path, scanned_pdfs, normal_pdfs, error_pdfs):
        """导出结果到CSV"""
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                '文件名', '路径', '类型', '置信度', '文本比例', 
                '文本页数', '采样页数', '总页数', '平均字符/页', '错误'
            ])
            
            for pdf_info in scanned_pdfs:
                writer.writerow([
                    pdf_info['name'],
                    pdf_info['file'],
                    '扫描版',
                    pdf_info['confidence'],
                    pdf_info['text_ratio'],
                    pdf_info.get('text_pages', ''),
                    pdf_info.get('sample_pages', ''),
                    pdf_info.get('total_pages', ''),
                    pdf_info.get('avg_chars_per_page', ''),
                    ''
                ])
            
            for pdf_info in normal_pdfs:
                writer.writerow([
                    pdf_info['name'],
                    pdf_info['file'],
                    '正常',
                    pdf_info['confidence'],
                    pdf_info['text_ratio'],
                    '', '', '', '', ''
                ])
            
            for pdf_info in error_pdfs:
                writer.writerow([
                    pdf_info['name'],
                    pdf_info['file'],
                    '错误',
                    '', '', '', '', '', '',
                    pdf_info.get('error', '')
                ])

    def update_database(self, scanned_pdfs):
        """更新数据库标记扫描版PDF"""
        updated_count = 0
        
        for pdf_info in scanned_pdfs:
            pdf_path = pdf_info['file']
            try:
                # 尝试根据路径查找PDFDocument
                pdf_doc = PDFDocument.objects.filter(file_path__endswith=pdf_info['name']).first()
                
                if pdf_doc:
                    # 在metadata中标记
                    import json
                    metadata = pdf_doc.metadata if isinstance(pdf_doc.metadata, dict) else {}
                    if isinstance(pdf_doc.metadata, str):
                        try:
                            metadata = json.loads(pdf_doc.metadata)
                        except:
                            metadata = {}
                    
                    metadata['is_scanned'] = True
                    metadata['scan_confidence'] = pdf_info['confidence']
                    pdf_doc.metadata = metadata
                    pdf_doc.save()
                    updated_count += 1
                    
            except Exception as e:
                logger.warning(f"更新PDF文档失败 {pdf_info['name']}: {e}")
        
        self.stdout.write(self.style.SUCCESS(f'已更新 {updated_count} 个PDF文档记录'))

