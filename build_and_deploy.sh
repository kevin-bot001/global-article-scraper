#!/usr/bin/env bash
# ==============================================================
# Article Scraper - Build & Deploy to Cloud Run Job
#
# Usage:
#   ./build_and_deploy.sh              # Build + Deploy
#   ./build_and_deploy.sh build        # Build only (push image)
#   ./build_and_deploy.sh deploy       # Deploy only (update job)
#   ./build_and_deploy.sh run eatbook  # Execute a scraper
# ==============================================================
set -euo pipefail

# ---- Configuration ----
PROJECT_ID="oppo-gcp-prod-digfood-129869"
REGION="asia-southeast2"
AR_REPO="maomao-docker"
IMAGE_NAME="article-scraper"
JOB_NAME="article-scraper"

# Cloud Run Job defaults
MEMORY="2Gi"
CPU="2"
TASK_TIMEOUT="3600s"
MAX_RETRIES=1

# Full image path
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${IMAGE_NAME}"
TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "manual")

# ---- Functions ----

build() {
    echo "============================================"
    echo "  Building & Pushing image"
    echo "  Image: ${IMAGE_URI}:${TAG}"
    echo "============================================"

    gcloud builds submit \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --tag="${IMAGE_URI}:${TAG}" \
        --timeout=1800s

    # Tag as latest
    gcloud artifacts docker tags add \
        "${IMAGE_URI}:${TAG}" \
        "${IMAGE_URI}:latest" \
        --quiet 2>/dev/null || true

    echo "✅ Image pushed: ${IMAGE_URI}:${TAG}"
}

deploy() {
    echo "============================================"
    echo "  Deploying Cloud Run Job: ${JOB_NAME}"
    echo "============================================"

    if gcloud run jobs describe "${JOB_NAME}" --region="${REGION}" --project="${PROJECT_ID}" &>/dev/null; then
        echo "Updating existing job..."
        gcloud run jobs update "${JOB_NAME}" \
            --project="${PROJECT_ID}" \
            --region="${REGION}" \
            --image="${IMAGE_URI}:${TAG}" \
            --memory="${MEMORY}" \
            --cpu="${CPU}" \
            --task-timeout="${TASK_TIMEOUT}" \
            --max-retries="${MAX_RETRIES}"
    else
        echo "Creating new job..."
        gcloud run jobs create "${JOB_NAME}" \
            --project="${PROJECT_ID}" \
            --region="${REGION}" \
            --image="${IMAGE_URI}:${TAG}" \
            --memory="${MEMORY}" \
            --cpu="${CPU}" \
            --task-timeout="${TASK_TIMEOUT}" \
            --max-retries="${MAX_RETRIES}" \
            --parallelism=1
    fi

    echo "✅ Job deployed: ${JOB_NAME}"
}

run_scraper() {
    local scraper_args="$*"
    if [ -z "${scraper_args}" ]; then
        echo "Usage: $0 run <scraper_name> [options]"
        echo "Example: $0 run eatbook --bq --proxy --no-json"
        exit 1
    fi

    echo "============================================"
    echo "  Executing: ${scraper_args}"
    echo "============================================"

    # Convert space-separated args to comma-separated for gcloud
    local comma_args
    comma_args=$(echo "-s ${scraper_args}" | tr ' ' ',')

    gcloud run jobs execute "${JOB_NAME}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" \
        --args="${comma_args}" \
        --wait

    echo "✅ Execution complete"
}

usage() {
    cat <<'EOF'
Article Scraper - Build & Deploy

Commands:
  ./build_and_deploy.sh              Build image + Deploy job
  ./build_and_deploy.sh build        Build & push image only
  ./build_and_deploy.sh deploy       Update Cloud Run Job only
  ./build_and_deploy.sh run <args>   Execute a scraper

Run examples:
  ./build_and_deploy.sh run eatbook
  ./build_and_deploy.sh run eatbook --bq --proxy --no-json
  ./build_and_deploy.sh run timeout:jakarta --bq --proxy --limit 50
  ./build_and_deploy.sh run eatbook miss_tam_chiak --bq --proxy
EOF
}

# ---- Main ----

case "${1:-all}" in
    build)
        build
        ;;
    deploy)
        deploy
        ;;
    run)
        shift
        run_scraper "$@"
        ;;
    all)
        build
        deploy
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "Unknown command: $1"
        usage
        exit 1
        ;;
esac
