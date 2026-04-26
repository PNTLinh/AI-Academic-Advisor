# AI hỗ trợ học tập

**Đề tài**: AI tư vấn đăng ký môn học, lịch học và xây dựng kế hoạch học tập theo mục tiêu cho sinh viên năm 3, 4

---
# 1. Mô tả đề tài
Nhiều sinh viên năm 3, năm 4 có nguyện vọng tốt nghiệp với tấm bằng mong muốn (VD: sinh viên năm 3, CPA hiện tại là 3.4, muốn tốt nghiệp xuất sắc). Việc lập kế hoạch thủ công bao gồm nhiều bước:

- Lấy danh sách các môn đã học
- Kiểm tra điều kiện hạ bằng (VD: Trượt 6 tín ---> hạ bằng với bằng giỏi và xuất sắc)
- Lập danh sách các môn trong chương trình đào tạo
- Điền kết quả các môn đã học
- Tính toán điểm trung bình (tối thiểu) cần đạt với các môn chưa học để đạt CPA mục tiêu
- Lập danh sách các môn cần cải thiện (nếu điểm cần đạt với các môn còn lại quá cao, quá sức với mình)
- Lập danh sách các môn cần đăng ký cho mỗi kỳ (có những môn chỉ mở ít lớp hay chỉ mở vào kì cố định)
- Lập thời khóa biểu và đăng ký lịch học

Đồng thời, trong quá trình học tập, sinh viên cần có chiến lược học tập, ôn tập phù hợp để đảm bảo kế hoạch đúng tiến độ. Nếu có thay đổi phát sinh trong kì (VD: điểm 1 môn thấp hơn kì vọng), cần điều chỉnh lại kế hoạch các kì sau.

Đề tài này nhằm xây dựng 1 AI agent có khả năng tư vấn đăng ký môn học, lớp học, lộ trình học tập phù hợp với mục tiêu tốt nghiệp cho sinh viên; lập kế hoạch học tập, ôn tập và giúp sinh viên bám sát tiến độ học tập, tốt nghiệp với CPA mong muốn.

---
# 2. Các chức năng chính

- Tư vấn đăng ký môn học và lớp học cho từng kỳ theo lịch sử học tập và CPA mong muốn
- Lập kế hoạch học tập ôn tập
- Giám sát tiến độ và hỗ trợ sinh viên thực hiện kế hoạch
- Tự động điều chỉnh lộ trình khi có thay đổi
- Hỗ trợ ôn tập (nice-to-have)

---
# 3. Tech stack
### Frontend
- **Framework**: Next.js 16.2
- **Language**: TypeScript
- **Styling**: Tailwind CSS + PostCSS
- **UI Components**: Radix UI + shadcn/ui
- **Forms**: React Hook Form + Zod validation
- **State Management**: React Hooks + Context API
---
# 4. Hướng dẫn cài đặt
## 4.1. Frontend

### Yêu cầu hệ thống
- Node.js 18+ 
- Package manager: `pnpm`, `npm`, hoặc `yarn`

```bash
cd src/ui
```

### Cài đặt dependencies
```bash
pnpm install
# hoặc
npm install
# hoặc
yarn install
```

### Chạy development server
```bash
pnpm dev
# hoặc
npm run dev
# hoặc
yarn dev
```

### Mở trong trình duyệt

- 🤖 **AI Advisor**: http://localhost:3000/advisor 
- 📋 **Course Planner**: http://localhost:3000/planner
