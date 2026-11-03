CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(16) NOT NULL DEFAULT 'member',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    session_version INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_rate_limits (
    key_hash VARCHAR(64) PRIMARY KEY,
    attempts INT NOT NULL,
    window_started_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_login_rate_limits_window_started_at
    ON login_rate_limits (window_started_at);

CREATE TABLE IF NOT EXISTS content_items (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence INT NOT NULL DEFAULT 0,
    competition TEXT NOT NULL DEFAULT 'medium',
    estimated_views TEXT NOT NULL DEFAULT 'medium',
    script TEXT,
    voice_file TEXT,
    thumbnail_path TEXT,
    video_path TEXT,
    seo_title TEXT,
    seo_description TEXT,
    hashtags TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    publish_target TEXT,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics (
    id SERIAL PRIMARY KEY,
    content_id INT REFERENCES content_items(id) ON DELETE CASCADE,
    views INT DEFAULT 0,
    ctr NUMERIC(5,2) DEFAULT 0,
    retention NUMERIC(5,2) DEFAULT 0,
    subscribers INT DEFAULT 0,
    rpm NUMERIC(10,2) DEFAULT 0,
    top_keywords TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learning_signals (
    id SERIAL PRIMARY KEY,
    content_id INT REFERENCES content_items(id) ON DELETE CASCADE,
    title_style TEXT,
    thumbnail_style TEXT,
    best_upload_time TEXT,
    topic_category TEXT,
    ctr NUMERIC(5,2) DEFAULT 0,
    retention NUMERIC(5,2) DEFAULT 0,
    rpm NUMERIC(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
