CREATE TABLE Course_Categories (
    category_id SERIAL PRIMARY KEY,
    category_name NVARCHAR(100) NOT NULL -- Ví dụ: 'Lý luận chính trị', 'Cơ sở ngành', 'Module 1', 'Tự chọn tự do'
);
CREATE TABLE Courses (
    course_id VARCHAR(20) PRIMARY KEY, -- Ví dụ: IT3011
    course_name NVARCHAR(255) NOT NULL,
    credits INT NOT NULL,
    description TEXT,
    department VARCHAR(100)           -- Viện/Khoa quản lý
    is_mandatory BOOLEAN DEFAULT TRUE,      -- TRUE: Bắt buộc, FALSE: Tự chọn
    category_id INT,                        -- Liên kết với bảng nhóm môn học
    
    FOREIGN KEY (category_id) REFERENCES Course_Categories(category_id)
);

-- 2. QUẢN LÝ QUY CHẾ & CHƯƠNG TRÌNH ĐÀO TẠO
CREATE TABLE Curriculums (
    curriculum_id SERIAL PRIMARY KEY,
    major_name NVARCHAR(255),         -- Ngành học
    total_credits_required INT,       -- Tổng tín chỉ tốt nghiệp
    version VARCHAR(10)               -- Khóa (VD: K65, K66)
);

CREATE TABLE Curriculum_Details (
    curriculum_id INT REFERENCES Curriculums(curriculum_id),
    course_id VARCHAR(20) REFERENCES Courses(course_id),
    is_required BOOLEAN DEFAULT TRUE, -- Môn bắt buộc hay tự chọn
    semester_propose INT,             -- Kỳ học gợi ý theo khung (1-10)
    PRIMARY KEY (curriculum_id, course_id)
);

-- Bảng quan trọng: Môn học tiên quyết/song hành
CREATE TABLE Course_Dependencies (
    course_id VARCHAR(20) REFERENCES Courses(course_id),
    dependency_id VARCHAR(20) REFERENCES Courses(course_id),
    dependency_type VARCHAR(50), -- 'Prerequisite' (Tiên quyết), 'Parallel' (Song hành), 'Pre-condition' (Học trước)
    PRIMARY KEY (course_id, dependency_id, dependency_type)
);

-- 3. QUẢN LÝ THỜI KHÓA BIỂU (Dữ liệu biến động theo kỳ)
CREATE TABLE Semesters (
    semester_id VARCHAR(10) PRIMARY KEY, -- Ví dụ: 20231, 20232
    start_date DATE,
    end_date DATE
);

CREATE TABLE Classes (
    class_id VARCHAR(20) PRIMARY KEY,    -- Mã lớp (VD: 123456)
    course_id VARCHAR(20) REFERENCES Courses(course_id),
    semester_id VARCHAR(10) REFERENCES Semesters(semester_id),
    instructor_name NVARCHAR(100),
    room_location VARCHAR(50),
    day_of_week INT,                    -- 2 to 7 (Thứ 2 - Thứ 7)
    start_period INT,                   -- Tiết bắt đầu
    end_period INT,                     -- Tiết kết thúc
    max_slots INT,
    current_slots INT
);

-- 4. DỮ LIỆU SINH VIÊN & BẢNG ĐIỂM
CREATE TABLE Students (
    student_id VARCHAR(20) PRIMARY KEY,
    full_name NVARCHAR(100),
    curriculum_id INT REFERENCES Curriculums(curriculum_id),
    target_cpa DECIMAL(3, 2),           -- CPA mục tiêu (VD: 3.6)
    current_cpa DECIMAL(3, 2) DEFAULT 0.0
    git add data/data.sql
);

CREATE TABLE Student_Transcripts (
    student_id VARCHAR(20) REFERENCES Students(student_id),
    course_id VARCHAR(20) REFERENCES Courses(course_id),
    semester_id VARCHAR(10) REFERENCES Semesters(semester_id),
    grade_letter VARCHAR(2),            -- A, B+, B, C...
    grade_number DECIMAL(2, 1),         -- 4.0, 3.5...
    is_passed BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (student_id, course_id)
);

-- 5. TÀI LIỆU HỌC THUẬT (Dùng để mapping sang Vector Database)
CREATE TABLE Academic_Materials (
    material_id SERIAL PRIMARY KEY,
    course_id VARCHAR(20) REFERENCES Courses(course_id),
    material_type VARCHAR(50),          -- 'Lecture', 'Exam', 'Textbook'
    title NVARCHAR(255),
    file_path TEXT,                     -- Đường dẫn đến file hoặc ID trong Vector DB
    chapter_index INT,                  -- Chương mấy (để Agent dễ tra cứu)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. QUY CHẾ HỌC VỤ (Dạng Text để RAG xử lý nhưng lưu Metadata tại đây)
CREATE TABLE Regulations (
    reg_id SERIAL PRIMARY KEY,
    title NVARCHAR(255),
    content_summary TEXT,
    document_url TEXT                   -- Link file gốc PDF
);