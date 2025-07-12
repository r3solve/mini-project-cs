from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from typing import Annotated, Any, TypedDict
import os
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent 


from core.helper_classes import QueryOutput, State
from core.tools import  agent_builder

load_dotenv()  # Load environment variables

langsmith_api_key = os.getenv('LANGSMITH_API_KEY')
database_url = os.getenv('DATABASE_URL')


class DatabaseLoader:
    def __init__(self, db_url="sqlite:///Chinook.db") -> None:
        self.db = None
        self.db_url = db_url

    def get_instance(self) -> Annotated[SQLDatabase, Any]:
        try:
            self.db = SQLDatabase.from_uri(self.db_url)
            # print(self.db.dialect)
            # print(self.db.get_usable_table_names())
            self.db.run("SELECT * FROM Artist LIMIT 10;")
            return self.db
        except Exception as e:
            raise Exception(f"Error Connecting to database: {str(e)}")

    def get_health(self) -> bool:
        # Placeholder for actual health logic
        return self.db is not None


class GeminiModelLoader:
    '''
    Initialize the Google API model
    '''
    def __init__(self, db):
        self.model = init_chat_model("gemini-2.0-flash", model_provider="google_genai")
        self.db = db
        self.toolkit = SQLDatabaseToolkit(db=self.db,  llm=self.model)
        self.tools = self.toolkit.get_tools()
    
        self.agent_executor = agent_builder(db=self.db, model=self.model)


        self._system_message = """
            Given an input question, create a syntactically correct {dialect} query to
            run to help find the answer. Unless the user specifies in his question a
            specific number of examples they wish to obtain, always limit your query to
            at most {top_k} results. You can order the results by a relevant column to
            return the most interesting examples in the database.

            Never query for all the columns from a specific table, only ask for a the
            few relevant columns given the question.

            Pay attention to use only the column names that you can see in the schema
            description. Be careful to not query for columns that do not exist. Also,
            pay attention to which column is in which table.

            Only use the following tables:
            {table_info}
        """

        self.agent_system_message = """
            You are an agent designed to interact with a SQL database.
            Given an input question, create a syntactically correct {dialect} query to run,
            then look at the results of the query and return the answer. Unless the user
            specifies a specific number of examples they wish to obtain, always limit your
            query to at most {top_k} results.

            You can order the results by a relevant column to return the most interesting
            examples in the database. Never query for all the columns from a specific table,
            only ask for the relevant columns given the question.

            You MUST double check your query before executing it. If you get an error while
            executing a query, rewrite the query and try again.

            DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the
            database.

            To start you should ALWAYS look at the tables in the database to see what you
            can query. Do NOT skip this step.

            Then you should query the schema of the most relevant tables.
            """.format(
                dialect="SQLite",
                top_k=5,
            )

    @property
    def system_message(self):
        return self._system_message

    @system_message.setter
    def system_message(self, message: str) -> None:
        self._system_message = message

    def get_sql_query(self, state: State):
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
            print("LLM or database execution error:", e)
            raise Exception(f"Error generating SQL: {e}")
    

    def generate_reports(self, state: State):
        """Generate reports using the agent executor. of the answer from the llm to be presented to stakeholders."""
        
        try:
            response = self.agent_executor.invoke(
                {"messages": [HumanMessage(content=state["question"])]}
            )
            state["query"] = response["query"]
            return state
        except Exception as e:
            print("Error generating reports:", e)
            raise Exception(f"Error generating reports: {e}")