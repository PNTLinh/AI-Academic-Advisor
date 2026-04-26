import sqlite3

conn = sqlite3.connect('data/academic.db')
cursor = conn.cursor()

# Delete existing corrupted data
cursor.execute("DELETE FROM student_notification_preferences WHERE student_id IN ('SV001', 'SV002', 'SV003')")
cursor.execute("DELETE FROM review_notifications_history WHERE student_id IN ('SV001', 'SV002', 'SV003')")
cursor.execute("DELETE FROM student_semester_study_schedule WHERE student_id IN ('SV001', 'SV002', 'SV003')")
cursor.execute("DELETE FROM Student_Transcripts WHERE student_id IN ('SV001', 'SV002', 'SV003')")
cursor.execute("DELETE FROM Students WHERE student_id IN ('SV001', 'SV002', 'SV003')")

# Delete existing semesters
cursor.execute("DELETE FROM Semesters WHERE semester_id IN ('2026-1', '2026-2')")

# Re-insert with proper UTF-8 encoding
cursor.execute("INSERT INTO Semesters (semester_id, start_date, end_date) VALUES ('2026-1', '2026-01-15', '2026-05-15')")
cursor.execute("INSERT INTO Semesters (semester_id, start_date, end_date) VALUES ('2026-2', '2026-09-01', '2026-12-31')")

cursor.execute("INSERT INTO Students (student_id, full_name, curriculum_id, target_cpa, current_cpa) VALUES ('SV001', 'Nguyễn Văn A', 'IT1', 3.5, 3.2)")
cursor.execute("INSERT INTO Students (student_id, full_name, curriculum_id, target_cpa, current_cpa) VALUES ('SV002', 'Trần Thị B', 'IT1', 3.6, 3.4)")
cursor.execute("INSERT INTO Students (student_id, full_name, curriculum_id, target_cpa, current_cpa) VALUES ('SV003', 'Phạm Minh C', 'IT2', 3.2, 3.0)")

# Insert transcripts
transcripts = [
    ('SV001', 'IT1108', '2026-1', 'A', 4.0, 1),
    ('SV001', 'MI1111', '2026-1', 'B+', 3.5, 1),
    ('SV001', 'PH1110', '2026-1', 'B', 3.0, 1),
    ('SV002', 'IT1108', '2026-1', 'A', 4.0, 1),
    ('SV002', 'IT1110', '2026-1', 'A-', 3.7, 1),
    ('SV002', 'MI1111', '2026-1', 'A', 4.0, 1),
    ('SV003', 'IT1110', '2026-1', 'B', 3.0, 1),
]
cursor.executemany("INSERT INTO Student_Transcripts (student_id, course_id, semester_id, grade_letter, grade_number, is_passed) VALUES (?, ?, ?, ?, ?, ?)", transcripts)

# Insert study schedules
schedules = [
    ('SV001', '2026-1', 'IT1108', 1, 120, 90, 75),
    ('SV001', '2026-1', 'MI1111', 1, 150, 120, 80),
    ('SV002', '2026-1', 'IT1108', 1, 120, 120, 100),
    ('SV002', '2026-1', 'IT1110', 1, 100, 100, 100),
]
cursor.executemany("INSERT INTO student_semester_study_schedule (student_id, semester_id, course_id, week_no, planned_study_minutes, actual_study_minutes, review_progress_pct) VALUES (?, ?, ?, ?, ?, ?, ?)", schedules)

# Insert lecture frames (ignore if already exists)
frames = [
    ('IT1', 'IT1108', 1, 'Giới thiệu Lập trình', 'Khái niệm cơ bản, biến, kiểu dữ liệu', 10),
    ('IT1', 'IT1108', 2, 'Cấu Trúc Điều Kiện', 'If/else, switch case, toán tử so sánh', 20),
    ('IT1', 'MI1111', 1, 'Giới thiệu Giải tích', 'Hàm, giới hạn, tính liên tục', 15),
]
cursor.executemany("INSERT OR IGNORE INTO course_lecture_frames (curriculum_id, course_id, week_no, lecture_title, topic_outline, expected_progress_pct) VALUES (?, ?, ?, ?, ?, ?)", frames)

# Insert notification preferences
prefs = [
    ('SV001', 1, 2, '22:00', '07:00', 420),
    ('SV002', 1, 3, '23:00', '06:00', 420),
    ('SV003', 0, 2, '22:00', '07:00', 420),
]
cursor.executemany("INSERT INTO student_notification_preferences (student_id, enabled, frequency_per_day, quiet_hours_start, quiet_hours_end, timezone_offset_minutes) VALUES (?, ?, ?, ?, ?, ?)", prefs)

conn.commit()
print("✅ Students inserted successfully with proper UTF-8 encoding")
print(f"Total students: {cursor.execute('SELECT COUNT(*) FROM Students').fetchone()[0]}")
conn.close()
