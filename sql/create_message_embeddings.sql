-- =============================================
-- Tạo bảng message_embeddings tách riêng khỏi messages
-- Bảng messages chỉ phục vụ summary
-- Bảng message_embeddings phục vụ vector search cho /ai
-- =============================================

-- Bật extension pgvector (nếu chưa có)
create extension if not exists vector;

-- Tạo bảng message_embeddings
create table if not exists message_embeddings (
    id bigserial primary key,
    chat_id bigint not null,
    user_id bigint,
    user_name text,
    text text not null,
    embedding vector(384) not null,
    created_at timestamptz default now()
);

-- Index cho tìm kiếm theo chat_id
create index if not exists idx_message_embeddings_chat_id 
    on message_embeddings(chat_id);

-- Index cho vector similarity search (IVFFlat hoặc HNSW)
-- Dùng HNSW cho tốc độ tốt hơn
create index if not exists idx_message_embeddings_vector 
    on message_embeddings 
    using hnsw (embedding vector_cosine_ops);

-- (Tuỳ chọn) Xoá cột embedding khỏi bảng messages nếu đã có
-- alter table messages drop column if exists embedding;

-- =============================================
-- Tạo lại RPC function match_messages 
-- để dựa trên bảng message_embeddings
-- =============================================
create or replace function match_messages(
    query_embedding vector(384),
    target_chat_id bigint,
    match_count int default 10
)
returns table (
    id bigint,
    chat_id bigint,
    user_id bigint,
    user_name text,
    text text,
    created_at timestamptz,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        me.id,
        me.chat_id,
        me.user_id,
        me.user_name,
        me.text,
        me.created_at,
        1 - (me.embedding <=> query_embedding) as similarity
    from message_embeddings me
    where me.chat_id = target_chat_id
    order by me.embedding <=> query_embedding
    limit match_count;
end;
$$;
