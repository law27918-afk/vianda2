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
    exclude_keywords: Optional[str] = None


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
    estimated_kcal_total: Optional[float] = None
    estimated_kcal_per_serving: Optional[float] = None

    class Config:
        from_attributes = True

    @staticmethod
    def from_orm_recipe(recipe):
        from app.core.calories import estimar_kcal_receta

        obj = RecipeOut.model_validate(recipe)
        kcal_info = estimar_kcal_receta(recipe.ingredients)
        obj.estimated_kcal_total = kcal_info["total_kcal"]
        if kcal_info["total_kcal"] is not None and recipe.servings:
            obj.estimated_kcal_per_serving = round(kcal_info["total_kcal"] / recipe.servings, 0)
        return obj


# ---------- Recetas externas (TheMealDB) ----------

class ExternalRecipeSummary(BaseModel):
    external_id: str
    name: str
    image_url: Optional[str] = None
    category: Optional[str] = None
    area: Optional[str] = None


class ExternalRecipeDetail(BaseModel):
    external_id: str
    name: str
    image_url: Optional[str] = None
    category: Optional[str] = None
    area: Optional[str] = None
    instructions: Optional[str] = None
    ingredients: list[str] = []  # líneas ya combinadas "medida + ingrediente"


# ---------- Planning ----------

class PlanMealCreate(BaseModel):
    recipe_id: str
    day: date
    meal_type: str
    member_id: Optional[str] = None
    is_required: bool = True
    servings_override: Optional[int] = None


class PlanMealOut(PlanMealCreate):
    id: str
    plan_id: str
    estimated_kcal: Optional[float] = None

    class Config:
        from_attributes = True

    @staticmethod
    def from_orm_meal(meal):
        from app.core.calories import estimar_kcal_receta

        obj = PlanMealOut.model_validate(meal)
        if meal.recipe:
            kcal_info = estimar_kcal_receta(meal.recipe.ingredients)
            if kcal_info["total_kcal"] is not None and meal.recipe.servings:
                scale = (meal.servings_override or meal.recipe.servings) / meal.recipe.servings
                obj.estimated_kcal = round(kcal_info["total_kcal"] * scale, 0)
        return obj


class PlanCreate(BaseModel):
    household_id: str
    start_date: date
    end_date: date


class PlanOut(BaseModel):
    id: str
    household_id: str
    start_date: date
    end_date: date
    meals: list[PlanMealOut] = []

    class Config:
        from_attributes = True

    @staticmethod
    def from_orm_plan(plan):
        obj = PlanOut.model_validate({**plan.__dict__, "meals": []})
        obj.meals = [PlanMealOut.from_orm_meal(m) for m in plan.meals]
        return obj


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
