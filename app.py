import streamlit as st
import os
from interview_logic import InterviewBot
from session_manager import SessionManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()  # Load from .env file for local development

# For Streamlit Cloud deployment, use secrets
if os.getenv("OPENAI_API_KEY") is None and hasattr(st, "secrets"):
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

if "OPENAI_API_KEY" not in os.environ:
    st.error("OpenAI API key not found. Please set it in .env file or Streamlit secrets.")
    st.stop()

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

def main():
    st.title("Interview Preparation Bot")
    
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
            st.subheader("Current Question")
            st.write(st.session_state.current_question)
            
            # Answer input
            answer = st.text_area("Your Answer:", height=150)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("Submit"):
                    if answer:
                        feedback, score = st.session_state.interview_bot.evaluate_answer(answer)
                        st.session_state.last_feedback = feedback
                        st.session_state.last_score = score
                        
                        # Move to next question or complete interview
                        current_idx = st.session_state.interview_bot.current_question_index
                        if current_idx < len(st.session_state.interview_bot.questions) - 1:
                            st.session_state.interview_bot.current_question_index += 1
                            st.session_state.current_question = (
                                st.session_state.interview_bot.questions[current_idx + 1]
                            )
                        else:
                            st.session_state.interview_complete = True
                        st.rerun()
            
            with col2:
                if st.button("Skip Question"):
                    current_idx = st.session_state.interview_bot.current_question_index
                    if current_idx < len(st.session_state.interview_bot.questions) - 1:
                        st.session_state.interview_bot.current_question_index += 1
                        st.session_state.current_question = (
                            st.session_state.interview_bot.questions[current_idx + 1]
                        )
                        st.rerun()
            
            # Show feedback if available
            if hasattr(st.session_state, 'last_feedback'):
                st.subheader("Feedback")
                st.write(st.session_state.last_feedback)
                st.progress(st.session_state.last_score)
        
        else:
            # Show final summary
            st.subheader("Interview Complete!")
            summary = st.session_state.interview_bot.generate_final_summary()
            
            st.write(summary['summary'])
            st.subheader(f"Final Score: {summary['average_score']*10:.1f}/10")
            
            # Export options
            if st.button("Export to PDF"):
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
                st.session_state.session_manager.export_to_pdf(session_data, pdf_path)
                
                st.success(f"Interview session exported to: {pdf_path}")

if __name__ == "__main__":
    main()
