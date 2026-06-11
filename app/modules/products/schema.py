from pydantic import BaseModel
from typing import List, Optional


# ─── Existing Models ──────────────────────────────────────────────────────────

class VialOption(BaseModel):
    label: str
    bonus: int

class Variants(BaseModel):
    concentration: List[str]
    vialCount: List[VialOption]

class Product(BaseModel):
    id: str
    name: str
    price: int
    description: str
    variants: Variants

class CartItem(BaseModel):
    product_id: str
    variant_id: str
    quantity: int

class CartDetailsRequest(BaseModel):
    items: List[CartItem]


# ─── New Admin Models ─────────────────────────────────────────────────────────

class ProductVariantInput(BaseModel):
    label: str       # e.g. "5mg"
    price: int       # e.g. 2500

class CreateProductRequest(BaseModel):
    name: str
    subtitle: Optional[str] = None
    description: str
    image_url: Optional[str] = None
    tag: Optional[str] = None
    min_price: Optional[int] = None
    variants: List[ProductVariantInput]

class CreateProductResponse(BaseModel):
    id: str
    name: str
    message: str