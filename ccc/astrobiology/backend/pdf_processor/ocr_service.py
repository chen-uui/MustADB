"""
OCR服务 - 用于处理扫描版PDF的文本识别

支持多种OCR引擎：
1. EasyOCR (推荐) - 准确度高，支持多语言，无需额外系统依赖
2. Tesseract OCR - 传统方案，需要安装Tesseract
3. PaddleOCR - 中文识别效果好

默认使用EasyOCR，可通过环境变量配置
"""

import os
import logging
import fitz  # PyMuPDF
from typing import Dict, List, Optional, Any
import io
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

# OCR引擎配置
OCR_ENGINE = os.getenv('OCR_ENGINE', 'easyocr').lower()  # easyocr, tesseract, paddleocr
OCR_ENABLED = os.getenv('OCR_ENABLED', 'true').lower() == 'true'
OCR_LANGUAGES = os.getenv('OCR_LANGUAGES', 'en').split(',')  # 支持多语言，如 'en,ch_sim'

# 懒加载OCR引擎
_ocr_engine = None
_ocr_engine_type = None


def get_ocr_engine():
    """
    获取OCR引擎实例（懒加载）
    
    Returns:
        OCR引擎实例
    """
    global _ocr_engine, _ocr_engine_type
    
    if not OCR_ENABLED:
        return None
    
    if _ocr_engine is None:
        try:
            if OCR_ENGINE == 'easyocr':
                import easyocr
                logger.info("初始化EasyOCR引擎...")
                _ocr_engine = easyocr.Reader(OCR_LANGUAGES, gpu=False)  # GPU可选
                _ocr_engine_type = 'easyocr'
                logger.info("EasyOCR引擎初始化完成")
            elif OCR_ENGINE == 'tesseract':
                import pytesseract
                # 检查Tesseract是否安装
                try:
                    pytesseract.get_tesseract_version()
                    _ocr_engine = pytesseract
                    _ocr_engine_type = 'tesseract'
                    logger.info("Tesseract OCR引擎初始化完成")
                except Exception as e:
                    logger.error(f"Tesseract未安装或不可用: {e}")
                    return None
            elif OCR_ENGINE == 'paddleocr':
                from paddleocr import PaddleOCR
                logger.info("初始化PaddleOCR引擎...")
                _ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')  # 中文用 'ch'
                _ocr_engine_type = 'paddleocr'
                logger.info("PaddleOCR引擎初始化完成")
            else:
                logger.error(f"不支持的OCR引擎: {OCR_ENGINE}")
                return None
        except ImportError as e:
            logger.warning(f"OCR引擎 {OCR_ENGINE} 未安装: {e}")
            logger.warning("安装命令: pip install easyocr 或 pip install pytesseract pillow")
            return None
        except Exception as e:
            logger.error(f"初始化OCR引擎失败: {e}")
            return None
    
    return _ocr_engine, _ocr_engine_type


