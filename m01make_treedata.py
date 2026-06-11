import os

from fitz import Document


def collect_pdf_paths(folder_path):
    """Return PDF file paths and empty leaf folders in sorted order."""
    paths = []
    for root, dirs, files in os.walk(folder_path):
        dirs.sort()
        files.sort()

        pdf_files = [file for file in files if file.lower().endswith(".pdf")]

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
    """Build tree rows and return them with the max folder depth."""
    paths = collect_pdf_paths(input_folder)
    row_parts = []

    for path in paths:
        page_count = get_pdf_page_count(path) if path.lower().endswith(".pdf") else 0
        relative_path = path.replace(input_folder + os.sep, "")
        parts = relative_path.split(os.sep)
        row_parts.append((page_count, path, parts))

    max_levels = max((len(parts) for _, _, parts in row_parts), default=0)
    rows = []
    for page_count, path, parts in row_parts:
        row = {
            "Page Count": page_count,
            "Full Path": path,
            "sortpath": path,
        }
        for index, part in enumerate(parts, start=1):
            row[f"Level {index}"] = part
        rows.append(row)

    return rows, max_levels


def main(input_folder):
    """Compatibility wrapper for older code."""
    return build_tree_data(input_folder)


if __name__ == "__main__":
    input_folder = r"F:\backup_data\sample"
    df, max_levels = build_tree_data(input_folder)
    print(df)
