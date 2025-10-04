import schedule
import time
import markdown
from gmail_service import get_gmail_service, send_message
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
from datetime import datetime
import os
import json
import re

load_dotenv()

# Initialize LLM (simpler, no agent needed)
llm = ChatGroq(model="openai/gpt-oss-120b", api_key=os.getenv("GROQ_API_KEY"))


def create_email(context: str) -> dict:
    """
    Extract email components from already-drafted email context.
    The context contains a drafted email that needs to be parsed for:
    - subject
    - Mail_draft 
    - to_mail
    - cc_mail
    """
    
    system_rules = """You are an email parser AI. 
Your job is to extract email components from already-drafted email content.

Given email content, extract:
1. recipient email(s) from To: line or context
2. CC email(s) if mentioned (or "none" if not specified)  
3. subject line (if provided) or generate appropriate one
4. email body/message content

The input may contain:
- A complete drafted email with headers
- Context mentioning recipient emails and draft content
- Mixed format with recipient info and message body

Output ONLY valid JSON in this exact format:
{"subject": "...", "Mail_draft": "...", "to_mail": "...", "cc_mail": "..."}

Rules:
- Extract recipient emails accurately
- Keep the email body content as-is (don't rewrite)
- If no subject provided, create a professional one
- If no CC mentioned, use "none"
- Multiple emails separated by commas"""

    messages = [
        SystemMessage(content=system_rules),
        HumanMessage(content=context)
    ]

    try:
        response = llm.invoke(messages)
        
        # Clean up the response content
        content = response.content.strip()
        
        # Remove any markdown formatting or extra text
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
        
        # Find JSON in the response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group()
        
        return json.loads(content)
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"Raw response: {response.content}")
        raise ValueError(f"Failed to parse email data: {e}")
    except Exception as e:
        print(f"❌ Error creating email: {e}")
        raise


def send_email_job(context: str):
    """Send an email using context from Sales AI system"""
    try:
        service = get_gmail_service()
        email_data = create_email(context)

        # Extract To and CC safely
        to_emails = [
            email.strip() for email in email_data["to_mail"].split(",")
            if email and email.lower() != "none" and "@" in email
        ]
        cc_emails = [
            email.strip() for email in email_data["cc_mail"].split(",")
            if email and email.lower() != "none" and "@" in email
        ] if email_data["cc_mail"].lower() != "none" else []
        
        subject = email_data["subject"]
        
        mail_body_html = markdown.markdown(email_data["Mail_draft"],extensions=['tables','fenced_code','nl2br','sane_lists','smarty','toc','wikilinks','attr_list','admonition','def_list','footnotes'])

        # Validate recipient
        if not to_emails:
            print("❌ No valid recipient email found. Please check the context.")
            return "❌ No valid recipient email found."

        # Send email
        send_message(service, to_emails, cc_emails, subject, mail_body_html)
        result = f"✅ Email sent successfully to {', '.join(to_emails)} with subject: {subject}"
        print(result)
        return result
        
    except Exception as e:
        error_msg = f"❌ Failed to send email: {str(e)}"
        print(error_msg)
        return error_msg


# Legacy function name for compatibility
def job(context: str):
    """Legacy wrapper for send_email_job"""
    return send_email_job(context)


# Test function for debugging
def test_email_parsing(context: str):
    """Test email parsing without sending"""
    try:
        email_data = create_email(context)
        print("Parsed email data:")
        print(f"To: {email_data['to_mail']}")
        print(f"CC: {email_data['cc_mail']}")
        print(f"Subject: {email_data['subject']}")
        print(f"Body: {email_data['Mail_draft'][:100]}...")
        return email_data
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None


# if __name__ == "__main__":
#   
#     test_context = """
#     To: john@example.com
#     Subject: Web Development Services
    
#     Hi John,
    
#     I hope this email finds you well. I wanted to reach out regarding our web development services that could benefit your company.
    
#     Best regards,
#     Sales Team
#     """
    
#     print("Testing email parsing:")
#     test_email_parsing(test_context)