import streamlit as st
import os
from interview_logic import InterviewBot
from session_manager import SessionManager
from dotenv import load_dotenv
import html
import re

# Page config must be the first Streamlit call
st.set_page_config(
    page_title="Mock View",
    page_icon="🎯",
    layout="wide",
)

# Get API key from environment variables
api_key = None

# For Streamlit Cloud, check secrets first
if hasattr(st, "secrets"):
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception as e:
        st.warning("Could not load API key from Streamlit secrets")

# If no API key yet, try local .env file
if not api_key:
    try:
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
    except Exception as e:
        st.warning("Could not load API key from .env file")

# Final check for API key
if not api_key:
    st.error("""
    OpenAI API key not found. Please set it in one of:
    1. Streamlit Cloud Secrets
    2. Local .env file
    
    To set up Streamlit Cloud Secrets:
    1. Go to your app dashboard
    2. Click on 'Manage app' ⚙️
    3. Go to 'Secrets' section
    4. Add your key as: OPENAI_API_KEY = "your-api-key-here"
    """)
    st.stop()

# Set the API key in environment
os.environ["OPENAI_API_KEY"] = api_key

# Initialize session state
if 'interview_bot' not in st.session_state:
    st.session_state.interview_bot = None
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'interview_complete' not in st.session_state:
    st.session_state.interview_complete = False
if 'session_manager' not in st.session_state:
    st.session_state.session_manager = SessionManager()

def get_domains_for_role(role: str) -> list:
    """Get relevant domains for the selected role."""
    role_domains = {
        "Software Engineer": [
            "",
            "Frontend Development",
            "Backend Development",
            "Full Stack Development",
            "Mobile Development",
            "System Design",
            "Cloud & DevOps",
            "Security Engineering",
            "Game Development",
            "Embedded Systems"
        ],
        "Data Scientist": [
            "",
            "Machine Learning",
            "Deep Learning",
            "Natural Language Processing",
            "Computer Vision",
            "Data Analytics",
            "Big Data Engineering",
            "MLOps",
            "Quantitative Analysis",
            "Business Intelligence"
        ],
        "Product Manager": [
            "",
            "Consumer Products",
            "Enterprise Software",
            "Mobile Applications",
            "Data Products",
            "AI/ML Products",
            "E-commerce",
            "FinTech",
            "Healthcare Tech",
            "Developer Tools"
        ],
        "DevOps Engineer": [
            "",
            "Cloud Infrastructure",
            "CI/CD Pipeline",
            "Container Orchestration",
            "Site Reliability",
            "Infrastructure Automation",
            "Security Operations",
            "Platform Engineering",
            "Network Operations",
            "Database Operations"
        ],
        "UX Designer": [
            "",
            "Mobile Design",
            "Web Design",
            "Product Design",
            "Interaction Design",
            "Service Design",
            "Design Systems",
            "Research & Testing",
            "Information Architecture",
            "Accessibility"
        ]
    }
    return role_domains.get(role, [""])

def initialize_interview():
    """Initialize a new interview session."""
    st.session_state.interview_bot = InterviewBot(
        role=st.session_state.role,
        domain=st.session_state.domain,
        interview_type=st.session_state.interview_type
    )
    questions = st.session_state.interview_bot.generate_questions(
        num_questions=st.session_state.num_questions
    )
    st.session_state.current_question = questions[0]
    st.session_state.interview_complete = False

def _strip_markdown(text: str) -> str:
    """Remove common markdown symbols (#, *, _, >, backticks, links, etc.)."""
    if not text:
        return ""
    # Remove code fences and inline code
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    # Remove headings and blockquotes
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    # Remove list markers
    text = re.sub(r"^\s*[\-\*\+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+[\.)]\s+", "", text, flags=re.MULTILINE)
    # Remove emphasis markers
    text = text.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    # Convert markdown links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    return text.strip()

def _bulletify_feedback(raw_feedback: str, max_items: int = 5) -> str:
    """Convert raw feedback text into a short bullet list HTML without markdown symbols."""
    if not raw_feedback:
        return "<ul class=\"bullets\"><li>No feedback available.</li></ul>"
    lines = [l.strip() for l in (raw_feedback or "").splitlines()]
    lines = [l for l in lines if l]
    # If feedback is one long paragraph, split into sentences
    if len(lines) <= 1 and lines:
        sentences = re.split(r"(?<=[.!?])\s+", lines[0])
        lines = [s.strip() for s in sentences if s.strip()]
    bullets = [_strip_markdown(l) for l in lines][:max_items]
    items_html = "\n".join([f"<li>{html.escape(item)}</li>" for item in bullets if item])
    return f"<ul class=\"bullets\">{items_html}</ul>"

