from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict, Optional, List, Dict, Any
import fitz  # PyMuPDF
from pathlib import Path
import base64
import os
from dotenv import load_dotenv
load_dotenv()

class ParserAgentState(TypedDict):
    pass




def pdf_to_images(pdf_path, output_dir="pdf_pages"):
 
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)

    image_paths = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        image_path = output_dir / f"{pdf_path.stem}_page_{page_num + 1}.png"
        pix.save(str(image_path))
        image_paths.append(str(image_path))

    doc.close()

    # return image_paths
    return str(output_dir)



def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from images in a folder using OpenAI vision model."""
    folder_path = pdf_to_images(pdf_path)
    try:
        image_paths = [f for f in os.listdir(folder_path) if f.endswith((".png", ".jpg", ".jpeg"))]
        extracted_text = ""

        for image_path in image_paths:
            with open(os.path.join(folder_path, image_path), "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

                # Detect mime type from extension
                ext = os.path.splitext(image_path)[-1].lower()
                mime_map = {".png": "image/png"}
                mime_type = mime_map.get(ext, "image/png")
                
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
    




if __name__ == "__main__":
    # Quick test for the PDF extraction function
    # print(pdf_to_images("SQA Engineer.pdf"))
    
    extracted_text = extract_text_from_pdf("syedali.pdf")
    print("Extracted Text:")
    print(extracted_text)