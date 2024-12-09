# YouTube视频下载器和播放器

这是一个基于Python的YouTube视频下载和播放工具，支持从YouTube下载视频并进行本地播放。

## 功能特点

- YouTube视频下载
  - 支持选择视频分辨率（2160p、1440p、1080p、720p等）
  - 自动选择最接近所选分辨率的可用格式
  - 智能重试机制，自动处理网络问题
  - 支持自定义存储位置
  - 显示实时下载进度和速度
  - 自动添加时间戳避免文件重名
  - 自动合并视频和音频流
  
- 视频播放
  - 支持播放/停止控制
  - 音量调节
  - 支持本地视频文件播放
  - 高清视频播放支持

## 技术实现

- 视频下载：使用 yt-dlp 库，支持自动重试和错误恢复
- 视频播放：使用 MoviePY 处理音频，OpenCV 处理视频帧
- 界面实现：PyQt6，现代化UI设计
- 外部工具：FFmpeg 用于视频处理和格式转换

## 系统要求

- Windows 操作系统
- Python 3.8 或更高版本
- FFmpeg（必需，用于视频处理）
- 安装所有必要的依赖包（见 requirements.txt）

## 完整安装步骤

1. **安装 Python**
   - 访问 [Python官网](https://www.python.org/downloads/)
   - 下载并安装 Python 3.8 或更高版本
   - 安装时勾选"Add Python to PATH"

2. **安装 FFmpeg**
   - 访问 [FFmpeg Builds](https://github.com/BtbN/FFmpeg-Builds/releases)
   - 下载 `ffmpeg-master-latest-win64-gpl.zip`
   - 解压下载的文件
   - 将解压后的 `ffmpeg-master-latest-win64-gpl\bin` 目录添加到系统环境变量：
     1. 按 Win + X，选择"系统"
     2. 点击"高级系统设置"
     3. 点击"环境变量"
     4. 在"系统变量"中找到"Path"
     5. 点击"编辑"
     6. 点击"新建"
     7. 粘贴 FFmpeg bin 目录的完整路径
     8. 点击"确定"保存所有更改

3. **克隆或下载此仓库**
   ```bash
   git clone [repository-url]
   cd [repository-directory]
   ```

4. **安装 Python 依赖**
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

1. **启动程序**
   ```bash
   python main.py
   ```

2. **下载视频**
   - 在URL输入框中粘贴YouTube视频链接
   - 从下拉菜单选择期望的视频分辨率
   - （可选）点击"更改位置"按钮选择存储目录
   - 点击"下载"按钮开始下载
   - 等待下载完成，进度会实时显示

3. **播放视频**
   - 点击"打开视频"按钮选择要播放的视频文件
   - 使用"停止"按钮控制播放
   - 视频会在主窗口中播放

## 故障排除

1. **下载失败**
   - 检查网络连接
   - 确认 FFmpeg 已正确安装并添加到环境变量
   - 尝试选择较低的视频分辨率
   - 检查是否有足够的磁盘空间

2. **播放问题**
   - 确保视频文件未被损坏
   - 检查是否安装了所有必要的编解码器
   - 重启程序尝试重新播放

## 依赖列表

- PyQt6==6.7.1：用于图形界面
- yt-dlp==2024.12.6：用于下载YouTube视频
- opencv-python==4.10.0.84：用于视频帧处理
- moviepy==1.0.3：用于音频处理
- numpy>=1.21.2：用于数据处理
- pygame==2.5.2：用于音频播放支持

## 更新日志

### 2023.12.09
- 添加视频分辨率选择功能
- 改进下载重试机制
- 添加文件名时间戳
- 优化界面布局
- 添加存储位置显示
- 改进错误处理和用户反馈

## 许可证

MIT License
