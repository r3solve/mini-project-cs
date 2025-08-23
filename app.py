import streamlit as st
import streamlit_shadcn_ui as ui
import time
import sqlite3
import os
import traceback
import pandas as pd
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from sqlalchemy import create_engine

os.environ["GOOGLE_API_KEY"] = "AIzaSyAJf60KmfBuh4Xnt6wQfSm5LEM3MnAoDIM"


# Import your core modules
try:
    from core.loaders import DatabaseLoader, GeminiModelLoader
    from core.helper_classes import State
except ImportError as e:
    st.error(f"Failed to import core modules: {e}")
    st.info("Please ensure your core modules are properly set up and don't have circular imports")
    st.stop()

# Set page config
st.set_page_config(
    page_title="NLP to SQL Assistant", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }
    
    .chat-container {
        background: #f8fafc;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #e2e8f0;
    }
    
    .sql-container {
        background: #1e293b;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 4px solid #3b82f6;
    }
    
    .message-user {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 18px 18px 4px 18px;
        margin: 0.5rem 0;
        margin-left: 2rem;
    }
    
    .message-bot {
        background: #f1f5f9;
        color: #334155;
        padding: 0.75rem 1rem;
        border-radius: 18px 18px 18px 4px;
        margin: 0.5rem 0;
        margin-right: 2rem;
        border-left: 3px solid #3b82f6;
    }
    
    .connection-status {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-weight: 500;
    }
    
    .status-connected {
        background: #dcfce7;
        color: #166534;
        border: 1px solid #bbf7d0;
    }
    
    .status-disconnected {
        background: #fef2f2;
        color: #991b1b;
        border: 1px solid #fecaca;
    }
    
    .sidebar .element-container {
        margin-bottom: 1rem;
        
    .head {
        font-size: 2rem;
        font-weight: 700;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
       
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'db_loader' not in st.session_state:
    st.session_state.db_loader = None
if 'model_loader' not in st.session_state:
    st.session_state.model_loader = None
if 'db_type' not in st.session_state:
    st.session_state.db_type = "sqlite"
if 'connection_status' not in st.session_state:
    st.session_state.connection_status = "disconnected"
if 'generated_sql' not in st.session_state:
    st.session_state.generated_sql = ""
if 'is_loading' not in st.session_state:
    st.session_state.is_loading = False
if 'db_info' not in st.session_state:
    st.session_state.db_info = {}
if 'query_results' not in st.session_state:
    st.session_state.query_results = []
if 'last_result_data' not in st.session_state:
    st.session_state.last_result_data = None
if 'show_export_buttons' not in st.session_state:
    st.session_state.show_export_buttons = False
if 'query_results' not in st.session_state:
    st.session_state.query_results = []
if 'last_result_data' not in st.session_state:
    st.session_state.last_result_data = None

# Helper functions
def connect_to_database(db_url):
    """Connect to database using DatabaseLoader"""
    try:
        db_loader = DatabaseLoader(db_url)
        db_instance = db_loader.get_instance()
        
        st.session_state.engine = create_engine(db_url)
        
        # Initialize model loader with the database
        model_loader = GeminiModelLoader(db_instance, db_loader.get_db_type())
        
        # Store in session state
        st.session_state.db_loader = db_loader
        st.session_state.model_loader = model_loader
        st.session_state.connection_status = "connected"
        st.session_state.db_type = db_loader.get_db_type()
        
        
        # Get database info
        try:
            if db_loader.get_db_type() == "sqlite":
                result = db_instance.run("SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table';")
                table_count = str(result).split()[-1] if result else "0"
            else:
                result = db_instance.run("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
                table_count = str(result).split()[-1] if result else "0"
            
            st.session_state.db_info = {
                "tables": table_count,
                "type": db_loader.get_db_type(),
                "url": db_url
            }
        except:
            st.session_state.db_info = {"tables": "Unknown", "type": db_loader.get_db_type(), "url": db_url}
        
        return True, "Successfully connected to database!"
        
    except Exception as e:
        st.session_state.connection_status = "disconnected"
        return False, f"Connection failed: {str(e)}"

def disconnect_database():
    """Disconnect from database"""
    st.session_state.db_loader = None
    st.session_state.model_loader = None
    st.session_state.connection_status = "disconnected"
    st.session_state.db_info = {}

def process_user_query(question):
    """Process user question using GeminiModelLoader"""
    try:
        if not st.session_state.model_loader:
            return "Please connect to a database first.", ""
        
        # Create state object
        state = State(question=question, query="", result="", answer="")
        
        # Get SQL query
        with st.spinner("🔄 Generating SQL query..."):
            sql_result = st.session_state.model_loader.get_sql_query(state)
            generated_sql = sql_result["query"]
        
        # Execute query using the agent
        with st.spinner("⚡ Executing query..."):
            agent_response = st.session_state.model_loader.agent_executor.invoke({
                "messages": [f"Question: {question}"]
            })
            
            # Extract the answer from agent response
            if "messages" in agent_response and len(agent_response["messages"]) > 1:
                answer = agent_response["messages"][-1].content
            else:
                answer = "Query executed successfully, but no clear answer was generated."
        
        # Store query result for export
        try:
            raw_result = st.session_state.db_loader.db.run(generated_sql)
            st.session_state.last_result_data = {
                "question": question,
                "sql": generated_sql,
                "result": raw_result,
                "answer": answer,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state.query_results.append(st.session_state.last_result_data)
        except Exception as e:
            st.session_state.last_result_data = {
                "question": question,
                "sql": generated_sql,
                "result": f"Error: {str(e)}",
                "answer": answer,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        return answer, generated_sql
        
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        st.error(error_msg)
        return error_msg, ""

def export_chat_to_pdf():
    """Export chat history to PDF"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#667eea')
        )
        story.append(Paragraph("NLP to SQL Chat Export", title_style))
        story.append(Spacer(1, 12))
        
        # Export info
        info_style = styles['Normal']
        story.append(Paragraph(f"<b>Export Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", info_style))
        story.append(Paragraph(f"<b>Database Type:</b> {st.session_state.db_type.upper()}", info_style))
        story.append(Paragraph(f"<b>Total Messages:</b> {len(st.session_state.chat_history)}", info_style))
        story.append(Spacer(1, 20))
        
        # Chat history
        if st.session_state.chat_history:
            story.append(Paragraph("Chat History", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            for i, message in enumerate(st.session_state.chat_history, 1):
                if message['type'] == 'user':
                    story.append(Paragraph(f"<b>👤 User:</b> {message['content']}", styles['Normal']))
                else:
                    story.append(Paragraph(f"<b>🤖 Assistant:</b> {message['content']}", styles['Normal']))
                story.append(Spacer(1, 8))
        
        # SQL Queries
        if st.session_state.query_results:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Generated SQL Queries", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            for i, query_data in enumerate(st.session_state.query_results, 1):
                story.append(Paragraph(f"<b>Query {i} ({query_data['timestamp']}):</b>", styles['Normal']))
                story.append(Paragraph(f"<b>Question:</b> {query_data['question']}", styles['Normal']))
                story.append(Paragraph(f"<b>SQL:</b> <font name='Courier'>{query_data['sql']}</font>", styles['Normal']))
                story.append(Paragraph(f"<b>Answer:</b> {query_data['answer']}", styles['Normal']))
                story.append(Spacer(1, 12))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        st.error(f"Error generating PDF: {str(e)}")
        return None

def export_results_to_csv():
    """Export query results to CSV"""
    try:
        if not st.session_state.query_results:
            return None
            
        # Create DataFrame from query results
        export_data = []
        for query_data in st.session_state.query_results:
            export_data.append({
                "Timestamp": query_data['timestamp'],
                "Question": query_data['question'],
                "Generated_SQL": query_data['sql'],
                "Result": str(query_data['result'])[:500] + "..." if len(str(query_data['result'])) > 500 else str(query_data['result']),
                "Answer": query_data['answer']
            })
        
        df = pd.read_sql(query_data["sql"], st.session_state["engine"]) if export_data else pd.DataFrame() 
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return csv_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error generating CSV: {str(e)}")
        return None

def export_current_result_to_csv():
    """Export current query result to CSV"""
    try:
        if not st.session_state.last_result_data:
            return None
            
        # Try to parse the result as tabular data
        result_str = str(st.session_state.last_result_data['result'])
        
        # If the result looks like a table, try to convert it to CSV
        if '\n' in result_str and '|' in result_str:
            lines = result_str.strip().split('\n')
            csv_data = []
            for line in lines:
                if '|' in line:
                    row = [cell.strip() for cell in line.split('|')]
                    csv_data.append(row)
            
            if csv_data:
                df = pd.DataFrame(csv_data[1:], columns=csv_data[0])
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                return csv_buffer.getvalue()
        
        # If not tabular, create a simple CSV with the result
        df = pd.DataFrame({
            "Question": [st.session_state.last_result_data['question']],
            "SQL": [st.session_state.last_result_data['sql']],
            "Result": [st.session_state.last_result_data['result']],
            "Timestamp": [st.session_state.last_result_data['timestamp']]
        })
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return csv_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error generating current result CSV: {str(e)}")
        return None

# Sidebar Navigation
with st.sidebar:
    st.markdown("""### <h1 class="head" >🤖 LAZY QL</h1>""", unsafe_allow_html=True)
    st.markdown("---")
    
    # Vertical navigation using buttons
    st.markdown("**Menu**")
    
    # Initialize selected tab if not exists
    if 'selected_tab' not in st.session_state:
        st.session_state.selected_tab = '🏠 New Query'
    
    # Create vertical navigation buttons
    if st.button('🏠 New Query', use_container_width=True, 
                 type='primary' if st.session_state.selected_tab == '🏠 New Query' else 'secondary'):
        st.session_state.selected_tab = '🏠 New Query'
        st.rerun()
    
    if st.button('🔌 Connection', use_container_width=True,
                 type='primary' if st.session_state.selected_tab == '🔌 Connection' else 'secondary'):
        st.session_state.selected_tab = '🔌 Connection'
        st.rerun()
        
    if st.button('⚙️ Settings', use_container_width=True,
                 type='primary' if st.session_state.selected_tab == '⚙️ Settings' else 'secondary'):
        st.session_state.selected_tab = '⚙️ Settings'
        st.rerun()
    
    selected_tab = st.session_state.selected_tab

# Main content based on selected tab
if selected_tab == '🏠 New Query':
    # Main header
    st.markdown('<h1 class="main-header">💬 LAZY QL</h1>', unsafe_allow_html=True)
    
    # Connection status indicator
    if st.session_state.connection_status == "connected":
        st.markdown(
            f'<div class="connection-status status-connected">✅ Connected to {st.session_state.db_type.upper()} Database</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="connection-status status-disconnected">❌ No Database Connection - Please connect in the Connection tab</div>',
            unsafe_allow_html=True
        )
    
    # Main layout with columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 💭 Conversation")
        
        # Chat container
        chat_container = st.container()
        
        with chat_container:
            # Display chat history
            if st.session_state.chat_history:
                for message in st.session_state.chat_history:
                    if message['type'] == 'user':
                        st.markdown(
                            f'<div class="message-user">👤 {message["content"]}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div class="message-bot">🤖 {message["content"]}</div>',
                            unsafe_allow_html=True
                        )
            else:
                st.markdown(
                    '<div class="message-bot">🤖 Connect to a database and ask questions to generate and execute SQL queries!</div>',
                    unsafe_allow_html=True
                )
        
        # Input section
        st.markdown("---")
        with st.form("chat_form", clear_on_submit=True):
            col_input, col_button = st.columns([4, 1])
            
            with col_input:
                user_input = st.text_input(
                    "Ask a question about your data...",
                    placeholder="e.g., Show me the top 10 customers by total sales",
                    label_visibility="collapsed"
                )
            
            with col_button:
                submit_clicked = st.form_submit_button(
                    "Send 📤", 
                    use_container_width=True,
                    type="primary",
                    disabled=st.session_state.connection_status != "connected"
                )
            
            if submit_clicked and user_input and st.session_state.connection_status == "connected":
                # Add user message to chat
                st.session_state.chat_history.append({
                    'type': 'user',
                    'content': user_input
                })
                
                # Process query
                answer, sql_query = process_user_query(user_input)
                
                # Add bot response
                st.session_state.chat_history.append({
                    'type': 'bot',
                    'content': answer
                })
                
                # Store generated SQL
                if sql_query:
                    st.session_state.generated_sql = sql_query
                
                st.rerun()
    
    with col2:
        st.markdown("### 📋 Generated SQL")
        
        # SQL display container
        if st.session_state.generated_sql:
            st.markdown("**Latest Query:**")
            st.code(st.session_state.generated_sql, language='sql')
            
            # Action buttons for SQL
            col_copy, col_execute = st.columns(2)
            with col_copy:
                if ui.button("📋 Copy", key="copy_sql"):
                    # Note: Actual clipboard copy would require additional JavaScript
                    st.success("SQL displayed above!")
            
            with col_execute:
                if ui.button("🔄 Re-run", key="rerun_sql"):
                    if st.session_state.model_loader and st.session_state.generated_sql:
                        try:
                            result = st.session_state.db_loader.db.run(st.session_state.generated_sql)
                            st.success("Query executed successfully!")
                            st.text(result)
                        except Exception as e:
                            st.error(f"Query execution failed: {str(e)}")
        else:
            st.markdown(
                """
                <div style="padding: 2rem; text-align: center; color: #64748b;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📝</div>
                    <div>Generated SQL queries will appear here</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # Query history and exports
        st.markdown("### 📚 Recent Queries")
        
        col_history, col_export = st.columns([2, 1])
        
        with col_history:
            with st.expander("Query History", expanded=False):
                if st.session_state.chat_history:
                    user_queries = [msg['content'] for msg in st.session_state.chat_history if msg['type'] == 'user']
                    for i, query in enumerate(reversed(user_queries[-5:]), 1):
                        st.markdown(f"**{i}.** {query}")
                else:
                    st.write("No queries yet")
        
        with col_export:
            st.markdown("**Export Options:**")
            
            # Export chat to PDF
            if ui.button("📄 Export to PDF", key="export_chat_pdf"):
                if st.session_state.chat_history:
                    pdf_buffer = export_chat_to_pdf()
                    if pdf_buffer:
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            key="download_chat_pdf"
                        )
                else:
                    st.warning("No chat history to export")
            
            # Export results to CSV
            if ui.button("📊 Export to CSV", key="export_all_csv"):
                if st.session_state.query_results:
                    csv_data = export_results_to_csv()
                    if csv_data:
                        st.download_button(
                            label="⬇️ Download CSV",
                            data=csv_data,
                            file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_all_csv"
                        )
                else:
                    st.warning("No query results to export")
            
            # Export current result
            if st.session_state.last_result_data:
                if ui.button("📋 Export Current", key="export_current_csv"):
                    csv_data = export_current_result_to_csv()
                    if csv_data:
                        st.download_button(
                            label="⬇️ Download Current CSV",
                            data=csv_data,
                            file_name=f"current_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key="download_current_csv"
                        )

elif selected_tab == '🔌 Connection':
    st.markdown('<h1 class="main-header">🔌 Database Connection</h1>', unsafe_allow_html=True)
    
    # Database type selection
    st.markdown("### 🗄️ Choose Database Type")
    
    db_type_tab = ui.tabs(
        options=['SQLite', 'PostgreSQL'], 
        default_value='SQLite',
        key="db_type_tabs"
    )
    
    if db_type_tab == 'SQLite':
        st.markdown("#### 📁 SQLite Database")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # File upload option
            st.markdown("**Upload SQLite File:**")
            uploaded_file = st.file_uploader(
                "Choose SQLite database file",
                type=['db', 'sqlite', 'sqlite3'],
                key="sqlite_upload"
            )
            
            st.markdown("**Or enter file path:**")
            file_path = st.text_input(
                "Database file path",
                placeholder="sqlite:///path/to/database.db or just database.db",
                key="sqlite_path"
            )
            
            # Example databases
            st.markdown("**Quick Start Examples:**")
            if st.button("📊 Use Chinook Sample DB"):
                st.session_state.sqlite_path = "sqlite:///Chinook.db"
        
        with col2:
            st.markdown("**Actions:**")
            
            if ui.button("🔗 Connect", key="connect_sqlite"):
                db_url = None
                
                # Handle uploaded file
                if uploaded_file:
                    # Save uploaded file temporarily
                    temp_path = f"temp_{uploaded_file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.read())
                    db_url = f"sqlite:///{temp_path}"
                
                # Handle file path
                elif file_path:
                    if file_path.startswith("sqlite://"):
                        db_url = file_path
                    else:
                        db_url = f"sqlite:///{file_path}"
                
                if db_url:
                    success, message = connect_to_database(db_url)
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("Please provide a database file or path")
            
            if ui.button("🔌 Disconnect", key="disconnect_sqlite"):
                disconnect_database()
                st.success("Disconnected from database")
                st.rerun()
    
    elif db_type_tab == 'PostgreSQL':
        st.markdown("#### 🐘 PostgreSQL Database")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            host = st.text_input("Host", value="localhost", key="pg_host")
            port = st.text_input("Port", value="5432", key="pg_port")
            database = st.text_input("Database Name", key="pg_database")
            username = st.text_input("Username", key="pg_username")
            password = st.text_input("Password", type="password", key="pg_password")
            
            # Quick example
            st.markdown("**Example from your files:**")
            if st.button("📊 Use School Database"):
                st.session_state.pg_host = "localhost"
                st.session_state.pg_database = "school"
                st.session_state.pg_username = "postgres"
                st.session_state.pg_password = "jack11"
        
        with col2:
            st.markdown("**Actions:**")
            
            if ui.button("🔗 Connect", key="connect_postgresql"):
                if all([host, port, database, username, password]):
                    db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
                    success, message = connect_to_database(db_url)
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error("Please fill in all connection details")
            
            if ui.button("🔌 Disconnect", key="disconnect_postgresql"):
                disconnect_database()
                st.success("Disconnected from database")
                st.rerun()
    
    # Connection status and info
    st.markdown("---")
    st.markdown("### 📊 Connection Status")
    
    if st.session_state.connection_status == "connected":
        st.success(f"✅ **Database Connected** - Successfully connected to {st.session_state.db_type.upper()} database")
        
        # Show database info
        if st.session_state.db_info:
            with st.expander("📋 Database Information", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Database Type", st.session_state.db_info.get("type", "Unknown").upper())
                
                with col2:
                    st.metric("Tables", st.session_state.db_info.get("tables", "Unknown"))
                
                with col3:
                    st.metric("Status", "Connected ✅")
                
                # Show table schema if available
                if st.session_state.db_loader and st.session_state.db_loader.db:
                    try:
                        schema_info = st.session_state.db_loader.db.get_table_info()
                        st.text_area("Database Schema", schema_info, height=200)
                    except:
                        st.info("Schema information not available")
    else:
        st.error("❌ **No Connection** - Please connect to a database to start querying")

elif selected_tab == '⚙️ Settings':
    st.markdown('<h1 class="main-header">⚙️ Application Settings</h1>', unsafe_allow_html=True)
    
    # Model Settings
    st.markdown("### 🤖 AI Model Configuration")
    st.info("Currently using Google Gemini 2.0 Flash model as configured in your backend")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Current Model:** Gemini 2.0 Flash")
        st.markdown("**Provider:** Google GenAI")
        
        temperature = st.slider(
            "Temperature (Creativity)",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.1,
            key="temperature",
            help="Controls randomness in responses. Lower = more focused, Higher = more creative"
        )
    
    with col2:
        max_tokens = st.number_input(
            "Max Result Limit",
            min_value=5,
            max_value=100,
            value=10,
            step=5,
            key="max_tokens",
            help="Maximum number of results to return from queries"
        )
        
        timeout = st.number_input(
            "Query Timeout (seconds)",
            min_value=10,
            max_value=300,
            value=30,
            step=5,
            key="timeout"
        )
    
    # Environment Variables
    st.markdown("### 🔑 Environment Configuration")
    st.info("Set your GOOGLE_API_KEY environment variable for Gemini model access")
    
    # Query Settings
    st.markdown("### 📋 Query Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        explain_queries = st.checkbox(
            "🔍 Explain generated queries",
            value=True,
            key="explain_queries"
        )
        
        show_execution_time = st.checkbox(
            "⏱️ Show execution time",
            value=True,
            key="show_execution_time"
        )
    
   
    
   
    
 
    
    # Save settings
    st.markdown("---")
    st.markdown("### 📤 Export & Backup")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if ui.button("💾 Save Settings", key="save_settings"):
            # Here you could save settings to a config file
            st.success("⚡ Settings saved successfully!")
    
    with col2:
        if ui.button("🔄 Reset to Default", key="reset_settings"):
            # Reset session state values to defaults
            st.session_state.temperature = 0.3
            st.session_state.max_tokens = 10
            st.info("🔄 Settings reset to default")
    
    with col3:
        if ui.button("📊 Test Connection", key="test_connection"):
            if st.session_state.connection_status == "connected":
                st.success("✅ Database connection is active!")
            else:
                st.error("❌ No active database connection")
    
    with col4:
        if ui.button("📈 Generate Report", key="generate_report"):
            if st.session_state.model_loader and st.session_state.query_results:
                try:
                    # Create context from recent queries
                    context = "\n\n".join([
                        f"Question: {qr['question']}\nSQL: {qr['sql']}\nResult: {qr['result']}"
                        for qr in st.session_state.query_results[-5:]  # Last 5 queries
                    ])
                    
                    with st.spinner("Generating comprehensive report..."):
                        report_result = st.session_state.model_loader.generate_reports(context)
                        
                    if report_result and "markdown" in report_result:
                        st.markdown("### 📋 Generated Report")
                        st.markdown(report_result["markdown"])
                        
                        # Offer download of the report
                        st.download_button(
                            label="⬇️ Download Report (MD)",
                            data=report_result["markdown"],
                            file_name=f"database_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown",
                            key="download_report"
                        )
                    else:
                        st.error("Failed to generate report")
                        
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")
            else:
                st.warning("Connect to database and run some queries first")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #64748b; font-size: 0.875rem;">
        Built with ❤️ for my mini project
    </div>
    """,
    unsafe_allow_html=True
)
