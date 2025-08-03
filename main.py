import customtkinter
import os
from pathlib import Path

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

        self.directory_path = Path("reports")

        self.directory_path.mkdir(parents=True, exist_ok=True)
        self._db = None
        self.db_instance = None
        self.gemini_model = None
        self.last_query_results = None  # Store last query results for CSV export
        super().__init__()
        self.report_folder = os.getcwd()  # Default save location

        self.title("Lazy QL")
        self.geometry("1000x700")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.build_widgets()

    def build_widgets(self):
       
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

        # Export buttons frame
        export_frame = customtkinter.CTkFrame(tab1)
        export_frame.grid(row=7, column=0, padx=10, pady=10, sticky="ew")
        export_frame.grid_columnconfigure(0, weight=1)
        export_frame.grid_columnconfigure(1, weight=1)

        self.reports_button = customtkinter.CTkButton(
            export_frame, text="Export PDF", command=self.generate_reports
        )
        self.reports_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.export_csv_button = customtkinter.CTkButton(
            export_frame, text="Export CSV", command=self.export_csv
        )
        self.export_csv_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")


        # === DB Connections Tab ===
        tab2 = self.tabview.tab("DB Connections")
        tab2.grid_columnconfigure(1, weight=1)

        page_label = customtkinter.CTkLabel(
            tab2, text="Database Connection Settings", font=customtkinter.CTkFont(size=16)
        )
        page_label.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        # Database Type Selection
        db_type_label = customtkinter.CTkLabel(tab2, text="Database Type:", anchor="w")
        db_type_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.db_type_var = customtkinter.StringVar(value="sqlite")
        self.db_type_menu = customtkinter.CTkOptionMenu(
            tab2,
            values=["sqlite", "postgresql"],
            variable=self.db_type_var,
            command=self.on_db_type_change
        )
        self.db_type_menu.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # SQLite Connection Fields
        self.sqlite_label = customtkinter.CTkLabel(tab2, text="SQLite Database File:", anchor="w")
        self.sqlite_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.sqlite3Host = customtkinter.CTkEntry(tab2, placeholder_text="Select SQLite3 DB file")
        self.sqlite3Host.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        self.browse_button = customtkinter.CTkButton(tab2, text="Browse", command=self.browse_database_file)
        self.browse_button.grid(row=2, column=2, padx=10, pady=5)

        # PostgreSQL Connection Fields
        self.postgres_label = customtkinter.CTkLabel(tab2, text="PostgreSQL Connection:", anchor="w")
        self.postgres_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        # PostgreSQL host
        self.postgres_host_label = customtkinter.CTkLabel(tab2, text="Host:", anchor="w")
        self.postgres_host_label.grid(row=4, column=0, padx=10, pady=2, sticky="w")
        self.postgres_host = customtkinter.CTkEntry(tab2, placeholder_text="localhost")
        self.postgres_host.grid(row=4, column=1, padx=10, pady=2, sticky="ew")
        
        # PostgreSQL port
        self.postgres_port_label = customtkinter.CTkLabel(tab2, text="Port:", anchor="w")
        self.postgres_port_label.grid(row=5, column=0, padx=10, pady=2, sticky="w")
        self.postgres_port = customtkinter.CTkEntry(tab2, placeholder_text="5432")
        self.postgres_port.grid(row=5, column=1, padx=10, pady=2, sticky="ew")
        
        # PostgreSQL database name
        self.postgres_db_label = customtkinter.CTkLabel(tab2, text="Database:", anchor="w")
        self.postgres_db_label.grid(row=6, column=0, padx=10, pady=2, sticky="w")
        self.postgres_db = customtkinter.CTkEntry(tab2, placeholder_text="database_name")
        self.postgres_db.grid(row=6, column=1, padx=10, pady=2, sticky="ew")
        
        # PostgreSQL username
        self.postgres_user_label = customtkinter.CTkLabel(tab2, text="Username:", anchor="w")
        self.postgres_user_label.grid(row=7, column=0, padx=10, pady=2, sticky="w")
        self.postgres_user = customtkinter.CTkEntry(tab2, placeholder_text="username")
        self.postgres_user.grid(row=7, column=1, padx=10, pady=2, sticky="ew")
        
        # PostgreSQL password
        self.postgres_password_label = customtkinter.CTkLabel(tab2, text="Password:", anchor="w")
        self.postgres_password_label.grid(row=8, column=0, padx=10, pady=2, sticky="w")
        self.postgres_password = customtkinter.CTkEntry(tab2, placeholder_text="password", show="*")
        self.postgres_password.grid(row=8, column=1, padx=10, pady=2, sticky="ew")

        connect_button = customtkinter.CTkButton(
            tab2, text="Connect", command=self.connect_to_database
        )
        connect_button.grid(row=9, column=0, columnspan=3, pady=20)

        # Initialize UI state
        self.on_db_type_change("sqlite")



    def on_db_type_change(self, db_type):
        """
        Handle database type change and show/hide appropriate fields.
        """
        if db_type == "sqlite":
            # Show SQLite fields
            self.sqlite_label.grid()
            self.sqlite3Host.grid()
            self.browse_button.grid()
            
            # Hide PostgreSQL fields
            self.postgres_label.grid_remove()
            self.postgres_host_label.grid_remove()
            self.postgres_host.grid_remove()
            self.postgres_port_label.grid_remove()
            self.postgres_port.grid_remove()
            self.postgres_db_label.grid_remove()
            self.postgres_db.grid_remove()
            self.postgres_user_label.grid_remove()
            self.postgres_user.grid_remove()
            self.postgres_password_label.grid_remove()
            self.postgres_password.grid_remove()
        else:
            # Hide SQLite fields
            self.sqlite_label.grid_remove()
            self.sqlite3Host.grid_remove()
            self.browse_button.grid_remove()
            
            # Show PostgreSQL fields
            self.postgres_label.grid()
            self.postgres_host_label.grid()
            self.postgres_host.grid()
            self.postgres_port_label.grid()
            self.postgres_port.grid()
            self.postgres_db_label.grid()
            self.postgres_db.grid()
            self.postgres_user_label.grid()
            self.postgres_user.grid()
            self.postgres_password_label.grid()
            self.postgres_password.grid()

    def browse_database_file(self):
        """
        Opens a file dialog to select a SQLite3 database file.
        """
        file_path = filedialog.askopenfilename(
            title="Select SQLite3 Database File",
            filetypes=[("SQLite3 Database Files", "*.sqlite3"), ("SQLite3 Database Files", "*.db"), ("All Files", "*.*")]
        )
        if file_path:
            self.sqlite3Host.delete(0, "end")
            self.sqlite3Host.insert(0, file_path)


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
            file_name = os.path.join(self.directory_path, f"report-{current_stamp}.pdf")



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

    def export_csv(self):
        """Export query results as CSV file."""
        try:
            # Check if we have a database connection
            if not self.db_instance:
                messagebox.showerror("Export Error", "Please connect to a database first.")
                return

            # Check if we have a generated SQL query
            sql_query = self.sql_textbox.get("0.0", "end").strip()
            if not sql_query or sql_query.startswith("Error:"):
                messagebox.showerror("Export Error", "Please execute a query first to generate SQL.")
                return

            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                title="Save CSV File",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if not file_path:
                return  # User cancelled

            # Use stored results if available, otherwise execute the query
            if self.last_query_results:
                result = self.last_query_results
            else:
                # Execute the query and get results
                result = self.db_instance.run(sql_query)
            
            # Convert result to CSV format
            csv_content = self._convert_result_to_csv(result)
            
            # Write to file
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                csvfile.write(csv_content)

            messagebox.showinfo("Export Successful", f"CSV file saved as {os.path.abspath(file_path)}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting CSV: {str(e)}")

    def _convert_result_to_csv(self, result):
        """Convert database query result to CSV format."""
        import csv
        import io
        import re
        
        # Create a string buffer to write CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        try:
            if isinstance(result, str):
                # Clean up the result string
                result = result.strip()
                
                # Split into lines
                lines = result.split('\n')
                
                # Find the data section (usually after headers)
                data_start = 0
                headers = []
                data_rows = []
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Look for separator lines (like "----" or "====")
                    if re.match(r'^[-=+]+$', line):
                        data_start = i + 1
                        break
                    
                    # If line contains pipe separators, it might be a header
                    if '|' in line:
                        # Extract headers from pipe-separated format
                        headers = [cell.strip() for cell in line.split('|') if cell.strip()]
                        data_start = i + 1
                        break
                
                # Process data rows
                for line in lines[data_start:]:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Skip separator lines
                    if re.match(r'^[-=+]+$', line):
                        continue
                    
                    # Parse the row
                    if '|' in line:
                        # Pipe-separated format
                        row = [cell.strip() for cell in line.split('|') if cell.strip()]
                    else:
                        # Try to split by whitespace (for simple cases)
                        row = [cell.strip() for cell in line.split() if cell.strip()]
                    
                    if row:
                        data_rows.append(row)
                
                # If we found structured data, write it
                if headers and data_rows:
                    writer.writerow(headers)
                    for row in data_rows:
                        writer.writerow(row)
                elif data_rows:
                    # If no headers but we have data, use generic headers
                    num_cols = max(len(row) for row in data_rows)
                    headers = [f'Column_{i+1}' for i in range(num_cols)]
                    writer.writerow(headers)
                    for row in data_rows:
                        # Pad row to match header length
                        while len(row) < num_cols:
                            row.append('')
                        writer.writerow(row)
                else:
                    # Fallback: write the raw result
                    writer.writerow(['Result'])
                    writer.writerow([result])
            else:
                # If result is not a string, write it as is
                writer.writerow(['Result'])
                writer.writerow([str(result)])
                
        except Exception as e:
            # Fallback: write the raw result
            writer.writerow(['Result'])
            writer.writerow([str(result)])
        
        return output.getvalue()
   
    def execute_query(self):
        query = self.query_entry.get()
        if not query:
            self._display_result("Please enter a query.")
            return

        print(f"User query: {query}")
        state = self.generate_sql_from_model()
        executed_results = execute_query(state, self.db_instance)
        state["result"] = executed_results["result"]
        
        # Store the results for CSV export
        self.last_query_results = executed_results["result"]

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
        db_type = self.db_type_var.get()
        
        if db_type == "sqlite":
            host = self.sqlite3Host.get()
            if not host:
                messagebox.showerror("Connection Error", "Please select a database file first.")
                return
            host_path = Path(host)
            if not host_path.is_absolute():
                host = str(Path.cwd() / host_path)
            connection_string = f"sqlite:///{host}"
        else:  # postgresql
            host = self.postgres_host.get().strip()
            port = self.postgres_port.get().strip() or "5432"
            database = self.postgres_db.get().strip()
            username = self.postgres_user.get().strip()
            password = self.postgres_password.get()
            
            if not all([host, database, username]):
                messagebox.showerror("Connection Error", "Please fill in all required PostgreSQL fields (Host, Database, Username).")
                return
            
            connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        
        print("connection_string", connection_string)
        try:
            self.db = DatabaseLoader(connection_string)
            self.db_instance = self.db.get_instance()
            self.gemini_model = GeminiModelLoader(self.db_instance, db_type)
            db_type_name = "SQLite" if db_type == "sqlite" else "PostgreSQL"
            messagebox.showinfo("Connection Successful", f"Connected to {db_type_name} database successfully!")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to database: {str(e)}")
            return
        
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
