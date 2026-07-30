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
