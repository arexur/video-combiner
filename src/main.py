#!/usr/bin/env python3
"""
Video Combiner Main Script for GitHub Actions
Optimized for free tier usage
"""

import os
import json
import logging
import tempfile
from google_sheets import GoogleSheetsManager
from video_processor import VideoProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/video_combiner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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

def main():
    logger.info("🚀 Starting Video Combiner...")
    
    spreadsheet_id = os.environ.get('SPREADSHEET_ID')
    if not spreadsheet_id:
        logger.error("❌ SPREADSHEET_ID environment variable not set")
        return
    
    creds_path = None
    try:
        # Load credentials
        creds_path = load_credentials_from_env()
        logger.info("✅ Credentials loaded successfully")
        
        # Initialize managers
        sheets_manager = GoogleSheetsManager(creds_path, spreadsheet_id)
        video_processor = VideoProcessor(creds_path)
        
        # Check for pending jobs
        pending_jobs = sheets_manager.get_pending_jobs()
        logger.info(f"📋 Found {len(pending_jobs)} pending jobs")
        
        if not pending_jobs:
            logger.info("✅ No pending jobs - exiting")
            return
        
        # Process each job
        successful_jobs = 0
        for job in pending_jobs:
            try:
                logger.info(f"🔄 Processing job: {job['job_id']}")
                
                # Update status to processing
                sheets_manager.update_job_status(job['job_id'], 'processing', 'Downloading videos...')
                
                # Process the job
                result = video_processor.process_job(job)
                
                if result['success']:
                    sheets_manager.update_job_status(
                        job['job_id'], 
                        'completed', 
                        f"Successfully processed {result['videos_processed']} videos",
                        result['output_url']
                    )
                    successful_jobs += 1
                    logger.info(f"✅ Job {job['job_id']} completed successfully")
                else:
                    sheets_manager.update_job_status(
                        job['job_id'], 
                        'failed', 
                        result['error_message']
                    )
                    logger.error(f"❌ Job {job['job_id']} failed: {result['error_message']}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing job {job['job_id']}: {str(e)}")
                sheets_manager.update_job_status(job['job_id'], 'failed', str(e))
        
        logger.info(f"🎉 Processing complete! {successful_jobs}/{len(pending_jobs)} jobs successful")
        
    except Exception as e:
        logger.error(f"💥 Critical error in main: {str(e)}")
        raise
        
    finally:
        # Cleanup
        if creds_path and os.path.exists(creds_path):
            os.unlink(creds_path)
            logger.info("🧹 Temporary files cleaned up")

if __name__ == "__main__":
    main()