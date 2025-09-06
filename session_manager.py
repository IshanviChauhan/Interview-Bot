import pandas as pd
from typing import Dict, List
import json
from datetime import datetime
import os

class SessionManager:
    def __init__(self, save_dir: str = "sessions"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        
    def save_session(self, session_data: Dict) -> str:
        """Save session data to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}.json"
        filepath = os.path.join(self.save_dir, filename)
        
        # Add metadata
        session_data['metadata'] = {
            'timestamp': timestamp,
            'role': session_data.get('role', ''),
            'domain': session_data.get('domain', ''),
            'interview_type': session_data.get('interview_type', '')
        }
        
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
            
        return filepath

    def load_session(self, filepath: str) -> Dict:
        """Load a saved session from a JSON file."""
        with open(filepath, 'r') as f:
            return json.load(f)

    def get_session_history(self) -> pd.DataFrame:
        """Get a DataFrame of all saved sessions."""
        sessions = []
        for filename in os.listdir(self.save_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.save_dir, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    metadata = data.get('metadata', {})
                    sessions.append({
                        'filename': filename,
                        'timestamp': metadata.get('timestamp', ''),
                        'role': metadata.get('role', ''),
                        'domain': metadata.get('domain', ''),
                        'interview_type': metadata.get('interview_type', ''),
                        'average_score': data.get('average_score', 0)
                    })
        
        return pd.DataFrame(sessions)

    def export_to_pdf(self, session_data: Dict, output_path: str) -> str:
        """Export session data to a PDF file."""
        # Create HTML content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                .section {{ margin: 20px 0; }}
                .question {{ color: #2980b9; }}
                .answer {{ margin-left: 20px; }}
                .feedback {{ margin-left: 20px; color: #27ae60; }}
            </style>
        </head>
        <body>
            <h1>Interview Session Summary</h1>
            <div class="section">
                <h2>Session Details</h2>
                <p>Role: {session_data.get('role', '')}</p>
                <p>Domain: {session_data.get('domain', '')}</p>
                <p>Interview Type: {session_data.get('interview_type', '')}</p>
                <p>Date: {session_data.get('metadata', {}).get('timestamp', '')}</p>
            </div>
            
            <div class="section">
                <h2>Questions and Answers</h2>
                {self._format_qa_pairs_html(session_data)}
            </div>
            
            <div class="section">
                <h2>Final Summary</h2>
                {session_data.get('summary', '').replace('\n', '<br>')}
            </div>
        </body>
        </html>
        """
        
        # Convert HTML to PDF using pdfkit
        import pdfkit
        pdfkit.from_string(html_content, output_path)
        
        return output_path

    def _format_qa_pairs_html(self, session_data: Dict) -> str:
        """Format Q&A pairs for HTML display."""
        qa_pairs = session_data.get('qa_pairs', [])
        html_parts = []
        
        for q, a, f in qa_pairs:
            html_parts.append(f"""
                <div class="qa-pair">
                    <p class="question"><strong>Q: {q}</strong></p>
                    <p class="answer">A: {a}</p>
                    <p class="feedback">Feedback: {f}</p>
                </div>
            """)
            
        return "\n".join(html_parts)
