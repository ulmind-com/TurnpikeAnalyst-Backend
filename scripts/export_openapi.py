import json
import os
from app.main import app

def export_swagger():
    print("Generating official Swagger / OpenAPI 3 specification from FastAPI application...")
    openapi_schema = app.openapi()
    
    swagger_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "swagger.json")
    openapi_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "openapi.json")
    
    with open(swagger_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
        
    with open(openapi_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
        
    print(f" [OK] Successfully generated: {swagger_path}")
    print(f" [OK] Successfully generated: {openapi_path}")
    print(" You can import these files directly into Postman, Swagger UI, or frontend TypeScript generators (e.g. openapi-typescript, orval, rtk-query)!")

if __name__ == "__main__":
    export_swagger()
