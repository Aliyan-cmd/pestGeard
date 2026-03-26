import google.generativeai as generativeai
import gradio as gr
from pathlib import Path
from dotenv import load_dotenv
import os
import mimetypes

load_dotenv()

generativeai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = generativeai.GenerativeModel(
    model_name="gemini-1.5-flash",
    safety_settings=safety_settings,
    generation_config={
        "temperature": 0.4,
        "top_p": 1,
        "top_k": 32,
        "max_output_tokens": 4096,
    }
)

def read_image_data(file_path):
    image_path = Path(file_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    # Dynamically detect MIME type instead of hardcoding image/jpeg
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/jpeg"  # fallback
    return {"mime_type": mime_type, "data": image_path.read_bytes()}

def generate_gemini_response(prompt, image_file):
    image_data = read_image_data(image_file)
    response = model.generate_content([prompt, image_data])
    return response.text

input_prompt = """
As a highly skilled plant pathologist, your expertise is indispensable in our pursuit of maintaining optimal plant health. You will be provided with information or samples related to plant diseases, and your role involves conducting a detailed analysis to identify the specific issues, propose solutions, and offer recommendations.

**Analysis Guidelines:**

1. **Disease Identification:** Examine the provided information or samples to identify and characterize plant diseases accurately.

2. **Detailed Findings:** Provide in-depth findings on the nature and extent of the identified plant diseases, including affected plant parts, symptoms, and potential causes.

3. **Next Steps:** Outline the recommended course of action for managing and controlling the identified plant diseases. This may involve treatment options, preventive measures, or further investigations.

4. **Recommendations:** Offer informed recommendations for maintaining plant health, preventing disease spread, and optimizing overall plant well-being.

5. **Important Note:** As a plant pathologist, your insights are vital for informed decision-making in agriculture and plant management. Your response should be thorough, concise, and focused on plant health.

**Disclaimer:**
*"Please note that the information provided is based on plant pathology analysis and should not replace professional agricultural advice. Consult with qualified agricultural experts before implementing any strategies or treatments."*

Your role is pivotal in ensuring the health and productivity of plants. Proceed to analyze the provided information or samples, adhering to the structured guidelines outlined above, and contribute to the advancement of plant health and disease management.
"""

def process_uploaded_file(file):
    if file is None:
        return None, "No file uploaded"
    try:
        # Gradio may pass a filepath string or a file-like object depending on version
        file_path = file if isinstance(file, str) else file.name
        response = generate_gemini_response(input_prompt, file_path)
        return file_path, response
    except Exception as e:
        return None, f"Error: {str(e)}"

with gr.Blocks() as demo:
    gr.Markdown("## 🌿 Plant Disease Analyzer")
    with gr.Row():
        image_output = gr.Image(label="Uploaded Image")
        file_output = gr.Textbox(label="Analysis Result", lines=20)
    upload_button = gr.UploadButton(
        "📷 Click to upload a plant image",
        file_types=["image"],
        file_count="single"
    )
    upload_button.upload(process_uploaded_file, upload_button, [image_output, file_output])

demo.launch(debug=True)
