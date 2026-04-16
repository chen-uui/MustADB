#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地外有机质数据库系统 - 启动器
集成语义搜索 + 大语言模型 + 文档管理
"""

import os
import sys
import subprocess
import time
import webbrowser
import requests
from pathlib import Path
from datetime import datetime

class AstrobiologySystem:
    def __init__(self):
        self.base_dir = Path(__file__).parent.absolute()
        self.config = {
            'weaviate_url': f"http://{os.getenv('WEAVIATE_HOST', 'localhost')}:{os.getenv('WEAVIATE_PORT', '8080')}",
            't2v_url': f"http://{os.getenv('T2V_HOST', 'localhost')}:{os.getenv('T2V_PORT', '9090')}",                     
            'backend_url': f"http://{os.getenv('BACKEND_HOST', 'localhost')}:{os.getenv('BACKEND_PORT', '8000')}",
            'frontend_url': f"http://{os.getenv('FRONTEND_HOST', 'localhost')}:{os.getenv('FRONTEND_PORT', '5173')}",
            'ollama_url': f"http://{os.getenv('OLLAMA_HOST', 'localhost')}:{os.getenv('OLLAMA_PORT', '11434')}",
        }
        self.service_status = {}
        
    def check_gpu_availability(self):
        """检查GPU可用性"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                print(f"[OK] GPU: {gpu_name} ({gpu_memory:.1f}GB)")
                return True
            else:
                print("[OK] 使用CPU模式")
                return False
        except ImportError:
            print("[OK] PyTorch未安装，使用CPU模式")
            return False
    
    def print_banner(self):
        """显示启动横幅"""
        print("\n" + "="*60)
        print("[*] 地外有机质数据库系统")
        print("="*60)
        print(f"[OK] 目录: {self.base_dir}")
        print(f"[OK] 时间: {datetime.now().strftime('%H:%M:%S')}")
    
    def check_port(self, port):
        """检查端口是否可用"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    def wait_for_service(self, name, url, timeout=120):
        """等待服务就绪"""
        print(f"⏳ 等待 {name} 启动...", end="", flush=True)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f" [OK] {int(time.time() - start_time)}秒")
                    return True
            except requests.exceptions.RequestException:
                pass
            except Exception:
                pass
            time.sleep(2)
            print(".", end="", flush=True)
        
        print(f" [OK] 超时")
        return False
    
    def start_docker_services(self):
        """启动Docker服务（Weaviate + Transformers）"""
        print("\n🐳 检查Docker服务状态...")
        
        # 检查Docker是否运行
        try:
            subprocess.run(['docker', 'info'], capture_output=True, check=True)
        except:
            print("[OK] Docker未运行，请先启动Docker Desktop")
            return False
        
        # 检查容器状态
        try:
            result = subprocess.run(['docker-compose', '-f', 'docker-compose.yml', 'ps', '-q'],
                               capture_output=True, text=True, cwd=self.base_dir)
            
            # 检查Weaviate端口
            weaviate_port = int(os.getenv('WEAVIATE_PORT', '8080'))
            weaviate_ready = self.check_port(weaviate_port)
            t2v_ready = self.check_port(9090)
            
            if weaviate_ready and t2v_ready:
                weaviate_port = os.getenv('WEAVIATE_PORT', '8080')
                t2v_port = os.getenv('T2V_PORT', '9090')
                print(f"[OK] Docker服务已运行 (Weaviate:{weaviate_port}, T2V:{t2v_port})")
                return True
            else:
                print("🔄 重新启动Docker服务...")
                
        except Exception as e:
            print(f"[OK] Docker检查失败: {e}")
        
        # 启动所有服务
        compose_file = self.base_dir / "docker-compose.yml"
        if compose_file.exists():
            # 先停止可能存在的旧服务
            subprocess.run(['docker-compose', '-f', str(compose_file), 'down'], 
                          capture_output=True, cwd=self.base_dir)
            
            # 启动服务
            cmd = f'docker-compose -f "{compose_file}" up -d'
            print(f"   运行: {cmd}")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("[OK] Docker服务已启动 (后台运行)")
                time.sleep(5)  # 等待服务完全启动
                return True
            else:
                print(f"[OK] 启动失败: {result.stderr}")
                return False
        else:
            print("[OK] 找不到docker-compose.yml")
            return False
    
    def check_ollama_model(self):
        """检查Ollama模型是否已安装"""
        print("🤖 检查Ollama模型状态...")
        
        try:
            # 检查Ollama服务是否运行
            response = requests.get("http://localhost:11434/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                if 'llama3.1:8b-instruct-q4_K_M' in model_names:
                    print("[OK] Ollama模型 llama3.1:8b-instruct-q4_K_M 已就绪")
                    return True
                else:
                    print("[OK] Ollama模型 llama3.1:8b-instruct-q4_K_M 未找到")
                    print("   请运行: ollama pull llama3.1:8b-instruct-q4_K_M")
                    return False
            else:
                print("[OK] Ollama服务未运行")
                print("   请先启动Ollama: ollama serve")
                return False
                
        except requests.exceptions.RequestException:
            print("[OK] Ollama服务未运行或无法连接")
            print("   请先启动Ollama: ollama serve")
            return False
        except Exception as e:
            print(f"[OK] 检查Ollama模型时出错: {e}")
            return False
    
    def check_ollama_service(self):
        """检查Ollama服务状态"""
        print("\n🤖 检查Ollama服务...")
        
        # 检查Ollama服务是否运行
        if self.wait_for_service("Ollama", "http://localhost:11434/api/tags", 30):
            print("[OK] Ollama服务已就绪")
            return True
        else:
            print("[OK] Ollama服务未运行")
            print("   请先启动Ollama: ollama serve")
            return False
    
    def start_backend(self):
        """启动Django后端"""
        print("\n[OK] 启动Django后端...")
        
        backend_dir = self.base_dir / "backend"
        if not backend_dir.exists():
            print("[OK] 找不到backend目录")
            return False
        
        python_exe = sys.executable
        # 使用安全的引号与转义，避免嵌套引号导致命令解析失败
        cmd = f'start "" cmd /k cd /d "{backend_dir}" ^&^& "{python_exe}" manage.py runserver 8000'
        subprocess.Popen(cmd, shell=True)
        return True
    
    def start_frontend(self):
        """启动Vue前端"""
        print("\n🎨 启动Vue前端...")
        
        frontend_dir = self.base_dir / "astro_frontend"
        if not frontend_dir.exists():
            print("[OK] 找不到astro_frontend目录")
            return False
        
        npm_exe = "npm.cmd" if os.name == 'nt' else "npm"
        
        package_json = frontend_dir / "package.json"
        if package_json.exists():
            # 使用安全的引号与转义
            cmd = f'start "" cmd /k cd /d "{frontend_dir}" ^&^& {npm_exe} run dev -- --port 5173'
            subprocess.Popen(cmd, shell=True)
            return True
        else:
            print("[OK] 找不到package.json")
            return False
    

    
    def check_all_services(self):
        """检查所有服务状态"""
        print("\n[OK] 检查服务状态...")
        
        services = [
            ('Weaviate', f"{self.config['weaviate_url']}/v1/meta", 'api'),
            ('T2V-Transformers', f"{self.config['t2v_url']}/meta", 'api'),
            ('Ollama', f"{self.config['ollama_url']}/api/tags", 'api'),
            ('Backend', f"{self.config['backend_url']}/admin/", 'api'),  # 检查Django管理页面
            ('Frontend', self.config['frontend_url'], 'port')
        ]
        
        all_ready = True
        for name, url, check_type in services:
            port = int(url.split(':')[2].split('/')[0])
            
            # 首先检查端口
            if not self.check_port(port):
                # 再等待3秒重试
                time.sleep(3)
                if not self.check_port(port):
                    self.service_status[name] = 'failed'
                    print(f"[OK] {name}: 端口未开放")
                    all_ready = False
                    continue
            
            # 对于API端点，进行HTTP检查
            if check_type == 'api':
                # 特殊处理后端，使用更短的超时
                timeout = 15 if name == 'Backend' else 30
                if self.wait_for_service(name, url, timeout=timeout):
                    self.service_status[name] = 'ready'
                    print(f"[OK] {name}: API端点正常")
                else:
                    # 后端可能还在启动，标记为警告而非失败
                    if name == 'Backend':
                        print(f"[OK] {name}: 可能仍在启动中")
                        self.service_status[name] = 'starting'
                    else:
                        self.service_status[name] = 'failed'
                        all_ready = False
            else:
                # 端口检查通过即可
                self.service_status[name] = 'ready'
                print(f"[OK] {name}: 端口已开放")
        
        return True  # 允许部分服务失败继续运行
    

    
    def show_final_info(self):
        """显示最终信息"""
        print("\n" + "="*40)
        print("🎉 系统启动完成")
        print("="*40)
        
        print(f"[OK] 主界面: {self.config['frontend_url']}")
        print(f"[OK] 后端: {self.config['backend_url']}")
        print(f"🤖 大模型: {self.config['ollama_url']} (llama3.1:8b-instruct-q4_K_M)")
        
        # 显示服务状态摘要
        starting_services = [k for k, v in self.service_status.items() if v == 'starting']
        if starting_services:
            print(f"\n⏳ 以下服务可能仍在启动: {', '.join(starting_services)}")
            print("   请等待30-60秒后刷新页面")
        
        # 自动打开浏览器
        try:
            webbrowser.open(self.config['frontend_url'])
        except:
            pass
    
    def run(self):
        """主运行函数"""
        self.print_banner()
        
        try:
            # 检查Ollama模型
            if not self.check_ollama_model():
                return False
            
            # 启动Docker服务
            if not self.start_docker_services():
                return False
            
            # 检查Ollama服务
            if not self.check_ollama_service():
                return False
            
            # 启动后端
            if not self.start_backend():
                return False
            
            # 启动前端
            if not self.start_frontend():
                return False
            
            # 等待后端完全启动
            time.sleep(3)
            
            # 检查服务状态
            self.check_all_services()
            
            # 显示最终信息
            self.show_final_info()
            
            return True
            
        except KeyboardInterrupt:
            print("\n🛑 用户中断")
            return False
        except Exception as e:
            print(f"\n[OK] 启动失败: {e}")
            return False

if __name__ == "__main__":
    system = AstrobiologySystem()
    system.run()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 系统关闭中...")
        print("[OK] 已退出地外有机质数据库系统")