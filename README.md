# Mock View — AI Interview Preparation Bot

An AI-powered interview simulator that generates unique technical or behavioral questions per role/domain, evaluates your answers with detailed feedback and scoring, and produces a structured final report with suggested learning resources.

## Highlights

- Role-aware interviews: Software Engineer, Data Scientist, Product Manager, DevOps Engineer, UX Designer
- Domain targeting: Frontend, Backend, System Design, Machine Learning, NLP, and more
- Technical and Behavioral modes with distinct prompts and constraints
- Unique questions per interview with over-generate → deduplicate → exclude pass
- Per-question feedback: big score, key points (bulleted), model answer
- Final feedback: final score, dropdowns per question, overall summary, strengths, improvements, AI-suggested resources
- Modern UI/UX (dark theme, cards, progress, full-width sidebar, improved spacing)
- PDF export with clean formatting and preserved line breaks
- Session save/load and history in `sessions/`

## Technical Interview Spec

- Categories (balanced mix):
  - Algorithms/Coding (≥30–40%): inputs/outputs, constraints, complexity
  - System Design (≥20%): scalability, reliability, data modeling, trade-offs
  - Role-specific technical concepts and domain-specific topics (≥20%)
  - OS, Networks, Database fundamentals (≥10% each) as applicable
  - Factual definitions (≥1) for core concepts
- Strictly excludes behavioral topics (teamwork, leadership, ownership, conflict resolution, etc.)
- Each question is unique, self-contained, assessable, and tests a distinct concept

## Behavioral Interview Spec

- STAR-style prompts with variety across teamwork, leadership, conflict resolution, communication, ambiguity, stakeholders
- Strictly excludes coding/system design/technical definition prompts
- Unique, measurable-outcome oriented

## Feedback & Scoring

- Per question: large numeric score with progress bar, distilled key points, model answer
- Final report (with dropdowns):
  1. Final score
  2. Each question’s feedback (expander per question)
  3. Overall summary
  4. Areas of strength
  5. Areas to improve
  6. Suggested resources (AI-generated)

## AI-Suggested Resources

- Uses the interview summary (gaps + role/domain + type) to ask the model for a JSON list of authoritative resources
- Renders clickable links; falls back gracefully if non-JSON

## Architecture

- Frontend: Streamlit (`app.py`) with custom theme/CSS (`styles.css`)
- Core logic: `interview_logic.py`
  - LangChain `ChatOpenAI` + `ChatPromptTemplate`
  - Question generation: over-generate → deduplicate → exclude-on-second-pass → fallback for distinct factual prompts
  - Evaluation prompt tailored per type (Technical vs Behavioral)
  - Final summary prompts tailored per type
  - AI resource generator returns [ { title, url } ] JSON
- Sessions/Export: `session_manager.py`
  - Saves JSON sessions to `sessions/`
  - PDF export via `pdfkit` + wkhtmltopdf

## Setup

1. Clone and enter the directory
```bash
git clone <your-repo>
cd InterviewBot
```
2. Create and activate a virtual environment
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```
3. Install dependencies
```bash
pip install -r requirements.txt
```
4. Configure environment
Create `.env` with:
```
OPENAI_API_KEY=your_api_key_here
```
5. Run
```bash
streamlit run app.py
```

## Usage

- Select role, optional domain, interview type, and number of questions
- Answer each question and submit to get immediate scoring and feedback
- After finishing, review the final report and download the PDF

## PDF Export Requirements

- Requires `pdfkit` Python package and the `wkhtmltopdf` binary installed on the system
- On Windows: install wkhtmltopdf and ensure it’s available at a standard path or in PATH

## Project Structure

- `app.py` — Streamlit app, UI flow, downloads
- `interview_logic.py` — LangChain prompts, question generation, evaluation, summary, resources
- `session_manager.py` — Save sessions, export to PDF
- `styles.css` — UI theme and layout
- `.streamlit/config.toml` — Streamlit theme configuration
- `sessions/` — Saved sessions and PDFs

## Configuration

- Model: default `gpt-3.5-turbo` via LangChain `ChatOpenAI` (set in `interview_logic.py`)
- Update the model or temperature as needed; environment key: `OPENAI_API_KEY`

## Roadmap

- Add keyboard shortcuts (submit/next)
- Option to tune category weighting
- Export final report with identical layout to PDF

## License

MIT (or your chosen license)
