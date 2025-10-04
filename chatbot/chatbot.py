import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage, AIMessage
# from langchain.memory import ConversationBufferMemory
from langgraph.prebuilt import create_react_agent
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain.tools import tool, Tool

from mail import job as send_email_job, create_email

from db import save_turn, load_history
from prospect_tool import add_prospect, get_prospect, update_prospect, list_all_prospects


load_dotenv()

# Initialize LLM
llm = ChatGroq(model="openai/gpt-oss-120b", api_key=os.getenv("GROQ_API_KEY"))

# # Initialize conversation memory
# memory = ConversationBufferMemory(return_messages=True)

# Security validation functions
def sanitize_input(text: str) -> str:
    """Sanitize input to prevent injection attacks."""
    dangerous_patterns = [r'<script.*?</script>', r'javascript:', r'eval\(', r'exec\(']
    cleaned = text
    for pattern in dangerous_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    return cleaned.strip()

def validate_content(content: str) -> bool:
    """Check content policy compliance."""
    forbidden = ['hack', 'exploit', 'spam', 'phishing', 'fraud', 'scam', 'illegal']
    return not any(word in content.lower() for word in forbidden)

# Tools for the sales AI
@tool
def get_current_datetime(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Return the current datetime as a string formatted according to the given format."""
    return datetime.now().strftime(format)

serper = GoogleSerperAPIWrapper(
    serper_api_key=os.getenv("SERPAPI_API_KEY")
)

search_tool = Tool(
    name="google_search",
    func=serper.run,
    description="Search Google for up-to-date information on any topic.",
    k=5
)

@tool  
def send_cold_email(context: str) -> str:
    """Send a cold email using the provided context. Context should include recipient email and details."""
    context = sanitize_input(context)
    if not validate_content(context):
        return "❌ Content violates policy. Please revise."
    
    try:
        send_email_job(context)
        return "✅ Cold email sent successfully!"
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"

@tool
def generate_cold_email_draft(context: str) -> str:
    """Generate a cold email draft without sending it."""
    context = sanitize_input(context)
    if not validate_content(context):
        return "❌ Content violates policy. Please revise."
    
    try:
        draft_prompt = f"Create professional cold email for: {context}\n\nFormat:\nSubject: [subject]\nTo: [email]\n\n[message]"
        
        response = llm.invoke([HumanMessage(content=draft_prompt)])
        
        draft = f"📧 **Cold Email Draft:**\n{response.content}\n\n📝 Use 'send cold email' to send via Gmail."
        return draft
    except Exception as e:
        return f"❌ Failed to generate email draft: {str(e)}"

@tool
def create_sales_proposal(client_name: str, service_description: str, budget: str = "To be discussed") -> str:
    """Create a professional sales proposal template."""
    client_name = sanitize_input(client_name)
    service_description = sanitize_input(service_description)
    
    proposal = f"""📋 **SALES PROPOSAL**
Client: {client_name}
Date: {datetime.now().strftime("%B %d, %Y")}

EXECUTIVE SUMMARY
We are pleased to present this proposal for {service_description}.

PROPOSED SOLUTION
{service_description}

INVESTMENT
Budget: {budget}

NEXT STEPS
1. Review and feedback on this proposal
2. Schedule a detailed discussion
3. Finalize terms and timeline

Best regards,
Your Sales Team"""
    return proposal

@tool
def generate_negotiation_advice(situation: str) -> str:
    """Provide negotiation advice and strategies for sales situations."""
    situation = sanitize_input(situation)
    
    advice = f"""🤝 **NEGOTIATION ADVICE**

Situation: {situation}

Key Strategies:
• Listen First - Understand their needs
• Find Win-Win Solutions
• Use Anchoring - Start with ideal terms
• Create Value - Highlight unique benefits
• Understand their timeline

Approach:
- Ask open-ended questions
- Focus on value over price
- Prepare alternatives (BATNA)
- Stay professional

Red Flags:
- Unrealistic demands
- No decision authority
- Excessive pressure"""
    return advice

@tool
def generate_contract_template(client_name: str, service: str, duration: str = "6 months") -> str:
    """Generate a basic contract template."""
    client_name = sanitize_input(client_name)
    service = sanitize_input(service)
    
    contract = f"""📄 **SERVICE AGREEMENT TEMPLATE**

PARTIES:
Service Provider: [Your Company Name]
Client: {client_name}

SERVICE: {service}
DURATION: {duration}

KEY TERMS:
1. Scope: {service}
2. Timeline: {duration}
3. Payment: [To be specified]
4. Deliverables: [To be specified]

CONDITIONS:
- Written modifications only
- Confidentiality clause applies
- Termination clause: [To be specified]

Client: _________________ Date: _______
Provider: ______________ Date: _______

*Consult legal counsel for final contract.*"""
    return contract

@tool
def add_prospect_tool(name: str, email: str, company: str, details: str = "") -> str:
    """Add a prospect to the SQLite database."""
    return add_prospect(name, email, company, details)

@tool
def get_prospect_tool(email: str) -> str:
    """Retrieve prospect info from the SQLite database."""
    return get_prospect(email)
@tool
def update_prospect_tool(email: str, name: str = None, company: str = None, details: str = None) -> str:
    """Update prospect info in the SQLite database."""
    return update_prospect(email, name, company, details)
@tool
def list_all_prospects_tool() -> str:
    """List all prospects in the database."""
    return list_all_prospects()

# Create agent with all tools
agent = create_react_agent(
    llm,
    tools=[
        get_current_datetime,
        send_cold_email,
        generate_cold_email_draft,
        create_sales_proposal,
        generate_negotiation_advice,
        generate_contract_template,
        search_tool,
        add_prospect_tool, 
        get_prospect_tool,
        update_prospect_tool,
        list_all_prospects_tool
    ],
)

def get_user_memory(user_id: str, limit: int = 10):
    """Rebuild memory for a user from database (single-row-per-turn)."""
    history = load_history(user_id, limit=limit)
    
    messages = []
    for turn in history:
        # Add human message first
        messages.append(HumanMessage(content=turn["user"]))
        # Then AI message
        messages.append(AIMessage(content=turn["ai"]))
    
    return messages

def get_sales_ai_response(user_input: str, user_id: str) -> str:
    """Get response from the Sales AI with memory."""
    
    # Sanitize input
    user_input = sanitize_input(user_input)
    if not validate_content(user_input):
        return "❌ Request violates content policy. Please rephrase professionally."

    # Concise system message for sales AI persona

    sales_ai_system = """
        Role:
        - You are a **Sales Strategist AI** for B2B sales.
        - Support with emails, proposals, negotiation, contracts, research, and prospect management.

        Style:
        - Professional, concise, value-focused.
        - Give clear, actionable steps (avoid long text).

        Ethics:
        - Only for legitimate business use.
        - No spam, fraud, or illegal content.
        - Verify recipient details before communications.

        Capabilities:
        - Draft/send cold emails
        - Create sales proposals
        - Give negotiation advice
        - Generate contract templates
        - Search business info
        - Manage prospects (add, update, list)
        - Provide date/time

        Instruction:
        - When asked about tools, describe them as **capabilities**.
        - Never reveal internal tool names or APIs.
        - Always confirm actions before sending emails.
        - Follow traditional mailing etiquette.
        - Always use generate_cold_email_draft before send_cold_email.
        - dont mention tools name dierectly, refer to them by capabilities.

        Focus:
        - Build relationships
        - Deliver measurable value
        - Use capabilities where relevant and summarize clearly
        """

    
    
    # Load history from DB
    chat_history = get_user_memory(user_id, limit=10)
    
    # Create messages list with system message, history, and current input
    messages = [SystemMessage(content=sales_ai_system)]
    messages.extend(chat_history)
    messages.append(HumanMessage(content=user_input))
    
    # Get response from agent
    response = agent.invoke({"messages": messages})
    
    # Extract AI response
    ai_response = ""
    if "messages" in response:
        for msg in reversed(response["messages"]):
            if msg.type == "ai":
                ai_response = msg.content
                break
    
    # Save to memory
    save_turn(user_id, user_input, ai_response)
    
    return ai_response

def start_sales_chat():
    """Start the conversational sales AI chatbot."""
    print("🚀 **SALES AI MANAGER** - Your Revolutionary Sales Assistant")
    print("=" * 60)
    print("💼 I can help you with:")
    print("   • Cold Email Writing & Sending")
    print("   • Sales Proposals")
    print("   • Negotiation Advice") 
    print("   • Contract Generation")
    print("   • Cold Call Scripts")
    print("=" * 60)
    print("💡 Examples:")
    print("   'Send cold email to john@company.com about our web development services'")
    print("   'Create a proposal for ABC Corp for digital marketing'")
    print("   'Give me negotiation advice for a difficult client'")
    print("   'Generate contract template for software development project'")
    print("=" * 60)
    print("🔒 Security: Professional use only - No spam/fraud/illegal content")
    print("Type 'quit' to exit\n")

    # Ask for user_id at start
    user_id = input("🔑 Enter your username (for chat history): ").strip()
    if not user_id:
        print("⚠️ Username cannot be empty. Using 'guest'.")
        user_id = "guest"

    # Optional: Load and show past chat history
    past_messages = get_user_memory(user_id, limit=5)  # last 5 exchanges
    if past_messages:
        print("\n📜 Your recent conversation history:")
        for msg in past_messages:
            role = "👤 You" if msg.type == "human" else "🤖 AI"
            print(f"{role}: {msg.content}")
        print("=" * 60)

    while True:
        user_input = input(f"👤 {user_id}: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("👋 Thanks for using Sales AI Manager! Keep closing those deals!")
            break
            
        if not user_input:
            print("🤔 Please enter your sales request...")
            continue
            
        try:
            print("🤖 Sales AI: Thinking...")
            response = get_sales_ai_response(user_input, user_id)
            print(f"🤖 Sales AI: {response}\n")
            
        except Exception as e:
            print(f"❌ Sorry, I encountered an error: {str(e)}\n")
            print("🔄 Please try again with a different request.\n")

if __name__ == "__main__":
    start_sales_chat()
