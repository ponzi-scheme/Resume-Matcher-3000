import tkinter as tk
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText
from functionsfix2 import chonker

class ResumeMatcherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Resume Matcher") # Application title
        self.root.geometry("600x460") #Initial window size

        # Data storage
        self.job_description = [] # Stores the job description 
        self.resumes = [] # Stores the resumes
        self.user_input_value = 1 # Default value of 1, if the user does not enter a number the program will only show top candidate

        self.results_table = [] # Results table in second screen
        
        # Job description section
        jd_frame = tk.Frame(root)
        jd_frame.pack(pady=10, fill="x")

        tk.Label(jd_frame, text="Job Description").pack(anchor="w")
        tk.Button(jd_frame, text="Upload Job Description", command=self.select_job_description).pack(anchor="w") # Opens file system and lets user select single job description

        self.jd_label = tk.Label(jd_frame, text="No job description uploaded") 
        self.jd_label.pack(anchor="w", padx=10)

        # Resume section
        resume_frame = tk.Frame(root)
        resume_frame.pack(pady=10, fill="both", expand=True)

        tk.Label(resume_frame, text="Resumes").pack(anchor="w")
        tk.Button(resume_frame, text="Upload Resumes", command=self.select_resumes).pack(anchor="w") # Opens file system and lets user select multiple resumes

        self.resume_display = ScrolledText(resume_frame, height=8, wrap="word")
        self.resume_display.pack(fill="both", expand=True, padx=10, pady=5)
        
        # No. of resumes section
        input_frame = tk.Frame(root)
        input_frame.pack(pady=10, fill="x")

        tk.Label(input_frame, text="Enter the number of candidates you want to be shown").pack(anchor="w")

        self.input_textbox = tk.Text(input_frame, height=1, width=20)
        self.input_textbox.pack(anchor="w", padx=10)
 
        tk.Button(input_frame, text="Save number", command=self.save_integer_input).pack(anchor="w", padx=10, pady=5) # locks in number chosen

        self.input_status_label = tk.Label(input_frame, text="")
        self.input_status_label.pack(anchor="w", padx=10)
        
        # Continue button
        self.continue_button = tk.Button(root, text="Continue", command=self.open_results_screen, state=tk.DISABLED)
        self.continue_button.pack(pady=10)

    def select_job_description(self): # Grabs job description
        file_path = filedialog.askopenfilename(title="Select Job Description", filetypes=[("Text and PDF Files", "*.txt *.pdf")])

        if file_path:
            self.job_description.clear()
            self.job_description.append(file_path)
            self.jd_label.config(text=file_path)
            self.check_ready()

    def select_resumes(self): # Grabs resumes
        file_paths = filedialog.askopenfilenames(title="Select Resumes", filetypes=[("Resume Files", "*.txt *.pdf")])

        if file_paths:
            self.resumes.clear()
            self.resume_display.delete("1.0", tk.END)

            for path in file_paths:
                self.resumes.append(path)
                self.resume_display.insert(tk.END, path + "\n")

            self.check_ready()
 
    def save_integer_input(self): # grabs no. of resumes displayed
        raw_input = self.input_textbox.get("1.0", tk.END).strip()

        try:
            self.user_input_value = abs(int(raw_input)) # Idiot proofed the input, if the user enters a negative number the number becomes positive
            self.input_status_label.config(
                text = f"{self.user_input_value} candidates will be shown" # Displayed under text field to confirm No. of candidates displayed
            )
        except ValueError:
            self.user_input_value = 1 #Default value
            self.input_status_label.config(
                text="Error: Please enter a whole number." #Tells the user to try again
            )

    def check_ready(self): # Checks to see if both the resumes and job description are uploaded before the continue button is availible
        
        if self.job_description and self.resumes:
            self.continue_button.config(state=tk.NORMAL)

    def open_results_screen(self): # Opens results string
        
        raw_results = chonker(self.job_description, self.resumes,self.user_input_value)

        # Header/ auto IDing
        self.results_table = [["Resume", "Score", "Feedback Path", "ID"]]
        for i, row in enumerate(raw_results, start=1):
            self.results_table.append(row + [i])

        results_window = tk.Toplevel(self.root)
        results_window.title("Results & Feedback")
        results_window.geometry("800x550")

        # Results Table
        tk.Label(results_window, text="Resume Matching Results", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=5)

        results_display = ScrolledText(results_window, height=8, wrap="word")
        results_display.pack(fill="x", padx=10)

        for row in self.results_table:
            results_display.insert(tk.END, "\t".join(map(str, row)) + "\n")

        # Feedback Selection
        feedback_frame = tk.Frame(results_window)
        feedback_frame.pack(anchor="w", padx=10, pady=10)

        tk.Label(feedback_frame, text="Enter Applicant ID Number:").pack(anchor="w")

        self.feedback_id_box = tk.Text(feedback_frame, height=1, width=10)
        self.feedback_id_box.pack(anchor="w")

        self.feedback_error_label = tk.Label(feedback_frame, text="", fg="red")
        self.feedback_error_label.pack(anchor="w")

        tk.Button(feedback_frame, text="Display Feedback", command=self.display_feedback).pack(anchor="w", pady=5)

        self.feedback_display = ScrolledText(results_window, wrap="word")
        self.feedback_display.pack(fill="both", expand=True, padx=10, pady=10)

    def display_feedback(self):
        self.feedback_display.delete("1.0", tk.END)
        self.feedback_error_label.config(text="")

        raw_input = self.feedback_id_box.get("1.0", tk.END).strip()

        try:
            selected_id = abs(int(raw_input))
            
        except ValueError:
            self.feedback_error_label.config(text="Error: Please enter a whole number.")
            return

        for row in self.results_table[1:]:
            if row[3] == selected_id:
                resume_name = row[0]
                feedback_path = row[2]

                try:
                    with open(feedback_path, "r", encoding="utf-8") as file:
                        feedback_text = file.read()
                except FileNotFoundError:
                    feedback_text = "Error: Feedback file not found."

                self.feedback_display.insert(tk.END, f"Feedback for {resume_name} (ID {selected_id}):\n\n{feedback_text}")
                return

        self.feedback_error_label.config(text="Error: No feedback found for that ID.")
        
if __name__ == "__main__":
    root = tk.Tk()
    app = ResumeMatcherGUI(root)
    root.mainloop()
