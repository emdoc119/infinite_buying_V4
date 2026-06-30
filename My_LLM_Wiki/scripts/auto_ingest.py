import os
import sys
import glob
import shutil
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load .env file from the workspace root
workspace_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(workspace_root / ".env")

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY is not set in .env")
    sys.exit(1)

client = genai.Client(api_key=api_key)

WIKI_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = WIKI_ROOT / "raw"
WIKI_DIR = WIKI_ROOT / "wiki"
ARCHIVE_DIR = RAW_DIR / "archive"

# Ensure directories exist
WIKI_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# Read AGENTS.md rules
try:
    with open(WIKI_ROOT / "AGENTS.md", "r", encoding="utf-8") as f:
        agents_prompt = f.read()
except FileNotFoundError:
    print("AGENTS.md not found!")
    agents_prompt = "Format output as Markdown with frontmatter and use [[wikilinks]]."

def process_file(file_path):
    print(f"Processing: {file_path}")
    
    try:
        # Upload file to Gemini File API
        print("Uploading file to Gemini API...")
        safe_name = file_path.stem.encode('ascii', 'ignore').decode()
        if not safe_name:
            safe_name = "upload_file"
        
        config = types.UploadFileConfig(display_name=safe_name)
        uploaded_file = client.files.upload(file=str(file_path), config=config)
        print(f"Uploaded as: {uploaded_file.uri}")
        
        prompt = f"""
        You are the Antigravity Autonomous System Architect operating an LLM OS.
        Here are the core rules you must follow:
        {agents_prompt}
        
        Please read the attached file and synthesize the knowledge into a markdown wiki page.
        Extract the core entities, concepts, and relationships.
        Generate a complete markdown file output.
        - INCLUDE the YAML frontmatter (title, created, updated, tags).
        - Use [[wikilinks]] extensively for key concepts.
        - Only output the raw markdown text, no extra conversational text. Do not wrap in markdown code blocks, just output the raw text.
        """
        
        print("Generating wiki page...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt],
        )
        
        result_text = response.text.strip()
        
        # Determine filename from the frontmatter title, or fallback to original filename
        filename = file_path.stem.replace(" ", "-").lower() + ".md"
        # Try to parse title from frontmatter
        for line in result_text.split('\n'):
            if line.startswith('title:'):
                parsed_title = line.split('title:')[1].strip().strip('"').strip("'")
                filename = parsed_title.replace(" ", "-").lower() + ".md"
                break
                
        output_path = WIKI_DIR / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result_text)
            
        print(f"Saved wiki page to: {output_path}")
        
        # Move original file to archive
        shutil.move(str(file_path), str(ARCHIVE_DIR / file_path.name))
        print(f"Archived {file_path.name}")
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    if not RAW_DIR.exists():
        print(f"Raw directory not found: {RAW_DIR}")
        return
        
    files = list(RAW_DIR.glob("*"))
    if not files:
        print("No files found in raw directory.")
        return
        
    print(f"Found {len(files)} files to process.")
    for file_path in files:
        if file_path.is_dir():
            continue
        # Skip if it's already a markdown file in raw (though shouldn't happen usually)
        if file_path.suffix.lower() == '.md':
            continue
        process_file(file_path)

if __name__ == "__main__":
    main()
