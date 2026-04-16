"""
工具函数 - 提供各种实用功能
"""

import logging
import os
import fitz  # PyMuPDF
from typing import Optional, Dict, Any
import hashlib
import json
from datetime import datetime

logger = logging.getLogger(__name__)


def extract_pdf_text(pdf_path: str) -> str:
    """
    提取PDF的完整文本
    
    注意：此函数使用统一的文本清理逻辑 (PDFUtils.clean_text)
    以确保与系统其他部分的一致性
    
    Args:
        pdf_path: PDF文件路径
        
    Returns:
        str: 提取的文本内容
        
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: PDF文件为空或无法读取
        Exception: 其他PDF处理错误
    """
    try:
        # 验证文件存在
        if not os.path.exists(pdf_path):
            error_msg = f"PDF文件不存在: {pdf_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # 检查文件大小
        file_size = os.path.getsize(pdf_path)
        if file_size == 0:
            error_msg = f"PDF文件为空: {pdf_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 尝试打开PDF文档
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            logger.debug(f"成功打开PDF: {pdf_path}, 总页数: {total_pages}, 文件大小: {file_size} bytes")
        except Exception as e:
            error_msg = f"无法打开PDF文件: {pdf_path}, 错误: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        
        full_text = ""
        failed_pages = []
        
        # 逐页提取文本
        for page_num in range(total_pages):
            try:
                page = doc.load_page(page_num)
                page_text = page.get_text()
                
                if page_text:
                    full_text += page_text + "\n"
            except Exception as e:
                failed_pages.append(page_num + 1)
                logger.warning(f"提取第 {page_num + 1} 页失败: {str(e)}")
                # 继续处理其他页面
        
        # 关闭文档
        doc.close()
        
        # 记录失败页面
        if failed_pages:
            logger.warning(f"共有 {len(failed_pages)} 页提取失败: {failed_pages}")
        
        # 检查是否提取到任何文本
        if not full_text.strip():
            error_msg = f"PDF文本提取为空，可能是扫描版PDF或加密PDF: {pdf_path}"
            logger.warning(error_msg)
            # 不抛出异常，返回空字符串，让调用者决定如何处理
        
        # 使用统一的文本清理函数（从 pdf_utils 导入）
        try:
            from pdf_processor.pdf_utils import PDFUtils
            cleaned_text = PDFUtils.clean_text(full_text, preserve_structure=True)
        except ImportError:
            # 如果无法导入，使用旧的清理方法作为后备
            logger.warning("无法导入 PDFUtils，使用基础文本清理")
            cleaned_text = clean_extracted_text(full_text)
        
        logger.info(f"成功提取PDF文本: {len(cleaned_text)} 字符 (原始: {len(full_text)} 字符), "
                   f"总页数: {total_pages}, 失败页数: {len(failed_pages)}")
        
        return cleaned_text
        
    except (FileNotFoundError, ValueError) as e:
        # 重新抛出已知的异常类型
        raise
    except MemoryError as e:
        error_msg = f"处理PDF时内存不足: {pdf_path}"
        logger.error(f"{error_msg}, 错误: {str(e)}")
        raise MemoryError(error_msg) from e
    except Exception as e:
        error_msg = f"提取PDF文本时发生未知错误: {pdf_path}"
        logger.error(f"{error_msg}, 错误类型: {type(e).__name__}, 详情: {str(e)}", exc_info=True)
        raise


def clean_extracted_text(text: str) -> str:
    """
    清理提取的文本（后备函数）
    
    注意：推荐使用 PDFUtils.clean_text() 以获得更好的清理效果
    此函数保留作为后备选项，以保持向后兼容性
    
    Args:
        text: 原始文本
        
    Returns:
        str: 清理后的文本
    """
    try:
        if not text:
            return ""
        
        # 移除多余的空白字符
        cleaned = " ".join(text.split())
        
        # 移除特殊字符
        cleaned = cleaned.replace('\x00', '')
        cleaned = cleaned.replace('\ufeff', '')
        
        # 标准化换行符
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除多余的换行符
        while '\n\n\n' in cleaned:
            cleaned = cleaned.replace('\n\n\n', '\n\n')
        
        return cleaned.strip()
        
    except Exception as e:
        logger.error(f"文本清理过程中出现错误: {str(e)}")
        # 即使出错，也要尝试基本的清理
        try:
            return text.replace('\x00', '').strip()
        except:
            return text