def is_scanned_pdf(pdf_path: str, sample_pages: int = 3) -> Dict[str, Any]:
    """
    检测PDF是否为扫描版（无文本层）
    
    Args:
        pdf_path: PDF文件路径
        sample_pages: 采样页面数（检查前N页）
        
    Returns:
        检测结果字典，包含：
        - is_scanned: 是否为扫描版
        - confidence: 置信度 (0-1)
        - text_ratio: 文本页面比例
        - sample_pages: 采样页面数
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        sample_pages = min(sample_pages, total_pages)
        
        text_pages = 0
        total_chars = 0
        
        for page_num in range(sample_pages):
            try:
                page = doc[page_num]
                page_text = page.get_text()
                char_count = len(page_text.strip())
                
                # 如果页面有超过50个字符，认为有文本
                if char_count > 50:
                    text_pages += 1
                    total_chars += char_count
            except Exception as e:
                logger.debug(f"检查第 {page_num + 1} 页时出错: {e}")
        
        doc.close()
        
        text_ratio = text_pages / sample_pages if sample_pages > 0 else 0
        avg_chars_per_page = total_chars / sample_pages if sample_pages > 0 else 0
        
        # 判断逻辑：
        # 1. 如果文本页面比例 < 20%，很可能是扫描版
        # 2. 如果平均字符数 < 100，可能是扫描版
        is_scanned = text_ratio < 0.2 or avg_chars_per_page < 100
        
        # 计算置信度
        if text_ratio == 0:
            confidence = 0.95  # 完全没有文本，高置信度是扫描版
        elif text_ratio < 0.1:
            confidence = 0.85
        elif text_ratio < 0.2:
            confidence = 0.70
        elif avg_chars_per_page < 100:
            confidence = 0.60
        else:
            confidence = 0.30  # 可能是混合PDF
        
        return {
            'is_scanned': is_scanned,
            'confidence': confidence,
            'text_ratio': text_ratio,
            'text_pages': text_pages,
            'sample_pages': sample_pages,
            'avg_chars_per_page': avg_chars_per_page,
            'total_pages': total_pages
        }
        
    except Exception as e:
        logger.error(f"检测扫描版PDF失败: {str(e)}")
        return {
            'is_scanned': False,
            'confidence': 0.0,
            'error': str(e)
        }


def extract_text_with_ocr(pdf_path: str, 
                          pages: Optional[List[int]] = None,
                          dpi: int = 300) -> Dict[str, Any]:
    """
    使用OCR从PDF中提取文本
    
    Args:
        pdf_path: PDF文件路径
        pages: 要处理的页面列表（None表示所有页面）
        dpi: 图片分辨率（DPI），越高越准确但越慢，推荐300-400
        
    Returns:
        提取结果字典，包含：
        - text: 提取的文本
        - pages: 每页的文本
        - success: 是否成功
        - engine: 使用的OCR引擎
        - processing_time: 处理时间（秒）
    """
    import time
    start_time = time.time()
    
    # 检查OCR是否可用
    ocr_result = get_ocr_engine()
    if ocr_result is None:
        return {
            'text': '',
            'pages': [],
            'success': False,
            'error': 'OCR引擎不可用，请安装OCR库',
            'error_code': 'OCR_NOT_AVAILABLE'
        }
    
    ocr_engine, engine_type = ocr_result
    
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        if pages is None:
            pages_to_process = list(range(total_pages))
        else:
            pages_to_process = [p for p in pages if 0 <= p < total_pages]
        
        all_text = ""
        page_texts = []
        
        logger.info(f"开始OCR处理: {len(pages_to_process)} 页, 引擎: {engine_type}")
        
        for page_num in pages_to_process:
            try:
                page = doc[page_num]
                
                # 将PDF页面渲染为图像
                # 提高DPI以获得更好的OCR质量
                mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72是PDF默认DPI
                pix = page.get_pixmap(matrix=mat)
                
                # 转换为PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # 转换为RGB格式（如果不是）
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 转换为numpy array
                img_array = np.array(img)
                
                # 使用OCR引擎识别
                if engine_type == 'easyocr':
                    results = ocr_engine.readtext(img_array)
                    page_text = '\n'.join([result[1] for result in results])
                elif engine_type == 'tesseract':
                    page_text = ocr_engine.image_to_string(img, lang='+'.join(OCR_LANGUAGES))
                elif engine_type == 'paddleocr':
                    results = ocr_engine.ocr(img_array, cls=True)
                    if results and results[0]:
                        page_text = '\n'.join([
                            line[1][0] for line in results[0] if line
                        ])
                    else:
                        page_text = ""
                else:
                    page_text = ""
                
                # 清理文本
                if page_text:
                    from pdf_processor.pdf_utils import PDFUtils
                    page_text = PDFUtils.clean_text(page_text, preserve_structure=True)
                
                page_texts.append({
                    'page_num': page_num + 1,
                    'text': page_text,
                    'text_length': len(page_text)
                })
                all_text += page_text + "\n"
                
                logger.debug(f"OCR处理第 {page_num + 1} 页完成: {len(page_text)} 字符")
                
            except Exception as e:
                logger.warning(f"OCR处理第 {page_num + 1} 页失败: {str(e)}")
                page_texts.append({
                    'page_num': page_num + 1,
                    'text': '',
                    'text_length': 0,
                    'error': str(e)
                })
        
        doc.close()
        
        processing_time = time.time() - start_time
        
        logger.info(f"OCR处理完成: 共 {len(pages_to_process)} 页, "
                   f"提取 {len(all_text)} 字符, 耗时 {processing_time:.2f} 秒")
        
        return {
            'text': all_text.strip(),
            'pages': page_texts,
            'success': True,
            'engine': engine_type,
            'processing_time': processing_time,
            'total_pages_processed': len(pages_to_process),
            'total_chars': len(all_text)
        }
        
    except Exception as e:
        logger.error(f"OCR提取失败: {str(e)}", exc_info=True)
        return {
            'text': '',
            'pages': [],
            'success': False,
            'error': str(e),
            'error_code': 'OCR_EXTRACTION_FAILED'
        }


def extract_pdf_text_with_fallback(pdf_path: str, 
                                   use_ocr_on_failure: bool = True,
                                   auto_detect_scanned: bool = True) -> Dict[str, Any]:
    """
    提取PDF文本，如果失败或检测为扫描版则自动使用OCR
    
    Args:
        pdf_path: PDF文件路径
        use_ocr_on_failure: 如果文本提取失败，是否使用OCR
        auto_detect_scanned: 是否自动检测扫描版PDF
        
    Returns:
        提取结果字典
    """
    from pdf_processor.pdf_utils import PDFUtils
    
    # 首先尝试标准文本提取
    result = PDFUtils.extract_text_and_metadata(pdf_path, detailed_errors=True)
    
    # 检查是否需要OCR
    needs_ocr = False
    ocr_reason = None
    
    if not result['success']:
        if result.get('error_code') == 'NO_TEXT_EXTRACTED':
            needs_ocr = True
            ocr_reason = "无文本提取"
    elif result.get('stats', {}).get('total_text_length', 0) < 100:
        # 文本很少，可能是扫描版
        if auto_detect_scanned:
            scan_check = is_scanned_pdf(pdf_path)
            if scan_check.get('is_scanned', False):
                needs_ocr = True
                ocr_reason = f"检测为扫描版PDF (置信度: {scan_check['confidence']:.2%})"
    
    # 如果需要且允许，使用OCR
    if needs_ocr and use_ocr_on_failure and OCR_ENABLED:
        logger.info(f"检测到需要OCR处理: {ocr_reason}")
        
        ocr_result = extract_text_with_ocr(pdf_path)
        
        if ocr_result['success']:
            # 合并OCR结果和原有元数据
            return {
                **result,
                'text': ocr_result['text'],
                'pages': ocr_result['pages'],
                'success': True,
                'extraction_method': 'ocr',
                'ocr_engine': ocr_result['engine'],
                'ocr_processing_time': ocr_result['processing_time'],
                'ocr_reason': ocr_reason,
                'original_result': result
            }
        else:
            # OCR也失败了
            return {
                **result,
                'ocr_attempted': True,
                'ocr_failed': True,
                'ocr_error': ocr_result.get('error'),
                'suggestion': 'OCR处理也失败，PDF可能质量较差或需要人工处理'
            }
    
    # 标准提取成功，返回结果
    if result['success']:
        result['extraction_method'] = 'standard'
    
    return result

