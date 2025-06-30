import streamlit as st
import pandas as pd
from langchain.prompts import PromptTemplate
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load .env for Gemini API key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("❌ Gemini API key not found in .env. Please set GOOGLE_API_KEY.")
    st.stop()

# Configure Gemini
genai.configure(api_key=api_key)

# Clean the generated Python code
def clean_generated_code(raw_output: str, df: pd.DataFrame) -> str:
    cleaned = raw_output.replace("```python", "").replace("```", "").strip()
    lines = cleaned.splitlines()
    code_lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]
    code = "\n".join(code_lines).strip()

    if code.startswith("."):
        code = "df" + code

    for col in df.columns:
        if f"['{col}']" in code:
            break
    else:
        if ".groupby(" in code or "[" in code:
            possible_value = code.split("[")[-1].split("]")[0].strip("'\"")
            code = f"df[df['Category'] == '{possible_value}'].shape[0]"

    if not code or "import" in code or "__" in code:
        return "raise ValueError('Invalid or unsafe code generated.')"

    return code

# Generate pandas code using Gemini
def generate_pandas_code(columns: list, question: str) -> str:
    prompt_template = PromptTemplate(
        input_variables=["columns", "question"],
        template = """
You are a Python data assistant. The user uploaded an Excel file with the following columns:
{columns}

Write a single-line pandas expression using the variable `df` to answer the following question:

"{question}"

Important:
- Treat exact text matches seriously. If a category contains spaces or symbols, use it exactly as-is.
- Don't split or assume multiple values unless asked.

Only return the code. No explanations or comments.
"""


    )
    prompt = prompt_template.format(columns=", ".join(columns), question=question)

    model = genai.GenerativeModel("models/gemini-1.5-flash")  # use a fast model for short output
    response = model.generate_content(prompt)
    return response.text.strip()

# Streamlit App
st.set_page_config(page_title="📊 Excel Q&A Chatbot (Gemini)", page_icon="📄")
st.title("📊 Ask Questions About Your Excel File")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.subheader("📄 Excel Preview")
    st.dataframe(df.head(10))

    user_question = st.text_input("Ask a question about your Excel data:")

    if st.button("Get Answer") and user_question:
        with st.spinner("🤖 Gemini is thinking..."):
            try:
                raw_code = generate_pandas_code(df.columns.tolist(), user_question)
                cleaned_code = clean_generated_code(raw_code, df)

                st.subheader("🧠 Generated Code")
                st.code(cleaned_code, language="python")

                result = eval(cleaned_code)
                st.success("✅ Answer:")
                st.write(result)

            except Exception as e:
                st.error("⚠️ Execution failed.")
                st.text(f"Generated Code: {cleaned_code if 'cleaned_code' in locals() else raw_code}")
                st.text(f"Error: {str(e)}")
