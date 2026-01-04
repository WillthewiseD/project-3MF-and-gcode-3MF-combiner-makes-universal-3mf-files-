import tkinter as tk
from tkinter import messagebox, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import zipfile
import shutil
import os
import re

class MetadataSwapperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("3MF Advanced Toolkit")
        self.root.geometry("600x850")
        
        self.target_files = {} 
        self.source_files = {} 

        tk.Label(root, text="3MF Advanced Toolkit", font=("Arial", 16, "bold")).pack(pady=10)
        tk.Label(root, text="App for formating 3mf files so that they work in 3d modeling studios and on your 3d printer.", font=("Arial", 10, "bold")).pack(pady=10)

        # --- Drop Zone 1: TARGETS ---
        self.lbl1 = tk.Label(root, text="1. Click or Drop Studio 3MFs(TARGETS) Here\n(Files to be modified)", 
                             bg="#e1e1e1", width=60, height=5, relief="groove", cursor="hand2")
        self.lbl1.pack(pady=10)
        self.lbl1.drop_target_register(DND_FILES)
        self.lbl1.dnd_bind('<<Drop>>', self.drop_targets)
        self.lbl1.bind("<Button-1>", self.browse_targets) # Click to browse

        # --- Drop Zone 2: SOURCES ---
        self.lbl2 = tk.Label(root, text="2. Click or Drop Gcode 3MFs(SOURCES) Here\n(Settings/Metadata to copy)(IMPORTANT: Same Name as The Target Files)", 
                             bg="#e1e1e1", width=60, height=5, relief="groove", cursor="hand2")
        self.lbl2.pack(pady=10)
        self.lbl2.drop_target_register(DND_FILES)
        self.lbl2.dnd_bind('<<Drop>>', self.drop_sources)
        self.lbl2.bind("<Button-1>", self.browse_sources) # Click to browse

        # --- List Display ---
        tk.Label(root, text="Queue (Select and press 'Delete' to remove):", font=("Arial", 9, "bold")).pack(pady=(10, 0))
        self.file_listbox = tk.Listbox(root, width=75, height=8, selectmode=tk.EXTENDED)
        self.file_listbox.pack(pady=5, padx=10)
        self.file_listbox.bind("<Delete>", self.delete_selected)

        tk.Button(root, text="Clear All Lists", command=self.clear_all, bg="#f8d7da").pack(pady=2)

        # --- Options ---
        opts_frame = tk.LabelFrame(root, text="Options", padx=10, pady=10)
        opts_frame.pack(pady=10, fill="x", padx=20)

        self.single_mode_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opts_frame, text="SINGLE FILE MODE (Wipe files images and/or names to the name of the file\n based on which checkboxes you checked, doesn't combine multiple files)", 
                       variable=self.single_mode_var, command=self.toggle_single_mode, 
                       font=("Arial", 9, "bold"), fg="#d9534f").pack(anchor="w")

        self.del_aux_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opts_frame, text="Delete 'Auxiliaries' folder(Delete all photos and gifs to make it just show the model as the picture)", variable=self.del_aux_var).pack(anchor="w")

        self.rename_plate_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opts_frame, text="Rename the model to the name of the file(what name shows up on the 3d printer)", variable=self.rename_plate_var).pack(anchor="w")

        # --- Process Button ---
        self.btn = tk.Button(root, text="Match & Process Files", command=self.process_files, 
                             bg="#28a745", fg="white", font=("Arial", 10, "bold"), state="disabled")
        self.btn.pack(pady=15)

        self.status_lbl = tk.Label(root, text="Drop files or click boxes to begin...", fg="blue")
        self.status_lbl.pack()

    # --- New Browser Methods ---
    def browse_targets(self, event=None):
        files = filedialog.askopenfilenames(title="Select Target 3MF Files", filetypes=[("3MF files", "*.3mf")])
        if files:
            self.add_targets(files)

    def browse_sources(self, event=None):
        if self.single_mode_var.get(): return
        files = filedialog.askopenfilenames(title="Select Source 3MF Files", filetypes=[("3MF files", "*.3mf")])
        if files:
            self.add_sources(files)

    def delete_selected(self, event):
        """Removes the selected items from the listbox and internal dictionaries."""
        selected_indices = self.file_listbox.curselection()
        for index in reversed(selected_indices):
            item_text = self.file_listbox.get(index)
            # Extract filename from "[STATUS] filename"
            filename = item_text.split("] ", 1)[-1]
            if filename in self.target_files: del self.target_files[filename]
            if filename in self.source_files: del self.source_files[filename]
        
        self.update_ui_state()

    def toggle_single_mode(self):
        if self.single_mode_var.get():
            self.lbl2.config(text="SOURCE DISABLED\n(Single File Mode Active)", bg="#f2dede", cursor="arrow")
            self.btn.config(text="Process Files (Standalone)")
        else:
            self.lbl2.config(text="2. Click or Drop SOURCE(S) Here\n(Settings/Metadata to copy)", bg="#e1e1e1", cursor="hand2")
            self.btn.config(text="Match & Process Files")
        self.update_ui_state()

    def parse_drop_data(self, data):
        pattern = r'\{(.*?)\}|(\S+)'
        files = []
        for match in re.finditer(pattern, data):
            path = match.group(1) if match.group(1) else match.group(2)
            if path and path.lower().endswith('.3mf'):
                files.append(os.path.abspath(path))
        return files

    def clear_all(self):
        self.target_files = {}
        self.source_files = {}
        self.update_ui_state()

    def update_ui_state(self):
        """Unified UI refresher."""
        self.update_listbox()
        self.check_ready()
        
        t_count = len(self.target_files)
        s_count = len(self.source_files)
        
        self.lbl1.config(text=f"{t_count} Targets Loaded" if t_count > 0 else "1. Click or Drop TARGET 3MF's Here that you want to modify", 
                         bg="#c1f0c1" if t_count > 0 else "#e1e1e1")
        
        if not self.single_mode_var.get():
            self.lbl2.config(text=f"{s_count} Sources Loaded" if s_count > 0 else "2. Click or Drop Gcode 3MFs(SOURCES) Here\n(Settings/Metadata to copy)(IMPORTANT: Same Name as The Target Files)", 
                             bg="#c1f0c1" if s_count > 0 else "#e1e1e1")

    def update_listbox(self):
        self.file_listbox.delete(0, tk.END)
        is_single = self.single_mode_var.get()
        all_filenames = sorted(set(list(self.target_files.keys()) + list(self.source_files.keys())))
        for name in all_filenames:
            if is_single:
                status = "✅ READY" if name in self.target_files else "⚙️ SOURCE (Ignored)"
            else:
                if name in self.target_files and name in self.source_files: status = "✅ READY"
                elif name in self.target_files: status = "📂 TARGET ONLY"
                else: status = "⚙️ SOURCE ONLY"
            self.file_listbox.insert(tk.END, f"[{status}] {name}")

    def add_targets(self, paths):
        for p in paths: self.target_files[os.path.basename(p)] = p
        self.update_ui_state()

    def add_sources(self, paths):
        for p in paths: self.source_files[os.path.basename(p)] = p
        self.update_ui_state()

    def drop_targets(self, event):
        self.add_targets(self.parse_drop_data(event.data))

    def drop_sources(self, event):
        if not self.single_mode_var.get():
            self.add_sources(self.parse_drop_data(event.data))

    def check_ready(self):
        is_single = self.single_mode_var.get()
        ready_count = len(self.target_files) if is_single else len([f for f in self.target_files if f in self.source_files])
        self.btn.config(state="normal" if ready_count > 0 else "disabled")
        self.status_lbl.config(text=f"{ready_count} files ready." if ready_count > 0 else "Waiting for files...", fg="green" if ready_count > 0 else "blue")

    def regex_rename_json(self, file_path, new_name):
        try:
            with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
            pattern = r'("name"\s*:\s*")([^"]*)(")'
            updated_content = re.sub(pattern, rf'\1{new_name}\3', content)
            with open(file_path, 'w', encoding='utf-8') as f: f.write(updated_content)
        except: pass

    def process_files(self):
        out_dir = filedialog.askdirectory(title="Select Folder to Save Results")
        if not out_dir: return
        is_single = self.single_mode_var.get()
        process_list = list(self.target_files.keys()) if is_single else [f for f in self.target_files if f in self.source_files]
        success_count = 0

        for filename in process_list:
            target_path = self.target_files[filename]
            clean_name = os.path.splitext(filename)[0]
            temp_target = os.path.join(os.getcwd(), f"temp_t_{clean_name}")
            try:
                with zipfile.ZipFile(target_path, 'r') as z: z.extractall(temp_target)
                if self.del_aux_var.get():
                    aux = os.path.join(temp_target, 'Auxiliaries')
                    if os.path.exists(aux): shutil.rmtree(aux)
                if not is_single:
                    source_path = self.source_files[filename]
                    temp_source = os.path.join(os.getcwd(), f"temp_s_{clean_name}")
                    with zipfile.ZipFile(source_path, 'r') as z: z.extractall(temp_source)
                    s_meta, t_meta = os.path.join(temp_source, 'Metadata'), os.path.join(temp_target, 'Metadata')
                    if os.path.exists(s_meta):
                        if os.path.exists(t_meta): shutil.rmtree(t_meta)
                        shutil.copytree(s_meta, t_meta)
                    shutil.rmtree(temp_source, ignore_errors=True)
                if self.rename_plate_var.get():
                    p_json = os.path.join(temp_target, 'Metadata', 'plate_1.json')
                    if os.path.exists(p_json): self.regex_rename_json(p_json, clean_name)
                final_out = os.path.join(out_dir, f"{filename}")
                with zipfile.ZipFile(final_out, 'w', zipfile.ZIP_DEFLATED) as nz:
                    for root, _, files in os.walk(temp_target):
                        for f in files:
                            fp = os.path.join(root, f)
                            rel = os.path.relpath(fp, temp_target)
                            nz.write(fp, rel)
                success_count += 1
            except: pass
            finally: shutil.rmtree(temp_target, ignore_errors=True)
        messagebox.showinfo("Success", f"Processed {success_count} files.")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = MetadataSwapperApp(root)
    root.mainloop()