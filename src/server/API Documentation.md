# **Adaptive Academic Advisor API Documentation**

**Base URL:**  
**Version:** 1.0.0  
**Description:** Hệ thống AI Agent hỗ trợ phân tích bảng điểm, lập lộ trình học tập và tối ưu hóa tiến độ sinh viên.

## **1\. Data Ingestion (Khởi tạo dữ liệu)**

### **POST /agent/ingest**

**Summary:** Upload và bóc tách dữ liệu từ bảng điểm.

**Description:** Thực hiện chuỗi hàm logic:  
extract\_user\_data → parse\_transcript → parse\_curriculum

**Request Body (JSON):**

{  
  "student\_id": "SV12345",  
  "file\_type": "pdf",  
  "content\_base64": "JVBERi0xLjQKJ..."  
}

**Responses:**

**200 OK:**

{  
  "status": "success",  
  "extracted\_courses": \[  
    {  
      "course\_id": "MATH201",  
      "name": "Calculus I",  
      "credits": 4,  
      "grade": "B+",  
      "is\_passed": true  
    },  
    {  
      "course\_id": "PHYS101",  
      "name": "Physics I",  
      "credits": 4,  
      "grade": "F",  
      "is\_passed": false  
    }  
  \]  
}

## **2\. Student Persona (TT sinh viên)**

### **GET /agent/status/{student\_id}**

**Summary:** Lấy trạng thái học tập chi tiết của sinh viên.

**Description:** Thực hiện các hàm:  
classify\_courses, calculate\_credits, summarize\_student\_context

**Parameters:**

* student\_id (path)

**Responses:**

**200 OK:**

{  
  "persona": {  
    "gpa": 2.67,  
    "standing": "Warning",  
    "credits\_summary": {  
      "earned": 72,  
      "total\_required": 120,  
      "debt": 12  
    },  
    "categorized\_lists": {  
      "passed": \["MATH201", "CS101"\],  
      "failed": \["PHYS101", "PHYS102"\],  
      "can\_improve": \["ENG101"\]  
    }  
  }  
}

## **3\. Goal & Limits (Mục tiêu & Hạn mức)**

### **POST /agent/set-goals**

**Summary:** Thiết lập mục tiêu và tính toán giới hạn đăng ký.

**Description:** Thực hiện các hàm:  
extract\_goals, get\_registration\_limits, adjust\_workload\_capacity

**Request Body (JSON):**

{  
  "student\_id": "SV12345",  
  "user\_intent": "Tôi muốn ra trường sớm và nâng GPA lên 3.0",  
  "life\_constraints": {  
    "work\_hours\_per\_week": 20,  
    "blackout\_slots": \[  
      {  
        "day": "Mon",  
        "start": "08:00",  
        "end": "12:00"  
      }  
    \]  
  }  
}

**Responses:**

**200 OK:**

{  
  "extracted\_goals": \["Tốt nghiệp sớm", "GPA \>= 3.0"\],  
  "limits": {  
    "min\_credits": 15,  
    "max\_credits": 22,  
    "difficulty\_cap": 0.75  
  }  
}

## **4\. Smart Planning (Lập kế hoạch thông minh)**

### **POST /agent/recommend**

**Summary:** Đề xuất danh mục môn học cho kỳ tới.

**Description:** Thực hiện các hàm:  
rank\_eligible\_courses, suggest\_next\_semester

**Request Body (JSON):**

{  
  "student\_id": "SV12345",  
  "semester": "2026.1"  
}

**Responses:**

**200 OK:**

{  
  "suggested\_cart": \[  
    {  
      "course\_id": "PHYS101",  
      "priority": "Critical",  
      "reason": "Môn nợ cần trả để học PHYS102",  
      "difficulty\_score": 0.8  
    },  
    {  
      "course\_id": "MATH301",  
      "priority": "High",  
      "reason": "Môn tiên quyết cho Đồ án chuyên ngành",  
      "difficulty\_score": 0.6  
    }  
  \],  
  "total\_credits": 18,  
  "balance\_status": "Balanced"  
}

## **5\. Adaptive Roadmap (Lộ trình tối ưu)**

### **GET /agent/roadmap/{student\_id}**

**Summary:** Trả về toàn bộ lộ trình dài hạn đã được tối ưu.

**Description:** Thực hiện chuỗi:  
generate\_graduation\_plan → analyze\_bottlenecks → optimize\_personalized\_plan

**Parameters:**

* student\_id (path)  
* use\_summer (query, default \= true)

**Responses:**

**200 OK:**

{  
  "overall\_plan": {  
    "graduation\_date": "Spring 2027",  
    "semesters\_remaining": 6  
  },  
  "optimized\_roadmap": \[  
    {  
      "term": "Fall 2026",  
      "is\_summer": false,  
      "credits": 18,  
      "term\_difficulty": 0.68,  
      "courses": \[  
        {  
          "id": "CS301",  
          "name": "Algorithms",  
          "type": "Core",  
          "difficulty": 0.85,  
          "reasoning": "Đẩy lên sớm để gỡ nút thắt kỳ lẻ"  
        }  
      \]  
    }  
  \],  
  "insights": \[  
    "Lộ trình đã dàn trải đều các môn nặng để tránh quá tải",  
    "Sử dụng học kỳ hè 2026 để rút ngắn thời gian 1 học kỳ"  
  \]  
}

## **6\. Incident Handling (Xử lý sự cố)**

### **POST /agent/re-optimize**

**Summary:** Tính toán lại lộ trình khi gặp sự cố bất ngờ.

**Description:** Sử dụng logic:  
re\_optimize\_on\_failure

**Request Body (JSON):**

{  
  "student\_id": "SV12345",  
  "incident\_type": "FAILED\_COURSE",  
  "course\_id": "MATH201",  
  "keep\_original\_grad\_date": true  
}

**Responses:**

**200 OK:**

{  
  "reoptimization\_report": {  
    "status": "Success",  
    "incident\_resolved": "FAILED\_COURSE: MATH201",  
    "action\_taken": "Rescheduled MATH201 to Summer 2024 to maintain Spring 2027 graduation",  
    "impact\_severity": "Medium"  
  },  
  "new\_optimized\_roadmap": {  
    "overall\_stats": {  
      "total\_semesters": 6,  
      "estimated\_graduation": "Spring 2027",  
      "avg\_difficulty\_score": 0.68  
    },  
    "semesters": \[  
      {  
        "term": "Summer 2024",  
        "is\_summer": true,  
        "total\_credits": 4,  
        "courses": \[  
          {  
            "id": "MATH201",  
            "name": "Calculus I",  
            "type": "Retake",  
            "priority": "Critical",  
            "reasoning": "Môn vừa trượt, cần học ngay kỳ hè để kịp tiến độ Calculus II"  
          }  
        \]  
      }  
    \],  
    "bottlenecks\_resolved": \[  
      "Dời Calculus II sang kỳ Thu 2024 để đảm bảo thứ tự tiên quyết",  
      "Bổ sung kỳ hè để không kéo dài thời gian ra trường"  
    \],  
    "warnings": \[  
      "Tổng độ khó kỳ hè tăng nhẹ do tính chất học nén"  
    \]  
  }  
}

## **Additional Notes**

* CORS: Bật cho mọi domain (v0.dev, localhost)  
* Authentication: Bearer Token (JWT)  
* Data Types: Các giá trị như difficulty\_score, gpa dùng kiểu float