def validate_pdf_file(pdf_path: str) -> Dict[str, Any]:
    """
    验证PDF文件
    
    Args:
        pdf_path: PDF文件路径
        
    Returns:
        Dict[str, Any]: 验证结果
    """
    try:
        validation_result = {
            'valid': False,
            'file_exists': False,
            'file_size': 0,
            'page_count': 0,
            'has_text': False,
            'error_message': ''
        }
        
        # 检查文件是否存在
        if not os.path.exists(pdf_path):
            validation_result['error_message'] = 'File does not exist'
            return validation_result
        
        validation_result['file_exists'] = True
        
        # 检查文件大小
        file_size = os.path.getsize(pdf_path)
        validation_result['file_size'] = file_size
        
        if file_size == 0:
            validation_result['error_message'] = 'File is empty'
            return validation_result
        
        # 检查文件大小限制 (50MB)
        if file_size > 50 * 1024 * 1024:
            validation_result['error_message'] = 'File too large (max 50MB)'
            return validation_result
        
        # 尝试打开PDF
        try:
            doc = fitz.open(pdf_path)
            validation_result['page_count'] = len(doc)
            
            # 检查是否有文本内容
            has_text = False
            for page_num in range(min(3, len(doc))):  # 检查前3页
                page = doc.load_page(page_num)
                if page.get_text().strip():
                    has_text = True
                    break
            
            validation_result['has_text'] = has_text
            doc.close()
            
            if not has_text:
                validation_result['error_message'] = 'PDF contains no readable text'
                return validation_result
            
            validation_result['valid'] = True
            return validation_result
            
        except Exception as e:
            validation_result['error_message'] = f'Invalid PDF file: {str(e)}'
            return validation_result
            
    except Exception as e:
        logger.error(f"Error validating PDF file {pdf_path}: {str(e)}")
        return {
            'valid': False,
            'file_exists': False,
            'file_size': 0,
            'page_count': 0,
            'has_text': False,
            'error_message': f'Validation error: {str(e)}'
        }


def generate_file_hash(file_path: str) -> str:
    """
    生成文件哈希值
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 文件哈希值
    """
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
        
    except Exception as e:
        logger.error(f"Error generating file hash for {file_path}: {str(e)}")
        return ""


def save_processing_result(result: Dict[str, Any], output_path: str) -> bool:
    """
    保存处理结果到文件
    
    Args:
        result: 处理结果
        output_path: 输出文件路径
        
    Returns:
        bool: 保存是否成功
    """
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 保存结果
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Processing result saved to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving processing result to {output_path}: {str(e)}")
        return False


def load_processing_result(file_path: str) -> Optional[Dict[str, Any]]:
    """
    加载处理结果文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        Optional[Dict[str, Any]]: 加载的结果，失败返回None
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Processing result file not found: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        logger.info(f"Processing result loaded from: {file_path}")
        return result
        
    except Exception as e:
        logger.error(f"Error loading processing result from {file_path}: {str(e)}")
        return None


def format_processing_time(seconds: float) -> str:
    """
    格式化处理时间
    
    Args:
        seconds: 处理时间（秒）
        
    Returns:
        str: 格式化后的时间字符串
    """
    try:
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分钟"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}小时"
            
    except Exception as e:
        logger.error(f"Error formatting processing time: {str(e)}")
        return f"{seconds:.1f}秒"


def calculate_text_complexity(text: str) -> Dict[str, Any]:
    """
    计算文本复杂度
    
    Args:
        text: 文本内容
        
    Returns:
        Dict[str, Any]: 复杂度信息
    """
    try:
        complexity_info = {
            'character_count': len(text),
            'word_count': len(text.split()),
            'line_count': len(text.split('\n')),
            'paragraph_count': len([p for p in text.split('\n\n') if p.strip()]),
            'sentence_count': len([s for s in text.split('.') if s.strip()]),
            'complexity_score': 0.0
        }
        
        # 计算复杂度分数
        char_count = complexity_info['character_count']
        word_count = complexity_info['word_count']
        
        if char_count > 0 and word_count > 0:
            # 基于字符数和词数的简单复杂度计算
            avg_word_length = char_count / word_count
            complexity_score = min(avg_word_length / 10.0, 1.0)  # 归一化到0-1
            complexity_info['complexity_score'] = complexity_score
        
        return complexity_info
        
    except Exception as e:
        logger.error(f"Error calculating text complexity: {str(e)}")
        return {
            'character_count': len(text),
            'word_count': 0,
            'line_count': 0,
            'paragraph_count': 0,
            'sentence_count': 0,
            'complexity_score': 0.0
        }


def extract_metadata_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    从PDF提取元数据
    
    Args:
        pdf_path: PDF文件路径
        
    Returns:
        Dict[str, Any]: 元数据信息
    """
    try:
        metadata = {
            'title': '',
            'author': '',
            'subject': '',
            'creator': '',
            'producer': '',
            'creation_date': '',
            'modification_date': '',
            'page_count': 0,
            'file_size': 0
        }
        
        if not os.path.exists(pdf_path):
            return metadata
        
        # 获取文件大小
        metadata['file_size'] = os.path.getsize(pdf_path)
        
        # 提取PDF元数据
        doc = fitz.open(pdf_path)
        metadata['page_count'] = len(doc)
        
        # 获取PDF元数据
        pdf_metadata = doc.metadata
        if pdf_metadata:
            metadata.update({
                'title': pdf_metadata.get('title', ''),
                'author': pdf_metadata.get('author', ''),
                'subject': pdf_metadata.get('subject', ''),
                'creator': pdf_metadata.get('creator', ''),
                'producer': pdf_metadata.get('producer', ''),
                'creation_date': pdf_metadata.get('creationDate', ''),
                'modification_date': pdf_metadata.get('modDate', '')
            })
        
        doc.close()
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting metadata from PDF {pdf_path}: {str(e)}")
        return {
            'title': '',
            'author': '',
            'subject': '',
            'creator': '',
            'producer': '',
            'creation_date': '',
            'modification_date': '',
            'page_count': 0,
            'file_size': 0
        }


