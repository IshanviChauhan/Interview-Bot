import streamlit as st
import os
from interview_logic import InterviewBot
from session_manager import SessionManager
from dotenv import load_dotenv

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
            # Calculate current question number and total questions
            current_idx = st.session_state.interview_bot.current_question_index
            total_questions = len(st.session_state.interview_bot.questions)
            
            # Display question number and progress
            st.subheader(f"Question {current_idx + 1} of {total_questions}")
            st.write(st.session_state.current_question)
            
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
            answer = st.text_area("Your Answer:", 
                                value=st.session_state.current_answer,
                                height=150,
                                key=f"answer_{current_idx}",
                                disabled=st.session_state.answer_submitted)  # Disable after submission
            
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
                # Score and Feedback section
                st.markdown("### Your Score")
                st.progress(st.session_state.current_score)
                st.write(f"Score: {st.session_state.current_score * 10:.1f}/10")
                
                st.markdown("### Feedback")
                st.write(st.session_state.current_feedback)
                
                st.markdown("### Model Answer")
                st.write(st.session_state.interview_bot.ideal_answers[current_idx])
        
        else:
            # Show final summary
            st.subheader("Interview Complete! 🎯")
            summary = st.session_state.interview_bot.generate_final_summary()
            
            # Overall score with visual indicator
            st.markdown("### Overall Performance")
            final_score = summary['average_score']*10
            st.progress(summary['average_score'])
            st.markdown(f"### Final Score: {final_score:.1f}/10")
            
            # Question by Question Analysis
            st.markdown("### Detailed Analysis")
            for i, (q, a, ideal_a, f, s) in enumerate(zip(
                st.session_state.interview_bot.questions,
                st.session_state.interview_bot.answers,
                st.session_state.interview_bot.ideal_answers,
                st.session_state.interview_bot.feedback,
                st.session_state.interview_bot.scores
            )):
                with st.expander(f"Question {i+1}: {q[:100]}..."):
                    st.markdown("### Question")
                    st.write(q)
                    
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.markdown("### Your Answer")
                        st.write(a)
                        st.progress(s)
                        st.markdown(f"Score: {s*10:.1f}/10")
                    
                    with col2:
                        st.markdown("### Model Answer")
                        st.write(ideal_a)
                    
                    st.markdown("### Feedback")
                    st.write(f)
            
            # Summary section
            st.markdown("### Summary Evaluation")
            st.write(summary['summary'])
            
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
