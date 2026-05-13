import logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Header, File, UploadFile, status, Form, Query, Depends
from fastapi.responses import Response 
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from schemas import JobPost





app = FastAPI(title="Recruitment Module API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.post("/job-posts", tags=["Job Posts"], status_code=status.HTTP_201_CREATED)
async def create_job_post(job_post: JobPost):
    # Here you would typically save the job post to a database
    # For this example, we'll just return the job post data
    return {"message": "Job post created successfully", "job_post": job_post.dict()}





@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"}