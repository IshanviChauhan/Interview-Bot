from typing import Dict, List, Tuple
import os
from dotenv import load_dotenv
import json

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

_llm: ChatOpenAI | None = None

def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        _llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)
    return _llm

class InterviewBot:
    def __init__(self, role: str, domain: str | None = None, interview_type: str = "technical"):
        self.role = role
        self.domain = domain
        self.interview_type = interview_type
        self.current_question_index = 0
        self.questions: List[str] = []
        self.answers: List[str] = []
        self.feedback: List[str] = []
        self.scores: List[float] = []
        self.ideal_answers: List[str] = []

    def generate_questions(self, num_questions: int = 3) -> List[str]:
        # Pass 1: over-generate to reduce duplicates
        primary_count = num_questions + 5
        prompt_text = self._create_questions_prompt(primary_count)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert interviewer for {role}. For each question, provide an ideal answer that scores 10/10."),
            ("human", "{prompt_text}\n\nFormat strictly as 'Q1. [Question]\nA1. [Ideal Answer]\n\nQ2. [Question]\nA2. [Ideal Answer]' with no extra commentary."),
        ])
        llm = get_llm()
        content = prompt.format_messages(role=self.role, prompt_text=prompt_text, interview_type=self.interview_type)
        resp = llm.invoke(content)
        text1 = (resp.content or "").strip()
        p_qs, p_as = self._parse_qa_pairs(text1)

        # Deduplicate and take up to needed
        uniq_qs: List[str] = []
        uniq_as: List[str] = []
        seen = set()
        for q, a in zip(p_qs, p_as):
            key = q.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            uniq_qs.append(q)
            uniq_as.append(a)
            if len(uniq_qs) >= num_questions:
                break

        # Pass 2: If still short, ask for remaining excluding used
        remaining = num_questions - len(uniq_qs)
        if remaining > 0:
            exclude_list = "\n".join([f"- {q}" for q in uniq_qs])
            prompt_text2 = self._create_questions_prompt(remaining, exclude=exclude_list)
            prompt2 = ChatPromptTemplate.from_messages([
                ("system", "You are an expert interviewer for {role}. Ensure uniqueness vs the provided list."),
                ("human", "{prompt_text}\n\nFormat strictly as 'Q1. [Question]\nA1. [Ideal Answer]' with no extra commentary."),
            ])
            content2 = prompt2.format_messages(role=self.role, prompt_text=prompt_text2)
            resp2 = llm.invoke(content2)
            text2 = (resp2.content or "").strip()
            s_qs, s_as = self._parse_qa_pairs(text2)
            for q, a in zip(s_qs, s_as):
                key = q.lower().strip()
                if key in seen:
                    continue
                seen.add(key)
                uniq_qs.append(q)
                uniq_as.append(a)
                if len(uniq_qs) >= num_questions:
                    break

        # Final fallback: synthesize distinct factual prompts
        while len(uniq_qs) < num_questions:
            idx = len(uniq_qs) + 1
            topic_hint = [
                "CAP theorem",
                "ACID vs BASE",
                "eventual consistency",
                "CQRS",
                "OAuth2 vs OIDC",
                "Big-O of common operations",
                "REST vs gRPC",
                "indexing strategies",
                "cache eviction policies",
                "message queues vs streaming",
            ][(idx - 1) % 10]
            q = f"Define and explain {topic_hint} in the context of {self.role}{' - ' + self.domain if self.domain else ''}."
            a = f"Precise definition of {topic_hint}, core properties, when to use, and a succinct example."
            key = q.lower().strip()
            if key not in seen:
                seen.add(key)
                uniq_qs.append(q)
                uniq_as.append(a)

        self.questions = uniq_qs[:num_questions]
        self.ideal_answers = uniq_as[:num_questions]
        return self.questions

    def evaluate_answer(self, answer: str) -> Tuple[str, float]:
        if not self.questions:
            raise ValueError("No questions available. Generate questions first.")
        q = self.questions[self.current_question_index]
        eval_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert {role} interviewer (domain: {domain})."),
            ("human", "{prompt}"),
        ])
        prompt = self._create_evaluation_prompt(q, answer)
        llm = get_llm()
        msgs = eval_prompt.format_messages(role=self.role, domain=self.domain or 'general', prompt=prompt, interview_type=self.interview_type)
        resp = llm.invoke(msgs)
        feedback = resp.content or ""
        score = 0.5
        try:
            score = float(feedback.split("Score:")[1].split("/")[0].strip()) / 10
        except Exception:
            pass
        self.answers.append(answer)
        self.feedback.append(feedback)
        self.scores.append(score)
        return feedback, score

    def generate_final_summary(self) -> Dict:
        if not self.answers:
            raise ValueError("No answers to summarize.")
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert interviewer providing a final evaluation."),
            ("human", "{prompt}"),
        ])
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
        llm = get_llm()
        msgs = summary_prompt.format_messages(prompt=prompt)
        resp = llm.invoke(msgs)
        return {
            "summary": resp.content or "",
            "average_score": sum(self.scores) / len(self.scores) if self.scores else 0,
            "qa_pairs": list(zip(self.questions, self.answers, self.feedback)),
        }

    def generate_learning_resources(self, session_summary: str | None = None, num_items: int = 8) -> List[Tuple[str, str]]:
        summary_text = session_summary or ""
        role = self.role or ""
        domain = self.domain or ""
        itype = self.interview_type or ""
        resources_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that returns strict JSON when asked."),
            ("human", "{prompt}"),
        ])
        prompt = f"""
        Suggest {num_items} high-quality, up-to-date learning resources tailored to a candidate preparing for {role} {('in ' + domain) if domain else ''} ({itype}).
        Include docs, tutorials, courses, and books where appropriate. Prefer authoritative sources.
        Ensure relevance to both conceptual depth and factual knowledge areas.
        Consider this interview summary and gaps:
        ---
        {summary_text}
        ---
        Respond as a compact JSON array where each item is an object with keys: "title" and "url" (absolute https link). Example:
        [{{"title":"System Design Primer","url":"https://github.com/donnemartin/system-design-primer"}}]
        Do not add commentary outside JSON.
        """
        llm = get_llm()
        msgs = resources_prompt.format_messages(prompt=prompt)
        resp = llm.invoke(msgs)
        content = (resp.content or "").strip()
        resources: List[Tuple[str, str]] = []
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    title = (item.get("title") if isinstance(item, dict) else "") or "Resource"
                    url = (item.get("url") if isinstance(item, dict) else "") or ""
                    resources.append((str(title), str(url)))
        except Exception:
            for line in content.splitlines():
                if not line.strip():
                    continue
                parts = line.split(" - ", 1)
                if len(parts) == 2:
                    resources.append((parts[0].strip(), parts[1].strip()))
                else:
                    resources.append((line.strip(), ""))
        return resources

    def _create_questions_prompt(self, num_questions: int, exclude: str | None = None) -> str:
        role = self.role
        domain = self.domain or "general"
        
        if self.interview_type.lower() == "technical":
            # Create domain-specific technical prompts
            domain_context = self._get_technical_domain_context(role, domain)
            base = (
                f"Generate {num_questions} unique TECHNICAL interview questions for a {role} role"
                f"{' specializing in ' + domain if domain and domain != 'general' else ''}.\n\n"
                f"IMPORTANT: Focus ONLY on technical aspects. NO behavioral questions allowed.\n\n"
                f"Question Categories (balanced distribution):\n"
                f"- Algorithm/Coding Problems (≥40%): {domain_context['coding']}\n"
                f"- System Design (≥25%): {domain_context['system_design']}\n"
                f"- Domain-Specific Technical Concepts (≥25%): {domain_context['domain_concepts']}\n"
                f"- Technical Definitions & Best Practices (≥10%): {domain_context['definitions']}\n\n"
                f"Technical Requirements:\n"
                f"- Each question must test distinct technical knowledge or problem-solving skills\n"
                f"- Include specific technical constraints, requirements, or expected complexity analysis\n"
                f"- Questions should be relevant to {role} working in {domain if domain != 'general' else 'general software development'}\n"
                f"- STRICTLY AVOID: teamwork, leadership, conflict resolution, communication, project management\n\n"
                f"Example Technical Question Formats (adapt to {domain}):\n"
                f"{domain_context['examples']}\n"
            )
        else:  # Behavioral interview
            # Create domain-specific behavioral prompts
            domain_context = self._get_behavioral_domain_context(role, domain)
            base = (
                f"Generate {num_questions} unique BEHAVIORAL interview questions for a {role} role"
                f"{' in ' + domain if domain and domain != 'general' else ''}.\n\n"
                f"IMPORTANT: Focus ONLY on behavioral aspects using STAR method. NO technical questions allowed.\n\n"
                f"Behavioral Categories (use variety):\n"
                f"- Leadership & Influence: {domain_context['leadership']}\n"
                f"- Problem Solving & Decision Making: {domain_context['problem_solving']}\n"
                f"- Teamwork & Collaboration: {domain_context['collaboration']}\n"
                f"- Communication & Stakeholder Management: {domain_context['communication']}\n"
                f"- Adaptability & Learning: {domain_context['adaptability']}\n\n"
                f"Behavioral Requirements:\n"
                f"- Use STAR format prompts (Situation, Task, Action, Result)\n"
                f"- Questions should be relevant to {role} challenges in {domain if domain != 'general' else 'professional settings'}\n"
                f"- Encourage specific examples with measurable outcomes\n"
                f"- STRICTLY AVOID: coding problems, system design, technical definitions\n\n"
                f"Example Behavioral Question Formats (adapt to {domain}):\n"
                f"{domain_context['examples']}\n"
            )
        
        if exclude:
            base += "\n\nAVOID DUPLICATING these existing questions:\n" + exclude
        return base

    def _create_evaluation_prompt(self, question: str, answer: str) -> str:
        return f"""
        Question: {question}
        Candidate's Answer: {answer}
        
        Provide:
        - Key strengths (bullets)
        - Areas for improvement (bullets with actionable guidance)
        - Score: X/10 (numeric)
        """

    def _format_qa_pairs(self) -> str:
        return "\n".join([f"Q: {q}\nA: {a}\n" for q, a in zip(self.questions, self.answers)])

    def _get_technical_domain_context(self, role: str, domain: str) -> dict:
        """Get domain-specific technical context for question generation."""
        contexts = {
            "Software Engineer": {
                "Frontend Development": {
                    "coding": "React/Vue/Angular components, DOM manipulation, async JavaScript, responsive design algorithms",
                    "system_design": "Client-side architecture, state management, performance optimization, browser caching, CDN strategies",
                    "domain_concepts": "Virtual DOM, component lifecycle, bundling, CSS-in-JS, accessibility, PWA concepts",
                    "definitions": "Closure, hoisting, event bubbling, critical rendering path",
                    "examples": "  • Implement a debounced search component with React hooks\n  • Design a micro-frontend architecture for a large e-commerce platform\n  • Explain the difference between server-side and client-side rendering"
                },
                "Backend Development": {
                    "coding": "API design, database queries, concurrent programming, data structures for server applications",
                    "system_design": "Microservices architecture, load balancing, database sharding, caching layers, message queues",
                    "domain_concepts": "REST vs GraphQL, authentication/authorization, rate limiting, API versioning",
                    "definitions": "ACID properties, eventual consistency, idempotency, distributed systems concepts",
                    "examples": "  • Design a rate limiting algorithm for an API gateway\n  • Implement a distributed cache with consistent hashing\n  • Explain database indexing strategies for high-read workloads"
                },
                "Mobile Development": {
                    "coding": "Platform-specific algorithms, memory management, offline-first data structures, touch gesture handling",
                    "system_design": "App architecture patterns, data synchronization, push notification systems, cross-platform strategies",
                    "domain_concepts": "Native vs hybrid development, app lifecycle management, background processing",
                    "definitions": "Memory management in mobile, app store optimization, platform-specific UI guidelines",
                    "examples": "  • Implement an offline-first data synchronization mechanism\n  • Design a push notification system for a social media app\n  • Explain memory management strategies in iOS/Android"
                },
                "System Design": {
                    "coding": "Distributed algorithms, consensus protocols, load balancer implementations, data pipeline processing",
                    "system_design": "Large-scale system architecture, fault tolerance, scalability patterns, data consistency models",
                    "domain_concepts": "CAP theorem, distributed consensus, eventual consistency, sharding strategies",
                    "definitions": "Horizontal vs vertical scaling, consistent hashing, circuit breaker pattern",
                    "examples": "  • Design a globally distributed chat application like WhatsApp\n  • Implement a consistent hashing algorithm for distributed caching\n  • Explain the trade-offs between different consensus algorithms"
                },
                "general": {
                    "coding": "Data structures, algorithms, object-oriented design, problem-solving patterns",
                    "system_design": "Application architecture, database design, API design, scalability considerations",
                    "domain_concepts": "Design patterns, SOLID principles, testing strategies, version control",
                    "definitions": "Big O notation, data structure properties, software engineering principles",
                    "examples": "  • Implement a LRU cache with O(1) operations\n  • Design a URL shortening service like bit.ly\n  • Explain when to use different data structures"
                }
            },
            "Data Scientist": {
                "Machine Learning": {
                    "coding": "ML algorithm implementations, feature engineering pipelines, model optimization, cross-validation",
                    "system_design": "ML model deployment, data pipeline architecture, model serving infrastructure, A/B testing systems",
                    "domain_concepts": "Model selection, hyperparameter tuning, bias-variance tradeoff, ensemble methods",
                    "definitions": "Overfitting, gradient descent, regularization, feature selection techniques",
                    "examples": "  • Implement a recommendation system using collaborative filtering\n  • Design an ML pipeline for real-time fraud detection\n  • Explain the bias-variance tradeoff with concrete examples"
                },
                "Deep Learning": {
                    "coding": "Neural network architectures, backpropagation, tensor operations, model training loops",
                    "system_design": "Distributed training systems, model versioning, GPU cluster management, inference optimization",
                    "domain_concepts": "CNN, RNN, Transformer architectures, transfer learning, attention mechanisms",
                    "definitions": "Gradient vanishing, batch normalization, dropout, activation functions",
                    "examples": "  • Implement a transformer model from scratch\n  • Design a computer vision pipeline for autonomous vehicles\n  • Explain different optimization algorithms for deep learning"
                },
                "general": {
                    "coding": "Statistical analysis, data preprocessing, visualization algorithms, hypothesis testing",
                    "system_design": "Data warehouse design, ETL pipelines, analytics platforms, reporting systems",
                    "domain_concepts": "Statistical inference, experimental design, data quality, model evaluation",
                    "definitions": "P-values, confidence intervals, correlation vs causation, sampling bias",
                    "examples": "  • Design an A/B testing framework with proper statistical rigor\n  • Implement a data quality monitoring system\n  • Explain different sampling techniques and their applications"
                }
            }
        }
        
        # Get role-specific context, fall back to general software engineering
        role_contexts = contexts.get(role, contexts["Software Engineer"])
        return role_contexts.get(domain, role_contexts.get("general", contexts["Software Engineer"]["general"]))

    def _get_behavioral_domain_context(self, role: str, domain: str) -> dict:
        """Get domain-specific behavioral context for question generation."""
        contexts = {
            "Software Engineer": {
                "Frontend Development": {
                    "leadership": "Leading UI/UX decisions, mentoring junior developers on frontend best practices",
                    "problem_solving": "Debugging complex browser compatibility issues, optimizing performance bottlenecks",
                    "collaboration": "Working with designers and backend teams, conducting code reviews for frontend code",
                    "communication": "Explaining technical constraints to non-technical stakeholders, presenting demo sessions",
                    "adaptability": "Adapting to new frontend frameworks, handling changing design requirements",
                    "examples": "  • Tell me about a time you had to optimize a slow-loading web application. What was your approach and the outcome?\n  • Describe a situation where you disagreed with a designer about user experience. How did you handle it?"
                },
                "Backend Development": {
                    "leadership": "Architecting backend systems, leading technical discussions about API design",
                    "problem_solving": "Resolving production incidents, optimizing database performance, handling scaling challenges",
                    "collaboration": "Working with frontend teams on API contracts, coordinating with DevOps for deployments",
                    "communication": "Explaining system architecture to stakeholders, documenting technical decisions",
                    "adaptability": "Migrating legacy systems, adopting new technologies for better performance",
                    "examples": "  • Describe a time when you had to handle a critical production outage. What steps did you take?\n  • Tell me about a challenging system integration project you led. What obstacles did you face?"
                },
                "general": {
                    "leadership": "Leading technical projects, mentoring team members, driving technical decisions",
                    "problem_solving": "Debugging complex issues, architecting solutions, handling technical debt",
                    "collaboration": "Working in cross-functional teams, conducting code reviews, pair programming",
                    "communication": "Explaining technical concepts to non-technical stakeholders, writing technical documentation",
                    "adaptability": "Learning new technologies, adapting to changing requirements, handling legacy code",
                    "examples": "  • Tell me about a time you had to learn a new technology quickly to meet a project deadline\n  • Describe a situation where you improved a process or system that benefited your team"
                }
            },
            "Data Scientist": {
                "Machine Learning": {
                    "leadership": "Leading ML model development, mentoring on ML best practices, driving model deployment decisions",
                    "problem_solving": "Debugging model performance issues, handling data quality problems, solving business problems with ML",
                    "collaboration": "Working with engineering teams for model deployment, collaborating with domain experts",
                    "communication": "Explaining ML model results to business stakeholders, presenting model performance metrics",
                    "adaptability": "Adapting models to new data, handling concept drift, learning new ML techniques",
                    "examples": "  • Describe a time when your ML model performed poorly in production. How did you identify and fix the issue?\n  • Tell me about a project where you had to explain complex ML concepts to business stakeholders"
                },
                "general": {
                    "leadership": "Leading data science projects, mentoring junior analysts, driving analytical decisions",
                    "problem_solving": "Solving complex business problems with data, handling messy datasets, debugging analysis",
                    "collaboration": "Working with business teams to understand requirements, collaborating with engineering teams",
                    "communication": "Presenting insights to executives, translating business requirements to technical solutions",
                    "adaptability": "Working with new datasets, learning domain knowledge, adapting to changing business needs",
                    "examples": "  • Tell me about a time when your analysis changed an important business decision\n  • Describe a situation where you had to work with incomplete or messy data"
                }
            },
            "Product Manager": {
                "general": {
                    "leadership": "Leading product strategy, influencing without authority, driving cross-functional alignment",
                    "problem_solving": "Prioritizing features, resolving conflicting stakeholder needs, handling product roadmap challenges",
                    "collaboration": "Working with engineering and design teams, managing stakeholder expectations",
                    "communication": "Presenting to executives, gathering user feedback, facilitating meetings",
                    "adaptability": "Pivoting product strategy, adapting to market changes, handling scope changes",
                    "examples": "  • Tell me about a time you had to make a difficult prioritization decision with limited resources\n  • Describe how you handled a situation where engineering and design had conflicting views on a feature"
                }
            }
        }
        
        # Get role-specific context, fall back to general
        role_contexts = contexts.get(role, contexts["Software Engineer"])
        return role_contexts.get(domain, role_contexts.get("general", contexts["Software Engineer"]["general"]))

    def _parse_qa_pairs(self, content: str) -> Tuple[List[str], List[str]]:
        qs: List[str] = []
        ans: List[str] = []
        chunks = [c for c in content.split("\n\n") if c.strip()]
        for c in chunks:
            parts = c.split("\n", 1)
            if len(parts) == 2 and "." in parts[0] and "." in parts[1]:
                try:
                    q = parts[0].split(".", 1)[1].strip()
                    a = parts[1].split(".", 1)[1].strip()
                except Exception:
                    continue
                qs.append(q)
                ans.append(a)
        return qs, ans



