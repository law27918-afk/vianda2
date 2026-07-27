from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.database import get_db

router = APIRouter(prefix="/plans", tags=["planning"])


@router.post("/", response_model=schemas.WeeklyPlanOut)
def create_plan(payload: schemas.WeeklyPlanCreate, db: Session = Depends(get_db)):
    plan = models.WeeklyPlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=schemas.WeeklyPlanOut)
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = db.query(models.WeeklyPlan).get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan no encontrado")
    return plan


@router.post("/{plan_id}/meals", response_model=schemas.PlanMealOut)
def add_meal(plan_id: str, payload: schemas.PlanMealCreate, db: Session = Depends(get_db)):
    """
    servings_override: cuántas porciones se necesitan ese día. Si no se manda,
    se asume recipe.servings. Esto es lo que permite que la misma receta
    sirva para 2 o 4 personas según el día, sin duplicar la receta.
    """
    meal = models.PlanMeal(plan_id=plan_id, **payload.model_dump())
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return meal


@router.delete("/{plan_id}/meals/{meal_id}")
def remove_meal(plan_id: str, meal_id: str, db: Session = Depends(get_db)):
    meal = db.query(models.PlanMeal).get(meal_id)
    if not meal:
        raise HTTPException(404, "Comida no encontrada en el plan")
    db.delete(meal)
    db.commit()
    return {"ok": True}
