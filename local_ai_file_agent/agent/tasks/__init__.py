from .create_file   import run as create_file
from .read_file     import run as read_file
from .rewrite_file  import run as rewrite_file
from .diff_preview  import run as diff_preview
from .generate_code import run as generate_code
from .validate_file import run as validate_file
from .chat          import run as chat
from .folder_analysis import run as folder_analysis
from .batch_ops     import run as batch_ops
from .file_convert  import run as file_convert
from .file_merge    import run as file_merge
from .file_search   import run as file_search
from .file_backup   import run as file_backup
from .zip_read      import run as zip_read
from .zip_create    import run as zip_create
from .recycle_bin   import run as recycle_bin
from .save_content  import run as save_content

TASK_MAP = {
    "CREATE_FILE":      create_file,
    "READ_FILE":        read_file,
    "REWRITE_FILE":     rewrite_file,
    "DIFF_PREVIEW":     diff_preview,
    "GENERATE_CODE":    generate_code,
    "VALIDATE_FILE":    validate_file,
    "FOLDER_ANALYSIS":  folder_analysis,
    "BATCH_OPS":        batch_ops,
    "FILE_CONVERT":     file_convert,
    "FILE_MERGE":       file_merge,
    "FILE_SEARCH":      file_search,
    "FILE_BACKUP":      file_backup,
    "ZIP_READ":         zip_read,
    "ZIP_CREATE":       zip_create,
    "RECYCLE_BIN":      recycle_bin,
    "SAVE_CONTENT":     save_content,
    "CHAT":             chat,
}
