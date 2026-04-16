"""
性能优化模块 - 优化直接处理系统的性能
"""

import logging
import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from functools import lru_cache, wraps
import psutil
import gc

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    processing_time: float
    memory_usage: float
    cpu_usage: float
    file_size: int
    text_length: int
    confidence_score: float


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        """初始化性能优化器"""
        self.cache_size = 100
        self.max_workers = 4
        self.memory_threshold = 0.8  # 80%内存使用率阈值
        self.cpu_threshold = 0.8     # 80%CPU使用率阈值
        
        logger.info("PerformanceOptimizer initialized")
    
    def monitor_system_resources(self) -> Dict[str, float]:
        """监控系统资源"""
        try:
            # 获取内存使用情况
            memory = psutil.virtual_memory()
            memory_usage = memory.percent / 100.0
            
            # 获取CPU使用情况
            cpu_usage = psutil.cpu_percent(interval=1) / 100.0
            
            # 获取磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent / 100.0
            
            return {
                'memory_usage': memory_usage,
                'cpu_usage': cpu_usage,
                'disk_usage': disk_usage,
                'available_memory': memory.available,
                'total_memory': memory.total
            }
            
        except Exception as e:
            logger.error(f"Error monitoring system resources: {str(e)}")
            return {
                'memory_usage': 0.0,
                'cpu_usage': 0.0,
                'disk_usage': 0.0,
                'available_memory': 0,
                'total_memory': 0
            }
    
    def should_optimize_memory(self) -> bool:
        """判断是否需要优化内存"""
        resources = self.monitor_system_resources()
        return resources['memory_usage'] > self.memory_threshold
    
    def should_optimize_cpu(self) -> bool:
        """判断是否需要优化CPU"""
        resources = self.monitor_system_resources()
        return resources['cpu_usage'] > self.cpu_threshold
    
    def optimize_memory(self):
        """优化内存使用"""
        try:
            # 强制垃圾回收
            gc.collect()
            
            # 清理缓存
            self.clear_caches()
            
            logger.info("Memory optimization completed")
            
        except Exception as e:
            logger.error(f"Error optimizing memory: {str(e)}")
    
    def optimize_cpu(self):
        """优化CPU使用"""
        try:
            # 调整工作线程数
            if self.should_optimize_cpu():
                self.max_workers = max(1, self.max_workers - 1)
                logger.info(f"Reduced max workers to {self.max_workers}")
            
        except Exception as e:
            logger.error(f"Error optimizing CPU: {str(e)}")
    
    def clear_caches(self):
        """清理缓存"""
        try:
            # 清理LRU缓存
            if hasattr(self, '_cached_functions'):
                for func in self._cached_functions:
                    func.cache_clear()
            
            logger.info("Caches cleared")
            
        except Exception as e:
            logger.error(f"Error clearing caches: {str(e)}")
    
    def get_optimal_workers(self) -> int:
        """获取最优工作线程数"""
        try:
            resources = self.monitor_system_resources()
            
            # 基于CPU核心数和内存使用情况计算最优线程数
            cpu_count = psutil.cpu_count()
            memory_usage = resources['memory_usage']
            
            if memory_usage > 0.8:
                return max(1, cpu_count // 2)
            elif memory_usage > 0.6:
                return max(1, cpu_count * 3 // 4)
            else:
                return cpu_count
                
        except Exception as e:
            logger.error(f"Error getting optimal workers: {str(e)}")
            return 2
    
    def batch_process_optimized(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化的批量处理"""
        try:
            # 获取最优工作线程数
            optimal_workers = self.get_optimal_workers()
            
            # 使用线程池进行并行处理
            with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
                futures = []
                for task in tasks:
                    future = executor.submit(self._process_single_task, task)
                    futures.append(future)
                
                # 等待所有任务完成
                results = []
                for future in futures:
                    try:
                        result = future.result(timeout=300)  # 5分钟超时
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Task failed: {str(e)}")
                        results.append({'error': str(e)})
                
                return results
                
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            return [{'error': str(e)} for _ in tasks]
    
    def _process_single_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个任务"""
        try:
            # 这里应该调用实际的文档处理逻辑
            # 为了演示，我们返回一个模拟结果
            return {
                'task_id': task.get('task_id'),
                'status': 'completed',
                'processing_time': 10.0,
                'confidence_score': 0.85
            }
            
        except Exception as e:
            logger.error(f"Error processing single task: {str(e)}")
            return {
                'task_id': task.get('task_id'),
                'status': 'failed',
                'error': str(e)
            }


def performance_monitor(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            processing_time = end_time - start_time
            memory_delta = end_memory - start_memory
            
            logger.info(f"Function {func.__name__} executed in {processing_time:.2f}s, "
                       f"memory delta: {memory_delta / 1024 / 1024:.2f}MB")
    
    return wrapper


def cache_result(maxsize: int = 128):
    """结果缓存装饰器"""
    def decorator(func):
        @lru_cache(maxsize=maxsize)
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


class AsyncProcessor:
    """异步处理器"""
    
    def __init__(self):
        """初始化异步处理器"""
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.optimizer = PerformanceOptimizer()
        
        logger.info("AsyncProcessor initialized")
    
    async def process_document_async(self, document_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """异步处理文档"""
        try:
            # 在线程池中执行CPU密集型任务
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._process_document_sync,
                document_path,
                options
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in async document processing: {str(e)}")
            return {'error': str(e)}
    
    def _process_document_sync(self, document_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """同步处理文档（在线程池中执行）"""
        try:
            # 这里应该调用实际的文档处理逻辑
            # 为了演示，我们返回一个模拟结果
            time.sleep(1)  # 模拟处理时间
            
            return {
                'document_path': document_path,
                'processing_time': 1.0,
                'confidence_score': 0.85,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Error in sync document processing: {str(e)}")
            return {'error': str(e)}
    
    async def batch_process_async(self, document_paths: List[str], options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """异步批量处理"""
        try:
            # 创建任务列表
            tasks = [
                self.process_document_async(path, options)
                for path in document_paths
            ]
            
            # 并行执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        'document_path': document_paths[i],
                        'error': str(result),
                        'status': 'failed'
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Error in async batch processing: {str(e)}")
            return [{'error': str(e)} for _ in document_paths]
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)


class MemoryManager:
    """内存管理器"""
    
    def __init__(self):
        """初始化内存管理器"""
        self.memory_threshold = 0.8
        self.cleanup_interval = 60  # 60秒清理一次
        self.last_cleanup = time.time()
        
        logger.info("MemoryManager initialized")
    
    def check_memory_usage(self) -> bool:
        """检查内存使用情况"""
        try:
            memory = psutil.virtual_memory()
            usage = memory.percent / 100.0
            
            if usage > self.memory_threshold:
                logger.warning(f"High memory usage: {usage:.2%}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking memory usage: {str(e)}")
            return False
    
    def cleanup_memory(self):
        """清理内存"""
        try:
            current_time = time.time()
            
            # 检查是否需要清理
            if current_time - self.last_cleanup < self.cleanup_interval:
                return
            
            # 强制垃圾回收
            gc.collect()
            
            # 记录清理时间
            self.last_cleanup = current_time
            
            logger.info("Memory cleanup completed")
            
        except Exception as e:
            logger.error(f"Error cleaning up memory: {str(e)}")
    
    def optimize_memory_usage(self):
        """优化内存使用"""
        try:
            if self.check_memory_usage():
                self.cleanup_memory()
                
                # 如果内存使用仍然很高，可以考虑其他优化策略
                memory = psutil.virtual_memory()
                if memory.percent / 100.0 > self.memory_threshold:
                    logger.warning("Memory usage still high after cleanup")
                    
        except Exception as e:
            logger.error(f"Error optimizing memory usage: {str(e)}")


class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        """初始化性能分析器"""
        self.metrics = []
        
        logger.info("PerformanceProfiler initialized")
    
    def start_profiling(self):
        """开始性能分析"""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss
        self.start_cpu = psutil.cpu_percent()
    
    def stop_profiling(self) -> PerformanceMetrics:
        """停止性能分析并返回指标"""
        try:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            end_cpu = psutil.cpu_percent()
            
            metrics = PerformanceMetrics(
                processing_time=end_time - self.start_time,
                memory_usage=(end_memory - self.start_memory) / 1024 / 1024,  # MB
                cpu_usage=end_cpu,
                file_size=0,  # 需要从外部传入
                text_length=0,  # 需要从外部传入
                confidence_score=0.0  # 需要从外部传入
            )
            
            self.metrics.append(metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Error stopping profiling: {str(e)}")
            return PerformanceMetrics(0, 0, 0, 0, 0, 0.0)
    
    def get_average_metrics(self) -> PerformanceMetrics:
        """获取平均性能指标"""
        if not self.metrics:
            return PerformanceMetrics(0, 0, 0, 0, 0, 0.0)
        
        avg_processing_time = sum(m.processing_time for m in self.metrics) / len(self.metrics)
        avg_memory_usage = sum(m.memory_usage for m in self.metrics) / len(self.metrics)
        avg_cpu_usage = sum(m.cpu_usage for m in self.metrics) / len(self.metrics)
        avg_file_size = sum(m.file_size for m in self.metrics) / len(self.metrics)
        avg_text_length = sum(m.text_length for m in self.metrics) / len(self.metrics)
        avg_confidence_score = sum(m.confidence_score for m in self.metrics) / len(self.metrics)
        
        return PerformanceMetrics(
            processing_time=avg_processing_time,
            memory_usage=avg_memory_usage,
            cpu_usage=avg_cpu_usage,
            file_size=avg_file_size,
            text_length=avg_text_length,
            confidence_score=avg_confidence_score
        )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self.metrics:
            return {'message': 'No metrics available'}
        
        avg_metrics = self.get_average_metrics()
        
        return {
            'total_operations': len(self.metrics),
            'average_processing_time': avg_metrics.processing_time,
            'average_memory_usage': avg_metrics.memory_usage,
            'average_cpu_usage': avg_metrics.cpu_usage,
            'average_file_size': avg_metrics.file_size,
            'average_text_length': avg_metrics.text_length,
            'average_confidence_score': avg_metrics.confidence_score,
            'performance_trend': self._calculate_trend()
        }
    
    def _calculate_trend(self) -> str:
        """计算性能趋势"""
        if len(self.metrics) < 2:
            return 'insufficient_data'
        
        recent_metrics = self.metrics[-5:]  # 最近5次操作
        older_metrics = self.metrics[:-5] if len(self.metrics) > 5 else self.metrics[:-len(recent_metrics)]
        
        if not older_metrics:
            return 'insufficient_data'
        
        recent_avg_time = sum(m.processing_time for m in recent_metrics) / len(recent_metrics)
        older_avg_time = sum(m.processing_time for m in older_metrics) / len(older_metrics)
        
        if recent_avg_time < older_avg_time * 0.9:
            return 'improving'
        elif recent_avg_time > older_avg_time * 1.1:
            return 'degrading'
        else:
            return 'stable'
