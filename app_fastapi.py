import gradio as gr
import re
import pdfplumber
import requests
from fastapi import FastAPI

CUSTOM_PATH = "/"

app = FastAPI()

# @app.get("/")
# def read_main():
#     return {"message": "This is the main app page, see the /nda-sanity-check"}

def get_rag_response(paragraphs):
    API_KEY = "4j7Om6KIHlSQk6gurAdQOH0Yd0bwyk6_9xO1OGumdnyU"
    token_response = requests.post('https://iam.cloud.ibm.com/identity/token', data={"apikey":
    API_KEY, "grant_type": 'urn:ibm:params:oauth:grant-type:apikey'})
    mltoken = token_response.json()["access_token"]

    header = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + mltoken}

    # NOTE: manually define and pass the array(s) of values to be scored in the next line
    # payload_scoring = {"input_data": [{"fields": [array_of_input_fields], "values": [array_of_values_to_be_scored, another_array_of_values_to_be_scored]}]}

    values = paragraphs

    payload = {
        "input_data": [{
            "fields": ["Text"],
            "values": [values]
        }]
    }
    response_scoring = requests.post('https://us-south.ml.cloud.ibm.com/ml/v4/deployments/rag_with_wx_es64bd3818/predictions?version=2021-05-01',
                                    json=payload, 
                                    headers={'Authorization': 'Bearer ' + mltoken})
    return response_scoring

def format_tool_output(paragraphs, response_scoring):
    output = ""
    for para, resp in zip(paragraphs, response_scoring.json()['predictions'][0]['values'][0]):
        output += f"{'='*82}\n\n"
        output += 'NDA Clause:\n----------------\n'
        output += para + '\n\n'
        formatted_resp = re.sub(r'\*\* (?!(\\n))', '** \n', resp)
        output += (formatted_resp.replace("**\n\n", "\n")
                       .replace("** \n\n", " \n")
                       .replace("**\n", "\n")
                       .replace("** \n", "\n")
                       .replace("**1. Compliance Issues:", "Compliance Issues:\n-------------------------")
                       .replace("**2. Corrections:", "Corrections:\n----------------") + '\n\n')
        output += f"{'='*82}\n"
    return output
    
def extract_text(pdf_path=None, text=None):
    if pdf_path is not None:
        paragraphs = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text(x_tolerance=1, y_tolerance=1)
                if text:
                    # Use regex to split paragraphs by numbering pattern
                    split_paragraphs = re.split(r'(\d+\.\s)', text)
                    
                    # Combine split parts correctly
                    current_paragraph = ""
                    for i, part in enumerate(split_paragraphs):
                        if re.match(r'\d+\.\s', part):
                            if current_paragraph:
                                paragraphs.append(current_paragraph.strip())
                            current_paragraph = part
                        else:
                            current_paragraph += part
                    
                    if current_paragraph:
                        paragraphs.append(current_paragraph.strip())
                    return paragraphs
    else:
        return [text]

def nda_sanity_check(pdf_path=None, text=None):
    paragraphs = extract_text(pdf_path=pdf_path, text=text)
    response_scoring = get_rag_response(paragraphs=paragraphs)
    return format_tool_output(paragraphs, response_scoring)

io = gr.Interface(
    fn=nda_sanity_check, 
    theme=gr.themes.Soft(),
    title="NDA Sanity Check",
    description="Verify you NDA against predefined standards in a matter of seconds!",
    inputs=[gr.File(label="Upload PDF with NDA"),
            gr.Textbox(label="Enter NDA text",
                       lines=10,
                       placeholder="Enter text here...")],
    outputs=gr.Textbox(label="Compliance Issues"),
    live=False,
    allow_flagging="never"
    )

app = gr.mount_gradio_app(app, io, path=CUSTOM_PATH)