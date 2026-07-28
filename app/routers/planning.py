from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.database import get_db

router = APIRouter(prefix="/plans", tags=["planning"])


@router.post("/", response_model=schemas.PlanOut)
def create_plan(payload: schemas.PlanCreate, db: Session = Depends(get_db)):
    if payload.end_date < payload.start_date:
        raise HTTPException(400, "La fecha final no puede ser anterior a la fecha de inicio")
    plan = models.Plan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return schemas.PlanOut.from_orm_plan(plan)


@router.get("/{plan_id}", response_model=schemas.PlanOut)
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = db.query(models.Plan).get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan no encontrado")
    return schemas.PlanOut.from_orm_plan(plan)


@router.post("/{plan_id}/meals", response_model=schemas.PlanMealOut)
def add_meal(plan_id: str, payload: schemas.PlanMealCreate, db: Session = Depends(get_db)):
    """
    servings_override: cuántas porciones se necesitan ese día/comida. Si no
    se manda, se asume recipe.servings. Para una comida de todo el hogar,
    normalmente es household.num_people; para una comida individual
    (member_id seteado, ej. la merienda de una sola persona), normalmente es 1.
    """
    meal = models.PlanMeal(plan_id=plan_id, **payload.model_dump())
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return schemas.PlanMealOut.from_orm_meal(meal)


@router.delete("/{plan_id}/meals/{meal_id}")
def remove_meal(plan_id: str, meal_id: str, db: Session = Depends(get_db)):
    meal = db.query(models.PlanMeal).get(meal_id)
    if not meal:
        raise HTTPException(404, "Comida no encontrada en el plan")
    db.delete(meal)
    db.commit()
    return {"ok": True}
