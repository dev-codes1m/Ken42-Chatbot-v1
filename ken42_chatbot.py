import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Dummy credentials for demo
USERS = {
    "user1": {"password": "userpass", "role": "user"},
    "admin1": {"password": "adminpass", "role": "admin"}
}

# Initialize model
gemini = ChatGoogleGenerativeAI(model='gemini-2.5-flash-preview-05-20', temperature=0, api_key=api_key)

# Load KB
with open("KB-Ken42-docs.txt", "r") as file:
    ken42_kb = file.read()

# Chat history file
CHAT_HISTORY_FILE = "chat_history.json"

def load_chat_history():
    """Load chat history from file with proper initialization"""
    try:
        with open(CHAT_HISTORY_FILE, "r") as f:
            data = json.load(f)
            # Ensure the loaded data is a dictionary
            if not isinstance(data, dict):
                return {"users": {}}  # Initialize with proper structure
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}}  # Initialize with proper structure

def save_chat_history(history):
    """Save chat history to file"""
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def get_response(user_input, chat_history):
    # Format the conversation history for the prompt
    conversation_history = "\n".join(
        [f"{msg['role'].capitalize()}: {msg['content']}" 
         for msg in chat_history[-10:]])  # Send last 10 messages for context
    
    prompt = f"""
    You are a helpful assistant for Ken42 University. Always refer to the Ken42 Data, never go outside this data even if user insists you.
    Ken42 Data: {ken42_kb}
    Conversation History: {conversation_history}
    Current Question: {user_input}
    Answer:
    """
    response = gemini.invoke(prompt)
    return response.content

def login():
    st.title("🔐 Ken42 Assistant Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = USERS.get(username)
        if user and user["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = user["role"]
            st.session_state.current_chat = f"chat_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Initialize chat history structure
            chat_history = load_chat_history()
            if "users" not in chat_history:
                chat_history["users"] = {}
            if username not in chat_history["users"]:
                chat_history["users"][username] = {}
            if st.session_state.current_chat not in chat_history["users"][username]:
                chat_history["users"][username][st.session_state.current_chat] = []
            
            st.session_state.messages = chat_history["users"][username][st.session_state.current_chat]
            save_chat_history(chat_history)
            
            st.rerun()
        else:
            st.error("Invalid credentials!")

def update_chat_history():
    """Update the chat history file with current messages"""
    chat_history = load_chat_history()
    if "users" not in chat_history:
        chat_history["users"] = {}
    if st.session_state.username not in chat_history["users"]:
        chat_history["users"][st.session_state.username] = {}
    
    # Update current chat
    chat_history["users"][st.session_state.username][st.session_state.current_chat] = st.session_state.messages
    save_chat_history(chat_history)

def chat_sidebar():
    with st.sidebar:        
        # New chat button at top
        if st.button("+ New chat", use_container_width=True):
            new_chat_id = f"chat_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            st.session_state.current_chat = new_chat_id
            st.session_state.messages = []
            
            # Save to history
            chat_history = load_chat_history()
            if "users" not in chat_history:
                chat_history["users"] = {}
            if st.session_state.username not in chat_history["users"]:
                chat_history["users"][st.session_state.username] = {}
            chat_history["users"][st.session_state.username][new_chat_id] = []
            save_chat_history(chat_history)
            
            st.rerun()
        
        st.divider()
        
        # Chat history list
        chat_history = load_chat_history()
        if "users" in chat_history and st.session_state.username in chat_history["users"]:
            user_chats = chat_history["users"][st.session_state.username]
            
            st.subheader("Chats")
            # Sort chats by timestamp (newest first)
            sorted_chats = sorted(user_chats.items(), key=lambda x: x[0], reverse=True)
            
            for chat_id, messages in sorted_chats:
                # Get first user message as title or "New chat" if empty
                chat_title = "New chat"
                for msg in messages:
                    if msg["role"] == "user":
                        chat_title = msg["content"][:30] + ("..." if len(msg["content"]) > 30 else "")
                        break
                
                if st.button(
                    chat_title,
                    key=f"chat_{chat_id}",
                    use_container_width=True,
                    type="primary" if chat_id == st.session_state.current_chat else "secondary"
                ):
                    st.session_state.current_chat = chat_id
                    st.session_state.messages = messages
                    st.rerun()
        
        st.divider()
        
        # User info and logout at bottom
        st.markdown(f"Logged in as: **{st.session_state.username}**")
        if st.button("Logout", use_container_width=True):
            update_chat_history()
            st.session_state.clear()
            st.rerun()

def chat_interface():
    chat_sidebar()
    
    # Main chat area
    st.title("🎓 Ken42 Assistant")
    
    # Display messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("timestamp"):
                st.caption(message["timestamp"])
    
    # Chat input
    if prompt := st.chat_input("Ask about Ken42 University"):
        user_message = {
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.messages.append(user_message)
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_response(prompt, st.session_state.messages)
                st.markdown(response)

        assistant_message = {
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.messages.append(assistant_message)
        
        # Update chat history after each message
        update_chat_history()

def admin_view():
    st.title("👨‍💼 Admin Dashboard")
    st.markdown(f"**Welcome, Admin {st.session_state.username}**")
    
    if st.button("Back to Chat"):
        st.session_state.show_admin_view = False
        st.rerun()
    
    st.subheader("User Chat Histories")
    chat_history = load_chat_history()
    
    if "users" not in chat_history or not chat_history["users"]:
        st.warning("No chat histories found")
        return
    
    user_select = st.selectbox("Select user", list(chat_history["users"].keys()))
    
    if user_select in chat_history["users"]:
        if not chat_history["users"][user_select]:
            st.warning("No chats found for this user")
            return
            
        chat_select = st.selectbox("Select chat", list(chat_history["users"][user_select].keys()))
        
        st.write(f"### Chat history for {user_select}")
        for message in chat_history["users"][user_select][chat_select]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message.get("timestamp"):
                    st.caption(message["timestamp"])

        if st.button(f"Delete this chat"):
            del chat_history["users"][user_select][chat_select]
            save_chat_history(chat_history)
            st.success("Chat deleted")
            st.rerun()

# App Entry Point
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "show_admin_view" not in st.session_state:
    st.session_state.show_admin_view = False

if not st.session_state.logged_in:
    login()
else:
    if st.session_state.role == "admin" and st.session_state.show_admin_view:
        admin_view()
    else:
        if st.session_state.role == "admin" and st.button("Admin Dashboard"):
            st.session_state.show_admin_view = True
            st.rerun()
        
        chat_interface()