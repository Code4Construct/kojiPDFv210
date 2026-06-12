import os

from fitz import Document, EmptyFileError, FileDataError, TOOLS


def _run_with_mupdf_messages_hidden(callback):
    TOOLS.mupdf_display_errors(False)
    TOOLS.mupdf_display_warnings(False)
    try:
        return callback()
    finally:
        TOOLS.mupdf_display_errors(True)
        TOOLS.mupdf_display_warnings(True)


def _validate_pdf(full_path):
    with Document(full_path) as pdf:
        if pdf.is_encrypted:
            raise ValueError("Encrypted PDF")
        if pdf.page_count <= 0:
            raise ValueError("PDF has no pages")

        scratch = Document()
        try:
            for page_index in range(pdf.page_count):
                pdf.load_page(page_index)
                scratch.insert_pdf(pdf, from_page=page_index, to_page=page_index)
        finally:
            scratch.close()


def find_invalid_pdfs_with_errors(folder_path):
    """
    Return PDFs that cannot be safely opened, read page-by-page, and inserted.
    """
    invalid_files = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            if not file.lower().endswith(".pdf"):
                continue

            full_path = os.path.join(root, file)

            if not os.path.isfile(full_path):
                invalid_files.append((full_path, "Not a file"))
            elif os.path.getsize(full_path) == 0:
                invalid_files.append((full_path, "File size is 0"))
            else:
                try:
                    _run_with_mupdf_messages_hidden(lambda: _validate_pdf(full_path))
                except EmptyFileError as e:
                    invalid_files.append((full_path, f"EmptyFileError: {str(e)}"))
                except FileDataError as e:
                    invalid_files.append((full_path, f"FileDataError: {str(e)}"))
                except Exception as e:
                    invalid_files.append((full_path, f"Other error: {str(e)}"))

    return invalid_files


if __name__ == "__main__":
    folder_path = r"F:\backup_data\sample"

    if not os.path.isdir(folder_path):
        print("Input folder does not exist.")
    else:
        invalids = find_invalid_pdfs_with_errors(folder_path)
        if invalids:
            print("\nInvalid PDF files:")
            for path, msg in invalids:
                print(f" - {path} -> {msg}")
        else:
            print("All PDF files are readable.")
