import requests
from pathlib import Path
import streamlit as st
from docx import Document
from io import BytesIO
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import re

# Directories and file paths
THIS_DIR = Path(__file__).parent
CSS_FILE = THIS_DIR / "style" / "style.css"
ASSETS = THIS_DIR / "assets"

# Constants
BASE_URL = "https://player.vimeo.com"
FILENAME = "subtitle.vtt"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://vimeo.com/"
}

# Apply custom CSS
with open(CSS_FILE) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def clean_hesitations(text):
    FILLERS = ["uh", "um", "hmm"]
    for filler in FILLERS:
        # Remove filler with optional trailing comma/period
        pattern = r'\b' + re.escape(filler) + r'[.,]?\b'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Remove extra spaces and fix space before punctuation
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s+([.,!?])', r'\1', text)

    # Handle leftover commas at beginning of sentences
    text = re.sub(r'^,\s*', '', text)

    return text.strip()

def create_pdf(text: str) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = []

    # Add a title
    story.append(Paragraph("Vimeo Subtitle Transcript", styles['Title']))
    story.append(Spacer(1, 12))

    # Add the subtitle text (wrapped automatically)
    paragraphs = text.split('\n')
    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(para.strip(), styles['Normal']))
            story.append(Spacer(1, 8))

    doc.build(story)
    buffer.seek(0)
    return buffer

def split_long_line(line, max_chars=100):
    return [line[i:i+max_chars] for i in range(0, len(line), max_chars)]

def create_docx(text: str) -> BytesIO:
    doc = Document()
    doc.add_paragraph(text)

    # Save the document to a BytesIO stream
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def sanitize_vtt(filename):
    cleaned_lines = []

    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()

            # Skip empty lines, WEBVTT, timestamps, and numbers
            if not line:
                continue
            if line == "WEBVTT":
                continue
            if line.isdigit():
                continue
            if "-->" in line:
                continue

            # Otherwise, it's actual subtitle text
            cleaned_lines.append(line)

    # Join into a single paragraph
    return " ".join(cleaned_lines)

def download_subtitles_file(full_url):
    response = requests.get(full_url, headers=HEADERS)
    if response.status_code == 200:
        with open(FILENAME, 'wb') as file:
            file.write(response.content)
        return True
    else:
        st.error(f"Failed to download file. Status code: {response.status_code}")
        return False

def setup_interface():
    st.markdown("""
        <h1 style='text-align: center; margin: 0; padding: 0;'>Vimeo Subtitle Transcript</h1>
        <p style='text-align: center; margin: 0.2em 0 2em 0; font-size: 0.9em; color: gray;'>
            Made by Fernando Silva · <a href="https://github.com/fernandojpsilva" target="_blank">GitHub</a>
        </p>
        """, unsafe_allow_html=True)

    # Ask user for input
    return st.text_input("Enter the subtitles path (e.g., `/texttrack/227834924.vtt?token=...`)")

def setup_sanitize_download(sub_path):
    if st.button("Sanitize"):
        if not sub_path.startswith("/"):
            sub_path = "/" + sub_path

        full_url = BASE_URL + sub_path
        download_subtitles_file(full_url)

        if download_subtitles_file(full_url):
            cleaned_text = sanitize_vtt(FILENAME)
        else:
            st.stop()

        if cleaned_text:
            filtered_text = clean_hesitations(cleaned_text)
            st.text_area("Cleaned Subtitles", filtered_text, height=300)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    "Download as TXT",
                    filtered_text,
                    file_name="subtitles.txt"
                )
            with col2:
                st.download_button(
                    "Download as DOCX",
                    create_docx(filtered_text),
                    file_name="subtitles.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            with col3:
                st.download_button(
                    "Download as PDF",
                    create_pdf(filtered_text),
                    file_name="subtitles.pdf",
                    mime="application/pdf"
                )

def main():
    sub_path = setup_interface()
    setup_sanitize_download(sub_path)


if __name__ == "__main__":
    main()


