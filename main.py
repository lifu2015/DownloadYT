import sys
import os
import cv2
import numpy as np
import threading
from moviepy.editor import VideoFileClip
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLineEdit, QPushButton, QTextEdit,
                           QComboBox, QLabel, QMessageBox, QSlider, QFileDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex
from PyQt6.QtGui import QImage, QPixmap
import yt_dlp
import time
import subprocess

class VideoDownloader(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, url, download_dir):
        super().__init__()
        self.url = url
        self.download_dir = download_dir
        self.selected_format = None
        self.preferred_resolution = None

    def check_ffmpeg(self):
        """检查是否安装了FFmpeg"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_format_for_resolution(self):
        """获取指定分辨率的视频格式"""
        try:
            self.progress.emit("正在获取可用的视频格式...")
            ydl_opts = {
                'quiet': True,
                'no_warnings': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                formats = []
                
                # 只收集视频格式，音频将单独处理
                for f in info['formats']:
                    if f.get('vcodec') != 'none' and f.get('acodec') == 'none':  # 只要纯视频流
                        format_id = f['format_id']
                        height = f.get('height', 0)
                        formats.append({
                            'format_id': format_id,
                            'height': height
                        })
                
                # 如果指定了分辨率，选择最接近的
                if self.preferred_resolution and formats:
                    target_height = int(self.preferred_resolution.replace('p', ''))
                    closest_format = min(formats, 
                                      key=lambda x: abs(x.get('height', 0) - target_height))
                    # 使用格式ID+最佳音频
                    self.selected_format = f"{closest_format['format_id']}+bestaudio/best"
                    self.progress.emit(f"已选择分辨率: {closest_format['height']}p")
                else:
                    # 如果没有指定分辨率或没找到合适格式，使用best
                    self.selected_format = "bestvideo+bestaudio/best"
                    self.progress.emit("已选择最佳可用格式")
                
        except Exception as e:
            error_msg = f"获取视频格式失败: {str(e)}"
            self.error.emit(error_msg)
            self.progress.emit(error_msg)

    def run(self):
        try:
            self.progress.emit("开始下载视频...")
            
            # 检查FFmpeg
            if not self.check_ffmpeg():
                error_msg = (
                    "未检测到FFmpeg。请按照以下步骤安装：\n"
                    "1. 访问 https://github.com/BtbN/FFmpeg-Builds/releases\n"
                    "2. 下载 ffmpeg-master-latest-win64-gpl.zip\n"
                    "3. 解压文件\n"
                    "4. 将解压后的 ffmpeg-master-latest-win64-gpl\\bin 目录添加到系统环境变量\n"
                    "5. 重启应用程序"
                )
                self.error.emit(error_msg)
                self.progress.emit(error_msg)
                return

            # 获取合适的格式
            self.get_format_for_resolution()
            
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)
                self.progress.emit(f"创建下载目录: {self.download_dir}")
            
            # 添加时间戳到文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_template = os.path.join(
                self.download_dir, 
                f'%(title)s_{timestamp}.%(ext)s'
            )
            
            ydl_opts = {
                'format': self.selected_format,
                'outtmpl': output_template,
                'progress_hooks': [self.progress_hook],
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'prefer_ffmpeg': True,
                'keepvideo': False,
                # 添加重试和超时设置
                'retries': 10,  # 重试次数
                'fragment_retries': 10,  # 片段重试次数
                'skip_unavailable_fragments': True,  # 跳过不可用片段
                'ignoreerrors': True,  # 忽略错误继续下载
                'socket_timeout': 30,  # 套接字超时时间
                'extractor_retries': 5,  # 提取器重试次数
                'file_access_retries': 5,  # 文件访问重试次数
                'hls_prefer_native': False,  # 使用ffmpeg下载HLS
                'external_downloader': 'ffmpeg',  # 使用ffmpeg作为外部下载器
                'external_downloader_args': {  # ffmpeg参数
                    'ffmpeg': [
                        '-reconnect', '1',
                        '-reconnect_streamed', '1',
                        '-reconnect_delay_max', '30',
                    ]
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.progress.emit("正在下载视频和音频...")
                try:
                    info = ydl.extract_info(self.url, download=True)
                    if info is None:
                        raise Exception("下载失败，请检查网络连接或尝试降低视频质量")
                    
                    video_path = ydl.prepare_filename(info)
                    
                    if os.path.exists(video_path):
                        size_mb = os.path.getsize(video_path) / (1024 * 1024)
                        self.progress.emit(f"文件已下载到: {video_path}")
                        self.progress.emit(f"文件大小: {size_mb:.1f} MB")
                        self.finished.emit(video_path)
                    else:
                        raise Exception("下载的文件未找到")
                        
                except Exception as e:
                    self.progress.emit(f"下载过程中出错: {str(e)}")
                    self.progress.emit("尝试使用较低质量重新下载...")
                    
                    # 如果下载失败，尝试使用较低质量
                    ydl_opts['format'] = 'best[height<=720]'
                    info = ydl.extract_info(self.url, download=True)
                    video_path = ydl.prepare_filename(info)
                    
                    if os.path.exists(video_path):
                        size_mb = os.path.getsize(video_path) / (1024 * 1024)
                        self.progress.emit(f"已使用较低质量完成下载: {video_path}")
                        self.progress.emit(f"文件大小: {size_mb:.1f} MB")
                        self.finished.emit(video_path)
                    else:
                        raise Exception("下载失败，请稍后重试")
                
        except Exception as e:
            error_msg = str(e)
            if "ffmpeg is not installed" in error_msg:
                error_msg = (
                    "未检测到FFmpeg。请按照以下步骤安装：\n"
                    "1. 访问 https://github.com/BtbN/FFmpeg-Builds/releases\n"
                    "2. 下载 ffmpeg-master-latest-win64-gpl.zip\n"
                    "3. 解压文件\n"
                    "4. 将解压后的 ffmpeg-master-latest-win64-gpl\\bin 目录添加到系统环境变量\n"
                    "5. 重启应用程序"
                )
            self.error.emit(error_msg)
            self.progress.emit(f"下载出错: {error_msg}")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            # 计算下载进度
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            
            if total > 0:
                percent = (downloaded / total) * 100
                speed = d.get('speed', 0)
                
                if speed:
                    speed_str = self.format_speed(speed)
                    # 转换ANSI颜色代码为HTML
                    progress_text = (
                        f'下载进度: <span style="color: #5c8eff;">{percent:.1f}%</span> '
                        f'速度: <span style="color: #00aa00;">{speed_str}</span>'
                    )
                    self.progress.emit(progress_text)

    def format_speed(self, speed):
        """格式化速度显示"""
        if speed < 1024:
            return f"{speed:.2f}B/s"
        elif speed < 1024 * 1024:
            return f"{speed/1024:.2f}KiB/s"
        elif speed < 1024 * 1024 * 1024:
            return f"{speed/(1024*1024):.2f}MiB/s"
        else:
            return f"{speed/(1024*1024*1024):.2f}GiB/s"

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            self.progress.emit(f"下载进度: {percent} 速度: {speed}")
        elif d['status'] == 'finished':
            self.progress.emit(f"下载完成，正在处理文件...")

class MediaPlayer(QThread):
    error_occurred = pyqtSignal(str)
    frame_ready = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.video_path = None
        self.playing = False
        self.volume = 1.0
        self.video_clip = None
        self.audio_clip = None
        self.current_time = 0
        self.mutex = QMutex()
        self.audio_thread = None
        
    def load_media(self, video_path):
        try:
            self.cleanup()
                
            self.video_clip = VideoFileClip(video_path)
            self.audio_clip = self.video_clip.audio
            self.current_time = 0
            self.video_path = video_path
            print(f"媒体已加载: {video_path}")
            
            if self.audio_clip:
                self.audio_clip.volumex = self.volume
                
            return True
        except Exception as e:
            print(f"加载媒体时出错: {str(e)}")
            self.error_occurred.emit(f"加载媒体时出错: {str(e)}")
            return False
            
    def play_audio(self):
        if self.audio_clip:
            self.audio_clip.preview()
            
    def run(self):
        if not self.video_clip:
            self.error_occurred.emit("未加载媒体文件")
            return
            
        try:
            self.playing = True
            fps = self.video_clip.fps
            frame_interval = 1.0 / fps if fps > 0 else 0.033
            duration = self.video_clip.duration
            print(f"视频FPS: {fps}, 帧间隔: {frame_interval}秒")
            
            if self.audio_clip and not self.audio_thread:
                self.audio_thread = threading.Thread(target=self.play_audio)
                self.audio_thread.daemon = True
                self.audio_thread.start()
            
            while self.playing:
                try:
                    if self.current_time >= duration:
                        self.current_time = 0
                        if self.audio_thread:
                            self.audio_thread.join()
                            self.audio_thread = threading.Thread(target=self.play_audio)
                            self.audio_thread.daemon = True
                            self.audio_thread.start()
                            
                    frame = self.video_clip.get_frame(self.current_time)
                    
                    self.mutex.lock()
                    if self.playing:
                        self.frame_ready.emit(frame)
                    self.mutex.unlock()
                    
                    start_time = time.time()
                    self.current_time += frame_interval
                    
                    elapsed = time.time() - start_time
                    wait_time = max(0, frame_interval - elapsed)
                    if wait_time > 0:
                        self.msleep(int(wait_time * 1000))
                            
                except Exception as e:
                    print(f"处理帧时出错: {str(e)}")
                    self.error_occurred.emit(f"处理帧时出错: {str(e)}")
                    break
        except Exception as e:
            print(f"播放出错: {str(e)}")
            self.error_occurred.emit(f"播放出错: {str(e)}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        self.playing = False
        if self.video_clip:
            try:
                self.video_clip.close()
            except:
                pass
            self.video_clip = None
            
        if self.audio_clip:
            try:
                self.audio_clip.close()
            except:
                pass
            self.audio_clip = None
            
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)
            self.audio_thread = None
            
        print("媒体资源已释放")
            
    def stop(self):
        print("正在停止播放...")
        self.mutex.lock()
        self.playing = False
        self.current_time = 0
        self.mutex.unlock()
        self.cleanup()
        self.wait()
        print("播放已停止")
        
    def set_volume(self, volume):
        self.volume = volume / 100.0
        if self.audio_clip:
            self.audio_clip.volumex = self.volume
        print(f"设置音量: {volume}%")
        
    def __del__(self):
        self.stop()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube视频下载器和播放器")
        self.setMinimumSize(800, 600)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 设置应用样式
        self.setStyleSheet("""
            QPushButton {
                background-color: #2b5b84;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                min-width: 80px;
                max-width: 150px;
            }
            QPushButton:hover {
                background-color: #3d7ab3;
            }
            QPushButton:pressed {
                background-color: #224b6f;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            QLabel {
                color: #333;
            }
        """)
        
        # URL输入区域
        url_layout = QVBoxLayout()
        url_layout.setSpacing(10)
        
        # URL输入框
        url_input_layout = QHBoxLayout()
        url_label = QLabel("视频URL:")
        url_input_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入YouTube视频URL")
        url_input_layout.addWidget(self.url_input)
        url_layout.addLayout(url_input_layout)
        
        # 控制选项区域
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        # 存储位置显示和选择
        storage_layout = QHBoxLayout()
        storage_label = QLabel("存储位置:")
        storage_layout.addWidget(storage_label)
        
        self.storage_path_label = QLabel()
        self.storage_path_label.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        storage_layout.addWidget(self.storage_path_label)
        
        self.download_dir_button = QPushButton("更改位置")
        self.download_dir_button.clicked.connect(self.select_download_dir)
        storage_layout.addWidget(self.download_dir_button)
        
        controls_layout.addLayout(storage_layout)
        
        # 分辨率选择
        resolution_layout = QHBoxLayout()
        resolution_label = QLabel("预设分辨率:")
        resolution_layout.addWidget(resolution_label)
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.setFixedWidth(100)
        self.resolution_combo.addItems(['自动', '2160p', '1440p', '1080p', '720p', '480p', '360p'])
        self.resolution_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        resolution_layout.addWidget(self.resolution_combo)
        
        controls_layout.addLayout(resolution_layout)
        
        # 下载按钮
        self.start_button = QPushButton("下载")
        self.start_button.clicked.connect(self.start_download)
        controls_layout.addWidget(self.start_button)
        
        # 添加到主布局
        url_layout.addLayout(controls_layout)
        layout.addLayout(url_layout)
        
        # 视频控制按钮
        video_controls = QHBoxLayout()
        video_controls.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.open_button = QPushButton("打开视频")
        self.open_button.clicked.connect(self.open_video_file)
        video_controls.addWidget(self.open_button)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_video)
        video_controls.addWidget(self.stop_button)
        
        layout.addLayout(video_controls)
        
        # 视频显示区域
        self.video_container = QWidget()
        self.video_container.setMinimumHeight(400)
        self.video_container.setStyleSheet("""
            background-color: #1e1e1e;
            border-radius: 8px;
        """)
        container_layout = QVBoxLayout(self.video_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.video_label)
        
        layout.addWidget(self.video_container)
        
        # 进度显示
        self.progress_text = QTextEdit()
        self.progress_text.setReadOnly(True)
        self.progress_text.setMaximumHeight(100)
        self.progress_text.setAcceptRichText(True)
        layout.addWidget(self.progress_text)
        
        # 初始化媒体播放器
        self.media_player = MediaPlayer()
        self.media_player.frame_ready.connect(self.update_frame)
        self.media_player.error_occurred.connect(self.handle_error)
        
        # 初始化下载目录
        self.download_dir = os.path.join(os.getcwd(), 'downloads')
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        self.update_storage_path_label()
        
        # 添加帧缓存
        self._current_frame = None
        self._frame_mutex = QMutex()

    def update_storage_path_label(self):
        """更新存储位置显示"""
        self.storage_path_label.setText(self.download_dir)
        self.storage_path_label.setToolTip(self.download_dir)

    def load_video(self, video_path):
        if not os.path.exists(video_path):
            self.handle_error(f"视频文件不存在: {video_path}")
            return False
            
        try:
            if self.media_player.load_media(video_path):
                self.media_player.start()
                return True
            return False
        except Exception as e:
            self.handle_error(f"加载视频失败: {str(e)}")
            return False
            
    def update_frame(self, frame):
        try:
            if not self.video_label.isVisible():
                return
                
            container_size = self.video_container.size()
            if container_size.width() <= 0 or container_size.height() <= 0:
                return
                
            self._frame_mutex.lock()
            self._current_frame = frame.copy()
            self._frame_mutex.unlock()
            
            h, w = frame.shape[:2]
            scale = min(container_size.width() / w, container_size.height() / h)
            new_size = (int(w * scale), int(h * scale))
            
            scaled_frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)
            
            h, w = scaled_frame.shape[:2]
            bytes_per_line = 3 * w
            qt_image = QImage(scaled_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(pixmap)
            
        except Exception as e:
            print(f"更新帧时出错: {str(e)}")
            
    def stop_video(self):
        print("停止播放")
        self.media_player.stop()
        self.video_label.clear()
        
    def select_download_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择存储位置", self.download_dir)
        if dir_path:
            self.download_dir = dir_path
            self.update_storage_path_label()
            self.progress_text.append(f"已选择存储位置: {self.download_dir}")

    def open_video_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            self.download_dir,
            "视频文件 (*.mp4 *.avi *.mkv *.mov);;所有文件 (*.*)"
        )
        if file_path:
            self.load_video(file_path)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入视频URL")
            return
            
        self.progress_text.clear()
        self.start_button.setEnabled(False)
        self.start_button.setText("下载中...")
        
        self.downloader = VideoDownloader(url, self.download_dir)
        
        selected_resolution = self.resolution_combo.currentText()
        if selected_resolution != '自动':
            self.downloader.preferred_resolution = selected_resolution
        
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.error.connect(self.on_download_error)
        self.downloader.progress.connect(self.on_download_progress)
        
        self.downloader.start()
        
    def on_download_error(self, error_msg):
        self.progress_text.append(f"错误: {error_msg}")
        self.start_button.setEnabled(True)
        self.start_button.setText("下载")
        
    def on_download_progress(self, progress_msg):
        self.progress_text.append(progress_msg)
        
    def on_download_finished(self, video_path):
        self.progress_text.append(f"下载完成: {video_path}")
        self.start_button.setEnabled(True)
        self.start_button.setText("下载")
        
    def handle_error(self, error_msg):
        print(f"错误: {error_msg}")
        QMessageBox.critical(self, "错误", error_msg)
        self.stop_video()

    def append_progress(self, text):
        """添加进度信息到进度框"""
        self.progress_text.append(text)
        # 滚动到底部
        scrollbar = self.progress_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
