# Exam Paper Extractor - Flask Web App

A Flask web application that extracts exam paper content from images and generates formatted DOCX documents. Supports multiple concurrent processes with local database storage.

## Features

- **Multiple Processes**: Run multiple extraction processes simultaneously
- **Local Database Storage**: All extraction results (JSON) are stored locally in SQLite database
- **Download Anytime**: Download previously generated documents from history
- **Upload Multiple Images**: Each process can handle one or more images
- **Automatic Content Extraction**: Uses Google Gemini API for intelligent extraction
- **Formatted DOCX Output**: Professional document formatting with proper styling
- **Clean Modern UI**: Drag-and-drop interface with process management

## Setup

1. **Install Dependencies**

```bash
pip install -r requirements_exam.txt
```

2. **Set Environment Variable**

Create a `.env` file in the project root or set the environment variable:

```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

3. **Run the Application**

```bash
python app_exam.py
```

The app will start on `http://localhost:5000`

## Usage

1. Open your browser and navigate to `http://localhost:5000`
2. **Start a Process**: Click the "+ Add New Process" button to create a new extraction process
3. **Upload Images**: Click the upload area or drag and drop exam paper images (one or multiple)
4. **Generate**: Click "Generate DOCX" button to extract and save the content
5. **Download**: Use the "Download DOCX" button to get the formatted document
6. **History**: View all past extractions in the history section and download them anytime
7. **Multiple Processes**: Add as many processes as needed using the "+" button

## How It Works

1. **Multiple Processes**: Each process can handle one or more images independently
2. **Image Upload**: User uploads exam paper images through the web interface
3. **Content Extraction**: Images are sent to OpenRouter API (mimo-v2.5) for text extraction
4. **Database Storage**: Extraction results (JSON) are saved to local SQLite database (`exam_extractions.db`)
5. **Normalization**: Extracted content is normalized to ensure required fields are present
6. **DOCX Generation**: Content is formatted and converted to a Word document on-demand with:
   - Two-column landscape layout
   - Proper spacing between questions and options
   - Professional styling (Times New Roman font)
   - Metadata fields (Title, Subject, Class, Time, Full Marks, Pass Marks)
7. **Download Anytime**: Previously saved extractions can be downloaded from the history section

## File Structure

- `app_exam.py` - Main Flask application with database support
- `templates/index.html` - Web interface with multi-process support
- `requirements_exam.txt` - Python dependencies
- `oldinput.txt` - Template file for extraction (optional)
- `exam_extractions.db` - SQLite database (created automatically) storing all extraction results

## Database Schema

The SQLite database stores:
- `process_id`: Unique identifier for each extraction
- `created_at`: Timestamp of extraction
- `image_count`: Number of images processed
- `extraction_json`: Raw JSON extraction data from Gemini API
- `text_content`: Normalized text content
- `status`: Process status (completed, error, etc.)

## API Endpoints

- `GET /` - Main web interface
- `POST /api/upload` - Upload images and extract content
- `GET /api/processes` - Get all extraction processes
- `GET /api/process/<process_id>` - Get specific process details
- `GET /api/download/<process_id>` - Download DOCX for a process
- `DELETE /api/delete/<process_id>` - Delete a process from database

## Notes

- Maximum file size: 16MB per file
- Supported image formats: JPG, PNG
- Images are not stored in database (only JSON extraction results)
- Each process can handle multiple images which are combined into one document
- Temporary files are automatically cleaned up after processing
- Database is stored locally on your computer

