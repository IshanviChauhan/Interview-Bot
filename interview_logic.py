from openai import OpenAI
from typing import Dict, List, Tuple
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client lazily to ensure environment is properly set up
client = None

def get_client():
    global client
    if client is None:
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OpenAI API key is not set in the environment")
        client = OpenAI()
    return client

class InterviewBot:
    def __init__(self, role: str, domain: str = None, interview_type: str = "technical"):
        self.role = role
        self.domain = domain
        self.interview_type = interview_type
        self.current_question_index = 0
        self.questions = []
        self.answers = []
        self.feedback = []
        self.scores = []

    def generate_questions(self, num_questions: int = 3) -> List[str]:
        """Generate interview questions based on role, domain, and interview type."""
        prompt = self._create_questions_prompt(num_questions)
        
        response = get_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are an expert technical interviewer specializing in {self.role} positions with extensive industry experience. You create challenging but fair interview questions that assess both theoretical knowledge and practical skills."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse the response and extract questions
        questions = response.choices[0].message.content.strip().split('\n')
        self.questions = [q.strip('1234567890. ') for q in questions if q.strip()]
        return self.questions

    def evaluate_answer(self, answer: str) -> Tuple[str, float]:
        """Evaluate the candidate's answer and provide feedback with scoring."""
        if not self.questions:
            raise ValueError("No questions available. Generate questions first.")
            
        current_question = self.questions[self.current_question_index]
        
        prompt = self._create_evaluation_prompt(current_question, answer)
        
        response = get_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are an expert {self.role} interviewer with deep industry experience. You provide detailed, constructive feedback that helps candidates improve their technical and communication skills. Your evaluation is based on industry standards and best practices specific to {self.domain if self.domain else 'the role'}."},
                {"role": "user", "content": prompt}
            ]
        )
        
        feedback = response.choices[0].message.content
        
        # Extract score from feedback (assuming it's in the format "Score: X/10")
        try:
            score = float(feedback.split("Score:")[1].split("/")[0].strip()) / 10
        except:
            score = 0.5  # Default score if parsing fails
            
        self.answers.append(answer)
        self.feedback.append(feedback)
        self.scores.append(score)
        
        return feedback, score

    def generate_final_summary(self) -> Dict:
        """Generate a final summary of the interview session."""
        if not self.answers:
            raise ValueError("No answers to summarize.")
            
        prompt = f"""
        Based on the following interview session, provide a comprehensive summary:
        Role: {self.role}
        Domain: {self.domain}
        Interview Type: {self.interview_type}
        
        Questions and Answers:
        {self._format_qa_pairs()}
        
        Please provide:
        1. Top 3 strengths
        2. Top 3 areas for improvement
        3. Specific resources for improvement
        4. Overall score (0-10)
        """
        
        response = get_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert interviewer providing a final evaluation."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            'summary': response.choices[0].message.content,
            'average_score': sum(self.scores) / len(self.scores) if self.scores else 0,
            'qa_pairs': list(zip(self.questions, self.answers, self.feedback))
        }

    def _create_questions_prompt(self, num_questions: int) -> str:
        """Create a prompt for generating interview questions."""
        role_specific_guidance = {
            "Software Engineer": """
                For technical questions, focus on:
                - Data structures and algorithms
                - System design and architecture
                - Code optimization and performance
                - Debugging and problem-solving
                - Software development best practices
                - Testing and quality assurance
            """,
            "Data Scientist": """
                For technical questions, focus on:
                - Statistical analysis and hypothesis testing
                - Machine learning algorithms and models
                - Data preprocessing and feature engineering
                - Model evaluation and validation
                - Big data technologies and tools
                - Experimental design and A/B testing
            """,
            "Product Manager": """
                For technical questions, focus on:
                - Product metrics and analytics
                - Feature prioritization and roadmap planning
                - User research and market analysis
                - Product development lifecycle
                - Stakeholder management
                - Technical feasibility assessment
            """,
            "DevOps Engineer": """
                For technical questions, focus on:
                - CI/CD pipelines and automation
                - Infrastructure as Code (IaC)
                - Cloud platforms and services
                - Container orchestration and microservices
                - Monitoring and logging
                - Security and compliance
            """,
            "UX Designer": """
                For technical questions, focus on:
                - User research methods and tools
                - Design systems and patterns
                - Prototyping and wireframing
                - Usability testing and metrics
                - Accessibility standards
                - Design tools and workflows
            """
        }.get(self.role, "")

        domain_specific_guidance = {
            # Software Engineer domains
            "Frontend Development": """
                Focus on:
                - Modern JavaScript frameworks (React, Vue, Angular)
                - Web performance optimization
                - Responsive design and CSS architecture
                - Browser APIs and compatibility
                - State management and data flow
                - Web accessibility standards
            """,
            "Backend Development": """
                Focus on:
                - API design and RESTful principles
                - Database design and optimization
                - Authentication and authorization
                - Microservices architecture
                - Message queues and async processing
                - Security best practices
            """,
            "Full Stack Development": """
                Focus on:
                - End-to-end application architecture
                - Frontend and backend integration
                - Database design and ORM usage
                - API design and implementation
                - Performance optimization
                - Development workflows
            """,
            "Mobile Development": """
                Focus on:
                - Native app development
                - Cross-platform frameworks
                - Mobile UI/UX best practices
                - App performance optimization
                - Mobile security
                - App lifecycle management
            """,
            # Data Scientist domains
            "Machine Learning": """
                Focus on:
                - ML algorithms and model selection
                - Feature engineering
                - Model evaluation metrics
                - Hyperparameter tuning
                - ML system design
                - Model deployment
            """,
            "Deep Learning": """
                Focus on:
                - Neural network architectures
                - Deep learning frameworks
                - Model optimization
                - Transfer learning
                - GPU acceleration
                - Training large models
            """,
            "Natural Language Processing": """
                Focus on:
                - Text preprocessing
                - Language models
                - Sentiment analysis
                - Named entity recognition
                - Machine translation
                - Document classification
            """,
            # DevOps Engineer domains
            "Cloud Infrastructure": """
                Focus on:
                - Cloud service architecture
                - Infrastructure as Code
                - Cost optimization
                - Multi-cloud strategy
                - Cloud security
                - Disaster recovery
            """,
            "CI/CD Pipeline": """
                Focus on:
                - Pipeline design and implementation
                - Build automation
                - Deployment strategies
                - Testing integration
                - Release management
                - Pipeline security
            """,
            "Site Reliability": """
                Focus on:
                - System reliability
                - Monitoring and alerting
                - Incident response
                - Performance optimization
                - Chaos engineering
                - SLO/SLA management
            """,
            # UX Designer domains
            "Mobile Design": """
                Focus on:
                - Mobile UI patterns
                - Gesture-based interactions
                - Platform guidelines
                - Responsive layouts
                - Mobile usability
                - Touch interfaces
            """,
            "Product Design": """
                Focus on:
                - Product thinking
                - User research
                - Design systems
                - Interaction patterns
                - Usability testing
                - Design documentation
            """,
            "Design Systems": """
                Focus on:
                - Component libraries
                - Design tokens
                - Documentation
                - Version control
                - Team collaboration
                - Implementation guidelines
            """
        }.get(self.domain, "")

        base_prompt = f"""
        Generate {num_questions} {'technical' if self.interview_type == 'technical' else 'behavioral'} 
        interview questions for a {self.role} position 
        {f'with focus on {self.domain}' if self.domain else ''}.

        {'For behavioral questions, ensure questions follow the STAR format and assess leadership, teamwork, conflict resolution, and problem-solving abilities.' if self.interview_type == 'behavioral' else f'''
        For technical questions:
        {role_specific_guidance}
        {domain_specific_guidance if self.domain else ''}
        
        Ensure questions:
        1. Are practical and scenario-based
        2. Test both theoretical knowledge and practical implementation
        3. Include problem-solving components
        4. Are relevant to current industry practices
        5. Have clear evaluation criteria
        '''}

        Question requirements:
        1. Be clear and specific
        2. Match senior-level interview difficulty
        3. Focus on real-world scenarios
        4. Enable candidates to demonstrate depth of knowledge

        Format: Provide just the questions, one per line, numbered.
        """
        return base_prompt

    def _create_evaluation_prompt(self, question: str, answer: str) -> str:
        """Create a prompt for evaluating an answer."""
        technical_criteria = {
            "Software Engineer": [
                "Code quality and best practices",
                "Algorithm efficiency and optimization",
                "System design considerations",
                "Error handling and edge cases",
                "Scalability considerations"
            ],
            "Data Scientist": [
                "Statistical reasoning",
                "Model selection and justification",
                "Data preprocessing considerations",
                "Evaluation metrics understanding",
                "Business impact awareness"
            ],
            "Product Manager": [
                "Product thinking and strategy",
                "Data-driven decision making",
                "Stakeholder consideration",
                "Technical feasibility assessment",
                "Market understanding"
            ],
            "DevOps Engineer": [
                "Automation and efficiency",
                "Security considerations",
                "Scalability planning",
                "Monitoring and reliability",
                "Infrastructure design"
            ],
            "UX Designer": [
                "User-centered design thinking",
                "Research methodology",
                "Design system consistency",
                "Accessibility considerations",
                "Interaction design patterns"
            ]
        }

        role_criteria = technical_criteria.get(self.role, [])
        
        return f"""
        Question: {question}
        Candidate's Answer: {answer}
        
        {'Evaluate the response based on STAR format criteria:' if self.interview_type == 'behavioral' else f'Evaluate the technical response based on these role-specific criteria:'}
        
        {'''1. Situation: Clear context and background
        2. Task: Specific role and responsibilities
        3. Action: Detailed steps taken
        4. Result: Quantifiable outcomes and learning''' if self.interview_type == 'behavioral' else f'''1. Technical Accuracy:
           - Correctness of technical concepts
           - {"\\n           - ".join(role_criteria) if role_criteria else "Understanding of core principles"}
        2. Problem-Solving Approach:
           - Methodology and structure
           - Consideration of alternatives
           - Optimization and improvements
        3. Real-world Application:
           - Practical implementation
           - Industry best practices
           - Scalability and maintenance'''}
        
        4. Communication:
           - Clarity of explanation
           - Technical terminology usage
           - Structured response
        
        Provide a detailed evaluation with:
        1. Key Strengths (specific examples)
        2. Areas for Improvement (with actionable suggestions)
        3. Score: X/10 (where X is your numerical score)
        
        Note: Consider both depth of knowledge and practical application in scoring.
        """

    def _format_qa_pairs(self) -> str:
        """Format all Q&A pairs for summary generation."""
        pairs = []
        for q, a in zip(self.questions, self.answers):
            pairs.append(f"Q: {q}\nA: {a}\n")
        return "\n".join(pairs)
