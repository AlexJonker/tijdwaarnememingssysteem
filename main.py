import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import datetime
import shutil

def parse_record(line):
    line = line.strip()
    if not line.startswith("aa0"):
        return None, None
    if len(line) < 36:
        return None, None
    tag_id = line[4:16].lower()
    if not tag_id.startswith("058") or len(tag_id) != 12:
        return None, None
    date_str = line[20:26]
    time_str = line[26:34]
    hundredths_hex = line[34:36]
    try:
        year = int(date_str[0:2]) + 2000
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        hour = int(time_str[0:2])
        minute = int(time_str[2:4])
        second = int(time_str[4:6])
        hundredths = int(hundredths_hex, 16)
        timestamp = datetime.datetime(year, month, day, hour, minute, second, hundredths * 10000)
        return tag_id, timestamp
    except:
        return None, None

def generate_record(tag_id, timestamp):
    header = "aa01"  # default reader ID
    receiver_irq = "0001"
    date_str = timestamp.strftime("%y%m%d")
    time_str = timestamp.strftime("%H%M%S")
    hundredths = int(timestamp.microsecond / 10000)
    hundredths_hex = f"{hundredths:02x}"
    full = f"{header}{tag_id}{receiver_irq}{date_str}{time_str}{hundredths_hex}"
    return full.lower()

class IpicoEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Ipico Tijdregistratie Editor")

        self.data = {}
        self.tagmap = {}
        self.reverse_tagmap = {}
        self.gunshot_time = None
        self.current_selected_tag = None
        self.reader_filepath = None
        self.original_lines = []

        self.build_ui()

    def build_ui(self):
        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10)

        top_buttons = tk.Frame(frame)
        top_buttons.grid(row=0, column=0, columnspan=3, pady=5)

        tk.Button(top_buttons, text="Laad Readerdata", command=self.load_file).pack(side="left", padx=2)
        tk.Button(top_buttons, text="Laad Tagmap", command=self.load_tagmap).pack(side="left", padx=2)
        tk.Button(top_buttons, text="Stel Gunshot-tijd in", command=self.set_gunshot_time).pack(side="left", padx=2)
        tk.Button(top_buttons, text="Opslaan als CSV", command=self.save_file).pack(side="left", padx=2)

        self.tag_listbox = tk.Listbox(frame, width=35, exportselection=False)
        self.tag_listbox.grid(row=1, column=0, sticky="ns")
        self.tag_listbox.bind('<<ListboxSelect>>', self.update_time_list)

        self.time_listbox = tk.Listbox(frame, width=50)
        self.time_listbox.grid(row=1, column=1, sticky="ns")
        self.time_listbox.bind('<Double-Button-1>', self.edit_time)

        

        button_frame = tk.Frame(frame)
        button_frame.grid(row=2, column=1, pady=5)
        tk.Button(button_frame, text="Verwijder geselecteerde tijd", command=self.remove_time).pack(side="left", padx=2)
        tk.Button(button_frame, text="Voeg tijd toe", command=self.add_time).pack(side="left", padx=2)

        copy_frame = tk.Frame(frame)
        copy_frame.grid(row=3, column=0, columnspan=2, pady=5)
        tk.Label(copy_frame, text="Geselecteerde chipcode (kopieerbaar):").pack(anchor="w")
        self.selected_tag_entry = tk.Entry(copy_frame, width=50)
        self.selected_tag_entry.pack(fill="x", padx=5)

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not filepath:
            return
        self.reader_filepath = filepath

        # Backup maken
        backup_path = filepath.replace(".txt", "_backup.txt")
        shutil.copy(filepath, backup_path)

        self.data.clear()
        self.original_lines.clear()
        try:
            with open(filepath, "r") as f:
                self.original_lines = f.readlines()

            for line in self.original_lines:
                tag_id, timestamp = parse_record(line)
                if tag_id and timestamp:
                    self.data.setdefault(tag_id, []).append(timestamp)

            for timestamps in self.data.values():
                timestamps.sort()

            self.update_tag_list()
            messagebox.showinfo("Gelukt", f"Readerdata geladen. Backup gemaakt als:\n{backup_path}")
        except Exception as e:
            messagebox.showerror("Fout", f"Kon bestand niet laden:\n{e}")

    def load_tagmap(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if not filepath:
            return
        try:
            with open(filepath, "r") as f:
                lines = f.readlines()[1:]
                self.tagmap.clear()
                self.reverse_tagmap.clear()
                for line in lines:
                    if "," in line:
                        startnummer, tag_id = line.strip().split(",", 1)
                        startnummer = int(startnummer)
                        tag_id = tag_id.strip().lower()
                        self.tagmap[tag_id] = startnummer
                        self.reverse_tagmap[startnummer] = tag_id
            messagebox.showinfo("Succes", "Tagmap succesvol geladen.")
            self.update_tag_list()
        except Exception as e:
            messagebox.showerror("Fout", f"Tagmap laden mislukt:\n{e}")

    def set_gunshot_time(self):
        input_str = simpledialog.askstring("Gunshot tijd", "Voer gunshot tijd in als 'YYYY-MM-DD HH:MM:SS'")
        try:
            self.gunshot_time = datetime.datetime.strptime(input_str, "%Y-%m-%d %H:%M:%S")
            self.update_time_list()
        except:
            messagebox.showerror("Fout", "Verkeerd formaat. Gebruik: YYYY-MM-DD HH:MM:SS")

    def update_tag_list(self):
        self.tag_listbox.delete(0, tk.END)
        tag_tuples = []
        for tag_id in self.data.keys():
            startnummer = self.tagmap.get(tag_id)
            tag_tuples.append((startnummer if startnummer is not None else float('inf'), tag_id))

        tag_tuples.sort()
        for startnummer, tag_id in tag_tuples:
            display_num = "?" if startnummer == float('inf') else startnummer
            self.tag_listbox.insert(tk.END, f"{display_num} ({tag_id})")

    def update_time_list(self, event=None):
        self.time_listbox.delete(0, tk.END)
        selection = self.tag_listbox.curselection()
        if not selection:
            return
        entry = self.tag_listbox.get(selection[0])
        tag_id = entry.split("(")[-1].replace(")", "")
        self.current_selected_tag = tag_id
        self.selected_tag_entry.delete(0, tk.END)
        self.selected_tag_entry.insert(0, tag_id)
        if tag_id not in self.data:
            return
        for t in self.data[tag_id]:
            if self.gunshot_time:
                netto = t - self.gunshot_time
                self.time_listbox.insert(tk.END, f"{t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} → {str(netto)}")
            else:
                self.time_listbox.insert(tk.END, t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])

    def remove_time(self):
        idx = self.time_listbox.curselection()
        if not self.current_selected_tag or not idx:
            return
        timestamp = self.data[self.current_selected_tag].pop(idx[0])
        self.update_time_list()

        # Verwijder uit originele bestand
        formatted_to_remove = generate_record(self.current_selected_tag, timestamp)
        self.original_lines = [line for line in self.original_lines if not line.lower().startswith(formatted_to_remove)]
        with open(self.reader_filepath, "w") as f:
            f.writelines(self.original_lines)

    def add_time(self):
        if not self.current_selected_tag:
            return
        input_str = simpledialog.askstring("Voeg tijd toe", "Voer tijd in als 'YYYY-MM-DD HH:MM:SS.ms'")
        try:
            new_time = datetime.datetime.strptime(input_str, "%Y-%m-%d %H:%M:%S.%f")
            self.data[self.current_selected_tag].append(new_time)
            self.data[self.current_selected_tag].sort()
            self.update_time_list()

            # Genereer en voeg toe aan bestand
            new_line = generate_record(self.current_selected_tag, new_time)
            with open(self.reader_filepath, "a") as f:
                f.write(new_line + "\n")
            self.original_lines.append(new_line + "\n")
        except Exception as e:
            messagebox.showerror("Fout", f"Kan tijd niet toevoegen:\n{e}")

    def edit_time(self, event):
        idx = self.time_listbox.curselection()
        if not self.current_selected_tag or not idx:
            return
        old_time = self.data[self.current_selected_tag][idx[0]]
        input_str = simpledialog.askstring(
            "Bewerk tijd",
            "Pas tijd aan als 'YYYY-MM-DD HH:MM:SS.ms'",
            initialvalue=old_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        )
        if not input_str:
            return
        try:
            new_time = datetime.datetime.strptime(input_str, "%Y-%m-%d %H:%M:%S.%f")
            # Update in-memory data
            self.data[self.current_selected_tag][idx[0]] = new_time
            self.data[self.current_selected_tag].sort()
            self.update_time_list()

            # Update in file: remove old, add new
            formatted_old = generate_record(self.current_selected_tag, old_time)
            self.original_lines = [line for line in self.original_lines if not line.lower().startswith(formatted_old)]
            formatted_new = generate_record(self.current_selected_tag, new_time)
            self.original_lines.append(formatted_new + "\n")
            with open(self.reader_filepath, "w") as f:
                f.writelines(self.original_lines)
        except Exception as e:
            messagebox.showerror("Fout", f"Kan tijd niet aanpassen:\n{e}")


    def save_file(self):
        if not self.gunshot_time:
            messagebox.showerror("Fout", "Geen gunshot-tijd ingesteld.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not filepath:
            return
        try:
            with open(filepath, "w") as f:
                f.write("Startnummer,Tag ID,Absolute Tijd,Netto Tijd\n")
                for tag_id in sorted(self.data.keys()):
                    startnummer = self.tagmap.get(tag_id, "")
                    for t in self.data[tag_id]:
                        netto = t - self.gunshot_time
                        f.write(f"{startnummer},{tag_id},{t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]},{str(netto)}\n")
            messagebox.showinfo("Succes", "CSV succesvol opgeslagen.")
        except Exception as e:
            messagebox.showerror("Fout", f"Kon niet opslaan:\n{e}")

# Start GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = IpicoEditor(root)
    root.mainloop()