def create_processing_summary(result: Dict[str, Any]) -> str:
    """
    创建处理摘要
    
    Args:
        result: 处理结果
        
    Returns:
        str: 处理摘要
    """
    try:
        summary_parts = []
        
        # 基本信息
        if 'document_path' in result:
            summary_parts.append(f"文档: {os.path.basename(result['document_path'])}")
        
        if 'processing_time' in result:
            summary_parts.append(f"处理时间: {format_processing_time(result['processing_time'])}")
        
        if 'confidence_score' in result:
            summary_parts.append(f"置信度: {result['confidence_score']:.2f}")
        
        # 数据统计
        if 'results' in result and result['results']:
            results = result['results']
            if hasattr(results, 'data'):
                data = results.data
                
                # 陨石数据统计
                if hasattr(data, 'meteorite_data') and data.meteorite_data:
                    summary_parts.append(f"陨石数据: {len(data.meteorite_data)} 项")
                
                # 有机化合物统计
                if hasattr(data, 'organic_compounds') and data.organic_compounds:
                    summary_parts.append(f"有机化合物: {len(data.organic_compounds)} 项")
                
                # 参考文献统计
                if hasattr(data, 'references') and data.references:
                    summary_parts.append(f"参考文献: {len(data.references)} 条")
        
        return " | ".join(summary_parts)
        
    except Exception as e:
        logger.error(f"Error creating processing summary: {str(e)}")
        return "处理摘要生成失败"


def validate_llm_response(response: str) -> Dict[str, Any]:
    """
    验证LLM响应
    
    Args:
        response: LLM响应内容
        
    Returns:
        Dict[str, Any]: 验证结果
    """
    try:
        validation_result = {
            'valid': False,
            'is_json': False,
            'has_required_fields': False,
            'response_length': len(response),
            'error_message': ''
        }
        
        if not response or len(response.strip()) < 10:
            validation_result['error_message'] = 'Response too short'
            return validation_result
        
        # 检查是否为JSON格式
        try:
            import json
            json.loads(response.strip())
            validation_result['is_json'] = True
        except:
            # 尝试提取JSON块
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                try:
                    json.loads(json_match.group(1))
                    validation_result['is_json'] = True
                except:
                    pass
        
        # 检查是否包含必需字段
        required_fields = ['meteorite_data', 'organic_compounds', 'scientific_insights']
        has_required_fields = any(field in response for field in required_fields)
        validation_result['has_required_fields'] = has_required_fields
        
        # 综合验证结果
        validation_result['valid'] = validation_result['is_json'] and validation_result['has_required_fields']
        
        if not validation_result['valid']:
            if not validation_result['is_json']:
                validation_result['error_message'] = 'Response is not valid JSON'
            elif not validation_result['has_required_fields']:
                validation_result['error_message'] = 'Response missing required fields'
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating LLM response: {str(e)}")
        return {
            'valid': False,
            'is_json': False,
            'has_required_fields': False,
            'response_length': len(response),
            'error_message': f'Validation error: {str(e)}'
        }
