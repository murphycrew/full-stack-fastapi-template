import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import Item, ItemCreate, User, UserCreate, UserUpdate


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def get_item(
    *, session: Session, item_id: uuid.UUID, owner_id: uuid.UUID
) -> Item | None:
    """Get an item by ID, ensuring it belongs to the owner (RLS enforced)."""
    statement = select(Item).where(Item.id == item_id, Item.owner_id == owner_id)
    return session.exec(statement).first()


def get_items(
    *, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[Item]:
    """Get items for a specific owner (RLS enforced)."""
    statement = select(Item).where(Item.owner_id == owner_id).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def update_item(
    *, session: Session, db_item: Item, item_in: dict[str, Any], owner_id: uuid.UUID
) -> Item:
    """Update an item, ensuring it belongs to the owner (RLS enforced)."""
    # Verify ownership before update
    if db_item.owner_id != owner_id:
        raise ValueError("Item does not belong to the specified owner")

    item_data = (
        item_in.model_dump(exclude_unset=True)
        if hasattr(item_in, "model_dump")
        else item_in
    )
    db_item.sqlmodel_update(item_data)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def delete_item(
    *, session: Session, item_id: uuid.UUID, owner_id: uuid.UUID
) -> Item | None:
    """Delete an item, ensuring it belongs to the owner (RLS enforced)."""
    db_item = get_item(session=session, item_id=item_id, owner_id=owner_id)
    if db_item:
        session.delete(db_item)
        session.commit()
    return db_item


# Admin CRUD operations (bypass RLS)
def get_all_items_admin(
    *, session: Session, skip: int = 0, limit: int = 100
) -> list[Item]:
    """Get all items (admin operation that bypasses RLS)."""
    statement = select(Item).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def get_item_admin(*, session: Session, item_id: uuid.UUID) -> Item | None:
    """Get any item by ID (admin operation that bypasses RLS)."""
    statement = select(Item).where(Item.id == item_id)
    return session.exec(statement).first()


def update_item_admin(
    *, session: Session, db_item: Item, item_in: dict[str, Any]
) -> Item:
    """Update any item (admin operation that bypasses RLS)."""
    item_data = (
        item_in.model_dump(exclude_unset=True)
        if hasattr(item_in, "model_dump")
        else item_in
    )
    db_item.sqlmodel_update(item_data)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def delete_item_admin(*, session: Session, item_id: uuid.UUID) -> Item | None:
    """Delete any item (admin operation that bypasses RLS)."""
    db_item = get_item_admin(session=session, item_id=item_id)
    if db_item:
        session.delete(db_item)
        session.commit()
    return db_item
