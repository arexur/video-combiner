#!/usr/bin/env python3
"""
Configuration for Video Combiner
Optimized for GitHub Actions free tier
"""

import os
import logging
from datetime import datetime

# 🎯 Application Settings
APP_NAME = "Video Combiner"
APP_VERSION = "1.0.0"
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

# 📊 Google API Settings
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# 🎥 Video Processing Settings
class VideoConfig:
    # Free tier optimizations
    MAX_VIDEOS_PER_JOB = 3  # Reduced from 5 untuk hemat memory
    MAX_DURATION_SECONDS = 300  # 5 minutes max
    MAX_VIDEO_SIZE_MB = 100  # Skip videos larger than 100MB
    OUTPUT_BITRATE = "1000k"  # Lower quality untuk hemat resource
    OUTPUT_FPS = 24  # Standard FPS
    
    # Video formats supported
    SUPPORTED_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']
    
    # Processing limits untuk GitHub Actions
    MAX_PROCESSING_TIME = 600  # 10 minutes max (GitHub timeout 15min)
    MAX_CONCURRENT_JOBS = 1  # Process one job at a time

# 📁 File & Storage Settings
class StorageConfig:
    TEMP_DIR = "/tmp/video_combiner"
    MAX_TEMP_STORAGE_MB = 500  # Max 500MB temporary files
    CLEANUP_AFTER_PROCESS = True
    
    # Google Drive settings
    DRIVE_PAGE_SIZE = 20  # Limit results untuk hemat API calls
    DRIVE_UPLOAD_CHUNK_SIZE = 100 * 1024 * 1024  # 100MB chunks

# 📋 Google Sheets Settings
class SheetsConfig:
    WORKSHEET_NAME = "JobQueue"
    CONFIG_WORKSHEET = "Configuration"
    
    # Column names in JobQueue worksheet
    COLUMNS = {
        'job_id': 'JobID',
        'created_date': 'CreatedDate', 
        'status': 'Status',
        'message': 'Message',
        'output_url': 'OutputURL',
        'source_folder': 'SourceFolderID',
        'output_folder': 'OutputFolderID',
        'max_videos': 'MaxVideos',
        'max_duration': 'MaxDuration'
    }
    
    # Valid status values
    STATUS_VALUES = ['pending', 'processing', 'completed', 'failed', 'cancelled']

# ⚙️ GitHub Actions Specific Settings
class GitHubActionsConfig:
    MAX_RUN_TIME = 840  # 14 minutes (safety margin from 15min timeout)
    REQUEST_TIMEOUT = 30  # API request timeout
    LOG_RETENTION_DAYS = 30
    
    # Resource limits
    MEMORY_LIMIT_MB = 7000  # GitHub Actions provides 7GB RAM
    CPU_LIMIT = 2  # 2 vCPUs

# 🔧 Performance Optimization
class PerformanceConfig:
    # MoviePy optimizations
    USE_MEMORY_CACHE = False  # Set False untuk hemat memory
    TEMP_AUDIO_DIR = "/tmp"
    RESIZE_VIDEO = True  # Resize videos to 720p untuk hemat processing
    TARGET_RESOLUTION = (1280, 720)  # 720p
    
    # Parallel processing (disable untuk free tier)
    ENABLE_PARALLEL = False
    MAX_WORKERS = 1

# 📝 Logging Configuration
def setup_logging():
    """Setup logging configuration"""
    log_level = logging.DEBUG if DEBUG else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/tmp/video_combiner.log'),
            logging.StreamHandler()
        ]
    )
    
    # Reduce verbosity for some noisy libraries
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('moviepy').setLevel(logging.INFO)

# 🔍 Validation Functions
def validate_job_config(job):
    """Validate job configuration"""
    errors = []
    
    max_videos = job.get('max_videos', VideoConfig.MAX_VIDEOS_PER_JOB)
    if max_videos > 5:
        errors.append("Max videos cannot exceed 5")
    
    max_duration = job.get('max_duration', VideoConfig.MAX_DURATION_SECONDS) 
    if max_duration > 600:
        errors.append("Max duration cannot exceed 10 minutes")
    
    return errors

def get_output_filename(job_id, extension='.mp4'):
    """Generate output filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"combined_{job_id}_{timestamp}{extension}"

# 🔄 Environment-based Configuration
def get_spreadsheet_id():
    """Get spreadsheet ID from environment"""
    spreadsheet_id = os.environ.get('SPREADSHEET_ID')
    if not spreadsheet_id:
        raise ValueError("SPREADSHEET_ID environment variable is required")
    return spreadsheet_id

def should_process_jobs():
    """Check if we should process jobs (for maintenance windows, etc)"""
    # Bisa ditambah logic untuk skip processing di waktu tertentu
    return True

# 📊 Metrics and Monitoring
class Metrics:
    jobs_processed = 0
    videos_combined = 0
    total_processing_time = 0
    errors_encountered = 0
    
    @classmethod
    def reset(cls):
        cls.jobs_processed = 0
        cls.videos_combined = 0  
        cls.total_processing_time = 0
        cls.errors_encountered = 0
    
    @classmethod
    def print_summary(cls):
        """Print processing summary"""
        logging.info("📊 Processing Summary:")
        logging.info(f"   Jobs Processed: {cls.jobs_processed}")
        logging.info(f"   Videos Combined: {cls.videos_combined}")
        logging.info(f"   Total Processing Time: {cls.total_processing_time:.2f}s")
        logging.info(f"   Errors Encountered: {cls.errors_encountered}")

# 🎯 Default Job Configuration
DEFAULT_JOB_CONFIG = {
    'max_videos': VideoConfig.MAX_VIDEOS_PER_JOB,
    'max_duration': VideoConfig.MAX_DURATION_SECONDS,
    'output_quality': 'medium',
    'add_transitions': False,  # Disable untuk hemat processing
    'include_audio': True
}

# Initialize logging when module is imported
setup_logging()