def _parse_final_summary(text: str) -> dict:
    """Parse LLM final summary into sections: summary, strengths, improvements, resources, overall_score."""
    if not text:
        return {"summary": "", "strengths": [], "improvements": [], "resources": [], "overall_score": None}
    cleaned = _strip_markdown(text)
    # Split by lines and detect sections
    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
    sections = {"summary": [], "strengths": [], "improvements": [], "resources": [], "overall_score": None}
    current = "summary"
    for line in lines:
        low = line.lower()
        if "strength" in low and ("area" not in low or "strength" in low and "areas" not in low) and len(line) < 60:
            current = "strengths"; continue
        if ("areas for improvement" in low) or ("improvement" in low and len(line) < 60):
            current = "improvements"; continue
        if ("resource" in low) and len(line) < 60:
            current = "resources"; continue
        if ("overall score" in low) or re.match(r"^score\s*[: ]", low):
            # try to grab score
            m = re.search(r"(\d+(?:\.\d+)?)\s*/?\s*10", low)
            if m:
                sections["overall_score"] = float(m.group(1))
            current = "summary"; continue
        sections[current].append(line)
    return sections

def _format_resource_item(title: str, url: str) -> str:
    safe_title = html.escape(title or "")
    if isinstance(url, str) and (url.startswith("https://") or url.startswith("http://")):
        safe_url = html.escape(url)
        return f"<li><a href=\"{safe_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{safe_title}</a></li>"
    return f"<li>{safe_title}</li>"

