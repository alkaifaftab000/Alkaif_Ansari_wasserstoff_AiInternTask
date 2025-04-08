
# 📬 Intelligent Email Assistant 🤖

An intelligent, multi-phase assistant that fetches emails, extracts insights using NLP and LLMs, performs smart actions like calendar scheduling and Slack notifications, and optionally replies to emails — all backed by Supabase.

---

## 📌 Features

- ✅ Configurable email fetching (`all/unread`, batch size)
- 🧠 LLaMA 3B-based email summarization
- 📎 Smart attachment parsing (PDF, DOCX, images)
- 🔍 Web search integration (DuckDuckGo)
- 🔔 Slack notifications for key emails
- 🗓️ Google Calendar scheduling & reminder management
- ✉️ LLM-powered auto-reply (context-aware)
- 🗃️ Supabase backend with relational email & analysis tables

---

## 🧱 Project Structure

```
📁 config/
    ├── credentials.json             # Gmail & Calendar OAuth credentials
    ├── google_calendar_credentials.json
    ├── token.json / token.pickle   # OAuth tokens

📁 src/
    ├── attachment_service.py
    ├── calendar_handler.py
    ├── calender_services.py
    ├── email_parser.py
    ├── email_reply_templates.py
    ├── email_service.py
    ├── gmail_service.py
    ├── llama_api.py
    ├── main.py                     # Entry point
    ├── slack_service.py
    ├── summarization_service.py
    ├── supabase_service.py
    ├── test_email_reply.py
    ├── update_calendar_action.py
    └── web_search_service.py

📄 .env                             # Environment variables
📄 requirements.txt                 # Python dependencies
📄 README.md                        # You are here!
```

---

## 🛠️ Setup Instructions

### 🔧 1. Clone the Repository

```bash
git clone https://github.com/your-username/intelligent-email-assistant.git
cd intelligent-email-assistant
```

### 📦 2. Create Virtual Environment & Install Dependencies

```bash
python -m venv venv
source venv/bin/activate     # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 🗝️ 3. Setup Environment Variables (`.env`)

Create a `.env` file in the root folder with the following:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
OPENAI_API_KEY=your_openai_or_llama_api_key
OCR_SPACE_API_KEY=your_ocr_space_api_key
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/hook/url
GOOGLE_CALENDAR_ID=primary
```

### 🔐 4. Setup Google API Credentials

- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a project → Enable **Gmail API** & **Google Calendar API**
- Download `credentials.json` for OAuth
- Place it in the `config/` folder

First run will trigger a browser window for OAuth login and create `token.pickle`.

---

## 🚀 Running the Assistant

```bash
python src/main.py
```

You will be prompted at each phase:

- Whether to fetch `all` or only `unread` emails
- Batch size to process (default: 50)
- Whether to analyze attachments
- Whether to start summarization
- Whether to send Slack notifications
- Whether to set calendar reminders/meetings
- Whether to auto-reply or get confirmation for reply

---

## 🔁 Workflow Phases

| Phase | Description |
|-------|-------------|
| 1     | Fetch and parse emails and attachments |
| 2     | Extract & summarize attachments (PDF, DOCX, images via OCR) |
| 3     | LLaMA-based summarization + optional DuckDuckGo web search |
| 4     | Slack notification for important emails |
| 5     | Calendar integration: reminders, meetings, conflict resolution |
| 6     | Auto-reply (if applicable) using LLM |

Each phase is **modular** and user-controlled.

---

## 🧠 Tech Stack

- Python
- Supabase (PostgreSQL backend)
- Gmail & Calendar API
- Slack Webhooks
- LLaMA 3B / LLMs
- DuckDuckGo Search
- OCR.Space API
- nltk, fitz (PyMuPDF), docx, etc.

---

## 📊 Database Schema (Simplified)

### `emails`
Stores fetched email metadata, content, and parsed attachments.

### `analysis`
Stores analysis results including summaries, insights, actions, calendar data, Slack messages, and more.

---

## 📌 Notes

- If any email triggers an action like meeting/reminder/slack, it will automatically generate a reply.
- For generic email queries, the assistant will ask the user before replying.

---

## 📫 Future Improvements

- Dashboard for managing email flows
- Inference optimization
- Multi-user support

---

## 🧑‍💻 Author

Made with ❤️ by [Your Name](https://github.com/your-profile)

---

## 📝 License

MIT License. Feel free to use, improve, and share.
