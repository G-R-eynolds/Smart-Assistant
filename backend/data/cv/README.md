# CV Directory

This directory contains your CV file for the Smart Assistant job pipeline.

## Setup

1. **Upload your CV**: Place your CV as a PDF file named `cv.pdf` in this directory
   
   You can either:
   - Copy it manually: `cp /path/to/your/cv.pdf ./cv.pdf`
   - Use the upload script: `python ../upload_cv.py /path/to/your/cv.pdf`

2. **Verify upload**: Once uploaded, you can test that it's working:
   ```bash
   # Start the backend server
   cd .. && python -m app.main
   
   # In another terminal, test the CV endpoints
   curl http://localhost:8080/api/smart-assistant/cv/info
   curl http://localhost:8080/api/smart-assistant/cv/summary
   ```

## File Structure

```
cv/
├── README.md          # This file
├── cv.pdf            # Your main CV (create this file)
└── cv_backup_*.pdf   # Automatic backups when you update your CV
```

## Supported Features

- **Automatic text extraction** from PDF using PyPDF2
- **Caching** for faster performance 
- **Automatic backup** when you update your CV
- **Integration** with cover letter generation
- **API endpoints** for CV management

## API Endpoints

- `GET /api/smart-assistant/cv/info` - Get CV file information
- `GET /api/smart-assistant/cv/summary` - Get CV content summary  
- `POST /api/smart-assistant/cv/refresh` - Force refresh CV cache

## Troubleshooting

- **"CV not found"**: Make sure your file is named exactly `cv.pdf`
- **"Text extraction failed"**: Try re-saving your PDF or converting it to a simpler format
- **"Permission denied"**: Check file permissions (`chmod 644 cv.pdf`)

## Next Steps

After setting up your CV:

1. Configure your `.env` file with API keys
2. Install dependencies: `pip install -r requirements.txt`
3. Test the job pipeline: Use `/find_jobs software engineer remote` in the frontend chat
