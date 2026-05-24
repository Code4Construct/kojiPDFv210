import os
from fitz import Document
from pandas import DataFrame, ExcelWriter

def collect_pdf_paths(folder_path):
    """Return PDF file paths and empty leaf folders in sorted order."""
    paths = []
    for root, dirs, files in os.walk(folder_path):
        dirs.sort()
        files.sort()
        
        pdf_files = [file for file in files if file.lower().endswith('.pdf')]
        
        if pdf_files:
            for pdf_file in pdf_files:
                paths.append(os.path.join(root, pdf_file))
        elif not dirs:
            paths.append(root)
            
    return paths

def get_pdf_page_count(pdf_path):
    """Return the page count of a PDF, or 0 when it cannot be opened."""
    try:
        with Document(pdf_path) as pdf_document:
            return pdf_document.page_count
    except Exception as e:
        print(f"Error opening {pdf_path}: {e}")
        return 0

def build_tree_data(input_folder):
    """Build the PDF tree DataFrame and return it with the max folder depth."""
    paths = collect_pdf_paths(input_folder)
    data = []
    for path in paths:
        row = []
        page_count = get_pdf_page_count(path) if path.lower().endswith('.pdf') else 0
        
        row.append(page_count)
        row.append(path)
        row.append(path)
        relative_path = path.replace(input_folder + os.sep, '')
        parts = relative_path.split(os.sep)
        row.extend(parts)

        data.append(row)

    max_levels = max(len(row) - 3 for row in data)
    columns = ["Page Count", "Full Path", "sortpath"] + [f"Level {i+1}" for i in range(max_levels)]
    df = DataFrame(data, columns=columns)
    return df, max_levels

def main(input_folder):
    """Compatibility wrapper for older code."""
    return build_tree_data(input_folder)

if __name__ == "__main__":
    input_folder = r"F:\バックアップデータ\201603建築企画代理データ"

    df, max_levels = build_tree_data(input_folder)

    with ExcelWriter('Treedata.xlsx') as writer:
        df.to_excel(writer, index=False)



