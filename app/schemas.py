from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


# ---------- Households ----------

class HouseholdBase(BaseModel):
    name: str
    budget: Optional[float] = None
    num_people: int = 2


class HouseholdCreate(HouseholdBase):
    pass


class HouseholdOut(HouseholdBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class MemberBase(BaseModel):
    name: str
    goal: Optional[str] = None
    is_personal_mode: bool = False


class MemberCreate(MemberBase):
    household_id: str


class MemberOut(MemberBase):
    id: str
    household_id: str

    class Config:
        from_attributes = True


class DietaryRuleBase(BaseModel):
    rule_type: str
    value: str
    is_hard: bool = True


class DietaryRuleCreate(DietaryRuleBase):
    household_id: str


class DietaryRuleOut(DietaryRuleBase):
    id: str
    household_id: str

    class Config:
        from_attributes = True


# ---------- Ingredients ----------

class IngredientBase(BaseModel):
    name: str
    default_unit: str = "g"
    category: Optional[str] = None


class IngredientCreate(IngredientBase):
    pass


class IngredientProductLinkOut(BaseModel):
    id: str
    store_product_id: str
    is_preferred: bool

    class Config:
        from_attributes = True


class IngredientOut(IngredientBase):
    id: str
    product_links: list[IngredientProductLinkOut] = []

    class Config:
        from_attributes = True


# ---------- Recipes ----------

class RecipeIngredientBase(BaseModel):
    raw_text: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    ingredient_id: Optional[str] = None


class RecipeIngredientLink(BaseModel):
    ingredient_id: str


class RecipeIngredientOut(RecipeIngredientBase):
    id: str

    class Config:
        from_attributes = True


class RecipeCreate(BaseModel):
    name: str
    servings: int = 4
    instructions: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    image_url: Optional[str] = None
    ingredients: list[RecipeIngredientBase] = []


class RecipeImportRequest(BaseModel):
    url: str


class RecipeOut(BaseModel):
    id: str
    name: str
    source: str
    source_url: Optional[str] = None
    servings: int
    instructions: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    image_url: Optional[str] = None
    ingredients: list[RecipeIngredientOut] = []

    class Config:
        from_attributes = True


# ---------- Planning ----------

class PlanMealCreate(BaseModel):
    recipe_id: str
    day: date
    meal_type: str
    servings_override: Optional[int] = None


class PlanMealOut(PlanMealCreate):
    id: str
    plan_id: str

    class Config:
        from_attributes = True


class WeeklyPlanCreate(BaseModel):
    household_id: str
    week_start: date


class WeeklyPlanOut(BaseModel):
    id: str
    household_id: str
    week_start: date
    meals: list[PlanMealOut] = []

    class Config:
        from_attributes = True


# ---------- Shopping list ----------

class ShoppingListItemOut(BaseModel):
    id: str
    ingredient_id: str
    quantity_needed: float
    unit: str
    cheapest_store_product_id: Optional[str] = None
    estimated_cost: Optional[float] = None
    is_checked: bool = False
    ingredient_name: Optional[str] = None
    store: Optional[str] = None

    class Config:
        from_attributes = True

    @staticmethod
    def from_orm_item(item):
        obj = ShoppingListItemOut.model_validate(item)
        obj.ingredient_name = item.ingredient.name if item.ingredient else None
        obj.store = item.cheapest_store_product.store if item.cheapest_store_product else None
        return obj


# ---------- Store products ----------

class StoreProductOut(BaseModel):
    id: str
    store: str
    sku: str
    category: Optional[str] = None
    name: str
    price: float
    currency: str
    product_url: Optional[str] = None

    class Config:
        from_attributes = True
