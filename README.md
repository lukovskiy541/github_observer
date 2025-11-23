# AI Recruiter Bot

A Telegram bot that uses Google Gemini AI to analyze GitHub profiles and help evaluate candidates for IT positions.

## Features

- 🤖 **AI-Powered Analysis**: Uses Google Gemini to intelligently analyze GitHub profiles
- 📊 **Repository Insights**: Examines user's repositories, languages, and code quality
- 💼 **Recruitment Assessment**: Evaluates candidates for specific IT positions
- 💬 **Conversational Interface**: Natural language interaction through Telegram

## How It Works

1. User asks the bot about a GitHub profile (username or URL)
2. Gemini calls the GitHub API to fetch user data and repositories
3. The AI analyzes the profile, code, and activity
4. User can ask follow-up questions like "Would this person be good for a Senior Python Developer role?"
5. Gemini provides professional recruitment recommendations

## Setup

### Prerequisites

- Python 3.10+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Google AI API Key (from [Google AI Studio](https://makersuite.google.com/app/apikey))
- GitHub Token (optional, for higher rate limits)

### Installation

1. **Clone or navigate to the project directory**

2. **Install dependencies**:

   ```bash
   uv pip install -r requirements.txt
   # or
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your tokens:

   ```env
   TELEGRAM_TOKEN=your_telegram_bot_token_here
   GOOGLE_API_KEY=your_gemini_api_key_here
   GITHUB_TOKEN=your_github_token_here  # Optional
   ```

4. **Run the bot**:

   ```bash
   uv run python bot.py
   # or
   python bot.py
   ```

## Usage

1. Start a chat with your bot on Telegram
2. Send `/start` to initialize
3. Ask questions like:
   - "What can you tell me about github.com/torvalds?"
   - "Analyze the user octocat"
   - "Would this person be good for a Senior Backend Developer position?"
   - "What are their strongest programming languages?"

## Project Structure

```text
.
├── bot.py              # Main bot application
├── ai_agent.py         # Gemini AI integration with function calling
├── github_client.py    # GitHub API client
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── README.md          # This file
```

## Architecture

- **bot.py**: Telegram bot handlers and main event loop
- **ai_agent.py**: Gemini model with function calling capabilities
- **github_client.py**: Fetches GitHub user data, repositories, and READMEs

The bot uses Gemini's function calling feature to automatically invoke the GitHub API when needed, making the interaction feel natural and intelligent.

## Notes

- The bot uses `gemini-1.5-flash` by default for speed and cost-efficiency
- GitHub API rate limits: 60 requests/hour (unauthenticated) or 5,000/hour (with token)
- The bot runs synchronous Gemini calls in an executor to avoid blocking the async event loop

## License

MIT
