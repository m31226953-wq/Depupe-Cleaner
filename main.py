import os
import hashlib
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ============= ЛОГИКА =============

def get_file_hash(filepath, chunk_size=8192):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return None

def find_duplicates(directory, extensions=None, min_size=1024):
    duplicates = {}
    for root, dirs, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                if os.path.getsize(filepath) < min_size:
                    continue
            except:
                continue
            
            if extensions:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in extensions:
                    continue
            
            file_hash = get_file_hash(filepath)
            if file_hash:
                if file_hash not in duplicates:
                    duplicates[file_hash] = []
                duplicates[file_hash].append(filepath)
    
    return {k: v for k, v in duplicates.items() if len(v) > 1}

def delete_duplicates_auto(duplicates, keep_newest=True):
    deleted = 0
    freed = 0
    
    for files in duplicates.values():
        file_info = []
        for f in files:
            try:
                file_info.append((f, os.path.getmtime(f), os.path.getsize(f)))
            except:
                continue
        
        if not file_info:
            continue
        
        file_info.sort(key=lambda x: x[1], reverse=keep_newest)
        
        for dup_path, dup_time, dup_size in file_info[1:]:
            try:
                os.remove(dup_path)
                deleted += 1
                freed += dup_size
            except:
                pass
    
    return deleted, freed

# ============= GUI =============

class DedupeCleanerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dedupe Cleaner")
        self.root.geometry("850x650")
        self.root.configure(bg='#1e1e1e')
        
        self.selected_folders = []
        self.duplicates_data = None
        
        self.setup_ui()
        
    def setup_ui(self):
        title = tk.Label(self.root, text="Dedupe Cleaner", 
                        font=("Segoe UI", 26, "bold"), 
                        bg='#1e1e1e', fg='#ffffff')
        title.pack(pady=20)
        
        # Папки
        frame_folders = tk.LabelFrame(self.root, text="Папки для сканирования", 
                                      bg='#2d2d2d', fg='#ffffff', font=("Segoe UI", 11))
        frame_folders.pack(fill="both", padx=20, pady=10)
        
        self.listbox = tk.Listbox(frame_folders, bg='#3d3d3d', fg='#ffffff', 
                                  height=5, font=("Consolas", 10))
        self.listbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        btn_frame = tk.Frame(frame_folders, bg='#2d2d2d')
        btn_frame.pack(pady=10)
        
        btn_add = tk.Button(btn_frame, text="+ Добавить папку", 
                           command=self.add_folder, bg='#4CAF50', fg='white',
                           font=("Segoe UI", 10), padx=20)
        btn_add.pack(side="left", padx=5)
        
        btn_remove = tk.Button(btn_frame, text="- Удалить", 
                               command=self.remove_folder, bg='#f44336', fg='white',
                               font=("Segoe UI", 10), padx=20)
        btn_remove.pack(side="left", padx=5)
        
        # Настройки
        frame_settings = tk.LabelFrame(self.root, text="Настройки", 
                                       bg='#2d2d2d', fg='#ffffff', font=("Segoe UI", 11))
        frame_settings.pack(fill="x", padx=20, pady=10)
        
        row1 = tk.Frame(frame_settings, bg='#2d2d2d')
        row1.pack(pady=10)
        
        tk.Label(row1, text="Расширения (через пробел):", 
                bg='#2d2d2d', fg='#ffffff').pack(side="left", padx=10)
        self.ext_entry = tk.Entry(row1, width=30, bg='#3d3d3d', fg='#ffffff')
        self.ext_entry.pack(side="left", padx=10)
        tk.Label(row1, text="пример: .jpg .png .mp4", 
                bg='#2d2d2d', fg='#888888').pack(side="left")
        
        row2 = tk.Frame(frame_settings, bg='#2d2d2d')
        row2.pack(pady=10)
        
        tk.Label(row2, text="Что оставлять:", bg='#2d2d2d', fg='#ffffff').pack(side="left", padx=10)
        self.keep_var = tk.StringVar(value="newest")
        tk.Radiobutton(row2, text="Новый файл", variable=self.keep_var, 
                      value="newest", bg='#2d2d2d', fg='#ffffff', selectcolor='#2d2d2d').pack(side="left", padx=10)
        tk.Radiobutton(row2, text="Старый файл", variable=self.keep_var, 
                      value="oldest", bg='#2d2d2d', fg='#ffffff', selectcolor='#2d2d2d').pack(side="left", padx=10)
        
        # Лог
        frame_log = tk.LabelFrame(self.root, text="Лог операций", 
                                  bg='#2d2d2d', fg='#ffffff', font=("Segoe UI", 11))
        frame_log.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.progress = ttk.Progressbar(frame_log, mode='indeterminate')
        self.progress.pack(fill="x", padx=10, pady=10)
        
        self.log_text = tk.Text(frame_log, bg='#0a0a0a', fg='#4ec9b0', 
                                font=("Consolas", 9), height=12)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Кнопки
        btn_control = tk.Frame(self.root, bg='#1e1e1e')
        btn_control.pack(pady=20)
        
        self.btn_start = tk.Button(btn_control, text="НАЙТИ ДУБЛИКАТЫ", 
                                   command=self.start_scan, bg='#2196F3', fg='white',
                                   font=("Segoe UI", 11, "bold"), padx=25, pady=8)
        self.btn_start.pack(side="left", padx=10)
        
        self.btn_clean = tk.Button(btn_control, text="УДАЛИТЬ ВСЁ", 
                                   command=self.start_clean, bg='#f44336', fg='white',
                                   font=("Segoe UI", 11, "bold"), padx=25, pady=8,
                                   state='disabled')
        self.btn_clean.pack(side="left", padx=10)
    
    def add_folder(self):
        folder = filedialog.askdirectory()
        if folder and folder not in self.selected_folders:
            self.selected_folders.append(folder)
            self.listbox.insert(tk.END, folder)
    
    def remove_folder(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            del self.selected_folders[idx]
            self.listbox.delete(idx)
    
    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def start_scan(self):
        if not self.selected_folders:
            messagebox.showerror("Ошибка", "Добавьте папку")
            return
        
        self.btn_start.config(state='disabled')
        self.btn_clean.config(state='disabled')
        self.duplicates_data = None
        self.log_text.delete(1.0, tk.END)
        self.progress.start()
        
        threading.Thread(target=self.scan_duplicates, daemon=True).start()
    
    def scan_duplicates(self):
        try:
            exts = None
            if self.ext_entry.get().strip():
                exts = [e.strip() for e in self.ext_entry.get().split()]
            
            all_dupes = {}
            for folder in self.selected_folders:
                self.log(f"[*] Сканирую: {folder}")
                dupes = find_duplicates(folder, exts, 1024)
                for h, f in dupes.items():
                    if h not in all_dupes:
                        all_dupes[h] = []
                    all_dupes[h].extend(f)
            
            all_dupes = {k: v for k, v in all_dupes.items() if len(v) > 1}
            
            if not all_dupes:
                self.log("\n[+] Дубликатов не найдено")
            else:
                total = sum(len(v)-1 for v in all_dupes.values())
                size = 0
                for v in all_dupes.values():
                    try:
                        size += os.path.getsize(v[0]) * (len(v)-1)
                    except:
                        pass
                
                self.log(f"\n[!] Найдено групп: {len(all_dupes)}")
                self.log(f"[!] Дубликатов: {total}")
                self.log(f"[💾] Освободится: {size/(1024*1024):.2f} MB")
                self.duplicates_data = all_dupes
                self.btn_clean.config(state='normal')
        except Exception as e:
            self.log(f"[X] Ошибка: {e}")
        finally:
            self.progress.stop()
            self.btn_start.config(state='normal')
    
    def start_clean(self):
        if not self.duplicates_data:
            messagebox.showerror("Ошибка", "Сначала найдите дубликаты")
            return
        
        if messagebox.askyesno("Подтверждение", "Удалить всё навсегда?\nОтменить нельзя!"):
            self.btn_clean.config(state='disabled')
            self.progress.start()
            threading.Thread(target=self.clean_duplicates, daemon=True).start()
    
    def clean_duplicates(self):
        try:
            keep = (self.keep_var.get() == 'newest')
            deleted, freed = delete_duplicates_auto(self.duplicates_data, keep)
            self.log(f"\n[✓] Удалено: {deleted} файлов")
            self.log(f"[💾] Освобождено: {freed/(1024*1024):.2f} MB")
            self.duplicates_data = None
            self.btn_clean.config(state='disabled')
        except Exception as e:
            self.log(f"[X] Ошибка: {e}")
        finally:
            self.progress.stop()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = DedupeCleanerGUI()
    app.run()