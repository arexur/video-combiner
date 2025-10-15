import os
import random
import tempfile
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy.editor import VideoFileClip, concatenate_videoclips

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self, credentials_path):
        self.credentials_path = credentials_path
        self.temp_dir = tempfile.mkdtemp()
        self.setup_drive_client()
    
    def setup_drive_client(self):
        """Setup Google Drive client"""
        try:
            scopes = ['https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
            self.drive_service = build('drive', 'v3', credentials=creds)
            logger.info("✅ Google Drive client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Drive client: {e}")
            raise
    
    def get_videos_from_folder(self, folder_id):
        """Get all videos from a Google Drive folder"""
        try:
            query = f"'{folder_id}' in parents and mimeType contains 'video/' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                pageSize=20,  # Limit for free tier
                fields="files(id, name, size, mimeType)"
            ).execute()
            
            videos = results.get('files', [])
            
            # Filter out very large files (>100MB) untuk hemat memory
            filtered_videos = [
                video for video in videos 
                if int(video.get('size', 0)) < 100 * 1024 * 1024  # 100MB limit
            ]
            
            logger.info(f"📹 Found {len(filtered_videos)} videos (after filtering)")
            return filtered_videos
            
        except Exception as e:
            logger.error(f"❌ Error listing videos: {e}")
            return []
    
    def download_video(self, file_id, filename):
        """Download video from Google Drive"""
        try:
            local_path = os.path.join(self.temp_dir, filename)
            
            request = self.drive_service.files().get_media(fileId=file_id)
            with open(local_path, 'wb') as f:
                f.write(request.execute())
            
            logger.info(f"⬇️ Downloaded: {filename}")
            return local_path
            
        except Exception as e:
            logger.error(f"❌ Error downloading {filename}: {e}")
            return None
    
    def upload_video(self, local_path, folder_id, filename):
        """Upload video to Google Drive"""
        try:
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(
                local_path,
                mimetype='video/mp4',
                resumable=True
            )
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            logger.info(f"⬆️ Uploaded: {filename}")
            return file.get('webViewLink')
            
        except Exception as e:
            logger.error(f"❌ Error uploading {filename}: {e}")
            return None
    
    def combine_videos(self, video_paths, output_path, max_duration=300):
        """Combine videos into one"""
        if not video_paths:
            return False
        
        try:
            clips = []
            total_duration = 0
            
            for video_path in video_paths:
                try:
                    clip = VideoFileClip(video_path)
                    
                    # Skip if would exceed max duration
                    if total_duration + clip.duration > max_duration:
                        clip.close()
                        logger.info(f"⏰ Skipping {os.path.basename(video_path)} - exceeds max duration")
                        continue
                    
                    clips.append(clip)
                    total_duration += clip.duration
                    logger.info(f"🎬 Added: {os.path.basename(video_path)} ({clip.duration:.1f}s)")
                    
                    # Stop if reached max duration
                    if total_duration >= max_duration:
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Error processing {video_path}: {e}")
                    continue
            
            if not clips:
                logger.error("❌ No valid clips to combine")
                return False
            
            logger.info(f"🔗 Combining {len(clips)} videos (total: {total_duration:.1f}s)")
            
            # Combine videos
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Write output dengan setting optimized untuk free tier
            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                bitrate="1000k",  # Lower bitrate untuk hemat resource
                verbose=False,
                logger=None
            )
            
            # Cleanup
            for clip in clips:
                clip.close()
            final_clip.close()
            
            logger.info(f"✅ Successfully created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error combining videos: {e}")
            return False
    
    def process_job(self, job):
        """Process a single job"""
        try:
            job_id = job['job_id']
            source_folder_id = job['source_folder_id']
            output_folder_id = job['output_folder_id']
            max_videos = job['max_videos']
            max_duration = job['max_duration']
            
            logger.info(f"🔄 Starting job {job_id}")
            
            # Get source videos
            source_videos = self.get_videos_from_folder(source_folder_id)
            if not source_videos:
                return {
                    'success': False,
                    'error_message': 'No videos found in source folder',
                    'videos_processed': 0
                }
            
            # Select random videos
            selected_videos = random.sample(
                source_videos, 
                min(max_videos, len(source_videos))
            )
            
            logger.info(f"🎲 Selected {len(selected_videos)} random videos")
            
            # Download videos
            local_video_paths = []
            for video in selected_videos:
                local_path = self.download_video(video['id'], video['name'])
                if local_path:
                    local_video_paths.append(local_path)
            
            if not local_video_paths:
                return {
                    'success': False,
                    'error_message': 'Failed to download any videos',
                    'videos_processed': 0
                }
            
            # Generate output filename
            output_filename = f"combined_{job_id}.mp4"
            local_output_path = os.path.join(self.temp_dir, output_filename)
            
            # Combine videos
            combine_success = self.combine_videos(
                local_video_paths, 
                local_output_path, 
                max_duration
            )
            
            if not combine_success:
                return {
                    'success': False,
                    'error_message': 'Failed to combine videos',
                    'videos_processed': 0
                }
            
            # Upload result
            output_url = self.upload_video(
                local_output_path, 
                output_folder_id, 
                output_filename
            )
            
            if not output_url:
                return {
                    'success': False,
                    'error_message': 'Failed to upload result',
                    'videos_processed': len(local_video_paths)
                }
            
            # Cleanup local files
            self.cleanup_temp_files(local_video_paths + [local_output_path])
            
            return {
                'success': True,
                'videos_processed': len(local_video_paths),
                'output_url': output_url
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing job: {e}")
            return {
                'success': False,
                'error_message': str(e),
                'videos_processed': 0
            }
    
    def cleanup_temp_files(self, file_paths):
        """Cleanup temporary files"""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"⚠️ Could not delete {file_path}: {e}")