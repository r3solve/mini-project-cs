import customtkinter
from core.loaders import DatabaseLoader, GeminiModelLoader

customtkinter.set_default_color_theme("green")

from core.tools import execute_query, generate_answer_from_llm
class App(customtkinter.CTk):
    def __init__(self):
        self.build_widgets()


    def build_widgets(self):
        self._db = DatabaseLoader()
        self.db_instance = self._db.get_instance()
        self.gemini_model = GeminiModelLoader(self.db_instance)
        super().__init__()
        self.title("Natural SQL")
        self.geometry("1000x700")

        # Configure grid layout (sidebar + main content)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar frame
        self.sidebar_frame = customtkinter.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Sidebar widgets
        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="Natural SQL",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.sidebar_button_1 = customtkinter.CTkButton(
            self.sidebar_frame, text="New Query", command=self.sidebar_button_event
        )
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)

        self.sidebar_button_2 = customtkinter.CTkButton(
            self.sidebar_frame, text="Query History", command=self.sidebar_button_event
        )
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)

        self.sidebar_button_3 = customtkinter.CTkButton(
            self.sidebar_frame, text="Settings", command=self.sidebar_button_event
        )
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

        # Appearance mode and scaling options
        self.appearance_mode_label = customtkinter.CTkLabel(
            self.sidebar_frame, text="Appearance Mode:", anchor="w"
        )
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=["System", "Light", "Dark"],
            command=self.change_appearance_mode_event,
        )
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(0, 10))

        self.scaling_label = customtkinter.CTkLabel(
            self.sidebar_frame, text="UI Scaling:", anchor="w"
        )
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling_event,
        )
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(0, 20))

        # Set default appearance and scaling
        self.appearance_mode_optionemenu.set("System")
        self.scaling_optionemenu.set("100%")

        # Main content frame
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Create Tabview inside main_frame
        self.tabview = customtkinter.CTkTabview(self.main_frame)
        self.tabview.grid(row=0, column=0, sticky="nsew")
        self.tabview.add("Main Query")
        self.tabview.add("DB Connections")

        # === Tab 1: Main Query UI ===
        tab1 = self.tabview.tab("Main Query")
        tab1.grid_columnconfigure(0, weight=1)
        tab1.grid_rowconfigure(2, weight=1)
        tab1.grid_rowconfigure(4, weight=1)

        self.main_label = customtkinter.CTkLabel(
            tab1,
            text="Enter your natural language query:",
            font=customtkinter.CTkFont(size=16),
        )
        self.main_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")

        self.query_entry = customtkinter.CTkEntry(
            tab1, placeholder_text="e.g., Show me all users from New York"
        )
        self.query_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.exec_raw_button = customtkinter.CTkButton(
            tab1, text="Execute Query", command=self.execute_query
        )
        self.exec_raw_button.grid(row=1, column=1, padx=10, pady=10)

        self.sql_textbox = customtkinter.CTkTextbox(tab1, wrap="word")
        self.sql_textbox.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.sql_textbox.insert("0.0", "Generated SQL will appear here...")

        self.execute_button = customtkinter.CTkButton(
            tab1, text="Generate SQL & Execute", command=self.execute_query
        )
        self.execute_button.grid(row=3, column=0, padx=10, pady=10)

        self.results_textbox = customtkinter.CTkTextbox(tab1, wrap="word")
        self.results_textbox.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.results_textbox.insert("0.0", "Query results will appear here...")
        self.results_textbox.configure(state="disabled")

        # === Tab 2: DB Connections UI ===
        tab2 = self.tabview.tab("DB Connections")
        tab2.grid_columnconfigure(1, weight=1)

        db_label = customtkinter.CTkLabel(
            tab2,
            text="Database Connection Setup",
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        db_label.grid(row=0, column=0, columnspan=2, pady=(10, 20))

        host_label = customtkinter.CTkLabel(tab2, text="Host:")
        host_label.grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.host_entry = customtkinter.CTkEntry(tab2, placeholder_text="localhost")
        self.host_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        port_label = customtkinter.CTkLabel(tab2, text="Port:")
        port_label.grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.port_entry = customtkinter.CTkEntry(tab2, placeholder_text="5432")
        self.port_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        user_label = customtkinter.CTkLabel(tab2, text="Username:")
        user_label.grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.user_entry = customtkinter.CTkEntry(tab2, placeholder_text="user")
        self.user_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        password_label = customtkinter.CTkLabel(tab2, text="Password:")
        password_label.grid(row=4, column=0, padx=10, pady=5, sticky="e")
        self.password_entry = customtkinter.CTkEntry(tab2, placeholder_text="password", show="*")
        self.password_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        dbname_label = customtkinter.CTkLabel(tab2, text="Database Name:")
        dbname_label.grid(row=5, column=0, padx=10, pady=5, sticky="e")
        self.dbname_entry = customtkinter.CTkEntry(tab2, placeholder_text="mydatabase")
        self.dbname_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        connect_button = customtkinter.CTkButton(
            tab2, text="Connect", command=self.connect_to_database
        )
        connect_button.grid(row=6, column=0, columnspan=2, pady=20)



    def execute_query(self):
        query = self.query_entry.get()
        if query:
            print(f"User query: {query}")
            # Simulated SQL generation and results display
            generated_query_state = self.generate_sql_from_model()
            executed_results = execute_query(generated_query_state,self.db_instance )

            natural_language_answer = generate_answer_from_llm({
                "question":"what is the total number of Employees",
                "query":generated_query_state,
                "result":f"{executed_results}"
            }, self.gemini_model.model)

            simulated_result = (
                f"SQL: {generated_query_state}\n\nDB Result:\n {executed_results} \n\n\n\nAnswer: {natural_language_answer.get("answer", "I did not get anything")}"
                
               
            )
            print(natural_language_answer)
            print("result", executed_results)
            self.results_textbox.configure(state="normal")
            self.results_textbox.delete("0.0", "end")
            self.results_textbox.insert("0.0", simulated_result)
            self.results_textbox.configure(state="disabled")
            self.sql_textbox.delete("0.0", "end")
            self.sql_textbox.insert("0.0", f"---")
            self.generate_sql_from_model()
        else:
            self.results_textbox.configure(state="normal")
            self.results_textbox.delete("0.0", "end")
            self.results_textbox.insert("0.0", "Please enter a query.")
            self.results_textbox.configure(state="disabled")

    def connect_to_database(self):
        host = self.host_entry.get()
        port = self.port_entry.get()
        user = self.user_entry.get()
        password = self.password_entry.get()
        dbname = self.dbname_entry.get()
        print(f"Connecting to DB at {host}:{port} with user '{user}' to database '{dbname}'")
        # Here you would add your actual DB connection logic
        # For now, just simulate success:
        customtkinter.CTkMessagebox(title="Connection", message="Successfully connected to the database!")

    def sidebar_button_event(self):
        print("Sidebar button clicked")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def generate_sql_from_model(self) -> str:
        try:
            state = {"question": "what is the total number of Employees"}
            ret = self.gemini_model.get_sql_query(state)
            print("Generated SQL:", ret)
            self.sql_textbox.delete("0.0", "end")
            self.sql_textbox.insert("0.0", ret["query"])
            print(ret)
            return ret
        except Exception as e:
            print("Error:", e)
            self.sql_textbox.delete("0.0", "end")
            self.sql_textbox.insert("0.0", f"Error: {str(e)}")
            return ""


if __name__ == "__main__":
    app = App()
    app.mainloop()
