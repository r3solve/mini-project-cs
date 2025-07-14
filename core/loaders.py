from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from typing import Annotated, Any, TypedDict
import os
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent 

from core.helper_classes import QueryOutput, State, ReportsOutPut
from core.tools import agent_builder

load_dotenv()

langsmith_api_key = os.getenv('LANGSMITH_API_KEY')
database_url = os.getenv('DATABASE_URL')


class DatabaseLoader:
    def __init__(self, db_url="sqlite:///Chinook.db") -> None:
        self.db = None
        self.db_url = db_url

    def get_instance(self) -> Annotated[SQLDatabase, Any]:
        try:
            self.db = SQLDatabase.from_uri(self.db_url)
            self.db.run("SELECT type, name, tbl_name, sql FROM sqlite_master;")
            return self.db
        except Exception as e:
            raise Exception(f"Error connecting to database: {str(e)}")

    def get_health(self) -> bool:
        return self.db is not None


class GeminiModelLoader:
    """
    Initialize the Google Gemini Model with database interaction.
    Provides SQL generation and report generation functionality.
    """

    def __init__(self, db):
        self.model = init_chat_model("gemini-2.0-flash", model_provider="google_genai")
        self.db = db
        self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.model)
        self.tools = self.toolkit.get_tools()
        self.agent_executor = agent_builder(db=self.db, model=self.model)

        self._system_message = """
            Given an input question, create a syntactically correct {dialect} query
            to run to help find the answer. Unless the user specifies a specific number 
            of examples they wish to obtain, always limit your query to at most {top_k} results.
            
            Never query for all columns; select only the relevant ones.

            Use only columns and tables present in this schema:

            {table_info}
        """

        self.agent_system_message = """
            You are an agent designed to interact with a SQL database.
            Given an input question, create a syntactically correct {dialect} query to run,
            then look at the results of the query and return the answer. Unless the user
            specifies a specific number of examples they wish to obtain, always limit your
            query to at most {top_k} results.

            Only query for relevant columns, not *.

            You MUST double-check your query before executing it.
            Do NOT make any DML statements (INSERT, UPDATE, DELETE, DROP).

            Start by reviewing the available tables and their schemas.
        """.format(
            dialect="SQLite",
            top_k=5,
        )

        self.reports_system_message = """
        You are a data reporting assistant that generates concise, insightful reports from database context. 
        Your output must be in Markdown format, ready to present to stakeholders who are not necessarily technical.

        **Your task:**
        - Create syntactically correct **Markdown (.md)** reports.
        - Analyze the provided context and extract meaningful insights.
        - Write clear summaries, highlighting key trends, anomalies, or actionable points.
        - Use **visualizations** (mermaid.js charts, markdown tables) to make the data intuitive and engaging.

        **Guidelines:**
        - **Audience:** Business stakeholders and decision-makers.
        - **Tone:** Professional, clear, and direct.
        - **Visuals:** Only include graphs that add genuine insight. Use bar charts, line graphs, pie charts, or tables.
        
        **Structure:**
        1. **Title** – A clear, engaging title for the report.
        2. **Executive Summary** – 2-3 sentence overview of findings.
        3. **Key Metrics** – Present important numbers in bold or table format.
        4. **Visualizations** – Use mermaid charts or Markdown tables. Provide captions.
        5. **Recommendations / Next Steps** – Offer actionable suggestions.

        **Example Output:**

        # [Report Title]

        ## Executive Summary
        [Brief summary of the data insights.]

        ## Key Metrics
        | Metric | Value |
        |---------|-------|
        | Example Metric | **1234** |

        ## Visualizations

        ```mermaid
        [Insert relevant mermaid chart code here]
        ```

        *Caption: Explain what this chart shows*

        ## Recommendations
        - [Actionable recommendation 1]
        - [Actionable recommendation 2]

        **Context to analyze:** {context}
        """

    @property
    def system_message(self):
        return self._system_message

    @system_message.setter
    def system_message(self, message: str) -> None:
        self._system_message = message

    def get_sql_query(self, state: State):
        """
        Generates a SQL query from a natural language question using the LLM.
        """
        user_prompt = "Question: {input}"

        try:
            query_prompt_template = ChatPromptTemplate.from_messages([
                ("system", self.system_message),
                ("user", user_prompt)
            ])

            prompt = query_prompt_template.invoke({
                "dialect": self.db.dialect,
                "top_k": 10,
                "table_info": self.db.get_table_info(),
                "input": state["question"]
            })

            structured_llm = self.model.with_structured_output(QueryOutput)
            result = structured_llm.invoke(prompt)

            return {"query": result["query"]}
        except Exception as e:
            raise Exception(f"Error generating SQL: {str(e)}")

    def generate_reports(self, context: str):
        """
        Generates stakeholder-friendly Markdown reports with visualizations from provided context.
        """
        user_prompt = "Generate a full Markdown report from the following context with proper visualizations."

        try:
            report_prompt_template = ChatPromptTemplate.from_messages([
                ("system", self.reports_system_message.format(context=context)),
                ("user", user_prompt)
            ])

            prompt = report_prompt_template.invoke({})

            structured_llm = self.model.with_structured_output(ReportsOutPut)
            result = structured_llm.invoke(prompt)

            return {"markdown": result["markdown"]}
        except Exception as e:
            raise Exception(f"Error generating report: {str(e)}")
