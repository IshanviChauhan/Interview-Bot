# Interview Preparation Bot

An AI-powered interview preparation tool that simulates technical and behavioral interviews for various roles and provides detailed feedback.

## Features

- Multiple role-specific interviews (Software Engineer, Data Scientist, Product Manager, etc.)
- Domain-specific technical questions
- Real-time feedback and scoring
- Comprehensive session summaries
- PDF export of interview sessions

## Live Demo

Try it out here: [Interview Preparation Bot](https://interview-bot-ishanvi.streamlit.app)

## Local Development

1. Clone the repository:
```bash
git clone https://github.com/IshanviChauhan/Interview-Bot.git
cd Interview-Bot
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```
OPENAI_API_KEY=your_api_key_here
```

5. Run the application:
```bash
streamlit run app.py
```

## Deployment

This application is deployed using [Streamlit Cloud](https://streamlit.io/cloud).

To deploy your own version:

1. Fork this repository
2. Sign up for [Streamlit Cloud](https://share.streamlit.io)
3. Create a new app and select your forked repository
4. Add your `OPENAI_API_KEY` in the Streamlit Cloud secrets management
5. Deploy!

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

## Project Structure

- `app.py`: Main Streamlit application
- `interview_logic.py`: Core interview logic and OpenAI integration
- `session_manager.py`: Session state management and data persistence
- `.env`: Environment variables (not tracked in git)
- `requirements.txt`: Project dependencies

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
