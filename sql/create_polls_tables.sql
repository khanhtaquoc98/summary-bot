-- 1. Bảng lưu danh sách các cuộc biểu quyết (Polls)
CREATE TABLE IF NOT EXISTS polls (
    poll_id TEXT PRIMARY KEY,
    message_id BIGINT,
    chat_id BIGINT,
    thread_id BIGINT,
    title TEXT NOT NULL,
    options JSONB NOT NULL,
    is_anonymous BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Bảng lưu chi tiết người dùng vote (Poll Answers)
CREATE TABLE IF NOT EXISTS poll_answers (
    id BIGSERIAL PRIMARY KEY,
    poll_id TEXT REFERENCES polls(poll_id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    user_name TEXT,
    option_ids JSONB NOT NULL, -- Danh sách index phương án đã vote (VD: [0] cho '0', [1] cho '+1'...)
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(poll_id, user_id)
);

-- Enable Row Level Security (RLS) & cấp quyền nếu cần
ALTER TABLE polls ENABLE ROW LEVEL SECURITY;
ALTER TABLE poll_answers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to polls" ON polls FOR ALL USING (true);
CREATE POLICY "Allow all access to poll_answers" ON poll_answers FOR ALL USING (true);