def main():
    # Inject base CSS
    try:
        with open("styles.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        pass

    st.markdown("<h1 class=\"app-title\">Mock View</h1>", unsafe_allow_html=True)
    st.caption("Practice interviews tailored to your role, get instant feedback, and track performance.")
    
    # Sidebar for setup
    with st.sidebar:
        st.header("Interview Setup")
        
        # Role selection
        roles = ["Software Engineer", "Data Scientist", "Product Manager", 
                "DevOps Engineer", "UX Designer"]
        selected_role = st.selectbox("Select Role:", roles, key="role_selector")
        st.session_state.role = selected_role
        
        # Domain selection - dynamically updated based on role
        available_domains = get_domains_for_role(selected_role)
        st.session_state.domain = st.selectbox(
            "Select Domain (Optional):", 
            available_domains,
            help=f"Specialized areas within {selected_role} role"
        )
        
        # Interview type
        st.session_state.interview_type = st.radio(
            "Interview Type:",
            ["Technical", "Behavioral"]
        )
        
        # Number of questions
        st.session_state.num_questions = st.slider(
            "Number of Questions:",
            min_value=3,
            max_value=10,
            value=5
        )
        
        # Start button
        if st.button("Start New Interview"):
            initialize_interview()

    # Main interview interface
    if st.session_state.interview_bot is None:
        st.info("👈 Please set up your interview parameters and click 'Start New Interview'")
    else:
        if not st.session_state.interview_complete:
            # Calculate current question number and total questions
            current_idx = st.session_state.interview_bot.current_question_index
            total_questions = len(st.session_state.interview_bot.questions)

            # Top progress
            progress_ratio = max(0, min(1, current_idx / max(1, total_questions)))
            st.progress(progress_ratio)
            
            # Display question number and progress
            st.subheader(f"Question {current_idx + 1} of {total_questions}")
            st.markdown(f"""
<div class=\"card\">
<p style=\"margin: 0; font-size: 1.05rem; line-height: 1.6;\">{st.session_state.current_question}</p>
</div>
""", unsafe_allow_html=True)
            
            # Initialize session state variables if not exists
            if 'current_answer' not in st.session_state:
                st.session_state.current_answer = ""
            if 'current_feedback' not in st.session_state:
                st.session_state.current_feedback = None
            if 'current_score' not in st.session_state:
                st.session_state.current_score = None
                
            # Initialize answer_submitted in session state if not exists
            if 'answer_submitted' not in st.session_state:
                st.session_state.answer_submitted = False

            # Answer input with session state
            answer = st.text_area(
                "Your Answer:", 
                value=st.session_state.current_answer,
                height=180,
                key=f"answer_{current_idx}",
                disabled=st.session_state.answer_submitted
            )
            
            # Create columns for button alignment
            left_align, _ = st.columns([1, 3])
            
            # Submit or Next Question button (aligned left)
            with left_align:
                if not st.session_state.answer_submitted:
                    if st.button("Submit Answer"):
                        if answer:
                            feedback, score = st.session_state.interview_bot.evaluate_answer(answer)
                            # Store feedback and score in session state
                            st.session_state.current_feedback = feedback
                            st.session_state.current_score = score
                            st.session_state.answer_submitted = True
                            st.session_state.current_answer = answer
                            st.rerun()
                elif current_idx < total_questions - 1:
                    if st.button("Next Question ➡️", key="next_question"):
                        st.session_state.interview_bot.current_question_index += 1
                        st.session_state.current_question = (
                            st.session_state.interview_bot.questions[current_idx + 1]
                        )
                        # Reset for next question
                        st.session_state.current_answer = ""
                        st.session_state.current_feedback = None
                        st.session_state.current_score = None
                        st.session_state.answer_submitted = False
                        st.rerun()
                else:
                    if st.button("Complete Interview ✨", key="complete"):
                        st.session_state.interview_complete = True
                        st.rerun()
            
            # Show feedback, score, and ideal answer after submission
            if st.session_state.answer_submitted:
                # 1) Big score + bar
                score_val = st.session_state.current_score or 0
                score_out_of_10 = score_val * 10
                st.markdown("""
<div class="card">
	<div class="section-header">Score</div>
	<div style="display:flex;gap:12px;align-items:center;">
		<div style="font-size: 2.4rem; font-weight: 800; line-height: 1;">{:.1f}</div>
		<div style="flex:1;">
			<div style="font-size: 0.9rem; opacity:0.85;">out of 10</div>
		</div>
	</div>
</div>
""".format(score_out_of_10), unsafe_allow_html=True)
                st.progress(score_val)
                
                # 2) Short bullet summary from feedback
                bullets_html = _bulletify_feedback(st.session_state.current_feedback)
                st.markdown(f"""
<div class="card">
	<div class="section-header">Key Points</div>
	{bullets_html}
</div>
""", unsafe_allow_html=True)
                
                # 3) Model answer (content enclosed within the card)
                model_answer_html = html.escape(_strip_markdown(st.session_state.interview_bot.ideal_answers[current_idx] or "")).replace('\n','<br>')
                st.markdown(f"""
<div class="card">
	<div class="section-header">Model Answer</div>
	<div class="model-answer">{model_answer_html}</div>
</div>
""", unsafe_allow_html=True)
        
        else:
            # Show final summary structured per requested format
            st.subheader("Final Feedback")
            summary = st.session_state.interview_bot.generate_final_summary()
            parsed = _parse_final_summary(summary.get('summary', ''))
            
            # 1) Final score
            final_score = summary['average_score'] * 10
            disp_score = parsed['overall_score'] if parsed['overall_score'] is not None else final_score
            st.markdown("""
<div class="card">
	<div class="section-header">Final Score</div>
	<div style="display:flex;gap:12px;align-items:center;">
		<div style="font-size: 2.6rem; font-weight: 800; line-height: 1;">{:.1f}</div>
		<div style="flex:1;">
			<div style="font-size: 0.9rem; opacity:0.85;">out of 10</div>
		</div>
	</div>
</div>
""".format(disp_score), unsafe_allow_html=True)
            st.progress(min(1.0, max(0.0, (disp_score/10) if disp_score else 0)))
            
            # 2) Feedback of each question and model answer (dropdowns)
            st.markdown("""
<div class="card">
	<div class="section-header">Question-by-Question Feedback</div>
</div>
""", unsafe_allow_html=True)
            for i, (q, a, f) in enumerate(summary['qa_pairs']):
                q_clean = _strip_markdown(q)
                label = f"Q{i+1}: {q_clean[:90]}{'...' if len(q_clean) > 90 else ''}"
                with st.expander(label, expanded=False):
                    q_html = html.escape(q_clean).replace('\n','<br>')
                    a_html = html.escape(_strip_markdown(a)).replace('\n','<br>')
                    f_bullets = _bulletify_feedback(f, max_items=6)
                    model = st.session_state.interview_bot.ideal_answers[i] if i < len(st.session_state.interview_bot.ideal_answers) else ""
                    m_html = html.escape(_strip_markdown(model)).replace('\n','<br>')
                    st.markdown(f"""
<div class="card">
	<div style="font-weight:700; margin-bottom:8px;">Q{i+1}. {q_html}</div>
	<div style="opacity:0.85; margin-bottom:8px;">Your Answer</div>
	<div class="model-answer" style="margin-bottom:10px;">{a_html}</div>
	<div style="opacity:0.85; margin-bottom:6px;">Key Points</div>
	{f_bullets}
	<div class="section-header" style="margin-top:12px;">Model Answer</div>
	<div class="model-answer">{m_html}</div>
</div>
""", unsafe_allow_html=True)
            
            # 3) Overall feedback summary
            overall_text = html.escape("\n".join(parsed['summary'])).replace('\n','<br>')
            st.markdown(f"""
<div class="card">
	<div class="section-header">Overall Feedback Summary</div>
	<div class="model-answer">{overall_text}</div>
</div>
""", unsafe_allow_html=True)
            
            # 4) Areas of strength
            strengths_items = "\n".join([f"<li>{html.escape(it)}</li>" for it in parsed['strengths']]) or "<li>Not specified.</li>"
            st.markdown(f"""
<div class="card">
	<div class="section-header">Areas of Strength</div>
	<ul class="bullets">{strengths_items}</ul>
</div>
""", unsafe_allow_html=True)
            
            # 5) Areas to improve
            improve_items = "\n".join([f"<li>{html.escape(it)}</li>" for it in parsed['improvements']]) or "<li>Not specified.</li>"
            st.markdown(f"""
<div class="card">
	<div class="section-header">Areas to Improve</div>
	<ul class="bullets">{improve_items}</ul>
</div>
""", unsafe_allow_html=True)
            
            # 6) Suggested resources (AI-generated)
            ai_resources = st.session_state.interview_bot.generate_learning_resources(
                session_summary=summary.get('summary', ''),
                num_items=8,
            )
            if ai_resources:
                items_html = "\n".join([_format_resource_item(t, u) for t, u in ai_resources])
            else:
                items_html = "<li>No resources suggested.</li>"
            st.markdown(f"""
<div class="card">
	<div class="section-header">Suggested Resources</div>
	<ul class="bullets">{items_html}</ul>
</div>
""", unsafe_allow_html=True)
            
            # Export options
            if st.button("Export to PDF"):
                try:
                    session_data = {
                        'role': st.session_state.role,
                        'domain': st.session_state.domain,
                        'interview_type': st.session_state.interview_type,
                        'summary': summary['summary'],
                        'average_score': summary['average_score'],
                        'qa_pairs': summary['qa_pairs']
                    }
                    
                    # Save session and export to PDF
                    session_path = st.session_state.session_manager.save_session(session_data)
                    pdf_path = session_path.replace('.json', '.pdf')
                    
                    try:
                        st.session_state.session_manager.export_to_pdf(session_data, pdf_path)
                        st.success(f"Interview session exported to: {pdf_path}")
                        # Offer direct download
                        try:
                            with open(pdf_path, 'rb') as f:
                                pdf_bytes = f.read()
                            st.download_button(
                                label="Download PDF",
                                data=pdf_bytes,
                                file_name=os.path.basename(pdf_path),
                                mime="application/pdf",
                                key=f"download_pdf_{os.path.basename(pdf_path)}"
                            )
                        except Exception as read_err:
                            st.warning(f"PDF created but could not read file for download: {read_err}")
                    except ImportError as e:
                        st.error(str(e))
                        st.info("Your session has been saved as JSON. Install the required dependencies to export as PDF.")
                    except OSError as e:
                        st.error(str(e))
                        st.info("Your session has been saved as JSON. Install wkhtmltopdf to export as PDF.")
                except Exception as e:
                    st.error(f"An error occurred while saving the session: {str(e)}")

if __name__ == "__main__":
    main()
