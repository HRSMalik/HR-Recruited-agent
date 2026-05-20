from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict, Optional, List, Dict, Any
import fitz  # PyMuPDF
from pathlib import Path
import base64
import json
import os
import shutil
import uuid
from datetime import date
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()


_MONGO_COLLECTION = None


def _get_candidates_collection():
    """Lazily build and cache the MongoDB `candidates_info` collection handle."""
    global _MONGO_COLLECTION
    if _MONGO_COLLECTION is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _MONGO_COLLECTION = MongoClient(uri)[db_name]["candidates_info"]
    return _MONGO_COLLECTION

class ParserAgentState(TypedDict):
    pass




def pdf_to_images(pdf_path, output_dir):
    """Render each PDF page to PNG inside output_dir."""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            pix.save(str(output_dir / f"page_{page_num + 1}.png"))
    finally:
        doc.close()

    return str(output_dir)



def extract_text_from_pdf(pdf_path: str, work_dir: str) -> str:
    """Render PDF pages into work_dir and OCR them with the OpenAI vision model."""
    folder_path = pdf_to_images(pdf_path, work_dir)
    try:
        image_paths = sorted(
            f for f in os.listdir(folder_path) if f.endswith((".png", ".jpg", ".jpeg"))
        )
        extracted_text = ""

        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        for image_path in image_paths:
            with open(os.path.join(folder_path, image_path), "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

                ext = os.path.splitext(image_path)[-1].lower()
                mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
                mime_type = mime_map.get(ext, "image/png")

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{mime_type};base64,{image_data}"}
                                },
                                {
                                    "type": "text",
                                    "text": "Extract and return all the text visible in this image. Return only the extracted text, nothing else."
                                }
                            ]
                        }
                    ],
                    max_tokens=2000
                )
                extracted_text += response.choices[0].message.content.strip() + "\n"
        return extracted_text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""
    

def extract_cv_details(cv_text: str, cv_id: str, output_dir: str = "extracted_data") -> dict:
    prompt = f"""
    Extract the following information from the CV text.

    Return ONLY valid JSON.

    Required fields:
    - name
    - phone
    - email
    - last_education_institution
    - last_education_degree (e.g., "Bachelor's in Computer Science", "Master's in Data Science", etc.)
    - experience_years (total years of relevant work experience)
    - freelance_experience_years (total years of freelance experience, if any)(optional)

    Rules:
    - If a field is missing, return an empty string
    - Do not include explanations
    - Do not wrap JSON in markdown
    - to get experience, count time from their jobs start date and end dates to get total number of year
    - get the experience in exact years, if experience starts from mar 2018 and ends in jan 2020, then experience is 1.8 years and so on, if it mentions jun 2018 to present then todays date is {date.today()} count the experience accordingly.
    - count freelance experience separately i.e. (upwork, fiverr, etc.)
    - do not add freelance experience in experience_years field, it should be only in freelance_experience_years field

    
    CV TEXT:
    {cv_text}
    """

    llm = init_chat_model("gpt-4o-mini", temperature=0)
    response = llm.invoke(prompt)

    try:
        json_response = json.loads(response.content)
    except Exception:
        json_response = {
            "name": "",
            "phone": "",
            "email": "",
            "last_education_institution": "",
            "last_education_degree": "",
            "experience_years": "",
            "freelance_experience_years": ""
        }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{cv_id}.json", "w") as f:
        json.dump(json_response, f)

    _get_candidates_collection().replace_one(
        {"_id": cv_id},
        {**json_response, "_id": cv_id},
        upsert=True,
    )

    return json_response


def process_cv(pdf_path: str, pages_root: str = "pdf_pages", extracted_root: str = "extracted_data",) -> dict:

    cv_id = str(uuid.uuid4())
    work_dir = Path(pages_root) / cv_id
    try:
        cv_text = extract_text_from_pdf(pdf_path, str(work_dir))
        data = extract_cv_details(cv_text, cv_id, extracted_root)
        return {"id": cv_id, "data": data}
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    result = process_cv("syedali.pdf")
    print(result)