"""
IMARA ONE Search - Seed Crawler CLI
Executes a permitted website crawl job from command line,
populating the search engine database and Meilisearch index.
"""

import argparse
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import init_db, SessionLocal
from backend.app.services.crawler_service import crawler_service
from backend.app.services.indexing_service import indexing_service
from backend.app.security.ssrf import validate_url_safe


def main():
    parser = argparse.ArgumentParser(
        description="IMARA ONE Search — Permitted Website Crawler CLI"
    )
    parser.add_argument(
        "url",
        help="Permitted public target URL to crawl (e.g. https://example.com)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="Maximum pages to crawl (default: 20)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum link traversal depth (default: 2)",
    )

    args = parser.parse_args()

    print(f"\n=======================================================")
    print(f"  IMARA ONE Search — Crawler Execution Engine")
    print(f"  One Ecosystem. Endless Protection.")
    print(f"=======================================================\n")

    # 1. SSRF Safety Verification
    print(f"[*] Validating target URL security and SSRF safeguards: {args.url}")
    is_safe, message, resolved_ip = validate_url_safe(args.url)
    if not is_safe:
        print(f"[!] ERROR: Target URL rejected by security policy: {message}")
        sys.exit(1)

    print(f"[+] Security check passed. Resolved IP: {resolved_ip}")

    # 2. Database and Index initialization
    print("[*] Initializing local database schemas and search index...")
    init_db()
    indexing_service.init_index()

    # 3. Schedule and run crawl job
    db = SessionLocal()
    try:
        print(f"[*] Submitting crawl job for {args.url} (max_pages={args.max_pages}, max_depth={args.max_depth})...")
        job_info = crawler_service.submit_crawl_job(
            db=db,
            url=args.url,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
        )
        print(f"[+] Job created successfully! Job ID: {job_info['job_id']}")
        print(f"[*] Crawler worker started in background. Polling job status...\n")

        import time
        while True:
            time.sleep(2)
            status = crawler_service.get_job_status(db=db, job_id=job_info['job_id'])
            if not status:
                break

            current_status = status['status']
            crawled = status['pages_crawled']
            indexed = status['pages_indexed']
            errors = status['errors_count']

            print(f"  -> Status: {current_status.upper()} | Pages Crawled: {crawled} | Indexed: {indexed} | Errors: {errors}")

            if current_status in ("completed", "failed"):
                if current_status == "completed":
                    print(f"\n[+] Crawl job COMPLETED successfully!")
                    print(f"    Indexed {indexed} documents into IMARA ONE Search.")
                else:
                    print(f"\n[!] Crawl job FAILED: {status.get('error_message')}")
                break

    except Exception as e:
        print(f"[!] Execution failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

