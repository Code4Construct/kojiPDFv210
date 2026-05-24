import os
import shutil
import sys
import traceback
from datetime import datetime


def startup_log(message):
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    log_dir = os.path.join(local_app_data, "kojiPDF")
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "kojiPDF_startup.log")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    startup_log(
        "Unhandled exception:\n"
        + "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    )
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = log_unhandled_exception
startup_log("kojiPDF process started")

from fitz import open as fitz_open

import m01make_treedata as tree_data
import m02merge_from_treedata as pdf_merge
import m03make_bookmark as bookmark_builder
import m04file_name_replace as tree_data_cleanup
import m05select_folder as gui
import m06finish_message as confirmation_dialog
import m10set_newtoc as bookmark_links
import m11add_number_bookmarks as bookmark_page_counts
import m14asper_format as asper_bookmarks
import m15bookmark_title_cleanup as bookmark_cleanup
import m21get_eachPDF_toc as source_bookmarks
import m22add_child_toc as child_bookmarks
import m44temp_convert as office_temp_convert
import m45invalid_pdflist as pdf_validation
import m46pdf_resize as pdf_resize
import m47add_pagenum as pdf_page_numbers


def ensure_output_file_writable(output_file_path):
    if not os.path.exists(output_file_path):
        return

    try:
        with open(output_file_path, "r+b"):
            pass
    except PermissionError as exc:
        raise PermissionError(
            "出力先PDFファイルが使用中のため上書きできません。\n"
            "PDFビューアなどで開いている場合は閉じてから、もう一度実行してください。\n"
            f"対象ファイル: {output_file_path}"
        ) from exc
    except OSError as exc:
        raise OSError(
            "出力先PDFファイルを上書きできるか確認できませんでした。\n"
            "PDFビューアなどで開いていないか確認してください。\n"
            f"対象ファイル: {output_file_path}\n"
            f"詳細: {exc}"
        ) from exc


def create_pdf(
    folder_path,
    output_file_path,
    add_page,
    exist_w_e_file,
    ppt_slide_bookmarks,
    resize_pdf,
    resize_size,
    save_options,
    add_pdf_page_numbers,
    page_number_options,
    xratio,
    yratio,
    base_view_width_mm,
    base_view_height_mm,
    expand_all,
    collapse_level,
    asper_format,
    keep_pdf_extension,
):
    print(f"選択されたフォルダ: {folder_path}")
    ensure_output_file_writable(output_file_path)

    if exist_w_e_file:
        print("OfficeファイルをPDFに変換するため、一時フォルダへコピーしています。")
        folder_path = office_temp_convert.copy_all_folders_to_temp(folder_path, output_file_path, ppt_slide_bookmarks)

    invalids = pdf_validation.find_invalid_pdfs_with_errors(folder_path)
    if invalids:
        result = "問題のあるPDFファイル一覧:\n"
        for path, msg in invalids:
            result += f" - {path} -> {msg}\n"
        result += "問題のあるファイルを削除してから、やり直してください。"
        print(result)
        confirmation_dialog.main(result)

    else:
        print("すべてのPDFファイルは正常に読み込めます。")

    print("フォルダー構造を解析しています。")
    df, max_levels = tree_data.build_tree_data(folder_path)

    if asper_format:
        print("電脳ASPer向けにしおり名を調整しています。")
        df = asper_bookmarks.modify_pdf_names_in_all_columns(df)

    print("しおり順とページ位置を計算しています。")
    df = tree_data_cleanup.prepare_treedata_for_merge(df)

    print("PDFファイルを結合しています。")
    output_pdf = pdf_merge.merge_pdfs_from_df(df)

    if resize_pdf:
        print(f"PDFページを{resize_size}サイズに変更しています。")
        output_pdf = pdf_resize.resize_doc_auto_orientation(output_pdf, size=resize_size)

    if add_pdf_page_numbers:
        print("結合PDFの各ページにページ番号を追加しています。")
        output_pdf = pdf_page_numbers.add_page_numbers_to_doc(
            output_pdf,
            **page_number_options,
        )

    print("親しおりを追加しています。")
    output_pdf = bookmark_builder.add_bookmarks_to_pdf(df, max_levels, output_pdf)

    print("結合前PDFが持つしおりを取得しています。")
    toc_dict = source_bookmarks.get_each_pdf_toc(df)

    print("結合前PDFのしおりを子しおりとして追加しています。")
    output_pdf = child_bookmarks.add_children_to_existing_toc(output_pdf, toc_dict)

    if asper_format:
        print("電脳ASPer向けにしおり名を最終調整しています。")
        output_pdf = asper_bookmarks.last_bookmarks_rename(output_pdf)

    if add_page:
        print("しおり名に含まれるページ数を追記しています。")
        output_pdf = bookmark_page_counts.add_page_number_to_bookmarks(output_pdf)

    temp_output_path = output_file_path[:-4] + "temp.PDF"
    print("一時PDFを保存しています。")
    output_pdf.save(temp_output_path)
    output_pdf.close()

    print("一時PDFを開き直しています。")
    output_pdf = fitz_open(temp_output_path)

    print("しおりのクリック位置、ズーム倍率、展開階層を設定しています。")
    toc_collapse_level = 99 if expand_all else collapse_level
    output_pdf = bookmark_links.set_newtoc(
        output_pdf,
        xratio,
        yratio,
        toc_collapse_level,
        base_view_width_mm,
        base_view_height_mm,
        apply_asper_bookmark_colors=asper_format,
    )

    if not keep_pdf_extension:
        print("しおり名の末尾にある.pdfを削除しています。")
        output_pdf = bookmark_cleanup.remove_pdf_extension_from_bookmarks(output_pdf, collapse=toc_collapse_level)

    print("最終PDFを保存しています。")
    ensure_output_file_writable(output_file_path)
    output_pdf.xref_set_key(output_pdf.pdf_catalog(), "PageMode", "/UseOutlines")
    output_pdf.save(output_file_path, **save_options)
    output_pdf.close()

    print("一時PDFを削除しています。")
    os.remove(temp_output_path)

    if exist_w_e_file:
        confirmation_dialog.main(f"{folder_path}を削除します。\nよろしいですか。")
        shutil.rmtree(folder_path)

    print(f"PDF作成が完了しました: {output_file_path}")


def main():
    (
        folder_path,
        output_file_path,
        add_page,
        exist_w_e_file,
        ppt_slide_bookmarks,
        resize_pdf,
        resize_size,
        save_options,
        asper_format,
        keep_pdf_extension,
        add_pdf_page_numbers,
        page_number_options,
        xratio,
        yratio,
        scale_enabled,
        base_view_width_mm,
        base_view_height_mm,
        expand_all,
        collapse_level,
        progress_ui,
    ) = gui.select_folder_and_file()

    if folder_path is None or output_file_path is None:
        print("キャンセルされたため、処理を中断します。")
        sys.exit(1)

    if not scale_enabled:
        xratio = 1.0
        yratio = 1.0
        base_view_width_mm = 330
        base_view_height_mm = 210

    while True:
        if progress_ui is not None:
            progress_ui.retry_requested = False

        original_stdout = sys.stdout
        sys.stdout = gui.ProgressWriter(progress_ui, original_stdout)
        success = False
        try:
            create_pdf(
                folder_path,
                output_file_path,
                add_page,
                exist_w_e_file,
                ppt_slide_bookmarks,
                resize_pdf,
                resize_size,
                save_options,
                add_pdf_page_numbers,
                page_number_options,
                xratio,
                yratio,
                base_view_width_mm,
                base_view_height_mm,
                expand_all,
                collapse_level,
                asper_format,
                keep_pdf_extension,
            )
            success = True
        except Exception as exc:
            print("処理中にエラーが発生しました。")
            traceback.print_exc()
            if progress_ui is not None:
                progress_ui.show_error_message(str(exc))
        finally:
            sys.stdout = original_stdout

        if progress_ui is None:
            break

        progress_ui.finish_progress(success)
        if success:
            exited = progress_ui.confirm_exit_after_completion()
            if not exited:
                progress_ui.window.mainloop()
            break

        progress_ui.window.mainloop()
        if not progress_ui.retry_requested:
            break


if __name__ == "__main__":
    main()
