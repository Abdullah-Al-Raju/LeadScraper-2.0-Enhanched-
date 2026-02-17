# Async Configuration for LeadScraper Pro
# ============================================

# Concurrency settings (LAPTOP OPTIMIZED)
MAX_CONCURRENT_BUSINESSES = 3   # Process 3 businesses at once (laptop-friendly)
MAX_CONCURRENT_SOURCES = 5       # 5 source calls at once per business

# Semaphore for rate control
ENABLE_ASYNC = True              # Enable async processing
