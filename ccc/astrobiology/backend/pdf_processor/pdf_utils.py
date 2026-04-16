"""
统一的PDF处理工具类
整合所有PDF相关操作，减少代码重复
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import fitz  # PyMuPDF
from pathlib import Path

# 统一环境配置
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

class GlobalConfig:
    """全局配置管理 - 优化版本"""
    
    # Weaviate配置
    WEAVIATE_URL = os.getenv('WEAVIATE_URL', f"http://{os.getenv('WEAVIATE_HOST', 'localhost')}:{os.getenv('WEAVIATE_PORT', '8080')}")
    
    # --- 优化后参数（2025-10）---
    # 分块大小：约700 token，适合英文论文段落级检索
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '700'))       # 以 token 为单位
    # 重叠：约10-12%（80 token），缓解句子截断
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '80'))  # 以 token 为单位

    # 检索相关性提升，减少杂片段，提高抽取可用率
    MIN_RELEVANCE_SCORE = 0.65
    # TOPK数量减为8，降低弱相关噪声
    MAX_SEARCH_RESULTS = 8
    # --- 其它参数保持不变 ---
    
    # 嵌入模型配置 - 升级到更高质量模型
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-mpnet-base-v2')  # 更高质量的嵌入模型
    EMBEDDING_DIMENSION = 768  # 更高维度嵌入
    
    # LLM配置 - 基于128K上下文优化
    LLM_CONTEXT_LENGTH = 128000  # 使用完整128K上下文
    MAX_ANSWER_LENGTH = 4000  # 允许更长回答，充分利用上下文
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

class PDFUtils:
    """统一的PDF处理工具类"""
    _tokenizer_type: Optional[str] = None  # 'tiktoken' or 'approx'
    _tokenizer = None
    _avg_chars_per_token: int = 4  # 英文平均字符数估计，用于无tiktoken时的近似

    @staticmethod
    def _snapshot_document_state(doc: fitz.Document) -> Tuple[Dict[str, Any], int]:
        """在文档关闭前一次性缓存会跨阶段使用的状态。"""
        metadata = dict(doc.metadata or {})
        total_pages = int(doc.page_count)
        return metadata, total_pages

    @staticmethod
    def _get_tokenizer() -> Tuple[str, Optional[Any]]:
        """获取tokenizer；优先使用tiktoken，缺失时退化到近似计算。"""
        if PDFUtils._tokenizer_type is not None:
            return PDFUtils._tokenizer_type, PDFUtils._tokenizer
        try:
            import tiktoken  # type: ignore
            encoding_name = os.getenv('TIKTOKEN_ENCODING', 'cl100k_base')
            PDFUtils._tokenizer = tiktoken.get_encoding(encoding_name)
            PDFUtils._tokenizer_type = 'tiktoken'
            logging.info(f"使用tiktoken编码: {encoding_name}")
        except Exception:
            PDFUtils._tokenizer = None
            PDFUtils._tokenizer_type = 'approx'
            logging.warning("未找到tiktoken，分块将使用字符近似估算token长度（默认4字符/ token）")
        return PDFUtils._tokenizer_type, PDFUtils._tokenizer

    @staticmethod
    def count_tokens(text: str) -> int:
        """计算token数，缺少tiktoken时退化为字符/4的估算。"""
        tokenizer_type, tokenizer = PDFUtils._get_tokenizer()
        if tokenizer_type == 'tiktoken' and tokenizer:
            try:
                return len(tokenizer.encode(text))
            except Exception:
                pass
        return max(1, (len(text) + PDFUtils._avg_chars_per_token - 1) // PDFUtils._avg_chars_per_token)

    @staticmethod
    def _chunk_tokens_with_tiktoken(text: str, chunk_size: int, overlap: int) -> List[Dict[str, Any]]:
        """使用tiktoken按token分块。"""
        tokenizer_type, tokenizer = PDFUtils._get_tokenizer()
        if tokenizer_type != 'tiktoken' or tokenizer is None:
            return []

        tokens = tokenizer.encode(text)
        chunks: List[Dict[str, Any]] = []
        token_start = 0
        search_pos = 0  # 用于定位原文中的char起点

        while token_start < len(tokens):
            token_end = min(token_start + chunk_size, len(tokens))
            chunk_tokens = tokens[token_start:token_end]
            chunk_text = tokenizer.decode(chunk_tokens).strip()
            if chunk_text:
                # 尝试在原文中定位chunk以给出字符边界；找不到时返回-1
                found_at = text.find(chunk_text, search_pos)
                if found_at != -1:
                    start_char = found_at
                    end_char = found_at + len(chunk_text)
                    search_pos = end_char  # 下一次搜索从当前块末尾起
                else:
                    start_char = -1
                    end_char = -1

                chunks.append({
                    'chunk_text': chunk_text,
                    'chunk_index': len(chunks),
                    'page_number': None,  # 稍后填充
                    'start_char': start_char,
                    'end_char': end_char,
                    'chunk_length': len(chunk_tokens),  # token数
                    'start_token': token_start,
                    'end_token': token_end
                })
            if token_end == len(tokens):
                break
            token_start = max(token_end - overlap, token_start + 1)

        return chunks

    @staticmethod
    def _chunk_text_approx(text: str, chunk_size_tokens: int, overlap_tokens: int) -> List[Dict[str, Any]]:
        """
        当无tiktoken可用时，退化为字符近似分块：
        使用约4字符/ token 估算窗口和重叠，chunk_length返回估算token数。
        """
        approx_size = chunk_size_tokens * PDFUtils._avg_chars_per_token
        approx_overlap = overlap_tokens * PDFUtils._avg_chars_per_token
        chunks: List[Dict[str, Any]] = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + approx_size, text_length)
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    'chunk_text': chunk_text,
                    'chunk_index': len(chunks),
                    'page_number': None,  # 稍后填充
                    'start_char': start,
                    'end_char': end,
                    'chunk_length': max(1, (len(chunk_text) + PDFUtils._avg_chars_per_token - 1) // PDFUtils._avg_chars_per_token),
                    'start_token': max(0, start // PDFUtils._avg_chars_per_token),
                    'end_token': max(0, end // PDFUtils._avg_chars_per_token),
                })
            if end == text_length:
                break
            start = max(end - approx_overlap, start + 1)

        return chunks
    
    @staticmethod
    def clean_text(text: str, preserve_structure: bool = True) -> str:
        """
        统一清理和标准化PDF提取的文本
        
        这是系统中唯一的文本清理函数，所有文本清理都应使用此函数
        以确保一致性和质量
        
        Args:
            text: 原始提取的文本
            preserve_structure: 是否保留段落结构（True保留换行，False压缩为单段）
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        try:
            cleaned = text
            
            # 1. 移除不可见的控制字符和BOM标记
            # 保留：\n (换行), \t (制表符), \x20-\x7E (可打印ASCII), \u00A0+ (可打印Unicode)
            # 移除：\x00-\x1F (控制字符，除\n\t), \x7F-\x9F (控制字符), \ufeff (BOM)
            import unicodedata
            cleaned = ''.join(
                char for char in cleaned 
                if unicodedata.category(char)[0] != 'C' or char in '\n\t\r'
            )
            cleaned = cleaned.replace('\ufeff', '')  # 移除BOM
            cleaned = cleaned.replace('\x00', '')  # 移除NULL字符
            
            # 2. 标准化换行符（统一为 \n）
            cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
            
            # 3. 修复断开的单词（行末连字符后的换行）
            # 模式：word-\nword -> word-word
            if preserve_structure:
                cleaned = re.sub(r'([a-zA-Z])-\n([a-zA-Z])', r'\1\2', cleaned)
            
            # 4. 规范化空白字符
            # 多个空格合并为单个空格（但保留换行）
            lines = cleaned.split('\n')
            normalized_lines = []
            for line in lines:
                # 移除行首尾空白，合并行内多个空格
                normalized_line = re.sub(r'[ \t]+', ' ', line.strip())
                if normalized_line or preserve_structure:
                    normalized_lines.append(normalized_line)
            cleaned = '\n'.join(normalized_lines)
            
            # 5. 处理多余的空行
            if preserve_structure:
                # 最多保留两个连续换行（段落分隔）
                while '\n\n\n' in cleaned:
                    cleaned = cleaned.replace('\n\n\n', '\n\n')
            else:
                # 如果不保留结构，移除所有换行
                cleaned = cleaned.replace('\n', ' ')
                # 合并多个空格
                cleaned = re.sub(r'\s+', ' ', cleaned)
            
            # 6. 移除行尾和行首的多余空白
            cleaned = cleaned.strip()
            
            # 7. 修复常见的OCR错误（如果检测到）
            # 注意：这里只修复明显的、通用的错误
            # 特定领域的错误应该在后续处理中修复
            
            # 8. 统一引号（可选，但对于学术文本通常不需要）
            # cleaned = cleaned.replace('"', '"').replace('"', '"')
            # cleaned = cleaned.replace(''', "'").replace(''', "'")
            
            return cleaned
            
        except Exception as e:
            logging.warning(f"文本清理过程中出现错误，返回部分清理的文本: {str(e)}")
            # 即使出错，也要尝试基本的清理
            try:
                return re.sub(r'\x00', '', text).strip()
            except:
                return text
    
    @staticmethod
    def extract_text_and_metadata(pdf_path: str, 
                                  exclude_references: bool = True,
                                  detailed_errors: bool = True) -> Dict[str, Any]:
        """
        统一提取PDF文本和元数据，包含学术元数据提取
        自动识别并排除参考文献部分
        
        Args:
            pdf_path: PDF文件路径
            exclude_references: 是否排除参考文献部分
            detailed_errors: 是否提供详细的错误诊断信息
            
        Returns:
            包含文本和元数据的字典，失败时包含详细的错误信息
        """
        error_context = {}  # 收集错误诊断信息
        
        doc = None
        document_metadata: Dict[str, Any] = {}
        total_pages = 0

        try:
            # 验证文件存在
            if not os.path.exists(pdf_path):
                error_msg = f"PDF文件不存在: {pdf_path}"
                logging.error(error_msg)
                return {
                    'text': '',
                    'pages': [],
                    'metadata': {},
                    'success': False,
                    'error': error_msg,
                    'error_code': 'FILE_NOT_FOUND',
                    'diagnostics': {'file_path': pdf_path} if detailed_errors else {}
                }
            
            # 检查文件大小
            file_size = os.path.getsize(pdf_path)
            error_context['file_size'] = file_size
            if file_size == 0:
                error_msg = f"PDF文件为空: {pdf_path}"
                logging.error(error_msg)
                return {
                    'text': '',
                    'pages': [],
                    'metadata': {},
                    'success': False,
                    'error': error_msg,
                    'error_code': 'EMPTY_FILE',
                    'diagnostics': error_context if detailed_errors else {}
                }
            
            # 尝试打开PDF
            try:
                doc = fitz.open(pdf_path)
                document_metadata, total_pages = PDFUtils._snapshot_document_state(doc)
                error_context['total_pages'] = total_pages
            except Exception as e:
                error_msg = f"无法打开PDF文件: {str(e)}"
                logging.error(f"{error_msg} | 文件路径: {pdf_path}")
                return {
                    'text': '',
                    'pages': [],
                    'metadata': {},
                    'success': False,
                    'error': error_msg,
                    'error_code': 'PDF_OPEN_FAILED',
                    'diagnostics': {
                        **error_context,
                        'exception_type': type(e).__name__,
                        'exception_details': str(e)
                    } if detailed_errors else {}
                }
            text = ""
            pages = []
            references_start_page = None
            page_texts = []  # 缓存所有页面文本
            
            # 第一遍：读取所有页面文本并识别参考文献开始位置
            failed_pages = []
            for page_num in range(total_pages):
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    # 使用统一的文本清理函数
                    if page_text:
                        page_text = PDFUtils.clean_text(page_text, preserve_structure=True)
                    
                    page_texts.append(page_text)
                    
                    # 检测参考文献标题（通常在页面顶部或前几行）
                    if exclude_references:
                        lines = page_text.split('\n')[:20]  # 检查前20行
                        is_references_page = False
                        
                        for line in lines:
                            line_lower = line.strip().lower()
                            # 识别参考文献标题模式
                            reference_markers = [
                                'references', 'reference', 'bibliography', 'bibliographies',
                                'cited references', 'literature cited', 'works cited',
                                '参考文献', '引用文献', '文献列表'
                            ]
                            if any(marker in line_lower and len(line_lower) < 50 for marker in reference_markers):
                                is_references_page = True
                                break
                        
                        if is_references_page and references_start_page is None:
                            references_start_page = page_num + 1
                            logging.info(f"检测到参考文献部分起始页: {page_num + 1}")
                            
                except Exception as e:
                    failed_pages.append(page_num + 1)
                    logging.warning(f"提取第 {page_num + 1} 页文本失败: {str(e)}")
                    page_texts.append("")  # 添加空文本占位
                    
            if failed_pages:
                error_context['failed_pages'] = failed_pages
                logging.warning(f"共有 {len(failed_pages)} 页提取失败: {failed_pages}")
            
            # 第二遍：过滤文本（排除参考文献部分）
            for page_num, page_text in enumerate(page_texts):
                # 如果从这一页开始是参考文献，则跳过
                if references_start_page and page_num + 1 >= references_start_page:
                    # 再次确认这一页确实是参考文献
                    lines = page_text.split('\n')[:10]
                    has_ref_markers = any(
                        any(marker in line.strip().lower()[:50] for marker in [
                            'references', 'reference', 'bibliography', 'cited references'
                        ])
                        for line in lines
                    )
                    
                    # 检查是否包含大量参考文献特征（作者名+年份模式）
                    ref_pattern_count = len(re.findall(
                        r'[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*[,.]\s*\d{4}', 
                        page_text
                    ))
                    
                    # 如果确认是参考文献页，则跳过
                    if has_ref_markers or ref_pattern_count > 5:
                        logging.debug(f"跳过参考文献页 {page_num + 1} (检测到 {ref_pattern_count} 个引用模式)")
                        continue
                
                if (not exclude_references) or references_start_page is None or page_num + 1 < references_start_page:
                    text += page_text + "\n"
                    pages.append({
                        'page_num': page_num + 1,
                        'text': page_text,
                        'text_length': len(page_text)
                    })
            
            # 如果没有任何文本，检查原因
            if not text.strip():
                # 检查是否所有页面都为空
                empty_pages = sum(1 for pt in page_texts if not pt.strip())
                total_pages = len(page_texts)
                
                if empty_pages == total_pages:
                    error_msg = "所有页面文本提取为空，可能是扫描版PDF或加密PDF"
                    logging.warning(f"{error_msg} | 文件: {pdf_path}")
                    return {
                        'text': '',
                        'pages': [],
                        'metadata': {},
                        'success': False,
                        'error': error_msg,
                        'error_code': 'NO_TEXT_EXTRACTED',
                        'diagnostics': {
                            **error_context,
                            'total_pages': total_pages,
                            'empty_pages': empty_pages,
                            'suggestion': '可能需要OCR处理或PDF可能已加密'
                        } if detailed_errors else {}
                    }
            
            # 使用统一的文本清理函数进行最终清理
            text = PDFUtils.clean_text(text, preserve_structure=True)
            
            # 从PDF内容中提取学术元数据（使用过滤后的文本）
            try:
                academic_metadata = PDFUtils.extract_academic_metadata(text)
            except Exception as e:
                logging.warning(f"提取学术元数据失败: {str(e)}")
                academic_metadata = {}
            
            # 优先使用学术元数据中的标题，如果没有则使用PDF元数据，最后才使用文件名
            title_source = academic_metadata.get('title', '') or document_metadata.get('title', '')
            
            # 如果标题是文档ID格式，尝试从PDF第一页更智能地提取
            if title_source and PDFUtils._is_document_id(title_source):
                logging.info(f"检测到文档ID格式的标题 '{title_source[:60]}'，尝试从PDF第一页重新提取标题")
                # 尝试从第一页提取更真实的标题
                first_page_text = page_texts[0] if page_texts else ''
                better_title = PDFUtils._extract_title_from_first_page(first_page_text)
                if better_title and not PDFUtils._is_document_id(better_title):
                    title_source = better_title
                    logging.info(f"从第一页提取到更好的标题: {better_title[:80]}")
            
            if not title_source or title_source.strip() == '' or PDFUtils._is_document_id(title_source):
                # 如果仍然没有有效标题，尝试从文件名提取（移除UUID前缀）
                filename = os.path.basename(pdf_path)
                # 移除UUID前缀（格式：uuid_actual_title.pdf）
                if '_' in filename:
                    parts = filename.split('_', 1)  # 只分割第一个下划线
                    if len(parts) > 1:
                        filename_title = parts[1].replace('.pdf', '').replace('_', ' ')
                    else:
                        filename_title = filename.replace('.pdf', '').replace('_', ' ')
                else:
                    filename_title = filename.replace('.pdf', '').replace('_', ' ')
                
                # 如果文件名也不是文档ID，使用它；否则使用通用标题
                if filename_title and not PDFUtils._is_document_id(filename_title):
                    title_source = filename_title
                else:
                    title_source = "Academic Paper"
            
            # 统计基础信息（使用文档打开期缓存的快照）
            file_size = os.path.getsize(pdf_path)
            
            # 轻量清洗标题：去除重复空白并截断过长标题
            cleaned_title = PDFUtils.clean_title(title_source)
            cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
            if len(cleaned_title) > 180:
                cleaned_title = cleaned_title[:177] + '...'

            # 合并PDF元数据和学术元数据
            metadata = {
                'title': cleaned_title,
                'author': document_metadata.get('author', '') or academic_metadata.get('authors', ''),
                'subject': document_metadata.get('subject', ''),
                'creator': document_metadata.get('creator', ''),
                'producer': document_metadata.get('producer', ''),
                'creation_date': str(document_metadata.get('creationDate', '')),
                'modification_date': str(document_metadata.get('modDate', '')),
                'total_pages': total_pages,
                'file_size': file_size,
                # 学术元数据
                'authors': academic_metadata.get('authors', ''),
                'year': academic_metadata.get('year', ''),
                'journal': academic_metadata.get('journal', ''),
                'doi': academic_metadata.get('doi', ''),
                'abstract': academic_metadata.get('abstract', ''),
                'keywords': academic_metadata.get('keywords', '')
            }
            
            # 计算统计信息
            stats = {
                'total_pages': total_pages,
                'pages_extracted': len(pages),
                'total_text_length': len(text),
                'avg_page_length': len(text) / max(len(pages), 1),
                'references_excluded': exclude_references and references_start_page is not None,
                'references_start_page': references_start_page
            }
            
            # 如果提取的页面数明显少于总页数，记录警告
            if len(pages) < total_pages * 0.5 and exclude_references:
                logging.info(f"提取的页面数 ({len(pages)}) 明显少于总页数 ({total_pages}), "
                           f"可能由于参考文献过滤")
            
            return {
                'text': text,
                'pages': pages,
                'metadata': metadata,
                'stats': stats,
                'success': True
            }
            
        except fitz.FileDataError as e:
            error_msg = f"PDF文件数据错误: {str(e)}"
            logging.error(f"{error_msg} | 文件: {pdf_path}")
            return {
                'text': '',
                'pages': [],
                'metadata': {},
                'success': False,
                'error': error_msg,
                'error_code': 'PDF_DATA_ERROR',
                'diagnostics': {
                    **error_context,
                    'exception_type': type(e).__name__,
                    'exception_details': str(e),
                    'suggestion': 'PDF文件可能已损坏，尝试使用其他PDF阅读器打开验证'
                } if detailed_errors else {}
            }
        except MemoryError as e:
            error_msg = f"处理PDF时内存不足: {str(e)}"
            logging.error(f"{error_msg} | 文件: {pdf_path} (大小: {error_context.get('file_size', 'unknown')} bytes)")
            return {
                'text': '',
                'pages': [],
                'metadata': {},
                'success': False,
                'error': error_msg,
                'error_code': 'MEMORY_ERROR',
                'diagnostics': {
                    **error_context,
                    'exception_type': type(e).__name__,
                    'suggestion': 'PDF文件可能过大，考虑分段处理或增加系统内存'
                } if detailed_errors else {}
            }
        except Exception as e:
            error_msg = f"PDF处理错误: {str(e)}"
            logging.error(f"{error_msg} | 文件: {pdf_path} | 异常类型: {type(e).__name__}", exc_info=True)
            return {
                'text': '',
                'pages': [],
                'metadata': {},
                'success': False,
                'error': error_msg,
                'error_code': 'UNKNOWN_ERROR',
                'diagnostics': {
                    **error_context,
                    'exception_type': type(e).__name__,
                    'exception_details': str(e),
                    'traceback_available': True
                } if detailed_errors else {}
            }
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    logging.debug("关闭PDF文档失败: %s", pdf_path, exc_info=True)
    
    @staticmethod
    def extract_academic_metadata(text: str) -> Dict[str, str]:
        """
        从PDF文本中提取学术元数据
        
        Args:
            text: PDF文本内容
            
        Returns:
            学术元数据字典
        """
        metadata = {}
        
        try:
            # 提取DOI
            doi_pattern = r'10\.\d{4,}\/[^\s]+'
            doi_matches = re.findall(doi_pattern, text)
            if doi_matches:
                metadata['doi'] = doi_matches[0]
            
            # 提取年份（增强版：优先选择合理的发表年份）
            year_pattern = r'\b(19|20)\d{2}\b'
            first_page_text = text[:3000]  # 扩展到前3000字符
            all_years = re.findall(year_pattern, first_page_text)
            
            if all_years:
                # 转换为整数并验证合理性
                current_year = datetime.now().year
                valid_years = []
                
                for year_str in all_years:
                    try:
                        year_int = int(year_str)
                        # 年份应该在1800到当前年份之间（不允许未来年份）
                        if 1800 <= year_int <= current_year:
                            valid_years.append(year_int)
                    except ValueError:
                        continue
                
                if valid_years:
                    # 优先选择最接近当前年份的年份（更可能是发表年份）
                    # 但也要考虑可能是最早的年份（如果都在合理范围内）
                    # 策略：选择在1900-当前年份范围内，且接近当前年份的
                    recent_years = [y for y in valid_years if 1900 <= y <= current_year]
                    if recent_years:
                        # 选择最近的年份（更可能是发表年份）
                        metadata['year'] = str(max(recent_years))
                    else:
                        # 如果没有近年的，选择第一个合理的
                        metadata['year'] = str(min(valid_years))
            
            # 提取期刊名称（增强版：多种策略）
            journal_candidates = []
            
            # 策略1: 从DOI提取期刊信息（如果DOI格式包含期刊信息）
            # 很多DOI格式：10.xxxx/journal_name/yyyy
            if metadata.get('doi'):
                doi = metadata['doi']
                # DOI格式: 10.prefix/journal_name/identifier
                doi_parts = doi.split('/')
                if len(doi_parts) >= 2:
                    # 尝试从DOI的journal部分提取（通常是第二部分）
                    potential_journal = doi_parts[1].strip()
                    # 移除常见的数字和标识符
                    potential_journal = re.sub(r'[0-9_-]+$', '', potential_journal)
                    if len(potential_journal) > 3 and not re.match(r'^[0-9]+$', potential_journal):
                        journal_candidates.append(('doi', potential_journal))
            
            # 策略2: 从文本中查找期刊名模式（增强模式）
            journal_patterns = [
                # 常见期刊格式
                r'([A-Z][a-zA-Z\s&]+\s+(?:Journal|Review|Letters|Proceedings|Transactions|Bulletin|Magazine))',
                # 期刊名 卷号(年份) - 注意括号需要转义
                r'([A-Z][a-zA-Z\s&]+\s+\d+\s*\([0-9]{4}\))',
                # 期刊名, 卷号( - 匹配到左括号但不包含括号
                r'([A-Z][a-zA-Z\s&]+,?\s*\d+)(?=\s*\()',
                # 期刊名后跟卷号、页码
                r'([A-Z][a-zA-Z\s&]+\s+\d+[:\s]+\d+)',
                # 知名期刊（缩写）
                r'\b(Nature|Science|PNAS|Cell|Lancet|JAMA|NEJM)\b',
            ]
            
            # 在前5000字符中查找（扩展到第一页的更多内容）
            search_text = text[:5000]
            for pattern in journal_patterns:
                try:
                    matches = re.findall(pattern, search_text, re.IGNORECASE)
                except re.error as e:
                    logging.warning(f"期刊提取正则表达式错误: {pattern} - {e}")
                    continue
                    
                if matches:
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0] if match else ''
                        # 清理期刊名
                        journal_name = match.strip()
                        # 移除卷号、页码等（但保留期刊名）
                        journal_name = re.sub(r'\s+\d+[:\s()].*$', '', journal_name).strip()
                        journal_name = re.sub(r',\s*\d+.*$', '', journal_name).strip()
                        # 移除尾部的括号和数字（注意转义括号）
                        journal_name = re.sub(r'\s*\([^)]*\)\s*$', '', journal_name).strip()
                        
                        # 验证期刊名是否有效
                        journal_lower = journal_name.lower()
                        is_valid_journal = (
                            len(journal_name) > 3 and len(journal_name) < 100 and
                            not re.match(r'^[0-9\s]+$', journal_name) and
                            not PDFUtils._is_document_id(journal_name) and
                            # 额外检查：不应该是纯DOI片段或文件名
                            not re.match(r'^[a-z]+\.[0-9]', journal_lower) and  # 如 "j.1945-5100"
                            not re.match(r'^doi:', journal_lower) and  # DOI前缀
                            not re.match(r'^[0-9]+$', journal_name.strip()) and  # 纯数字
                            not journal_lower.startswith('essoar.') and  # essoar文档ID
                            # 单字母点开头必须是期刊缩写（如 "J. Geophys. Res."），否则拒绝
                            not (re.match(r'^[a-z]\.$', journal_lower) or  # 单字母点结尾
                                 re.match(r'^[a-z]\.[a-z]+\.[0-9]', journal_lower)) and  # j.journal.123格式
                            # 包含至少一个字母（不能全是数字和符号）
                            bool(re.search(r'[a-z]{3,}', journal_lower))  # 至少3个连续字母
                        )
                        
                        if is_valid_journal:
                            journal_candidates.append(('pattern', journal_name))
                            break  # 找到第一个就停止
            
            # 策略3: 从已知期刊列表匹配（常见期刊名称）
            known_journals = [
                'Nature', 'Science', 'PNAS', 'Cell', 'Lancet', 'JAMA', 'NEJM',
                'Astrophysical Journal', 'Astronomy & Astrophysics', 'Monthly Notices',
                'Icarus', 'Geochimica et Cosmochimica Acta', 'Meteoritics & Planetary Science',
                'International Journal of Astrobiology', 'Astrobiology', 'Origins of Life',
                'Earth and Planetary Science Letters', 'Planetary and Space Science',
            ]
            for known_journal in known_journals:
                if known_journal.lower() in search_text.lower():
                    journal_candidates.append(('known', known_journal))
                    break
            
            # 选择最佳候选（优先DOI，然后模式匹配，最后已知期刊）
            # 同时进行最终验证，确保不是文档ID格式
            if journal_candidates:
                valid_candidates = []
                for source, journal in journal_candidates:
                    journal_lower = journal.lower()
                    # 最终验证：确保不是文档ID格式
                    if not PDFUtils._is_document_id(journal):
                        # 额外验证：检查是否是明显的文档ID或文件名
                        is_valid = (
                            not re.match(r'^[a-z]+\.[0-9]', journal_lower) and  # 如 "j.1945-5100"
                            not journal_lower.startswith('doi:') and
                            not journal_lower.startswith('essoar.') and
                            len(journal.split()) > 0 and  # 至少有一个词
                            # 必须包含至少3个连续字母
                            bool(re.search(r'[a-z]{3,}', journal_lower)) and
                            # 不能是纯数字或主要是数字
                            not re.match(r'^[0-9.,\s]+$', journal) and
                            # 不能是明显的文件名格式
                            not re.match(r'^[a-z]+\.[a-z]+\.[0-9]', journal_lower)  # j.journal.123
                        )
                        if is_valid:
                            valid_candidates.append((source, journal))
                
                if valid_candidates:
                    # 优先选择来自DOI或已知期刊的，否则选择第一个
                    for source, journal in valid_candidates:
                        if source in ('doi', 'known'):
                            metadata['journal'] = journal
                            break
                    else:
                        # 如果没有优先来源，选择第一个
                        metadata['journal'] = valid_candidates[0][1]
            
            # 提取作者（从标题下方寻找）
            # 寻找大写字母开头的名字模式
            author_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+\s+[A-Z][a-z]+)*)'
            lines = text.split('\n')[:10]  # 前10行
            for line in lines:
                line = line.strip()
                if line and not line.startswith('Abstract') and not line.startswith('ABSTRACT'):
                    author_match = re.search(author_pattern, line)
                    if author_match and len(line) < 200:
                        authors = author_match.group(0)
                        # 清理作者名
                        authors = re.sub(r'\d+', '', authors)
                        authors = re.sub(r'[^A-Za-z\s,]', '', authors)
                        authors = re.sub(r'\s+', ' ', authors).strip()
                        if authors and len(authors) > 5:
                            metadata['authors'] = authors
                            break
            
            # 提取标题（优化版本 - 支持跨行标题）
            lines = text.split('\n')
            title_candidates = []
            
            # 跳过前几行（通常是DOI、期刊信息等）
            start_line = 0
            for i, line in enumerate(lines[:10]):
                line = line.strip()
                # 如果遇到DOI模式，跳过
                if re.search(r'10\.\d{4,}\/[^\s]+', line):
                    start_line = i + 1
                    continue
                # 如果遇到期刊模式，跳过
                if re.search(r'[A-Z][a-zA-Z\s]+\s+\d+\s*\(\d{4}\)', line):
                    start_line = i + 1
                    continue
                # 如果遇到页码模式，跳过
                if re.search(r'^\d+\s*$', line):
                    start_line = i + 1
                    continue
            
            # 寻找跨行标题
            title_lines = []
            for i in range(start_line, min(start_line + 25, len(lines))):
                line = lines[i].strip()
                if not line:
                    continue
                
                # 跳过明显的非标题内容（增强版：包含文档ID和期刊代码）
                skip_patterns = [
                    r'^10\.\d{4,}\/[^\s]+',  # DOI
                    r'^[A-Z][a-zA-Z\s]+\s+\d+\s*\(\d{4}\)',  # 期刊信息
                    r'^\d+\s*$',  # 纯数字（页码）
                    r'^[0-9]{4}[-]?[0-9]{3,4}X',  # 文档ID格式 "0004-637X"
                    r'^[0-9]{4}[-]?[0-9]{3,4}X\s+[0-9]+\s+[0-9]+\s+[0-9]+',  # "0004-637X 783 2 140"
                    r'^[A-Z0-9]+[-][0-9]+[-][0-9]+',  # "S0960-9822(96)00698-7"
                    r'^[a-z]+[0-9]+[-][0-9]+',  # "isms-2018-TL03"
                    r'^[0-9]+\s+[0-9]+\s+[0-9]+$',  # "783 2 140" (期刊页码)
                    r'^Abstract',  # 摘要
                    r'^ABSTRACT',
                    r'^Keywords',
                    r'^KEYWORDS',
                    r'^Introduction',
                    r'^INTRODUCTION',
                    r'^[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+',  # 作者名模式
                    r'^\d+\s*,\s*[A-Z][a-z]+',  # 作者编号模式
                    r'^Received\s+',  # 接收日期
                    r'^Accepted\s+',  # 接受日期
                    r'^Published\s+',  # 发表日期
                    r'^Research Article',  # 文章类型
                    r'^Review Article',  # 文章类型
                    r'^Citation:',  # 引用信息
                    r'^CITATION:',  # 引用信息
                    r'^arXiv:',  # arXiv信息
                    r'^ARXIV:',  # arXiv信息
                    r'^AST-\d+',  # AST期刊编号
                    r'^[A-Z]{2,}-\d{4}',  # 期刊编号模式
                    r'^[A-Z][a-z]+\s+[A-Z][a-z]+.*University',  # 作者+大学模式
                    r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+.*University',  # 作者+大学模式
                    r'^Academic Editors:',  # 学术编辑
                    r'^ACADEMIC EDITORS:',  # 学术编辑
                    r'^Editors:',  # 编辑
                    r'^EDITORS:',  # 编辑
                    r'^TYPE\s+',  # 文章类型
                    r'^PUBLISHED\s+',  # 发表日期
                    r'^DOI\s+',  # DOI
                    r'^OPEN ACCESS',  # 开放获取
                    r'^EDITED BY',  # 编辑者
                    r'^REVIEWED BY',  # 审稿者
                    r'^CORRESPONDENCE',  # 通讯作者
                    r'^SPECIALTY SECTION',  # 专业领域
                    r'^This article was submitted to',  # 投稿信息
                    r'^Frontiers in',  # Frontiers期刊
                    r'^RECEIVED\s+',  # 接收日期
                    r'^ACCEPTED\s+',  # 接受日期
                    r'^COPYRIGHT',  # 版权信息
                    r'^©\s+\d{4}',  # 版权年份
                ]
                
                # 检查是否是文档ID/期刊代码格式（需要先检查）
                is_document_id = (
                    re.match(r'^[0-9]{4}[-]?[0-9]{3,4}X', line) or  # "0004-637X"
                    re.match(r'^[0-9]{4}[-]?[0-9]{3,4}X\s+[0-9]+\s+[0-9]+\s+[0-9]+', line) or  # "0004-637X 783 2 140"
                    re.match(r'^[A-Z0-9]+[-][0-9]+[-][0-9]+', line) or  # "S0960-9822(96)00698-7"
                    re.match(r'^[a-z]+[0-9]+[-][0-9]+', line.lower()) or  # "isms-2018-TL03"
                    re.match(r'^[0-9]+\s+[0-9]+\s+[0-9]+$', line)  # "783 2 140"
                )
                if is_document_id:
                    logging.debug(f"跳过文档ID/期刊代码行: {line[:60]}")
                    continue
                
                should_skip = False
                for pattern in skip_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        should_skip = True
                        break
                
                if should_skip:
                    continue
                
                # 检查是否是潜在的标题行（增强版：排除文档ID格式）
                # 排除文档ID和期刊代码
                if (re.match(r'^[0-9]{4}[-]?[0-9]{3,4}X', line) or
                    re.match(r'^[0-9]{4}[-]?[0-9]{3,4}X\s+[0-9]+\s+[0-9]+\s+[0-9]+', line) or
                    re.match(r'^[A-Z0-9]+[-][0-9]+[-][0-9]+', line) or
                    re.match(r'^[0-9]+\s+[0-9]+\s+[0-9]+$', line)):
                    continue  # 跳过文档ID/期刊代码
                
                # 检查是否是潜在的标题行
                if (len(line) > 10 and len(line) < 200 and 
                    not line.isupper() and  # 不是全大写
                    not line.islower() and   # 不是全小写
                    not re.search(r'^\d+\.?\s*$', line) and  # 不是纯数字
                    re.search(r'[A-Z]', line) and  # 包含大写字母
                    not re.search(r'^\d+\s*,\s*[A-Z]', line) and  # 不是作者编号
                    not re.search(r'^[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z]', line) and  # 不是作者名
                    # 额外检查：不是文档ID模式
                    not re.match(r'^[0-9]{4}[-]?[0-9]{3,4}X', line) and
                    not re.match(r'^[0-9]+\s+[0-9]+\s+[0-9]+$', line)):
                    
                    title_lines.append(line)
                    
                    # 如果遇到作者行或摘要，停止收集标题行
                    if (re.search(r'^Abstract', line, re.IGNORECASE) or
                        re.search(r'^Keywords', line, re.IGNORECASE) or
                        re.search(r'^Introduction', line, re.IGNORECASE)):
                        break
                    
                    # 检查是否是作者行（更严格的检查）
                    if re.search(r'^[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+\s+[A-Z][a-z]+)*$', line):
                        # 如果已经有标题行，停止收集
                        if title_lines:
                            break
                        # 否则跳过这一行，继续寻找标题
                        continue
            
            # 合并标题行
            if title_lines:
                # 合并所有标题行
                full_title = ' '.join(title_lines)
                
                # 清理标题
                full_title = re.sub(r'\s+', ' ', full_title).strip()
                full_title = re.sub(r'[^\w\s\-.,:;!?()]', '', full_title)  # 移除特殊字符
                
                # 验证标题不是文档ID或期刊代码
                is_invalid_title = (
                    re.match(r'^[0-9]{4}[-]?[0-9]{3,4}X', full_title) or  # "0004-637X"
                    re.match(r'^[0-9]{4}[-]?[0-9]{3,4}X\s+[0-9]+\s+[0-9]+\s+[0-9]+', full_title) or  # "0004-637X 783 2 140"
                    re.match(r'^[A-Z0-9]+[-][0-9]+[-][0-9]+', full_title) or  # "S0960-9822(96)00698-7"
                    re.match(r'^[0-9]+\s+[0-9]+\s+[0-9]+$', full_title) or  # "783 2 140"
                    # 检查是否主要是数字和符号（可能是期刊代码）
                    (len(re.findall(r'[0-9]', full_title)) > len(full_title) * 0.5 and len(full_title) < 30)
                )
                
                if not is_invalid_title and len(full_title) > 15 and len(full_title) < 500:
                    metadata['title'] = full_title
                elif is_invalid_title:
                    logging.warning(f"检测到文档ID格式的标题，拒绝: {full_title[:60]}")
            
            # 提取摘要
            abstract_patterns = [
                r'Abstract\s*[\s\S]*?(?=\n\s*\n|\n\s*Keywords|\n\s*Introduction)',
                r'ABSTRACT\s*[\s\S]*?(?=\n\s*\n|\n\s*KEYWORDS|\n\s*INTRODUCTION)',
            ]
            
            for pattern in abstract_patterns:
                abstract_match = re.search(pattern, text, re.IGNORECASE)
                if abstract_match:
                    abstract = abstract_match.group(0)
                    abstract = re.sub(r'^Abstract\s*', '', abstract, flags=re.IGNORECASE)
                    abstract = re.sub(r'^ABSTRACT\s*', '', abstract, flags=re.IGNORECASE)
                    abstract = abstract.strip()
                    if len(abstract) > 50:
                        metadata['abstract'] = abstract
                        break
            
            # 提取关键词
            keywords_pattern = r'Keywords?\s*:\s*([^\n]+)'
            keywords_match = re.search(keywords_pattern, text, re.IGNORECASE)
            if keywords_match:
                keywords = keywords_match.group(1)
                keywords = re.sub(r'Keywords?\s*:\s*', '', keywords, flags=re.IGNORECASE)
                metadata['keywords'] = keywords
                
        except Exception as e:
            logging.warning(f"提取学术元数据失败: {str(e)}")
            
        return metadata
    
    @staticmethod
    def _is_document_id(text: str) -> bool:
        """
        检查文本是否是文档ID或期刊代码格式
        
        Args:
            text: 要检查的文本
            
        Returns:
            如果是文档ID格式，返回True
        """
        if not text or not text.strip():
            return False
        
        text = text.strip()
        
        # 文档ID模式
        document_id_patterns = [
            r'^[0-9]{4}[-]?[0-9]{3,4}X\s+[0-9]+\s+[0-9]+\s+[0-9]+',  # "0004-637X 783 2 140"
            r'^[0-9]{4}[-]?[0-9]{3,4}X',  # "0004-637X"
            r'^[A-Z0-9]+[-][0-9]+[-][0-9]+',  # "S0960-9822(96)00698-7"
            r'^[a-z]+[0-9]+[-][0-9]+',  # "isms-2018-TL03"
            r'^[0-9]+\s+[0-9]+\s+[0-9]+$',  # "783 2 140"
        ]
        
        for pattern in document_id_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # 检查是否主要是数字和符号（可能是期刊代码变体）
        if (len(re.findall(r'[0-9]', text)) > len(text) * 0.5 and 
            len(text) < 30 and 
            len(re.findall(r'[A-Za-z]', text)) < len(text) * 0.3):
            return True
        
        return False
    
    @staticmethod
    def _extract_title_from_first_page(first_page_text: str) -> str:
        """
        从PDF第一页更智能地提取标题（当检测到文档ID时使用）
        
        Args:
            first_page_text: PDF第一页的文本
            
        Returns:
            提取的标题，如果没有找到返回空字符串
        """
        if not first_page_text:
            return ""
        
        lines = first_page_text.split('\n')
        
        # 在前30行中寻找标题候选
        candidates = []
        skip_next = False
        
        for i, line in enumerate(lines[:30]):
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # 跳过已知的噪声模式
            if (re.match(r'^10\.\d{4,}\/[^\s]+', line) or  # DOI
                re.match(r'^[0-9]{4}[-]?[0-9]{3,4}X', line) or  # 文档ID
                re.match(r'^[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z]', line) or  # 作者名
                'Received:' in line or 'Accepted:' in line or 'Published:' in line or
                line.lower().startswith(('abstract', 'keywords', 'introduction'))):
                skip_next = False
                continue
            
            # 寻找潜在的标题行
            if (20 <= len(line) <= 200 and
                not line.isupper() and
                not line.islower() and
                re.search(r'[A-Z][a-z]+', line) and  # 包含大写+小写字母组合
                not PDFUtils._is_document_id(line) and
                not re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+$', line)):  # 不是作者名模式
                candidates.append((i, line))
                
                # 如果找到第一个好的候选，且下一行是作者或摘要，停止
                if i < len(lines) - 1:
                    next_line = lines[i + 1].strip()
                    if (re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+', next_line) or
                        next_line.lower().startswith('abstract')):
                        break
        
        # 选择最佳候选（通常是第一个）
        if candidates:
            # 优先选择第一个，但如果它看起来像文档ID，尝试下一个
            for idx, candidate in candidates:
                if not PDFUtils._is_document_id(candidate):
                    return candidate[:200]  # 限制长度
        
        return ""
    
    @staticmethod
    def clean_title(title: str) -> str:
        """
        统一清理和标准化PDF标题，拒绝文档ID和期刊代码格式
        
        Args:
            title: 原始标题
            
        Returns:
            清理后的标题
        """
        if not title or title.strip() == '':
            return "Untitled Document"
        
        cleaned = title.strip()
        
        # 检测并拒绝文档ID/期刊代码格式（优先检查）
        document_id_patterns = [
            r'^[0-9]{4}[-]?[0-9]{3,4}X\s+[0-9]+\s+[0-9]+\s+[0-9]+',  # "0004-637X 783 2 140"
            r'^[0-9]{4}[-]?[0-9]{3,4}X',  # "0004-637X"
            r'^[A-Z0-9]+[-][0-9]+[-][0-9]+',  # "S0960-9822(96)00698-7"
            r'^[a-z]+[0-9]+[-][0-9]+',  # "isms-2018-TL03" (忽略大小写)
            r'^[0-9]+\s+[0-9]+\s+[0-9]+$',  # "783 2 140" (纯期刊页码)
        ]
        
        for pattern in document_id_patterns:
            if re.match(pattern, cleaned, re.IGNORECASE):
                logging.info(f"检测到文档ID格式的标题，使用通用标题: {cleaned[:60]}")
                return "Academic Paper"
        
        # 检查是否主要是数字和符号（可能是期刊代码变体）
        if (len(re.findall(r'[0-9]', cleaned)) > len(cleaned) * 0.5 and 
            len(cleaned) < 30 and 
            len(re.findall(r'[A-Za-z]', cleaned)) < len(cleaned) * 0.3):
            logging.info(f"检测到疑似期刊代码格式的标题，使用通用标题: {cleaned[:60]}")
            return "Academic Paper"
        
        # 如果标题是DOI格式，返回通用标题
        if re.match(r'^10\.\d{4,}\/[^\s]+', cleaned):
            return "Academic Paper"
        
        # 清理标题
        # 移除常见的非标题内容
        cleaned = re.sub(r'^10\.\d{4,}\/[^\s]+', '', cleaned)  # 移除DOI
        cleaned = re.sub(r'^[A-Z][a-zA-Z\s]+\s+\d+\s*\(\d{4}\)', '', cleaned)  # 移除期刊信息
        cleaned = re.sub(r'^\d+\s*$', '', cleaned)  # 移除纯数字
        
        # 移除引用信息
        cleaned = re.sub(r'^Citation:\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^CITATION:\s*', '', cleaned, flags=re.IGNORECASE)
        
        # 移除arXiv信息
        cleaned = re.sub(r'^arXiv:\s*[^\s]+\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^ARXIV:\s*[^\s]+\s*', '', cleaned, flags=re.IGNORECASE)
        
        # 移除期刊编号
        cleaned = re.sub(r'^AST-\d+[^\s]*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^[A-Z]{2,}-\d{4}[^\s]*', '', cleaned, flags=re.IGNORECASE)
        
        # 移除作者+大学模式
        cleaned = re.sub(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+University[^.]*\.', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+University[^.]*\.', '', cleaned, flags=re.IGNORECASE)
        
        # 移除学术编辑信息
        cleaned = re.sub(r'^Academic Editors:[^.]*\.', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^ACADEMIC EDITORS:[^.]*\.', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^Editors:[^.]*\.', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^EDITORS:[^.]*\.', '', cleaned, flags=re.IGNORECASE)
        
        # 移除文件名中的UUID前缀（如果存在）
        # 匹配UUID格式：xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\s*'
        cleaned = re.sub(uuid_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # 移除其他常见的文件名前缀模式
        cleaned = re.sub(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\s*', '', cleaned, flags=re.IGNORECASE)
        
        # 清理特殊字符，但保留标点符号
        cleaned = re.sub(r'[^\w\s\-.,:;!?()\[\]]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # 如果清理后为空，返回通用标题
        if not cleaned or len(cleaned.strip()) < 5:
            return "Academic Paper"
        
        # 限制长度
        max_length = 200
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length-3] + "..."
        
        return cleaned.strip()
    
    @staticmethod
    def extract_text_and_chunks(pdf_path: str, chunk_size: int = None, overlap: int = None) -> Dict[str, Any]:
        """
        统一提取PDF文本并分块，整合所有处理步骤
        
        Args:
            pdf_path: PDF文件路径
            chunk_size: 分块大小
            overlap: 重叠大小
            
        Returns:
            包含文本、分块和元数据的字典
        """
        try:
            # 提取文本和元数据
            extraction_result = PDFUtils.extract_text_and_metadata(pdf_path)
            
            if not extraction_result['success']:
                return extraction_result
            
            # 获取页面信息
            pages = extraction_result['pages']
            
            # 分块处理
            chunks = PDFUtils.chunk_text_by_pages(pages, chunk_size, overlap)
            
            return {
                'text': extraction_result['text'],
                'chunks': chunks,
                'metadata': extraction_result['metadata'],
                'total_pages': len(pages),
                'success': True
            }
            
        except Exception as e:
            logging.error(f"提取文本和分块错误: {str(e)}")
            return {
                'text': '',
                'chunks': [],
                'metadata': {},
                'total_pages': 0,
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def chunk_text_by_pages(pages: List[Dict[str, Any]], 
                          chunk_size: int = None, 
                          overlap: int = None) -> List[Dict[str, Any]]:
        """按 token 分块（优先tiktoken，否则字符近似），逐页处理
        
        Args:
            pages: 页文本列表
            chunk_size: 分块大小（token）
            overlap: 重叠大小（token）
            
        Returns:
            分块结果列表，每个分块包含chunk_text、chunk_length(=token数)等
        """
        if chunk_size is None:
            chunk_size = GlobalConfig.CHUNK_SIZE
        if overlap is None:
            overlap = GlobalConfig.CHUNK_OVERLAP
        
        actual_chunk_size = chunk_size
        actual_overlap = overlap
        tokenizer_type, _ = PDFUtils._get_tokenizer()
        
        chunks: List[Dict[str, Any]] = []
        
        for page in pages:
            text = page['text']
            if not text.strip():
                continue

            if tokenizer_type == 'tiktoken':
                page_chunks = PDFUtils._chunk_tokens_with_tiktoken(
                    text, actual_chunk_size, actual_overlap
                )
            else:
                page_chunks = PDFUtils._chunk_text_approx(
                    text, actual_chunk_size, actual_overlap
                )

            for chunk in page_chunks:
                chunk['page_number'] = page['page_num']
                chunk['chunk_index'] = len(chunks)
                chunks.append(chunk)
        
        return chunks

    @staticmethod
    def chunk_plain_text(text: str,
                         chunk_size: int = None,
                         overlap: int = None) -> List[str]:
        """对整段文本进行token分块（无分页），返回chunk文本列表。"""
        pages = [{'text': text, 'page_num': 1}]
        chunk_dicts = PDFUtils.chunk_text_by_pages(pages, chunk_size, overlap)
        return [c['chunk_text'] for c in chunk_dicts]
    
    @staticmethod
    def extract_basic_metadata(pdf_path: str) -> Dict[str, Any]:
        """
        快速提取基本元数据（用于验证）
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            基本元数据
        """
        doc = None
        try:
            doc = fitz.open(pdf_path)
            metadata, total_pages = PDFUtils._snapshot_document_state(doc)
            
            return {
                'title': PDFUtils.clean_title(metadata.get('title', '')),
                'author': metadata.get('author', ''),
                'pages': total_pages,
                'file_size': os.path.getsize(pdf_path)
            }
        except Exception as e:
            return {
                'title': 'Error',
                'author': '',
                'pages': 0,
                'file_size': 0,
                'error': str(e)
            }
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    logging.debug("关闭PDF文档失败: %s", pdf_path, exc_info=True)
    
    @staticmethod
    def assess_text_quality(text: str) -> Dict[str, Any]:
        """
        评估提取文本的质量
        
        Args:
            text: 提取的文本内容
            
        Returns:
            质量评估指标字典
        """
        if not text or len(text.strip()) == 0:
            return {
                'overall_quality': 0.0,
                'character_count': 0,
                'has_content': False,
                'warnings': ['文本为空']
            }
        
        metrics = {
            'character_count': len(text),
            'non_empty_ratio': len(text.strip()) / len(text) if text else 0,
            'has_excessive_whitespace': len(re.findall(r'\s{5,}', text)) > 10,
            'has_gibberish_patterns': False,
            'line_count': len(text.split('\n')),
            'avg_line_length': len(text) / max(len(text.split('\n')), 1),
            'has_reasonable_punctuation': bool(re.search(r'[.!?]{1,2}', text)),
            'encoding_issues': bool(re.search(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', text)),
        }
        
        # 检测可能的乱码模式（连续的不可打印字符或异常字符序列）
        non_printable_ratio = len(re.findall(r'[^\x20-\x7E\n\t]', text)) / len(text) if text else 0
        metrics['non_printable_ratio'] = non_printable_ratio
        metrics['has_gibberish_patterns'] = non_printable_ratio > 0.3  # 如果超过30%是不可打印字符
        
        # 检测异常短的单词（可能是提取问题）
        words = text.split()
        if words:
            short_words_ratio = len([w for w in words if len(w) == 1]) / len(words)
            metrics['short_words_ratio'] = short_words_ratio
            metrics['has_excessive_single_chars'] = short_words_ratio > 0.2
        
        # 生成警告
        warnings = []
        if metrics['character_count'] < 100:
            warnings.append('文本长度过短，可能是提取失败')
        if metrics['has_excessive_whitespace']:
            warnings.append('检测到大量空白字符')
        if metrics['has_gibberish_patterns']:
            warnings.append('检测到可能的乱码或编码问题')
        if metrics['encoding_issues']:
            warnings.append('检测到编码问题字符')
        if metrics.get('has_excessive_single_chars', False):
            warnings.append('检测到异常的单字符单词')
        if not metrics['has_reasonable_punctuation'] and metrics['character_count'] > 500:
            warnings.append('文本缺少标点符号，可能提取不完整')
        
        # 计算总体质量分数（0-1）
        quality_factors = []
        
        # 内容长度分数（至少100字符为合格）
        length_score = min(1.0, metrics['character_count'] / 1000)
        quality_factors.append(length_score * 0.2)
        
        # 非空字符比例（应该接近1）
        non_empty_score = metrics['non_empty_ratio']
        quality_factors.append(non_empty_score * 0.15)
        
        # 可打印字符比例（应该较高）
        printable_score = 1.0 - min(1.0, metrics['non_printable_ratio'] * 2)
        quality_factors.append(printable_score * 0.25)
        
        # 文本结构分数（有合理的标点和长度）
        structure_score = 0.5
        if metrics['has_reasonable_punctuation']:
            structure_score += 0.2
        if 20 < metrics['avg_line_length'] < 150:  # 合理的行长度
            structure_score += 0.2
        if not metrics['has_excessive_whitespace']:
            structure_score += 0.1
        quality_factors.append(structure_score * 0.25)
        
        # 异常模式惩罚
        penalty = 0.0
        if metrics['has_gibberish_patterns']:
            penalty += 0.3
        if metrics['encoding_issues']:
            penalty += 0.2
        if metrics.get('has_excessive_single_chars', False):
            penalty += 0.15
        
        overall_quality = max(0.0, min(1.0, sum(quality_factors) - penalty))
        
        return {
            'overall_quality': overall_quality,
            'metrics': metrics,
            'warnings': warnings,
            'has_content': metrics['character_count'] > 0,
            'quality_level': (
                'excellent' if overall_quality >= 0.9 else
                'good' if overall_quality >= 0.7 else
                'fair' if overall_quality >= 0.5 else
                'poor' if overall_quality >= 0.3 else
                'very_poor'
            )
        }
    
    @staticmethod
    def extract_text_with_quality_assessment(pdf_path: str, 
                                            exclude_references: bool = True) -> Dict[str, Any]:
        """
        提取PDF文本并进行质量评估（增强版本）
        
        Args:
            pdf_path: PDF文件路径
            exclude_references: 是否排除参考文献
            
        Returns:
            包含文本、质量评估和元数据的字典
        """
        try:
            # 使用现有的提取方法
            extraction_result = PDFUtils.extract_text_and_metadata(pdf_path)
            
            if not extraction_result['success']:
                return {
                    'success': False,
                    'error': extraction_result.get('error', '提取失败'),
                    'quality_assessment': {
                        'overall_quality': 0.0,
                        'warnings': ['提取失败']
                    }
                }
            
            # 提取文本
            extracted_text = extraction_result['text']
            
            # 如果不需要排除参考文献，重新提取完整文本
            if not exclude_references:
                doc = None
                try:
                    doc = fitz.open(pdf_path)
                    _, total_pages = PDFUtils._snapshot_document_state(doc)
                    full_text = ""
                    for page_num in range(total_pages):
                        page = doc[page_num]
                        full_text += page.get_text() + "\n"
                    extracted_text = full_text
                except Exception as e:
                    logging.warning(f"提取完整文本失败，使用过滤后的文本: {e}")
                finally:
                    if doc is not None:
                        try:
                            doc.close()
                        except Exception:
                            logging.debug("关闭PDF文档失败: %s", pdf_path, exc_info=True)
            
            # 进行质量评估
            quality_assessment = PDFUtils.assess_text_quality(extracted_text)
            
            # 合并结果
            result = {
                'success': True,
                'text': extracted_text,
                'quality_assessment': quality_assessment,
                'metadata': extraction_result['metadata'],
                'pages': extraction_result.get('pages', []),
                'total_pages': extraction_result['metadata'].get('total_pages', 0),
                'text_length': len(extracted_text),
                'references_excluded': exclude_references
            }
            
            # 如果质量较差，添加建议
            if quality_assessment['overall_quality'] < 0.5:
                suggestions = []
                if quality_assessment['metrics'].get('has_gibberish_patterns'):
                    suggestions.append('考虑使用OCR处理（可能是扫描版PDF）')
                if quality_assessment['metrics']['character_count'] < 100:
                    suggestions.append('文本提取可能不完整，检查PDF是否为扫描版或加密')
                if quality_assessment['metrics'].get('encoding_issues'):
                    suggestions.append('检测到编码问题，尝试使用不同的提取方法')
                
                result['improvement_suggestions'] = suggestions
            
            return result
            
        except Exception as e:
            logging.error(f"PDF文本提取和质量评估错误: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'quality_assessment': {
                    'overall_quality': 0.0,
                    'warnings': [f'处理失败: {str(e)}']
                }
            }

# 设置统一日志
logging.basicConfig(
    level=getattr(logging, GlobalConfig.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
