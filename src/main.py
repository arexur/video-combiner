#!/usr/bin/env python3
"""
Video Combiner Main Script for GitHub Actions
Optimized for free tier usage
"""

import os
import json
import time
import tempfile
from config import (
    setup_logging, get_spreadsheet_id, validate_job_config,
    VideoConfig, GitHubActionsConfig, Metrics, should_process_jobs
)
from google_sheets import GoogleSheetsManager
from video_processor import VideoProcessor

# Setup logging
logger = setup_logging()

def load_credentials_from_env():
    """Load credentials from environment variable"""
    creds_json = os.environ.get('CREDENTIALS_JSON')
    if not creds_json:
        raise ValueError("CREDENTIALS_JSON environment variable not set")
    
    # Create temporary credentials file
    temp_creds = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_creds.write(creds_json)
    temp_creds.close()
    
    return temp_creds.name

def check_system_resources():
    """Check if we have enough resources to process"""
    # Simple resource check - bisa dikembangkan
    import shutil
    
    # Check disk space
    total, used, free = shutil.disk_usage("/")
    free_gb = free // (2**30)
    
    if free_gb < 1:  # Less than 1GB free
        logger.warning("⚠️ Low disk space available")
        return False
        
    return True

def main():
    start_time = time.time()
    logger.info("🚀 Starting Video Combiner...")
    
    try:
        # Check system resources
        if not check_system_resources():
            logger.error("❌ Insufficient system resources")
            return
        
        # Check if we should process jobs
        if not should_process_jobs():
            logger.info("⏸️ Skipping processing based on configuration")
            return
        
        # Load configuration from environment
        spreadsheet_id = get_spreadsheet_id()
        creds_path = load_credentials_from_env()
        logger.info("✅ Configuration loaded successfully")
        
        # Initialize managers
        sheets_manager = GoogleSheetsManager(creds_path, spreadsheet_id)
        video_processor = VideoProcessor(creds_path)
        
        # Check for pending jobs
        pending_jobs = sheets_manager.get_pending_jobs()
        logger.info(f"📋 Found {len(pending_jobs)} pending jobs")
        
        if not pending_jobs:
            logger.info("✅ No pending jobs - exiting")
            return
        
        # Process each job dengan batasan waktu
        successful_jobs = 0
        for job in pending_jobs:
            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > GitHubActionsConfig.MAX_RUN_TIME:
                logger.warning("⏰ Approaching timeout - stopping processing")
                break
            
            try:
                # Validate job config
                validation_errors = validate_job_config(job)
                if validation_errors:
                    error_msg = "; ".join(validation_errors)
                    sheets_manager.update_job_status(job['job_id'], 'failed', error_msg)
                    Metrics.errors_encountered += 1
                    continue
                
                logger.info(f"🔄 Processing job: {job['job_id']}")
                
                # Update status to processing
                sheets_manager.update_job_status(job['job_id'], 'processing', 'Downloading videos...')
                
                # Process the job
                job_start_time = time.time()
                result = video_processor.process_job(job)
                job_processing_time = time.time() - job_start_time
                
                Metrics.total_processing_time += job_processing_time
                
                if result['success']:
                    sheets_manager.update_job_status(
                        job['job_id'], 
                        'completed', 
                        f"Successfully processed {result['videos_processed']} videos in {job_processing_time:.1f}s",
                        result['output_url']
                    )
                    successful_jobs += 1
                    Metrics.jobs_processed += 1
                    Metrics.videos_combined += result['videos_processed']
                    logger.info(f"✅ Job {job['job_id']} completed in {job_processing_time:.1f}s")
                else:
                    sheets_manager.update_job_status(
                        job['job_id'], 
                        'failed', 
                        result['error_message']
                    )
                    Metrics.errors_encountered += 1
                    logger.error(f"❌ Job {job['job_id']} failed: {result['error_message']}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing job {job['job_id']}: {str(e)}")
                sheets_manager.update_job_status(job['job_id'], 'failed', str(e))
                Metrics.errors_encountered += 1
        
        # Print summary
        total_time = time.time() - start_time
        logger.info(f"🎉 Processing complete in {total_time:.2f}s!")
        Metrics.print_summary()
        
    except Exception as e:
        logger.error(f"💥 Critical error in main: {str(e)}")
        Metrics.errors_encountered += 1
        raise
        
    finally:
        # Cleanup
        if 'creds_path' in locals() and os.path.exists(creds_path):
            os.unlink(creds_path)
            logger.info("🧹 Temporary files cleaned up")

if __name__ == "__main__":
    main()
