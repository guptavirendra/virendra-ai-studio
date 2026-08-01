# API Specification

## Overview

Ye API documentation `Virendra AI Studio` backend endpoints ko define karti hai, jo content generation, review, publishing, analytics, aur learning workflows ko support karti hai.

## Endpoints

### POST /content/generate
- Create a content draft
- Request body:
  - `topic`: string
  - `source`: string
  - `confidence`: integer
  - `competition`: string
  - `estimated_views`: string
- Response: Content item object

### POST /content/{item_id}/generate-ai
- Generate AI script and SEO metadata for an existing draft
- Responses:
  - 200: Content item with `script`, `seo_title`, `seo_description`, `hashtags`
  - 400: when content not found
  - 500: when AI integration fails

### POST /content/{item_id}/upload-youtube
- Upload a video to YouTube
- Request body:
  - `file_path`: string
  - `privacy_status`: string
  - `tags`: string[]
- Response: YouTube upload response

### POST /content/{item_id}/analytics
- Submit analytics data for a content item
- Request body:
  - `views`: integer
  - `ctr`: float
  - `retention`: float
  - `subscribers`: integer
  - `rpm`: float
  - `top_keywords`: string
- Response: analytics object

### POST /content/{item_id}/learning
- Submit learning signals for a content item
- Request body:
  - `title_style`: string
  - `thumbnail_style`: string
  - `best_upload_time`: string
  - `topic_category`: string
  - `ctr`: float
  - `retention`: float
  - `rpm`: float
- Response: learning signal object

### GET /content/review
- Fetch pending content items needing review
- Response: array of content items

### GET /content/{item_id}/analytics
- Fetch analytics history for a content item
- Response: array of analytics records

### GET /content/{item_id}/learning
- Fetch learning signal history for a content item
- Response: array of learning signal records

### POST /content/{item_id}/approve
- Approve a content item
- Response: updated content item

### POST /content/{item_id}/publish
- Publish approved content
- Response: updated content item

### GET /content/{item_id}
- Get a specific content item by ID
- Response: content item object

### GET /api/health
- Health check endpoint
- Response: service status
