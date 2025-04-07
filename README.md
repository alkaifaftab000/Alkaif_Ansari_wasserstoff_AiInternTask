# Smart Email Attachment Analyzer

This project extends the Smart Email system by adding comprehensive attachment analysis capabilities.

## Features

- PDF text extraction using PyMuPDF
- DOCX text extraction using python-docx
- Image text extraction using OCR.space API
- Text summarization using sumy
- Key phrase extraction
- Sentiment analysis
- Supabase integration for storage

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your credentials:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OCR_API_KEY=your_ocr_api_key
```

4. Set up the Supabase database:
```sql
create table attachment_analysis (
    id uuid default uuid_generate_v4() primary key,
    attachment_id uuid references attachments(id),
    extracted_text text,
    summary text,
    key_phrases text[],
    sentiment float,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now())
);
```

## Usage

1. Run the attachment analyzer:
```bash
python new_main.py
```

2. Run tests:
```bash
python -m pytest tests/
```

## Project Structure

```
smart_email_v2/
├── config.py              # Configuration settings
├── new_main.py           # Main entry point
├── new_attachment_service.py  # Attachment analysis service
├── requirements.txt      # Project dependencies
├── tests/               # Test files
│   └── test_attachment_analyzer.py
└── README.md            # This file
```

## Error Handling

The system includes comprehensive error handling:
- File download failures
- Text extraction errors
- OCR processing issues
- Database operation failures
- Invalid file types
- Size limitations

## Logging

Logs are written to `attachment_analysis.log` with the following levels:
- INFO: General operation information
- WARNING: Non-critical issues
- ERROR: Critical failures
- DEBUG: Detailed debugging information

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 