import customtkinter
import os
from tkinter import messagebox
from tkinter.simpledialog import askstring
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from markdown_pdf import MarkdownPdf, Section
import datetime
from tkinter import filedialog

from core.loaders import DatabaseLoader, GeminiModelLoader
from core.tools import execute_query, generate_answer_from_llm


customtkinter.set_default_color_theme("green")

class App(customtkinter.CTk):
    def __init__(self):
        self.build_widgets()

    def build_widgets(self):
        self._db = DatabaseLoader()
        self.db_instance = self._db.get_instance()
        self.gemini_model = GeminiModelLoader(self.db_instance)
        super().__init__()
        self.report_folder = os.getcwd()  # Default save location

        self.title("Lazy QL")
        self.geometry("1000x700")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = customtkinter.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="LazyQL",
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
            self.sidebar_frame, text="Settings", command=self.open_settings_popup
        )
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

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

        self.appearance_mode_optionemenu.set("System")
        self.scaling_optionemenu.set("100%")

        self.main_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.tabview = customtkinter.CTkTabview(self.main_frame)
        self.tabview.grid(row=0, column=0, sticky="nsew")
        self.tabview.add("Main Query")
        self.tabview.add("DB Connections")

        # === Main Query Tab ===
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
            tab1, placeholder_text="e.g., Show me all users from New York",
            height=50,
            font=customtkinter.CTkFont(size=18)
        )
        self.query_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.exec_raw_button = customtkinter.CTkButton(
            tab1, text="Execute Query", command=self.execute_query
        )
        self.exec_raw_button.grid(row=1, column=1, padx=10, pady=10)

        self.sql_textbox = customtkinter.CTkTextbox(tab1, wrap="word")
        self.sql_textbox.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        # self.sql_textbox.configure()

        self.answer_labelbox = customtkinter.CTkLabel(tab1, text="Answer", font=customtkinter.CTkFont(size=20,) )
        self.answer_labelbox.grid(row=3, column=0)

       
       

        self.final_result_textbox = customtkinter.CTkTextbox(tab1, wrap='word')
        self.final_result_textbox.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="nsew")
        # self.final_result_textbox.configure(state='disabled')

        self.output_labelbox = customtkinter.CTkLabel(tab1, text="Processs", font=customtkinter.CTkFont(size=20,) )
        self.output_labelbox.grid(row=5, column=0)

        self.results_textbox = customtkinter.CTkTextbox(tab1, wrap="word")
        self.results_textbox.grid(row=6, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.results_textbox.configure(state="disabled")

        self.reports_button = customtkinter.CTkButton(
            tab1, text="Export ", command=self.generate_reports
        )
        self.reports_button.grid(row=7, column=0, padx=10, pady=10)


        # === DB Connections Tab ===
        tab2 = self.tabview.tab("DB Connections")
        tab2.grid_columnconfigure(1, weight=1)

        labels = ["Host:", "Port:", "Username:", "Password:", "Database Name:"]
        placeholders = ["localhost", "5432", "user", "password", "mydatabase"]
        self.entries = []

        for i, (label, placeholder) in enumerate(zip(labels, placeholders)):
            customtkinter.CTkLabel(tab2, text=label).grid(row=i+1, column=0, padx=10, pady=5, sticky="e")
            entry = customtkinter.CTkEntry(tab2, placeholder_text=placeholder, show="*" if label == "Password:" else None)
            entry.grid(row=i+1, column=1, padx=10, pady=5, sticky="ew")
            self.entries.append(entry)

        connect_button = customtkinter.CTkButton(
            tab2, text="Connect", command=self.connect_to_database
        )
        connect_button.grid(row=6, column=0, columnspan=2, pady=20)

    def open_settings_popup(self):
        popup_window = customtkinter.CTkToplevel(self)
        popup_window.title("Settings")
        popup_window.geometry("400x250")

        label = customtkinter.CTkLabel(popup_window, text="Report Save Folder:")
        label.pack(pady=(20, 5))

        # Display current folder
        current_folder_label = customtkinter.CTkLabel(popup_window, text=self.report_folder)
        current_folder_label.pack(pady=5)

        def choose_folder():
            folder = filedialog.askdirectory(initialdir=self.report_folder)
            if folder:
                self.report_folder = folder
                current_folder_label.configure(text=folder)

        folder_button = customtkinter.CTkButton(popup_window, text="Choose Folder", command=choose_folder)
        folder_button.pack(pady=10)

        close_button = customtkinter.CTkButton(popup_window, text="Close", command=popup_window.destroy)
        close_button.pack(pady=10)

    def open_database_settings_popup(self):
        popup_window = customtkinter.CTkToplevel(self)  # Pass the main window as parent
        popup_window.title("Database Settings")
        popup_window.geometry("300x200")

        # Add widgets to the pop-up window
        label = customtkinter.CTkLabel(popup_window, text="This is a pop-up!")
        label.pack(pady=20)

        close_button = customtkinter.CTkButton(popup_window, text="Close", command=popup_window.destroy)
        close_button.pack(pady=10)


    def generate_reports(self):
        try:
            current_stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_name = os.path.join(self.report_folder, f"report-{current_stamp}.pdf")


            # Ask user whether to include process/steps
            include_process = messagebox.askyesno(
                "Generate Report",
                "Do you want to include the process/steps in the PDF?"
            )

            # Get the result text from the textbox
            self.results_textbox.configure(state="normal")
            results_text = self.results_textbox.get("0.0", "end").strip()
            self.results_textbox.configure(state="disabled")

            # Initialize PDF generator
            pdf = MarkdownPdf(toc_level=2, optimize=True)

            if include_process:
                # Assuming context is the same as results_text for now
                # Replace this with actual data if needed
                markdown_report = self.gemini_model.generate_reports(
                            context=results_text + 
                             "\n\n" + "Process Steps:\n" + 
                             self.results_textbox.get("0.0", "end").strip()   
                                                                      )
                pdf.add_section(Section(markdown_report["markdown"]))
                
            else:
                # Export only the results_text
                pdf.add_section(Section(results_text))

            # Save PDF
            pdf.save(file_name)

            messagebox.showinfo("Export Successful", f"PDF saved as {os.path.abspath(file_name)}")

        except Exception as e:
            messagebox.showerror("Export Failed", f"Error generating PDF: {str(e)}")
   
    def execute_query(self):
        query = self.query_entry.get()
        if not query:
            self._display_result("Please enter a query.")
            return

        print(f"User query: {query}")
        state = self.generate_sql_from_model()
        executed_results = execute_query(state, self.db_instance)
        state["result"] = executed_results["result"]

        natural_language_answer = generate_answer_from_llm(state, self.gemini_model.model)
        state["answer"] = natural_language_answer["answer"]

        self.results_textbox.configure(state="normal")
        self.results_textbox.delete("0.0", "end")



        for step in self.gemini_model.agent_executor.stream(
            {"messages": [{"role": "user", "content": state["question"]}]},
            stream_mode="values",
        ):
            step_output = step["messages"][-1].content
            self.results_textbox.insert("end", f"Step Output:\n{step_output}\n\n")
            self.results_textbox.update_idletasks()
        
        self.final_result_textbox.configure(state="normal")
        self.final_result_textbox.delete("0.0", "end")
        
        self.results_textbox.insert("end", f"Generated SQL:\n{state['query']}\n\n")
        self.results_textbox.insert("end", f"Natural Language Answer:\n{state['answer']}\n")
        self.results_textbox.configure(state="disabled")
        


        self.sql_textbox.delete("0.0", "end")
        self.sql_textbox.insert("0.0", state["query"])



        self.final_result_textbox.insert("end", f"Natural Language Answer:\n{state['answer']}\n")
        self.final_result_textbox.configure()

        try:
            mark_down_code = self.gemini_model.generate_reports(f"{state['answer']}")
        except:
            print("could not generate reports")
       

    def generate_sql_from_model(self) -> dict:
        try:
            question = self.query_entry.get()
            if not question:
                raise ValueError("Empty query")

            state =  {"question": question}
            ret = self.gemini_model.get_sql_query(state)
            state["query"] = ret["query"]
            return state
        except Exception as e:
            self.sql_textbox.delete("0.0", "end")
            self.sql_textbox.insert("0.0", f"Error: {str(e)}")
            return {"question": "", "query": "", "result": "", "answer": ""}

    def connect_to_database(self):
        host, port, user, password, dbname = (entry.get() for entry in self.entries)
        print(f"Connecting to DB at {host}:{port} with user '{user}' to database '{dbname}'")
        customtkinter.CTkMessagebox(title="Connection", message="Successfully connected to the database!")

    def sidebar_button_event(self):
        print("Sidebar button clicked")

    def change_appearance_mode_event(self, new_mode: str):
        customtkinter.set_appearance_mode(new_mode)

    def change_scaling_event(self, new_scaling: str):
        scale = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(scale)

    def _display_result(self, message: str):
        self.results_textbox.configure(state="normal")
        self.results_textbox.delete("0.0", "end")
        self.results_textbox.insert("0.0", message)
        self.results_textbox.configure(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
