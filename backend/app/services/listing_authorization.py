from fastapi import HTTPException, status

from app.models.user import User

LISTING_LOCKED_FOR_EMPLOYEE_DETAIL = "Цей лот закріплений за іншим співробітником, ви не можете його редагувати"


def is_listing_locked_for_employee(seller_employee_id: int | None, current_user: User) -> bool:
    """True when `current_user` is an employee and the listing's seller Client
    is assigned to a DIFFERENT employee. An unassigned listing (None) and a
    listing assigned to `current_user` themselves are both left unlocked —
    only someone else's assignment blocks access."""
    return (
        current_user.role == "employee"
        and seller_employee_id is not None
        and seller_employee_id != current_user.id
    )


def ensure_employee_can_act_on_listing(seller_employee_id: int | None, current_user: User) -> None:
    if is_listing_locked_for_employee(seller_employee_id, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=LISTING_LOCKED_FOR_EMPLOYEE_DETAIL)
