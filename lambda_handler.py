from mangum import Mangum

from app.main import app

# FastAPI adapter for AWS Lambda behind API Gateway REST API
handler = Mangum(app)
