import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry  # Красивый календарь
from datetime import datetime, timedelta

# ==========================================
# 1. ЛОГИКА БАЗЫ ДАННЫХ (SQLite)
# ==========================================
DB_NAME = "hospital.db"
HOSPITAL_NAME = "Городская Поликлиника №1"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Таблица пользователей (Добавлено поле dob - дата рождения)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                full_name TEXT NOT NULL,
                dob TEXT,
                phone TEXT,
                city TEXT,
                address TEXT,
                specialty TEXT
            )
        ''')

        # Таблица записей (Добавлено поле report - протокол осмотра)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                doctor_id INTEGER NOT NULL,
                appt_date TEXT NOT NULL,
                appt_time TEXT NOT NULL,
                snils TEXT NOT NULL,
                hospital_name TEXT NOT NULL,
                visited INTEGER DEFAULT 0,
                report TEXT,
                FOREIGN KEY (patient_id) REFERENCES users(id),
                FOREIGN KEY (doctor_id) REFERENCES users(id)
            )
        ''')

        # Обновление старой базы (если она была создана в предыдущей версии)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN dob TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE appointments ADD COLUMN report TEXT")
        except sqlite3.OperationalError:
            pass

        # Создаем тестового врача, если врачей нет
        cursor.execute("SELECT COUNT(*) FROM users WHERE role='doctor'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO users (username, password, role, full_name, specialty) 
                VALUES ('doc', '123', 'doctor', 'Иванов И.И.', 'Терапевт')
            ''')
            cursor.execute('''
                INSERT INTO users (username, password, role, full_name, specialty) 
                VALUES ('doc2', '123', 'doctor', 'Петров П.П.', 'Хирург')
            ''')
        conn.commit()


def generate_time_slots():
    slots = []
    start_time = datetime.strptime('08:00', '%H:%M')
    end_time = datetime.strptime('18:00', '%H:%M')
    while start_time <= end_time:
        slots.append(start_time.strftime('%H:%M'))
        start_time += timedelta(minutes=15)
    return slots


def get_available_slots(doctor_id, date_str, exclude_appt_id=None):
    all_slots = generate_time_slots()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        query = "SELECT appt_time FROM appointments WHERE doctor_id = ? AND appt_date = ?"
        params = [doctor_id, date_str]

        if exclude_appt_id:  # Исключаем текущую запись (при переносе)
            query += " AND id != ?"
            params.append(exclude_appt_id)

        cursor.execute(query, params)
        booked_slots = [row[0] for row in cursor.fetchall()]

    return [slot for slot in all_slots if slot not in booked_slots]


# ==========================================
# 2. ГРАФИЧЕСКИЙ ИНТЕРФЕЙС
# ==========================================
class HospitalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Система Управления Поликлиникой")
        self.root.geometry("800x600")

        # Настройка красивого стиля
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6, font=("Segoe UI", 10))
        style.configure("TLabel", font=("Segoe UI", 11))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#2c3e50")
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=25)
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), background="#ecf0f1")

        self.current_user = None
        self.show_login_screen()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    # ==========================================
    # АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ
    # ==========================================
    def show_login_screen(self):
        self.clear_window()

        frame = ttk.Frame(self.root, padding=40)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(frame, text="Авторизация", style="Header.TLabel").pack(pady=(0, 20))

        ttk.Label(frame, text="Логин:").pack(anchor="w")
        login_entry = ttk.Entry(frame, width=30, font=("Segoe UI", 11))
        login_entry.pack(pady=(0, 10))

        ttk.Label(frame, text="Пароль:").pack(anchor="w")
        pass_entry = ttk.Entry(frame, width=30, show="*", font=("Segoe UI", 11))
        pass_entry.pack(pady=(0, 20))

        def login():
            username, password = login_entry.get(), pass_entry.get()
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
                user = cursor.fetchone()

            if user:
                # Столбцы: 0:id, 1:user, 2:pass, 3:role, 4:fio, 5:dob, 6:phone, 7:city, 8:addr, 9:spec
                self.current_user = {
                    "id": user[0], "role": user[3], "full_name": user[4],
                    "dob": user[5], "phone": user[6], "city": user[7], "address": user[8]
                }
                if self.current_user["role"] == "doctor":
                    self.show_doctor_screen()
                else:
                    self.show_patient_screen()
            else:
                messagebox.showerror("Ошибка", "Неверный логин или пароль!")

        ttk.Button(frame, text="Войти", command=login, width=28).pack(pady=5)
        ttk.Button(frame, text="Регистрация пациента", command=self.show_register_screen, width=28).pack()

    def show_register_screen(self):
        self.clear_window()

        frame = ttk.Frame(self.root, padding=40)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(frame, text="Регистрация", style="Header.TLabel").pack(pady=(0, 15))

        entries = {}
        fields = [("Логин", False), ("Пароль", True), ("ФИО", False),
                  ("Дата рождения (ДД.ММ.ГГГГ)", False), ("Телефон", False),
                  ("Город", False), ("Адрес", False)]

        for field, is_pass in fields:
            ttk.Label(frame, text=field + ":").pack(anchor="w")
            e = ttk.Entry(frame, width=40, show="*" if is_pass else "")
            e.pack(pady=(0, 5))
            entries[field] = e

        def register():
            data = [entries[f[0]].get() for f in fields]
            if not all(data):
                messagebox.showerror("Ошибка", "Заполните все поля!")
                return

            try:
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO users (username, password, full_name, dob, phone, city, address, role) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'patient')
                    ''', data)
                    conn.commit()
                messagebox.showinfo("Успех", "Регистрация успешна!")
                self.show_login_screen()
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Этот логин уже занят!")

        ttk.Button(frame, text="Зарегистрироваться", command=register).pack(pady=(15, 5))
        ttk.Button(frame, text="Назад", command=self.show_login_screen).pack()

    # ==========================================
    # ПАНЕЛЬ ПАЦИЕНТА (4 Вкладки)
    # ==========================================
    def show_patient_screen(self):
        self.clear_window()

        top_frame = tk.Frame(self.root, bg="#34495e")
        top_frame.pack(fill="x")
        tk.Label(top_frame, text=f"Пациент: {self.current_user['full_name']}", font=("Segoe UI", 14), fg="white",
                 bg="#34495e").pack(side="left", padx=20, pady=10)
        ttk.Button(top_frame, text="Выйти", command=self.show_login_screen).pack(side="right", padx=20)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Создаем вкладки
        tab1 = ttk.Frame(notebook);
        notebook.add(tab1, text="Запись на прием")
        tab2 = ttk.Frame(notebook);
        notebook.add(tab2, text="Мои записи")
        tab3 = ttk.Frame(notebook);
        notebook.add(tab3, text="Протоколы осмотров")
        tab4 = ttk.Frame(notebook);
        notebook.add(tab4, text="Профиль")

        self.build_patient_tab_book(tab1)
        self.build_patient_tab_my_appts(tab2)
        self.build_patient_tab_reports(tab3)
        self.build_patient_tab_profile(tab4)

        # Обновляем данные при переключении вкладок
        notebook.bind("<<NotebookTabChanged>>", lambda e: self.build_patient_tab_my_appts(tab2))
        notebook.bind("<<NotebookTabChanged>>", lambda e: self.build_patient_tab_reports(tab3), add="+")

    def build_patient_tab_book(self, parent):
        frame = ttk.Frame(parent, padding=20)
        frame.pack(fill="both", expand=True)

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, full_name, specialty FROM users WHERE role='doctor'")
            doctors = {f"{r[1]} ({r[2]})": r[0] for r in cursor.fetchall()}

        ttk.Label(frame, text="СНИЛС:").grid(row=0, column=0, sticky="w", pady=10)
        snils_entry = ttk.Entry(frame, width=30)
        snils_entry.grid(row=0, column=1, pady=10)

        ttk.Label(frame, text="Врач:").grid(row=1, column=0, sticky="w", pady=10)
        doc_combo = ttk.Combobox(frame, values=list(doctors.keys()), state="readonly", width=28)
        doc_combo.grid(row=1, column=1, pady=10)

        ttk.Label(frame, text="Дата приема:").grid(row=2, column=0, sticky="w", pady=10)
        cal = DateEntry(frame, width=28, background='darkblue', foreground='white', borderwidth=2,
                        date_pattern='yyyy-mm-dd')
        cal.grid(row=2, column=1, pady=10)

        ttk.Label(frame, text="Свободное время:").grid(row=3, column=0, sticky="w", pady=10)
        time_combo = ttk.Combobox(frame, state="readonly", width=28)
        time_combo.grid(row=3, column=1, pady=10)

        def update_times(*args):
            doc_name, date_str = doc_combo.get(), cal.get()
            if doc_name and date_str:
                avail_slots = get_available_slots(doctors[doc_name], date_str)
                time_combo['values'] = avail_slots
                time_combo.set(avail_slots[0] if avail_slots else "Нет свободных мест")

        doc_combo.bind('<<ComboboxSelected>>', update_times)
        cal.bind("<<DateEntrySelected>>", update_times)

        def save():
            doc_name, time_str, snils_str = doc_combo.get(), time_combo.get(), snils_entry.get()
            if not doc_name or time_str in ("", "Нет свободных мест") or not snils_str:
                messagebox.showwarning("Ошибка", "Заполните все поля и выберите время.")
                return

            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO appointments (patient_id, doctor_id, appt_date, appt_time, snils, hospital_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (self.current_user['id'], doctors[doc_name], cal.get(), time_str, snils_str, HOSPITAL_NAME))
                conn.commit()
            messagebox.showinfo("Успех", "Талон успешно оформлен!")
            update_times()

        ttk.Button(frame, text="Записаться", command=save).grid(row=4, column=0, columnspan=2, pady=20)

    def build_patient_tab_my_appts(self, parent):
        for widget in parent.winfo_children(): widget.destroy()

        columns = ("id", "date", "time", "doctor", "status")
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        tree.heading("id", text="ID")
        tree.heading("date", text="Дата")
        tree.heading("time", text="Время")
        tree.heading("doctor", text="Врач")
        tree.heading("status", text="Статус")

        tree.column("id", width=30)
        tree.column("date", width=100)
        tree.column("time", width=80)
        tree.column("doctor", width=250)
        tree.column("status", width=100)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.id, a.appt_date, a.appt_time, u.full_name, a.visited 
                FROM appointments a JOIN users u ON a.doctor_id = u.id
                WHERE a.patient_id = ? ORDER BY a.appt_date, a.appt_time
            ''', (self.current_user['id'],))

            for row in cursor.fetchall():
                status = "✅ Посетил" if row[4] else "⏳ Ожидается"
                tree.insert("", "end", values=(row[0], row[1], row[2], row[3], status))

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", padx=10, pady=10)

        def cancel_appt():
            selected = tree.selection()
            if not selected: return
            appt_id = tree.item(selected[0])['values'][0]
            if messagebox.askyesno("Подтверждение", "Вы точно хотите отменить запись?"):
                with sqlite3.connect(DB_NAME) as conn:
                    conn.cursor().execute("DELETE FROM appointments WHERE id = ?", (appt_id,))
                    conn.commit()
                self.build_patient_tab_my_appts(parent)

        def reschedule_appt():
            selected = tree.selection()
            if not selected: return
            appt_id = tree.item(selected[0])['values'][0]
            doc_name = tree.item(selected[0])['values'][3]

            # Открываем окно переноса
            top = tk.Toplevel(self.root)
            top.title("Перенос записи")
            top.geometry("300x250")

            ttk.Label(top, text=f"Перенос приема: {doc_name}").pack(pady=10)
            cal = DateEntry(top, width=20, background='darkblue', foreground='white', date_pattern='yyyy-mm-dd')
            cal.pack(pady=10)

            time_combo = ttk.Combobox(top, state="readonly", width=20)
            time_combo.pack(pady=10)

            def get_doc_id():
                with sqlite3.connect(DB_NAME) as c:
                    return c.cursor().execute("SELECT id FROM users WHERE full_name=?", (doc_name,)).fetchone()[0]

            def update_t(*args):
                avail_slots = get_available_slots(get_doc_id(), cal.get(), appt_id)
                time_combo['values'] = avail_slots
                time_combo.set(avail_slots[0] if avail_slots else "")

            cal.bind("<<DateEntrySelected>>", update_t)
            update_t()

            def confirm():
                if not time_combo.get(): return
                with sqlite3.connect(DB_NAME) as conn:
                    conn.cursor().execute("UPDATE appointments SET appt_date=?, appt_time=? WHERE id=?",
                                          (cal.get(), time_combo.get(), appt_id))
                    conn.commit()
                top.destroy()
                self.build_patient_tab_my_appts(parent)

            ttk.Button(top, text="Сохранить новую дату", command=confirm).pack(pady=10)

        ttk.Button(btn_frame, text="Отменить запись", command=cancel_appt).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Перенести запись", command=reschedule_appt).pack(side="left", padx=5)

    def build_patient_tab_reports(self, parent):
        for widget in parent.winfo_children(): widget.destroy()

        list_frame = ttk.Frame(parent)
        list_frame.pack(side="left", fill="y", padx=10, pady=10)

        tree = ttk.Treeview(list_frame, columns=("date", "doc"), show="headings")
        tree.heading("date", text="Дата")
        tree.heading("doc", text="Врач")
        tree.column("date", width=100)
        tree.column("doc", width=150)
        tree.pack(fill="y", expand=True)

        text_area = tk.Text(parent, wrap="word", font=("Segoe UI", 11), bg="#fdfdfd")
        text_area.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.appt_date, u.full_name, a.report 
                FROM appointments a JOIN users u ON a.doctor_id = u.id
                WHERE a.patient_id = ? AND a.report IS NOT NULL
            ''', (self.current_user['id'],))
            records = cursor.fetchall()

            for i, r in enumerate(records):
                tree.insert("", "end", iid=i, values=(r[0], r[1]))

        def on_select(event):
            selected = tree.selection()
            if selected:
                idx = int(selected[0])
                text_area.delete("1.0", tk.END)
                text_area.insert(tk.END, records[idx][2])

        tree.bind("<<TreeviewSelect>>", on_select)

    def build_patient_tab_profile(self, parent):
        frame = ttk.Frame(parent, padding=30)
        frame.pack(fill="both", expand=True)

        fields = ["full_name", "dob", "phone", "city", "address"]
        labels = ["ФИО:", "Дата рождения:", "Телефон:", "Город:", "Адрес:"]
        entries = {}

        for i, key in enumerate(fields):
            ttk.Label(frame, text=labels[i]).grid(row=i, column=0, sticky="w", pady=10, padx=10)
            e = ttk.Entry(frame, width=40)
            e.insert(0, self.current_user[key] if self.current_user[key] else "")
            e.grid(row=i, column=1, pady=10)
            entries[key] = e

        def save_profile():
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users SET full_name=?, dob=?, phone=?, city=?, address=? WHERE id=?
                ''', (entries["full_name"].get(), entries["dob"].get(), entries["phone"].get(),
                      entries["city"].get(), entries["address"].get(), self.current_user["id"]))
                conn.commit()

            # Обновляем данные в кэше
            for k in fields: self.current_user[k] = entries[k].get()
            messagebox.showinfo("Успех", "Данные профиля обновлены!")

        ttk.Button(frame, text="Сохранить изменения", command=save_profile).grid(row=len(fields), column=0,
                                                                                 columnspan=2, pady=20)

    # ==========================================
    # ПАНЕЛЬ ВРАЧА
    # ==========================================
    def show_doctor_screen(self):
        self.clear_window()

        top_frame = tk.Frame(self.root, bg="#27ae60")
        top_frame.pack(fill="x")
        tk.Label(top_frame, text=f"Доктор: {self.current_user['full_name']}", font=("Segoe UI", 14), fg="white",
                 bg="#27ae60").pack(side="left", padx=20, pady=10)
        ttk.Button(top_frame, text="Выйти", command=self.show_login_screen).pack(side="right", padx=20)

        # Фильтры
        filter_frame = ttk.Frame(self.root)
        filter_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(filter_frame, text="Выбрать дату:").pack(side="left", padx=5)
        cal = DateEntry(filter_frame, width=15, background='darkblue', foreground='white', date_pattern='yyyy-mm-dd')
        cal.pack(side="left", padx=5)

        # Таблица записей
        columns = ("id", "time", "patient", "snils", "status")
        tree = ttk.Treeview(self.root, columns=columns, show="headings")
        tree.heading("id", text="ID")
        tree.heading("time", text="Время")
        tree.heading("patient", text="Пациент")
        tree.heading("snils", text="СНИЛС")
        tree.heading("status", text="Статус")

        tree.column("id", width=30)
        tree.column("time", width=80)
        tree.column("patient", width=250)
        tree.column("snils", width=120)
        tree.column("status", width=120)
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        def load_patients(*args):
            for item in tree.get_children(): tree.delete(item)
            selected_date = cal.get()
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT a.id, a.appt_time, u.full_name, a.snils, a.visited 
                    FROM appointments a JOIN users u ON a.patient_id = u.id
                    WHERE a.doctor_id = ? AND a.appt_date = ?
                    ORDER BY a.appt_time
                ''', (self.current_user['id'], selected_date))

                for row in cursor.fetchall():
                    status = "✅ Был на приеме" if row[4] else "❌ Ожидается"
                    tree.insert("", "end", values=(row[0], row[1], row[2], row[3], status))

        cal.bind("<<DateEntrySelected>>", load_patients)
        ttk.Button(filter_frame, text="Сбросить дату (Показать всех)",
                   command=lambda: [cal.delete(0, 'end'), load_patients()]).pack(side="left", padx=10)

        # Действия врача
        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", padx=10, pady=10)

        def toggle_visited():
            selected = tree.selection()
            if not selected: return
            appt_id = tree.item(selected[0])['values'][0]
            current_status = tree.item(selected[0])['values'][4]
            new_status = 0 if "Был" in current_status else 1

            with sqlite3.connect(DB_NAME) as conn:
                conn.cursor().execute("UPDATE appointments SET visited = ? WHERE id = ?", (new_status, appt_id))
                conn.commit()
            load_patients()

        def write_report():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Внимание", "Выберите пациента!")
                return

            appt_id = tree.item(selected[0])['values'][0]
            pat_name = tree.item(selected[0])['values'][2]

            top = tk.Toplevel(self.root)
            top.title(f"Медицинский протокол: {pat_name}")
            top.geometry("500x400")

            ttk.Label(top, text="Заключение / Назначение:", font=("Segoe UI", 12, "bold")).pack(pady=10)
            text_area = tk.Text(top, wrap="word", font=("Segoe UI", 11))
            text_area.pack(fill="both", expand=True, padx=10)

            # Загружаем существующий текст, если есть
            with sqlite3.connect(DB_NAME) as conn:
                old_report = conn.cursor().execute("SELECT report FROM appointments WHERE id=?", (appt_id,)).fetchone()[
                    0]
                if old_report: text_area.insert("1.0", old_report)

            def save_rep():
                with sqlite3.connect(DB_NAME) as conn:
                    # Сохраняем протокол и автоматически отмечаем, что пациент БЫЛ (visited=1)
                    conn.cursor().execute("UPDATE appointments SET report = ?, visited = 1 WHERE id = ?",
                                          (text_area.get("1.0", "end-1c"), appt_id))
                    conn.commit()
                top.destroy()
                load_patients()

            ttk.Button(top, text="Сохранить протокол", command=save_rep).pack(pady=10)

        ttk.Button(action_frame, text="Отметить Присутствие/Отсутствие", command=toggle_visited).pack(side="left",
                                                                                                      padx=5)
        ttk.Button(action_frame, text="Написать протокол осмотра", command=write_report).pack(side="left", padx=5)

        load_patients()  # Изначальная загрузка


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = HospitalApp(root)
    root.mainloop()