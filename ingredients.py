from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.database import get_db

router = APIRouter(prefix="/households", tags=["households"])


@router.get("/", response_model=list[schemas.HouseholdOut])
def list_households(db: Session = Depends(get_db)):
    return db.query(models.Household).all()


@router.post("/", response_model=schemas.HouseholdOut)
def create_household(payload: schemas.HouseholdCreate, db: Session = Depends(get_db)):
    household = models.Household(**payload.model_dump())
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


@router.get("/{household_id}", response_model=schemas.HouseholdOut)
def get_household(household_id: str, db: Session = Depends(get_db)):
    h = db.query(models.Household).get(household_id)
    if not h:
        raise HTTPException(404, "Hogar no encontrado")
    return h


@router.patch("/{household_id}", response_model=schemas.HouseholdOut)
def update_household(household_id: str, payload: schemas.HouseholdCreate, db: Session = Depends(get_db)):
    """Aquí se cambia, por ejemplo, num_people cuando cambia la cantidad de personas del hogar."""
    h = db.query(models.Household).get(household_id)
    if not h:
        raise HTTPException(404, "Hogar no encontrado")
    for k, v in payload.model_dump().items():
        setattr(h, k, v)
    db.commit()
    db.refresh(h)
    return h


@router.post("/{household_id}/members", response_model=schemas.MemberOut)
def add_member(household_id: str, payload: schemas.MemberBase, db: Session = Depends(get_db)):
    member = models.Member(household_id=household_id, **payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.post("/{household_id}/dietary-rules", response_model=schemas.DietaryRuleOut)
def add_dietary_rule(household_id: str, payload: schemas.DietaryRuleBase, db: Session = Depends(get_db)):
    rule = models.DietaryRule(household_id=household_id, **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
