from typing import Optional, List
from pydantic import BaseModel, Field

class TestimonialBase(BaseModel):
    quote: str
    name: str
    role: str

class TestimonialCreate(TestimonialBase):
    pass

class TestimonialResponse(TestimonialBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

class AwardBase(BaseModel):
    title: str
    body: str

class AwardCreate(AwardBase):
    pass

class AwardResponse(AwardBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

class StatBase(BaseModel):
    label: str
    value: str
    suffix: Optional[str] = ""

class StatCreate(StatBase):
    pass

class StatResponse(StatBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

class ClientItem(BaseModel):
    name: str
    img: str

class ClientCategoryBase(BaseModel):
    category: str
    cols: int
    clients: List[ClientItem]

class ClientCategoryCreate(ClientCategoryBase):
    pass

class ClientCategoryResponse(ClientCategoryBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

class ClientIndustryBase(BaseModel):
    name: str
    icon: str

class ClientIndustryCreate(ClientIndustryBase):
    pass

class ClientIndustryResponse(ClientIndustryBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

class BlogPostBase(BaseModel):
    title: str
    slug: str
    date: str
    author: str
    excerpt: str
    image_url: str
    content: str

class BlogPostCreate(BlogPostBase):
    pass

class BlogPostResponse(BlogPostBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True


class FaqBase(BaseModel):
    question: str
    answer: str

class FaqCreate(FaqBase):
    pass

class FaqResponse(FaqBase):
    id: str = Field(alias='_id')

    class Config:
        populate_by_name = True

class JobBase(BaseModel):
    title: str
    location: str
    type: str
    req: str

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: str = Field(alias='_id')

    class Config:
        populate_by_name = True
