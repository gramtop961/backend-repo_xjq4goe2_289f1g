"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

# Example schemas (you can keep these if useful):

class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Hotel booking application schemas

class Hotel(BaseModel):
    name: str = Field(..., description="Hotel name")
    location: str = Field(..., description="City/Country or full address")
    description: Optional[str] = Field(None, description="About the hotel")
    rating: Optional[float] = Field(4.5, ge=0, le=5, description="Average rating 0-5")
    amenities: List[str] = Field(default_factory=list, description="Amenities list")
    image_url: Optional[str] = Field(None, description="Hero image URL")

class Room(BaseModel):
    hotel_id: str = Field(..., description="Related hotel id as string")
    name: str = Field(..., description="Room name or type, e.g., Deluxe Suite")
    price_per_night: float = Field(..., ge=0, description="Nightly rate")
    capacity: int = Field(..., ge=1, description="Max guests")
    amenities: List[str] = Field(default_factory=list)
    images: Optional[List[str]] = Field(default=None)

class Booking(BaseModel):
    hotel_id: str = Field(...)
    room_id: str = Field(...)
    guest_name: str = Field(...)
    guest_email: str = Field(...)
    check_in: date = Field(...)
    check_out: date = Field(...)
    guests: int = Field(1, ge=1)
    total_price: float = Field(..., ge=0)
    status: str = Field("confirmed", description="confirmed | cancelled")
