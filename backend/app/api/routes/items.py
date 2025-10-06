import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlmodel import func, select

from app import crud
from app.api.deps import (
    AdminSessionDep,
    CurrentUser,
    RLSSessionDep,
)
from app.models import Item, ItemCreate, ItemPublic, ItemsPublic, ItemUpdate, Message

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=ItemsPublic)
def read_items(
    session: RLSSessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve items with RLS enforcement.
    Regular users see only their items, admins see all items.
    """
    if current_user.is_superuser:
        # Admin can see all items (RLS policies allow this)
        count_statement = select(func.count()).select_from(Item)
        count = session.exec(count_statement).one()
        statement = select(Item).offset(skip).limit(limit)
        items = session.exec(statement).all()
    else:
        # Regular users see only their items (enforced by RLS policies)
        items = crud.get_items(
            session=session, owner_id=current_user.id, skip=skip, limit=limit
        )
        count = len(items)

    return ItemsPublic(data=items, count=count)


@router.get("/{id}", response_model=ItemPublic)
def read_item(session: RLSSessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get item by ID with RLS enforcement.
    """
    if current_user.is_superuser:
        # Admin can access any item
        item = crud.get_item_admin(session=session, item_id=id)
    else:
        # Regular users can only access their own items
        item = crud.get_item(session=session, item_id=id, owner_id=current_user.id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    return item


@router.post("/", response_model=ItemPublic)
def create_item(
    *, session: RLSSessionDep, current_user: CurrentUser, item_in: ItemCreate
) -> Any:
    """
    Create new item with RLS enforcement.
    """
    item = crud.create_item(session=session, item_in=item_in, owner_id=current_user.id)
    return item


@router.put("/{id}", response_model=ItemPublic)
def update_item(
    *,
    session: RLSSessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> Any:
    """
    Update an item with RLS enforcement.
    """
    if current_user.is_superuser:
        # Admin can update any item
        item = crud.get_item_admin(session=session, item_id=id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        item = crud.update_item_admin(
            session=session,
            db_item=item,
            item_in=item_in.model_dump(exclude_unset=True),
        )
    else:
        # Regular users can only update their own items
        item = crud.get_item(session=session, item_id=id, owner_id=current_user.id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
            )
        try:
            item = crud.update_item(
                session=session,
                db_item=item,
                item_in=item_in.model_dump(exclude_unset=True),
                owner_id=current_user.id,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return item


@router.delete("/{id}")
def delete_item(
    session: RLSSessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an item with RLS enforcement.
    """
    if current_user.is_superuser:
        # Admin can delete any item
        item = crud.delete_item_admin(session=session, item_id=id)
    else:
        # Regular users can only delete their own items
        item = crud.delete_item(session=session, item_id=id, owner_id=current_user.id)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )

    return Message(message="Item deleted successfully")


# Admin-only endpoints for managing all items
@router.get("/admin/all", response_model=ItemsPublic)
def read_all_items_admin(
    session: AdminSessionDep,
    _current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve all items (admin only).
    This endpoint bypasses RLS and shows all items regardless of ownership.
    """
    items = crud.get_all_items_admin(session=session, skip=skip, limit=limit)
    count = len(items)
    return ItemsPublic(data=items, count=count)


@router.post("/admin/", response_model=ItemPublic)
def create_item_admin(
    *,
    session: AdminSessionDep,
    _current_user: CurrentUser,
    item_in: ItemCreate,
    owner_id: uuid.UUID,
) -> Any:
    """
    Create item for any user (admin only).
    """
    item = crud.create_item(session=session, item_in=item_in, owner_id=owner_id)
    return item


@router.put("/admin/{id}", response_model=ItemPublic)
def update_item_admin(
    *,
    session: AdminSessionDep,
    _current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> Any:
    """
    Update any item (admin only).
    """
    item = crud.get_item_admin(session=session, item_id=id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )

    item = crud.update_item_admin(
        session=session, db_item=item, item_in=item_in.model_dump(exclude_unset=True)
    )
    return item


@router.delete("/admin/{id}")
def delete_item_admin(
    session: AdminSessionDep, _current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete any item (admin only).
    """
    item = crud.delete_item_admin(session=session, item_id=id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )

    return Message(message="Item deleted successfully")
