"""
直接文档处理器 - 核心类
负责协调整个文档处理流程
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from .llm_analyzer import LLMAnalyzer
from .data_extractor import DataExtractor
from .result_validator import ResultValidator
from .utils import extract_pdf_text

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """处理结果"""
    document_path: str
    processing_time: float
    results: 'ValidatedResult'
    confidence_score: float
    extraction_method: str = "direct_processing"
    timestamp: datetime = field(default_factory=datetime.now)


class DirectDocumentProcessor:
    """直接文档处理器 - 核心类"""
    
    def __init__(self):
        """初始化处理器"""
        self.llm_analyzer = LLMAnalyzer()
        self.data_extractor = DataExtractor()
        self.validator = ResultValidator()
        
        logger.info("DirectDocumentProcessor initialized")
    
    def process_document(self, pdf_path: str, options: Dict[str, Any] = None) -> ProcessingResult:
        """
        处理单个PDF文档
        
        Args:
            pdf_path: PDF文件路径
            options: 处理选项
            
        Returns:
            ProcessingResult: 处理结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting document processing: {pdf_path}")
            
            # 1. 提取完整文本
            logger.info("Extracting complete text from PDF")
            full_text = self.extract_complete_text(pdf_path)
            
            if not full_text or len(full_text.strip()) < 100:
                raise ValueError("PDF text extraction failed or text too short")
            
            logger.info(f"Extracted text length: {len(full_text)} characters")
            
            # 2. LLM分析
            logger.info("Starting LLM analysis")
            analysis_result = self.llm_analyzer.analyze_document(full_text, options)
            
            # 3. 数据提取
            logger.info("Extracting structured data")
            extracted_data = self.data_extractor.extract_structured_data(analysis_result)
            
            # 4. 结果验证
            logger.info("Validating results")
            validated_result = self.validator.validate_result(extracted_data)
            
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                document_path=pdf_path,
                processing_time=processing_time,
                results=validated_result,
                confidence_score=self.calculate_confidence(validated_result)
            )
            
            logger.info(f"Document processing completed in {processing_time:.2f} seconds")
            logger.info(f"Confidence score: {result.confidence_score:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {pdf_path}: {str(e)}")
            raise
    
    def extract_complete_text(self, pdf_path: str) -> str:
        """
        提取PDF的完整文本
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            str: 提取的文本内容
        """
        try:
            return extract_pdf_text(pdf_path)
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {str(e)}")
            raise
    
    def calculate_confidence(self, validated_result: 'ValidatedResult') -> float:
        """
        计算处理结果的置信度
        
        Args:
            validated_result: 验证后的结果
            
        Returns:
            float: 置信度分数 (0.0 - 1.0)
        """
        try:
            # 基于验证检查结果计算置信度
            validation_checks = validated_result.validation_checks
            
            if not validation_checks:
                return 0.5  # 默认中等置信度
            
            # 计算验证通过率
            passed_checks = sum(1 for check in validation_checks if check.passed)
            total_checks = len(validation_checks)
            
            if total_checks == 0:
                return 0.5
            
            base_confidence = passed_checks / total_checks
            
            # 基于数据完整性调整置信度
            data_completeness = self._assess_data_completeness(validated_result.data)
            
            # 综合置信度计算
            final_confidence = (base_confidence * 0.7) + (data_completeness * 0.3)
            
            return min(max(final_confidence, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5
    
    def _assess_data_completeness(self, data: 'StructuredData') -> float:
        """
        评估数据完整性
        
        Args:
            data: 结构化数据
            
        Returns:
            float: 数据完整性分数 (0.0 - 1.0)
        """
        try:
            completeness_scores = []
            
            # 检查陨石数据完整性
            meteorite_data = data.meteorite_data
            meteorite_completeness = 0.0
            if meteorite_data and len(meteorite_data) > 0:
                required_fields = ['name', 'classification', 'location']
                filled_fields = sum(1 for field in required_fields if field in meteorite_data and meteorite_data[field])
                meteorite_completeness = filled_fields / len(required_fields)
            else:
                # 如果没有陨石数据，给予基础分数
                meteorite_completeness = 0.3
            completeness_scores.append(meteorite_completeness)
            
            # 检查有机化合物数据完整性
            organic_data = data.organic_compounds
            organic_completeness = 0.0
            if organic_data and isinstance(organic_data, dict) and len(organic_data) > 0:
                organic_completeness = 0.8 if len(organic_data) > 0 else 0.2
            else:
                # 如果没有有机化合物数据，给予基础分数
                organic_completeness = 0.3
            completeness_scores.append(organic_completeness)
            
            # 检查科学洞察完整性
            insights_data = data.scientific_insights
            insights_completeness = 0.0
            if insights_data and isinstance(insights_data, dict):
                insights_completeness = 0.8 if len(insights_data) > 0 else 0.2
            completeness_scores.append(insights_completeness)
            
            # 计算平均完整性
            return sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.5
            
        except Exception as e:
            logger.error(f"Error assessing data completeness: {str(e)}")
            return 0.5
    
    def batch_process_documents(self, pdf_paths: list, options: Dict[str, Any] = None) -> list:
        """
        批量处理多个PDF文档
        
        Args:
            pdf_paths: PDF文件路径列表
            options: 处理选项
            
        Returns:
            list: 处理结果列表
        """
        results = []
        
        logger.info(f"Starting batch processing of {len(pdf_paths)} documents")
        
        for i, pdf_path in enumerate(pdf_paths):
            try:
                logger.info(f"Processing document {i+1}/{len(pdf_paths)}: {pdf_path}")
                result = self.process_document(pdf_path, options)
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to process document {pdf_path}: {str(e)}")
                # 创建错误结果
                error_result = ProcessingResult(
                    document_path=pdf_path,
                    processing_time=0.0,
                    results=None,
                    confidence_score=0.0
                )
                results.append(error_result)
        
        logger.info(f"Batch processing completed. {len(results)} results generated")
        return results
