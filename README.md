# Video Combiner - GitHub Actions

Automatically combine random videos from Google Drive using GitHub Actions.

## Setup

1. **Create GitHub Secrets:**
   - `SPREADSHEET_ID`: Your Google Sheet ID
   - `GOOGLE_CREDENTIALS`: Full service account JSON

2. **Google Sheet Structure:**
   - Worksheet: "JobQueue"
   - Columns: JobID, CreatedDate, Status, Message, OutputURL, SourceFolderID, OutputFolderID, MaxVideos, MaxDuration

3. **Share Resources:**
   - Share Google Sheet with service account
   - Share Google Drive folders with service account

## Manual Trigger

Go to Actions → Video Combiner → Run Workflow
