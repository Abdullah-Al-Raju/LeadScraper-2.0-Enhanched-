"""
LeadScraper Progress Cache
Enables resume capability - save progress and resume after crash
"""

import json
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProgressCache:
    """Manages progress caching for resume capability"""
    
    def __init__(self, cache_file='cache/progress.json'):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(exist_ok=True, parents=True)
    
    def save(self, data):
        """
        Save progress to cache
        
        Args:
            data: dict with progress information
        """
        try:
            # Add timestamp
            data['last_updated'] = datetime.now().isoformat()
            
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Progress saved: {data}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def load(self):
        """
        Load progress from cache
        
        Returns:
            dict or None
        """
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded cached progress: {data.get('completed', 0)} items completed")
                return data
            return None
        except Exception as e:
            logger.error(f"Failed to load progress: {e}")
            return None
    
    def clear(self):
        """Clear cache file"""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
                logger.info("Progress cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def exists(self):
        """Check if cache exists"""
        return self.cache_file.exists()
    
    def get_completed_rows(self):
        """Get list of completed row numbers"""
        data = self.load()
        if data:
            return data.get('completed_rows', [])
        return []
    
    def add_completed_row(self, row_number):
        """Add row to completed list"""
        data = self.load() or {'completed_rows': []}
        
        if row_number not in data['completed_rows']:
            data['completed_rows'].append(row_number)
            data['last_row'] = row_number
            data['completed'] = len(data['completed_rows'])
            self.save(data)
