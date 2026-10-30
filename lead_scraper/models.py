"""
Data models for LeadScraper using Pydantic.
Provides strong typing, complete contact vectors, serialization, and card rendering for business leads.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class Lead(BaseModel):
    """Normalized structured representation of a business lead with complete vector channels."""
    id: Optional[int] = Field(None, description="Incremental lead identifier")
    business_name: str = Field(..., description="Official name of the business")
    website: Optional[str] = Field(None, description="Official website URL")
    category: Optional[str] = Field(None, description="Industry or business category")
    cuisine: Optional[str] = Field(None, description="Culinary specialty or subcategory if applicable")
    location: Optional[str] = Field(None, description="Target location or city description")
    city: Optional[str] = Field(None, description="Parsed city name")
    subdivision: Optional[str] = Field(None, description="State, province, or region")
    country: Optional[str] = Field(None, description="Country name")
    
    emails: List[str] = Field(default_factory=list, description="Extracted contact emails")
    phones: List[str] = Field(default_factory=list, description="Extracted phone numbers")
    social_media: Dict[str, str] = Field(
        default_factory=dict,
        description="Social media profile URLs (instagram, facebook, linkedin, twitter_x, etc.)"
    )
    address: Optional[str] = Field(None, description="Physical location or street address")
    
    verified: bool = Field(True, description="Whether the lead has been validated")
    confidence_score: float = Field(0.0, description="Lead quality confidence score (0.0 to 1.0)")
    status: str = Field("success", description="Scrape status (success, partial, not_found)")
    engine: str = Field("milli-scrapes", description="Extraction engine used")
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of extraction"
    )

    def calculate_confidence(self) -> float:
        """Computes a heuristic quality score based on verified data points."""
        score = 0.0
        if self.website:
            score += 0.30
        if self.emails:
            score += 0.30
        if self.phones:
            score += 0.20
        if self.social_media:
            score += 0.10
        if self.address:
            score += 0.10
        self.confidence_score = round(min(score, 1.0), 2)
        return self.confidence_score

    def to_flat_dict(self) -> Dict[str, Any]:
        """Flattens lead fields for tabular CSV export with all vector columns."""
        return {
            "id": self.id if self.id is not None else "",
            "business_name": self.business_name,
            "website": self.website or "",
            "category": self.category or "",
            "cuisine": self.cuisine or "",
            "location": self.location or "",
            "city": self.city or "",
            "subdivision": self.subdivision or "",
            "country": self.country or "",
            "address": self.address or "",
            "emails": ", ".join(self.emails),
            "phones": ", ".join(self.phones),
            "instagram": self.social_media.get("instagram", ""),
            "facebook": self.social_media.get("facebook", ""),
            "linkedin": self.social_media.get("linkedin", ""),
            "twitter_x": self.social_media.get("twitter_x", "") or self.social_media.get("twitter", ""),
            "youtube": self.social_media.get("youtube", ""),
            "tiktok": self.social_media.get("tiktok", ""),
            "verified": self.verified,
            "confidence_score": self.confidence_score,
            "status": self.status,
            "engine": self.engine,
            "scraped_at": self.scraped_at,
        }

    def display_card(self) -> str:
        """Generates a clean text card for text file export or terminal preview."""
        lead_id_str = f" #{self.id}" if self.id is not None else ""
        lines = [
            f"=== {self.business_name.upper()}{lead_id_str} ===",
            f"Website:    {self.website or 'N/A'}",
            f"Category:   {self.category or 'N/A'}" + (f" ({self.cuisine})" if self.cuisine else ""),
            f"Location:   {self.location or 'N/A'}",
        ]
        if self.city or self.subdivision or self.country:
            geo_parts = [p for p in [self.city, self.subdivision, self.country] if p]
            lines.append(f"Region:     {', '.join(geo_parts)}")
        if self.address:
            lines.append(f"Address:    {self.address}")
        lines.extend([
            f"Emails:     {', '.join(self.emails) if self.emails else 'None'}",
            f"Phones:     {', '.join(self.phones) if self.phones else 'None'}",
        ])
        if self.social_media:
            socials_str = ", ".join(f"{k}: {v}" for k, v in self.social_media.items() if v)
            lines.append(f"Socials:    {socials_str}")
        lines.append(f"Confidence: {int(self.confidence_score * 100)}% ({self.status})")
        lines.append("-" * 40)
        return "\n".join(lines)
