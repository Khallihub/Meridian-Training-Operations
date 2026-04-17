"""Unit tests for location/room model defaults and schemas."""


def test_location_column_defaults():
    from app.modules.locations.models import Location
    table = Location.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["timezone"].default.arg == "UTC"
    assert cols["is_active"].default.arg is True


def test_room_column_defaults():
    from app.modules.locations.models import Room
    table = Room.__table__
    cols = {c.name: c for c in table.columns}
    assert cols["capacity"].default.arg == 20
    assert cols["is_active"].default.arg is True


def test_location_create_schema_defaults():
    from app.modules.locations.schemas import LocationCreate
    loc = LocationCreate(name="Test Site")
    assert loc.name == "Test Site"
    assert loc.timezone == "UTC"


def test_room_create_schema_defaults():
    from app.modules.locations.schemas import RoomCreate
    room = RoomCreate(name="Room A")
    assert room.name == "Room A"
    assert room.capacity == 20


def test_room_create_custom_capacity():
    from app.modules.locations.schemas import RoomCreate
    room = RoomCreate(name="R", capacity=50)
    assert room.capacity == 50
