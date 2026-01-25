from docx2pdf import convert
import os

def convert_docx_to_pdf(docx_path, output_dir=None):
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"{docx_path} not found")

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        convert(docx_path, output_dir)
    else:
        convert(docx_path)

    print("PDF generated successfully")
