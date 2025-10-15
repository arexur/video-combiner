import gspread
from google.oauth2.service_account import Credentials
import logging

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self, credentials_path, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.setup_sheets_client(credentials_path)
    
    def setup_sheets_client(self, credentials_path):
        """Setup Google Sheets client"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            
            logger.info("✅ Google Sheets client initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Sheets client: {e}")
            raise
    
    def get_pending_jobs(self):
        """Get all pending jobs from the queue"""
        try:
            worksheet = self.spreadsheet.worksheet("JobQueue")
            records = worksheet.get_all_records()
            
            pending_jobs = []
            for record in records:
                if record.get('Status', '').lower() in ['pending', 'new']:
                    job = {
                        'job_id': record.get('JobID'),
                        'source_folder_id': record.get('SourceFolderID'),
                        'output_folder_id': record.get('OutputFolderID'),
                        'max_videos': int(record.get('MaxVideos', 3)),
                        'max_duration': int(record.get('MaxDuration', 300)),
                        'row_index': records.index(record) + 2  # +2 for header and 1-based index
                    }
                    pending_jobs.append(job)
            
            return pending_jobs
            
        except Exception as e:
            logger.error(f"❌ Error reading job queue: {e}")
            return []
    
    def update_job_status(self, job_id, status, message="", output_url=""):
        """Update job status in spreadsheet"""
        try:
            worksheet = self.spreadsheet.worksheet("JobQueue")
            records = worksheet.get_all_records()
            
            for idx, record in enumerate(records, start=2):
                if record.get('JobID') == job_id:
                    # Update cells
                    worksheet.update_cell(idx, 3, status)  # Status column
                    worksheet.update_cell(idx, 4, message)  # Message column
                    if output_url:
                        worksheet.update_cell(idx, 5, output_url)  # OutputURL column
                    
                    logger.info(f"📝 Updated job {job_id} to {status}")
                    return True
            
            logger.warning(f"⚠️ Job {job_id} not found in spreadsheet")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error updating job status: {e}")
            return False
    
    def create_job(self, source_folder_id, output_folder_id, max_videos=3, max_duration=300):
        """Create a new job in the queue"""
        try:
            worksheet = self.spreadsheet.worksheet("JobQueue")
            
            import datetime
            job_id = f"job_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            new_row = [
                job_id,
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'pending',
                'Waiting for processing',
                '',  # OutputURL
                source_folder_id,
                output_folder_id,
                max_videos,
                max_duration
            ]
            
            worksheet.append_row(new_row)
            logger.info(f"✅ Created new job: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Error creating job: {e}")
            return None