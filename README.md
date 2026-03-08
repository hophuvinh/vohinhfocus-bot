# FocusFlow Bot — Hướng dẫn deploy

## Deploy lên Railway (miễn phí, 5 phút)

### Bước 1 — Tạo tài khoản Railway
1. Vào https://railway.app
2. Đăng ký bằng GitHub (cần có tài khoản GitHub)

### Bước 2 — Đưa code lên GitHub
1. Vào https://github.com → New repository → Đặt tên `focusflow-bot` → Create
2. Upload 3 file: `bot.py`, `requirements.txt`, `Procfile`
   - Bấm "uploading an existing file" → kéo thả 3 file vào → Commit

### Bước 3 — Deploy trên Railway
1. Vào https://railway.app → New Project → Deploy from GitHub repo
2. Chọn repo `focusflow-bot`
3. Sau khi Railway detect xong → vào tab **Variables**
4. Thêm biến môi trường:
   - Key: `BOT_TOKEN`
   - Value: token bot của bạn
5. Bấm **Deploy** — Railway sẽ tự build và chạy

### Bước 4 — Kiểm tra
- Vào Telegram, tìm bot của bạn
- Nhắn `/start`
- Nếu bot trả lời = thành công! 🎉

---

## Cách dùng bot

### Nhắn tự nhiên để thêm task:
```
Hôm nay cần làm KV cho dự án Better Choice
Feedback 3 banner editorial gấp
Sếp giao làm proposal Samsung ngày mai
Review UI trang chủ tuần này
```

### Lệnh nhanh:
- `/today` — Xem việc hôm nay (Focus + Reactive)
- `/inbox` — Xem tất cả task chưa assign
- `/done` — Đánh dấu task hoàn thành
- `/week` — Tổng quan deadline tuần này
- `/move [id] focus` — Chuyển task vào Deep Focus
- `/move [id] reactive` — Chuyển task vào Reactive

---

## Lưu ý
- Data lưu trong file `tasks.json` trên server Railway
- Railway free tier có thể sleep sau 30 phút không hoạt động — lần đầu nhắn có thể chậm ~10 giây
- Để data bền vững hơn sau này có thể nâng cấp lên database (mình sẽ hỗ trợ)
