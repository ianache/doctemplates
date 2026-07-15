# Task 4 Review Package

## git diff
diff --git a/.env.example b/.env.example
index 99f0f3b..26c9793 100644
--- a/.env.example
+++ b/.env.example
@@ -36,3 +36,19 @@ MINIO_ROOT_PASSWORD=password123
 # Celery/Redis Configuration
 CELERY_BROKER_URL=redis://localhost:6379/0
 CELERY_RESULT_BACKEND=redis://localhost:6379/1
+
+# AI Improve is disabled by default. To enable it, set AI_REQUESTS_ENABLED=true,
+# configure a provider API key below, and restart/recreate the backend service
+# when running through Docker Compose.
+AI_REQUESTS_ENABLED=false
+AI_DEFAULT_MODEL=gemini/gemini-2.0-flash
+AI_PROVIDER_MODEL=gpt-4o-mini
+AI_ALLOWED_MODELS=gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1
+AI_REQUEST_TIMEOUT_SECONDS=30
+AI_MAX_INPUT_CHARS=20000
+AI_MAX_OUTPUT_TOKENS=2000
+# OPENAI_API_KEY=
+# ANTHROPIC_API_KEY=
+# GEMINI_API_KEY=
+# GROQ_API_KEY=
+# OLLAMA_API_BASE=http://host.docker.internal:11434
diff --git a/docker-compose.yml b/docker-compose.yml
index e046bbf..ac8b8fd 100644
--- a/docker-compose.yml
+++ b/docker-compose.yml
@@ -54,6 +54,18 @@ services:
       STORAGE_S3_REGION: us-east-1
       STORAGE_S3_BUCKET_STATIC_PDFS: docmanagement-static-pdfs
       STORAGE_S3_BUCKET_ISSUANCES: docmanagement-issuances
+      AI_REQUESTS_ENABLED: ${AI_REQUESTS_ENABLED:-false}
+      AI_DEFAULT_MODEL: ${AI_DEFAULT_MODEL:-gemini/gemini-2.0-flash}
+      AI_PROVIDER_MODEL: ${AI_PROVIDER_MODEL:-gpt-4o-mini}
+      AI_ALLOWED_MODELS: ${AI_ALLOWED_MODELS:-gemini/gemini-2.0-flash,groq/llama-3.1-8b-instant,ollama/llama3.1}
+      AI_REQUEST_TIMEOUT_SECONDS: ${AI_REQUEST_TIMEOUT_SECONDS:-30}
+      AI_MAX_INPUT_CHARS: ${AI_MAX_INPUT_CHARS:-20000}
+      AI_MAX_OUTPUT_TOKENS: ${AI_MAX_OUTPUT_TOKENS:-2000}
+      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
+      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
+      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
+      GROQ_API_KEY: ${GROQ_API_KEY:-}
+      OLLAMA_API_BASE: ${OLLAMA_API_BASE:-http://host.docker.internal:11434}
       CELERY_BROKER_URL: redis://redis:6379/0
       CELERY_RESULT_BACKEND: redis://redis:6379/1
     ports:
