from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.database import get_db

router = APIRouter(prefix="/plans", tags=["shopping"])


@router.post("/{plan_id}/shopping-list/generate", response_model=list[schemas.ShoppingListItemOut])
def generate_shopping_list(plan_id: str, db: Session = Depends(get_db)):
    """
    Deriva la lista de compras del plan semanal:
    1. Suma cantidades de cada ingrediente vinculado a través de todas las comidas del plan,
       escalando por servings_override / recipe.servings.
    2. Para cada ingrediente, busca sus productos vinculados y elige el más barato
       entre Super99 y Riba Smith.
    Ingredientes de recipe_ingredients sin ingredient_id vinculado se ignoran
    (no pueden comprarse automáticamente hasta que se vinculen).
    """
    plan = db.query(models.WeeklyPlan).get(plan_id)
    if not plan:
        raise HTTPException(404, "Plan no encontrado")

    # borra lista previa para regenerar limpio
    db.query(models.ShoppingListItem).filter(models.ShoppingListItem.plan_id == plan_id).delete()

    totals: dict[str, dict] = defaultdict(lambda: {"quantity": 0.0, "unit": None})

    for meal in plan.meals:
        recipe = meal.recipe
        servings_needed = meal.servings_override or recipe.servings
        scale = servings_needed / recipe.servings if recipe.servings else 1

        for ri in recipe.ingredients:
            if not ri.ingredient_id or ri.quantity is None:
                continue  # no vinculado o sin cantidad estructurada, se omite del cálculo automático
            totals[ri.ingredient_id]["quantity"] += ri.quantity * scale
            totals[ri.ingredient_id]["unit"] = ri.unit

    items = []
    for ingredient_id, data in totals.items():
        cheapest_id = None
        cheapest_price = None

        links = (
            db.query(models.IngredientProductLink)
            .filter(models.IngredientProductLink.ingredient_id == ingredient_id)
            .all()
        )
        for link in links:
            product = link.store_product
            if product and (cheapest_price is None or product.price < cheapest_price):
                cheapest_price = product.price
                cheapest_id = product.id

        item = models.ShoppingListItem(
            plan_id=plan_id,
            ingredient_id=ingredient_id,
            quantity_needed=round(data["quantity"], 2),
            unit=data["unit"] or "unidad",
            cheapest_store_product_id=cheapest_id,
            estimated_cost=cheapest_price,
        )
        db.add(item)
        items.append(item)

    db.commit()
    for item in items:
        db.refresh(item)
    return items


@router.get("/{plan_id}/shopping-list", response_model=list[schemas.ShoppingListItemOut])
def get_shopping_list(plan_id: str, db: Session = Depends(get_db)):
    return db.query(models.ShoppingListItem).filter(models.ShoppingListItem.plan_id == plan_id).all()


class CheckPayload(BaseModel):
    checked: bool


@router.patch("/{plan_id}/shopping-list/{item_id}/check")
def toggle_checked(plan_id: str, item_id: str, payload: CheckPayload, db: Session = Depends(get_db)):
    item = db.query(models.ShoppingListItem).get(item_id)
    if not item:
        raise HTTPException(404, "Ítem no encontrado")
    item.is_checked = payload.checked
    db.commit()
    return {"ok": True}
