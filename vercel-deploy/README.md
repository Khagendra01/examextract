# Exam Paper Extractor - Vercel Deployment

This is the Vercel deployment package for the Exam Paper Extractor Flask application.

## Prerequisites

1. A Vercel account
2. Vercel CLI installed (`npm i -g vercel`)
3. A Gemini API key from Google AI Studio

## Deployment Steps

### 1. Install Vercel CLI (if not already installed)
```bash
npm i -g vercel
```

### 2. Navigate to the deployment folder
```bash
cd vercel-deploy
```

### 3. Login to Vercel
```bash
vercel login
```

### 4. Set Environment Variables

Set your Gemini API key as an environment variable in Vercel:

**Option A: Using Vercel CLI**
```bash
vercel env add GEMINI_API_KEY
# When prompted, enter your Gemini API key
```

**Option B: Using Vercel Dashboard**
1. Go to your project settings on Vercel
2. Navigate to "Environment Variables"
3. Add `GEMINI_API_KEY` with your API key value

### 5. Deploy to Vercel
```bash
vercel
```

For production deployment:
```bash
vercel --prod
```

## Project Structure

```
vercel-deploy/
├── api/
│   └── index.py          # Vercel serverless function entry point
├── templates/
│   └── index.html        # Frontend HTML template
├── app.py                # Main Flask application
├── oldinput.txt          # Template file for exam extraction
├── requirements.txt      # Python dependencies
├── vercel.json          # Vercel configuration
└── README.md            # This file
```

## Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required)

## Important Notes

1. **Database Storage**: The SQLite database is stored in `/tmp` on Vercel, which is ephemeral. Data will be lost between deployments. For persistent storage, consider using:
   - Vercel KV (Redis)
   - Vercel Postgres
   - External database service

2. **File Uploads**: Uploaded images are temporarily stored in `/tmp` and cleaned up after processing.

3. **Function Timeout**: Vercel serverless functions have execution time limits:
   - Hobby plan: 10 seconds
   - Pro plan: 60 seconds
   - Enterprise: Custom limits

   The Gemini API call may take longer than 10 seconds, so you may need to upgrade to Pro plan or use background jobs.

4. **API Routes**: All routes are handled through the single `api/index.py` serverless function.

## Troubleshooting

### Function Timeout
If you encounter timeout errors, consider:
- Upgrading to Vercel Pro plan (60s timeout)
- Implementing background job processing
- Optimizing the Gemini API call

### Database Issues
If database operations fail:
- Check that `/tmp` directory is writable
- Consider migrating to a persistent database service
- Check Vercel function logs for errors

### Environment Variables
If `GEMINI_API_KEY` is not found:
- Verify the environment variable is set in Vercel dashboard
- Ensure it's set for the correct environment (production/preview)
- Redeploy after adding environment variables

## Local Development

To test locally with Vercel:

```bash
vercel dev
```

This will start a local development server that mimics Vercel's serverless environment.

## Support

For issues related to:
- **Vercel deployment**: Check Vercel documentation and logs
- **Application code**: See the main project README
- **Gemini API**: Check Google AI Studio documentation



