import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson.objectid import ObjectId
from datetime import datetime
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import Hotel, Room, Booking

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to convert Mongo _id to string

def serialize_doc(doc):
    doc = dict(doc)
    if doc.get("_id"):
        doc["id"] = str(doc.pop("_id"))
    return doc


@app.get("/")
def read_root():
    return {"message": "Hotel Booking API ready"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response


# Seed data route to quickly add sample hotels/rooms
@app.post("/seed")
def seed_data():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    hotels = [
        Hotel(
            name="Seaside Resort",
            location="Malibu, USA",
            description="Oceanfront stays with stunning sunsets.",
            rating=4.7,
            amenities=["Pool", "WiFi", "Breakfast", "Spa"],
            image_url="https://images.unsplash.com/photo-1501117716987-c8e2a9ce5e1d?auto=format&fit=crop&w=1200&q=60",
        ),
        Hotel(
            name="Mountain Lodge",
            location="Zermatt, Switzerland",
            description="Cozy lodge with alpine views.",
            rating=4.6,
            amenities=["WiFi", "Sauna", "Restaurant"],
            image_url="https://images.unsplash.com/photo-1528909514045-2fa4ac7a08ba?auto=format&fit=crop&w=1200&q=60",
        ),
    ]

    hotel_ids = []
    for h in hotels:
        hid = create_document("hotel", h)
        hotel_ids.append(hid)

    rooms = [
        Room(
            hotel_id=hotel_ids[0],
            name="Deluxe Ocean View",
            price_per_night=320,
            capacity=2,
            amenities=["Balcony", "King Bed", "Mini Bar"],
            images=["https://images.unsplash.com/photo-1505691723518-36a5ac3b2d95?auto=format&fit=crop&w=1200&q=60"],
        ),
        Room(
            hotel_id=hotel_ids[0],
            name="Family Suite",
            price_per_night=450,
            capacity=4,
            amenities=["Two Bedrooms", "Kitchenette"],
            images=["https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&w=1200&q=60"],
        ),
        Room(
            hotel_id=hotel_ids[1],
            name="Alpine Classic",
            price_per_night=280,
            capacity=2,
            amenities=["Queen Bed", "Mountain View"],
        ),
    ]

    for r in rooms:
        create_document("room", r)

    return {"inserted_hotels": len(hotels), "inserted_rooms": len(rooms)}


# Public endpoints
@app.get("/hotels")
def list_hotels():
    items = get_documents("hotel")
    return [serialize_doc(i) for i in items]


@app.get("/hotels/{hotel_id}")
def get_hotel(hotel_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db["hotel"].find_one({"_id": ObjectId(hotel_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Hotel not found")
    rooms = list(db["room"].find({"hotel_id": hotel_id}))
    return {"hotel": serialize_doc(doc), "rooms": [serialize_doc(r) for r in rooms]}


class AvailabilityQuery(BaseModel):
    check_in: str
    check_out: str
    guests: int = 1


@app.post("/availability/{hotel_id}")
def check_availability(hotel_id: str, payload: AvailabilityQuery):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # For demo: a room is unavailable if there's any overlap with existing bookings
    try:
        from datetime import date
        from datetime import datetime as dt
        ci = dt.fromisoformat(payload.check_in).date()
        co = dt.fromisoformat(payload.check_out).date()
        if co <= ci:
            raise HTTPException(status_code=400, detail="Check-out must be after check-in")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    rooms = list(db["room"].find({"hotel_id": hotel_id}))

    available_rooms = []
    for room in rooms:
        bookings = list(db["booking"].find({"room_id": str(room["_id"])}))
        overlap = False
        for b in bookings:
            b_ci = datetime.fromisoformat(b["check_in"]).date()
            b_co = datetime.fromisoformat(b["check_out"]).date()
            if not (co <= b_ci or ci >= b_co):
                overlap = True
                break
        if not overlap and payload.guests <= room.get("capacity", 1):
            available_rooms.append(serialize_doc(room))

    return {"available": available_rooms}


@app.post("/book")
def create_booking(payload: Booking):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Ensure room exists
    room = db["room"].find_one({"_id": ObjectId(payload.room_id)})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Check for overlaps
    bookings = list(db["booking"].find({"room_id": payload.room_id}))
    ci = payload.check_in
    co = payload.check_out
    if isinstance(ci, str):
        from datetime import datetime as dt
        ci = dt.fromisoformat(ci).date()
        co = dt.fromisoformat(co).date()

    for b in bookings:
        b_ci = datetime.fromisoformat(b["check_in"]).date()
        b_co = datetime.fromisoformat(b["check_out"]).date()
        if not (co <= b_ci or ci >= b_co):
            raise HTTPException(status_code=400, detail="Selected dates overlap with an existing booking")

    # Compute total
    nights = (co - ci).days
    total = nights * room.get("price_per_night", 0)

    booking_doc = payload.model_dump()
    booking_doc["check_in"] = ci.isoformat()
    booking_doc["check_out"] = co.isoformat()
    booking_doc["total_price"] = total

    bid = create_document("booking", booking_doc)
    return {"booking_id": bid, "total_price": total, "status": "confirmed"}


@app.get("/bookings")
def list_bookings():
    items = get_documents("booking")
    return [serialize_doc(i) for i in items]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
