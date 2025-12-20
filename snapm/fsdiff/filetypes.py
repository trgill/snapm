# Copyright Red Hat
#
# snapm/fsdiff/filetypes.py - Snapshot Manager fs diff file types
#
# This file is part of the snapm project.
#
# SPDX-License-Identifier: Apache-2.0
"""
File type information support.
"""
from typing import ClassVar, Dict, Optional, Tuple
from pathlib import Path
from enum import Enum
import logging
import magic

from snapm import SNAPM_SUBSYSTEM_FSDIFF

_log = logging.getLogger(__name__)

_log_debug = _log.debug
_log_info = _log.info
_log_warn = _log.warning
_log_error = _log.error


def _log_debug_fsdiff(msg, *args, **kwargs):
    """A wrapper for fsdiff subsystem debug logs."""
    _log.debug(msg, *args, extra={"subsystem": SNAPM_SUBSYSTEM_FSDIFF}, **kwargs)


# Mappings for Text-based Extensions
# Format: ".ext": ("mime/type", "description starting with lowercase")
TEXT_EXTENSION_MAP = {
    # General Text & Documentation
    ".txt": ("text/plain", "plain text document"),
    ".text": ("text/plain", "plain text document"),
    ".md": ("text/markdown", "markdown documentation"),
    ".markdown": ("text/markdown", "markdown documentation"),
    ".rst": ("text/x-rst", "reStructuredText document"),
    ".adoc": ("text/asciidoc", "asciidoc document"),
    ".asciidoc": ("text/asciidoc", "asciidoc document"),
    ".nfo": ("text/x-nfo", "nfo information file"),
    ".tex": ("text/x-tex", "latex source document"),
    ".bib": ("text/x-bibtex", "bibtex bibliography"),
    ".lyx": ("application/x-lyx", "lyx document"),
    ".rtf": ("text/rtf", "rich text format document"),
    ".1": ("text/troff", "troff or preprocessor input"),
    ".2": ("text/troff", "troff or preprocessor input"),
    ".3": ("text/troff", "troff or preprocessor input"),
    ".4": ("text/troff", "troff or preprocessor input"),
    ".5": ("text/troff", "troff or preprocessor input"),
    ".6": ("text/troff", "troff or preprocessor input"),
    ".7": ("text/troff", "troff or preprocessor input"),
    ".8": ("text/troff", "troff or preprocessor input"),
    ".9": ("text/troff", "troff or preprocessor input"),
    # Data & Configuration
    ".json": ("application/json", "json data file"),
    ".json5": ("application/json5", "json5 data file"),
    ".jsonl": ("application/x-jsonlines", "json lines data file"),
    ".ndjson": ("application/x-ndjson", "newline delimited json file"),
    ".xml": ("application/xml", "xml document"),
    ".yaml": ("application/yaml", "yaml configuration file"),
    ".yml": ("application/yaml", "yaml configuration file"),
    ".toml": ("application/toml", "toml configuration file"),
    ".ini": ("text/x-ini", "ini configuration file"),
    ".cfg": ("text/x-config", "configuration file"),
    ".conf": ("text/x-config", "configuration file"),
    ".properties": ("text/x-java-properties", "java properties file"),
    ".env": ("text/x-env", "environment variable file"),
    ".csv": ("text/csv", "comma-separated values"),
    ".tsv": ("text/tab-separated-values", "tab-separated values"),
    ".log": ("text/x-log", "log file"),
    ".dat": ("text/x-fixed-field", "data file"),  # Ambiguous, defaults to text here
    ".reg": ("text/x-windows-registry", "windows registry file"),
    ".service": ("text/plain", "systemd service unit file"),
    ".socket": ("text/plain", "systemd socket unit file"),
    ".device": ("text/plain", "systemd device unit file"),
    ".mount": ("text/plain", "systemd mount unit file"),
    ".automount": ("text/plain", "systemd automount unit file"),
    ".swap": ("text/plain", "systemd swap unit file"),
    ".target": ("text/plain", "systemd target unit file"),
    ".path": ("text/plain", "systemd path unit file"),
    ".timer": ("text/plain", "systemd timer unit file"),
    ".slice": ("text/plain", "systemd slice unit file"),
    ".scope": ("text/plain", "systemd scope unit file"),
    # Web Standards
    ".html": ("text/html", "html document"),
    ".htm": ("text/html", "html document"),
    ".xhtml": ("application/xhtml+xml", "xhtml document"),
    ".css": ("text/css", "cascading style sheet"),
    ".scss": ("text/x-scss", "sass style sheet"),
    ".sass": ("text/x-sass", "sass style sheet"),
    ".less": ("text/x-less", "less style sheet"),
    ".styl": ("text/x-stylus", "stylus style sheet"),
    ".svg": ("image/svg+xml", "scalable vector graphics"),
    ".rss": ("application/rss+xml", "rss feed"),
    ".atom": ("application/atom+xml", "atom syndication feed"),
    ".js": ("text/javascript", "javascript source code"),
    ".jsx": ("text/jsx", "react jsx source code"),
    ".ts": ("application/typescript", "typescript source code"),
    ".tsx": ("application/typescript", "typescript jsx source code"),
    ".mjs": ("text/javascript", "modular javascript source code"),
    ".cjs": ("text/javascript", "commonjs source code"),
    # Strictly speaking, it's ".wasm.wat" but currently we only consider the
    # final extension.
    ".wat": ("text/wasm", "webassembly text format"),
    ".coffee": ("text/coffee", "coffeescript source code"),
    # Scripting & Shell
    ".sh": ("application/x-sh", "shell script"),
    ".bash": ("application/x-sh", "bash script"),
    ".zsh": ("application/x-zsh", "zsh script"),
    ".fish": ("application/x-fish", "fish script"),
    ".ksh": ("application/x-ksh", "kornshell script"),
    ".csh": ("application/x-csh", "c shell script"),
    ".bat": ("application/x-bat", "dos batch file"),
    ".cmd": ("application/x-bat", "windows command script"),
    ".ps1": ("text/x-powershell", "powershell script"),
    ".psm1": ("text/x-powershell", "powershell module"),
    ".psd1": ("text/x-powershell", "powershell data file"),
    ".vbs": ("text/vbs", "vbscript file"),
    ".lua": ("text/x-lua", "lua script"),
    ".pl": ("text/x-perl", "perl script"),
    ".pm": ("text/x-perl", "perl module"),
    ".t": ("text/x-perl", "perl test file"),
    ".tcl": ("text/x-tcl", "tcl script"),
    ".awk": ("text/x-awk", "awk script"),
    ".sed": ("text/x-sed", "sed script"),
    # Source Code
    ".py": ("text/x-python", "python source code"),
    ".pyw": ("text/x-python", "python gui source code"),
    ".pyi": ("text/x-python", "python interface file"),
    ".rb": ("text/x-ruby", "ruby source code"),
    ".erb": ("application/x-erb", "embedded ruby template"),
    ".rake": ("text/x-ruby", "ruby rake file"),
    ".gemspec": ("text/x-ruby", "ruby gem specification"),
    ".java": ("text/x-java-source", "java source code"),
    ".kt": ("text/x-kotlin", "kotlin source code"),
    ".kts": ("text/x-kotlin", "kotlin script"),
    ".groovy": ("text/x-groovy", "groovy source code"),
    ".scala": ("text/x-scala", "scala source code"),
    ".clj": ("text/x-clojure", "clojure source code"),
    ".c": ("text/x-c", "c source code"),
    ".h": ("text/x-c", "c header file"),
    ".cpp": ("text/x-c++", "c++ source code"),
    ".hpp": ("text/x-c++", "c++ header file"),
    ".cc": ("text/x-c++", "c++ source code"),
    ".cxx": ("text/x-c++", "c++ source code"),
    ".m": ("text/x-objective-c", "objective-c source code"),
    ".mm": ("text/x-objective-c++", "objective-c++ source code"),
    ".cs": ("text/x-csharp", "c# source code"),
    ".vb": ("text/x-vb", "visual basic source code"),
    ".fs": ("text/x-fsharp", "f# source code"),
    ".fsx": ("text/x-fsharp", "f# script"),
    ".go": ("text/x-go", "go source code"),
    ".rs": ("text/rust", "rust source code"),
    ".swift": ("text/x-swift", "swift source code"),
    ".dart": ("application/vnd.dart", "dart source code"),
    ".d": ("text/x-d", "d source code"),
    ".php": ("application/x-php", "php source code"),
    ".phtml": ("application/x-php", "php template"),
    ".r": ("text/x-r", "r source code"),
    ".rmd": ("text/x-r", "r markdown file"),
    ".jl": ("text/x-julia", "julia source code"),
    ".sql": ("application/x-sql", "sql database script"),
    ".pgsql": ("application/x-sql", "postgresql script"),
    ".psql": ("application/x-sql", "postgresql script"),
    ".f": ("text/x-fortran", "fortran source code"),
    ".for": ("text/x-fortran", "fortran source code"),
    ".f90": ("text/x-fortran", "fortran 90 source code"),
    ".f95": ("text/x-fortran", "fortran 95 source code"),
    ".asm": ("text/x-asm", "assembly source code"),
    ".s": ("text/x-asm", "assembly source code"),
    ".nasm": ("text/x-nasm", "nasm assembly source code"),
    ".elm": ("text/x-elm", "elm source code"),
    ".erl": ("text/x-erlang", "erlang source code"),
    ".hrl": ("text/x-erlang", "erlang header file"),
    ".ex": ("text/x-elixir", "elixir source code"),
    ".exs": ("text/x-elixir", "elixir script"),
    ".hs": ("text/x-haskell", "haskell source code"),
    ".lhs": ("text/x-literate-haskell", "literate haskell source code"),
    ".ml": ("text/x-ocaml", "ocaml source code"),
    ".mli": ("text/x-ocaml", "ocaml interface file"),
    ".lisp": ("text/x-lisp", "lisp source code"),
    ".lsp": ("text/x-lisp", "lisp source code"),
    ".scm": ("text/x-scheme", "scheme source code"),
    ".ada": ("text/x-ada", "ada source code"),
    ".adb": ("text/x-ada", "ada body file"),
    ".ads": ("text/x-ada", "ada specification file"),
    ".pas": ("text/x-pascal", "pascal source code"),
    ".pp": ("text/x-pascal", "pascal source code"),
    ".vhdl": ("text/x-vhdl", "vhdl source code"),
    ".vhd": ("text/x-vhdl", "vhdl source code"),
    ".v": ("text/x-verilog", "verilog source code"),
    ".sv": ("text/x-systemverilog", "systemverilog source code"),
    # Components & Templates
    ".vue": ("text/x-vue", "vue.js component"),
    ".svelte": ("text/x-svelte", "svelte component"),
    ".astro": ("text/x-astro", "astro component"),
    ".ejs": ("text/x-ejs", "embedded javascript template"),
    ".hbs": ("text/x-handlebars", "handlebars template"),
    ".mustache": ("text/x-mustache", "mustache template"),
    ".twig": ("text/x-twig", "twig template"),
    ".jinja": ("text/jinja", "jinja template"),
    ".jinja2": ("text/jinja", "jinja2 template"),
    ".liquid": ("text/x-liquid", "liquid template"),
    ".jsp": ("application/x-jsp", "java server page"),
    ".asp": ("text/asp", "active server page"),
    ".aspx": ("text/asp", "active server page extended"),
    ".razor": ("text/x-razor", "razor view"),
    ".haml": ("text/x-haml", "haml template"),
    ".jade": ("text/x-jade", "jade template"),
    ".pug": ("text/x-pug", "pug template"),
    # Build & Version Control
    ".cmake": ("text/x-cmake", "cmake script"),
    ".makefile": ("text/x-makefile", "makefile script"),
    ".mk": ("text/x-makefile", "makefile script"),
    ".gradle": ("text/x-gradle", "gradle build script"),
    ".pom": ("text/xml", "maven project object model"),
    ".bazel": ("text/x-bazel", "bazel build script"),
    ".dockerfile": ("text/x-dockerfile", "docker build script"),
    ".containerfile": ("text/x-dockerfile", "container build script"),
    ".vagrantfile": ("text/x-ruby", "vagrant configuration file"),
    ".diff": ("text/x-diff", "patch diff file"),
    ".patch": ("text/x-diff", "patch file"),
    ".gitignore": ("text/plain", "git ignore file"),
    ".gitattributes": ("text/plain", "git attributes file"),
    ".gitmodules": ("text/plain", "git modules file"),
    ".lock": ("text/plain", "lock file"),
    # Parsers
    ".y": ("text/x-yacc", "yacc grammar file"),
    ".yacc": ("text/x-yacc", "yacc grammar file"),
    ".yy": ("text/x-yacc", "bison grammar file"),
    ".l": ("text/x-lex", "lex file"),
    ".lex": ("text/x-lex", "lex file"),
    ".ll": ("text/x-lex", "flex file"),
    ".m4": ("text/x-m4", "m4 macro file"),
    ".proto": ("text/x-protobuf", "protocol buffers file"),
    ".thrift": ("application/x-thrift", "thrift definition file"),
    ".g4": ("text/x-antlr", "antlr4 grammar file"),
    # Misc
    ".eps": ("application/postscript", "encapsulated postscript"),
    ".ps": ("application/postscript", "postscript file"),
    ".pem": ("application/x-pem-file", "privacy enhanced mail certificate"),
    ".csr": ("application/pkcs10", "certificate signing request"),
    ".key": ("application/pkcs8", "private key file"),
    ".ics": ("text/calendar", "icalendar file"),
    ".vcf": ("text/vcard", "vcard file"),
    ".srt": ("text/srt", "subrip subtitle file"),
    ".vtt": ("text/vtt", "web video text track"),
    ".sub": ("text/x-microdvd", "microdvd subtitle file"),
}

# Mappings for Text-based Filenames (Extensionless)
# Format: "filename": ("mime/type", "description starting with lowercase")
TEXT_FILENAME_MAP = {
    "*makefile": ("text/x-makefile", "makefile build script"),
    "*dockerfile": ("text/x-dockerfile", "docker build script"),
    "*containerfile": ("text/x-dockerfile", "container build script"),
    "*rakefile": ("text/x-ruby", "ruby rake build script"),
    "*gemfile": ("text/x-ruby", "ruby gem dependency file"),
    "*vagrantfile": ("text/x-ruby", "vagrant configuration file"),
    "*procfile": ("text/plain", "process declaration file"),
    "*license": ("text/plain", "license text"),
    "*readme": ("text/plain", "readme text"),
    "*changelog": ("text/plain", "changelog text"),
    "*copying": ("text/plain", "copyright text"),
    "*os-release": ("text/plain", "OS release data"),
    "*system-release-cpe": ("text/plain", "common platform enumerator OS release data"),
    "*system-release": ("text/plain", "OS release name"),
    "*fedora-release": ("text/plain", "OS release name"),
    "*centos-release": ("text/plain", "OS release name"),
    "*redhat-release": ("text/plain", "OS release name"),
    "*issue": ("text/plain", "login banner message"),
    "*issue.net": ("text/plain", "login banner message"),
    "*motd": ("text/plain", "message of the day"),
    "*fstab": ("text/plain", "static file system information"),
}

# List of systemd unit file extensions for special handling.
SYSTEMD_UNIT_EXTENSIONS = (
    ".service",
    ".socket",
    ".device",
    ".mount",
    ".automount",
    ".swap",
    ".target",
    ".path",
    ".timer",
    ".slice",
    ".scope",
)

# Mappings for Binary Extensions
# Format: ".ext": ("mime/type", "description starting with lowercase")
BINARY_EXTENSION_MAP = {
    # Executables & Libraries
    ".exe": (
        "application/vnd.microsoft.portable-executable",
        "windows executable file",
    ),
    ".bin": ("application/octet-stream", "binary data file"),
    ".elf": ("application/x-elf", "elf executable"),
    ".o": ("application/x-object", "object file"),
    ".so": ("application/x-sharedlib", "shared library"),
    ".dll": ("application/x-msdownload", "dynamic link library"),
    ".class": ("application/java-vm", "java class file"),
    ".pyc": ("application/x-python-code", "compiled python bytecode"),
    ".pyo": ("application/x-python-code", "optimized python bytecode"),
    ".pyd": ("application/x-python-code", "python extension module"),
    ".jar": ("application/java-archive", "java archive"),
    ".war": ("application/java-archive", "web application archive"),
    ".ear": ("application/java-archive", "enterprise application archive"),
    ".msi": ("application/x-msi", "windows installer package"),
    ".deb": ("application/vnd.debian.binary-package", "debian software package"),
    ".rpm": ("application/x-rpm", "red hat package manager file"),
    ".app": ("application/x-apple-diskimage", "macos application bundle"),
    ".dmg": ("application/x-apple-diskimage", "apple disk image"),
    ".pkg": ("application/x-newton-compatible-pkg", "macos package file"),
    # Archives & Compression
    ".zip": ("application/zip", "zip archive"),
    ".tar": ("application/x-tar", "tar archive"),
    ".gz": ("application/gzip", "gzip compressed file"),
    ".bz2": ("application/x-bzip2", "bzip2 compressed file"),
    ".xz": ("application/x-xz", "xz compressed file"),
    ".7z": ("application/x-7z-compressed", "7-zip archive"),
    ".rar": ("application/x-rar-compressed", "rar archive"),
    ".z": ("application/x-compress", "unix compressed file"),
    ".lz": ("application/x-lzip", "lzip compressed file"),
    ".tgz": ("application/gzip", "tarball archive"),
    ".tbz2": ("application/x-bzip2", "bzip2 tarball archive"),
    ".iso": ("application/x-iso9660-image", "disk image file"),
    ".cab": ("application/vnd.ms-cab-compressed", "windows cabinet file"),
    ".arj": ("application/x-arj", "arj archive"),
    ".lzh": ("application/x-lzh", "lzh archive"),
    ".ace": ("application/x-ace-compressed", "ace archive"),
    ".uue": ("text/x-uuencode", "uuencoded file"),
    ".bz": ("application/x-bzip", "bzip compressed file"),
    ".lzma": ("application/x-lzma", "lzma compressed file"),
    ".zst": ("application/zstd", "zstandard compressed file"),
    # Media: Images
    ".jpg": ("image/jpeg", "jpeg image"),
    ".jpeg": ("image/jpeg", "jpeg image"),
    ".png": ("image/png", "portable network graphics image"),
    ".gif": ("image/gif", "gif image"),
    ".bmp": ("image/bmp", "bitmap image"),
    ".ico": ("image/x-icon", "icon file"),
    ".tif": ("image/tiff", "tiff image"),
    ".tiff": ("image/tiff", "tiff image"),
    ".webp": ("image/webp", "webp image"),
    ".raw": ("image/x-panasonic-raw", "raw image data"),
    ".heic": ("image/heic", "heic image"),
    ".psd": ("image/vnd.adobe.photoshop", "photoshop document"),
    ".ai": ("application/illustrator", "adobe illustrator file"),
    ".xcf": ("image/x-xcf", "gimp image file"),
    ".indd": ("application/x-indesign", "indesign document"),
    # Media: Audio
    ".mp3": ("audio/mpeg", "mp3 audio file"),
    ".wav": ("audio/wav", "wav audio file"),
    ".ogg": ("audio/ogg", "ogg vorbis audio file"),
    ".flac": ("audio/flac", "flac audio file"),
    ".aac": ("audio/aac", "aac audio file"),
    ".wma": ("audio/x-ms-wma", "windows media audio"),
    ".m4a": ("audio/mp4", "m4a audio file"),
    ".aiff": ("audio/x-aiff", "aiff audio file"),
    ".mid": ("audio/midi", "midi audio file"),
    ".midi": ("audio/midi", "midi audio file"),
    # Media: Video
    ".mp4": ("video/mp4", "mp4 video file"),
    ".avi": ("video/x-msvideo", "avi video file"),
    ".mkv": ("video/x-matroska", "matroska video file"),
    ".mov": ("video/quicktime", "quicktime video file"),
    ".wmv": ("video/x-ms-wmv", "windows media video"),
    ".flv": ("video/x-flv", "flash video file"),
    ".webm": ("video/webm", "webm video file"),
    ".m4v": ("video/x-m4v", "m4v video file"),
    ".mpg": ("video/mpeg", "mpeg video file"),
    ".mpeg": ("video/mpeg", "mpeg video file"),
    ".3gp": ("video/3gpp", "3gpp video file"),
    ".mts": ("video/mp2t", "hdv video file"),
    ".vob": ("video/mpeg", "dvd video object"),
    # Documents (Binary)
    ".pdf": ("application/pdf", "pdf document"),
    ".epub": ("application/epub+zip", "epub ebook"),
    ".mobi": ("application/x-mobipocket-ebook", "mobipocket ebook"),
    ".azw": ("application/vnd.amazon.ebook", "kindle ebook"),
    ".djvu": ("image/vnd.djvu", "djvu document"),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "word document",
    ),
    ".doc": ("application/msword", "legacy word document"),
    ".xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "excel spreadsheet",
    ),
    ".xls": ("application/vnd.ms-excel", "legacy excel spreadsheet"),
    ".pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "powerpoint presentation",
    ),
    ".ppt": ("application/vnd.ms-powerpoint", "legacy powerpoint presentation"),
    ".xlsm": (
        "application/vnd.ms-excel.sheet.macroenabled.12",
        "macro-enabled excel spreadsheet",
    ),
    ".docm": (
        "application/vnd.ms-word.document.macroenabled.12",
        "macro-enabled word document",
    ),
    ".odt": ("application/vnd.oasis.opendocument.text", "opendocument text"),
    ".ods": (
        "application/vnd.oasis.opendocument.spreadsheet",
        "opendocument spreadsheet",
    ),
    ".odp": (
        "application/vnd.oasis.opendocument.presentation",
        "opendocument presentation",
    ),
    ".odg": ("application/vnd.oasis.opendocument.graphics", "opendocument graphics"),
    # Database & Disk Images
    ".sqlite": ("application/vnd.sqlite3", "sqlite database"),
    ".sqlite3": ("application/vnd.sqlite3", "sqlite database"),
    ".db": ("application/octet-stream", "database file"),
    ".mdb": ("application/x-msaccess", "access database"),
    ".accdb": ("application/x-msaccess", "access database"),
    ".frm": ("application/octet-stream", "mysql table definition"),
    ".ibd": ("application/octet-stream", "mysql innodb tablespace"),
    ".dbf": ("application/x-dbf", "database file"),
    ".img": ("application/octet-stream", "disk image"),
    ".vmdk": ("application/x-vmware-vmdk", "vmware virtual disk"),
    ".vdi": ("application/x-virtualbox-vdi", "virtualbox virtual disk"),
    ".qcow2": ("application/x-qemu-disk", "qemu copy-on-write disk"),
    ".hdd": ("application/octet-stream", "virtual hard disk"),
    # Miscellaneous / System
    ".ds_store": ("application/octet-stream", "macos folder metadata"),
    ".thumbs.db": ("application/octet-stream", "windows thumbnail cache"),
    ".lnk": ("application/x-ms-shortcut", "windows shortcut"),
    ".sys": ("application/octet-stream", "windows system file"),
    ".drv": ("application/octet-stream", "device driver"),
    ".cur": ("image/x-win-bitmap", "windows cursor"),
    ".ttf": ("font/ttf", "truetype font"),
    ".otf": ("font/otf", "opentype font"),
    ".woff": ("font/woff", "web open font format"),
    ".woff2": ("font/woff2", "web open font format 2"),
    ".eot": ("application/vnd.ms-fontobject", "embedded opentype font"),
}

# Mappings for Binary Filenames/Patterns
# Format: "pattern": ("mime/type", "description starting with lowercase")
BINARY_FILENAME_MAP = {
    "*.so.*": ("application/x-sharedlib", "versioned shared library"),
    "*vmlinuz*": ("application/x-linux-kernel", "linux kernel executable"),
    "*initrd*": ("application/x-cpio", "initial ramdisk image"),
    "*initramfs*": ("application/x-cpio", "initial ramdisk image"),
    "*core.*": ("application/x-coredump", "system core dump"),
    "*swapfile": ("application/octet-stream", "system swap file"),
    "*.git/objects/*": ("application/x-git-object", "git internal object"),
    "*.git/index": ("application/x-git-index", "git index file"),
}

BINARY_FILE_PATHS = {
    # Directories strictly for binaries/libraries on Modern Linux
    "/bin": ("application/x-executable", "executable"),
    "/sbin": ("application/x-executable", "executable"),
    "/lib": ("application/x-sharedlib", "shared library"),
    "/lib32": ("application/x-sharedlib", "shared library"),
    "/lib64": ("application/x-sharedlib", "shared library"),
    "/libx32": ("application/x-sharedlib", "shared library"),
    "/usr/bin": ("application/x-executable", "executable"),
    "/usr/sbin": ("application/x-executable", "executable"),
    "/usr/lib": ("application/x-sharedlib", "shared library"),
    "/usr/lib32": ("application/x-sharedlib", "shared library"),
    "/usr/lib64": ("application/x-sharedlib", "shared library"),
    "/usr/libexec": ("application/x-executable", "executable"),
    "/usr/local/bin": ("application/x-executable", "executable"),
    "/usr/local/sbin": ("application/x-executable", "executable"),
    "/usr/local/lib": ("application/x-sharedlib", "shared library"),
    "/usr/local/lib64": ("application/x-sharedlib", "shared library"),
}


def _generic_guess_file(
    file_path: Path,
    extension_map: Dict[str, Tuple[str, str]],
    filename_map: Dict[str, Tuple[str, str]],
    encoding: str,
) -> Optional[Tuple[str, str, str]]:
    """
    Attempt to guess a file's MIME type and description based on the file
    name and extension.

    :param file_path: A ``Path`` instance containing the file path to check.
    :type file_path: ``Path``
    :param extension_map: A map of ".extension": (mime_type, description)
                          tuples to use.
    :type extension_map: ``Dict[str, Tuple[str, str]]``
    :param filename_map: A map of "filename": (mime_type, description)
                         tuples to use.
    :returns: A 3-tuple containing (mime_type, description, encoding) if the
              type could be guessed or ``None`` otherwise.
    :rtype: ``Optional[Tuple[str, str, str]]``
    """
    # Check exact filename match (case-insensitive) for extensionless files
    for file_name_pattern in filename_map.keys():
        if Path(file_path.name.lower()).match(file_name_pattern):
            return (*filename_map[file_name_pattern], encoding)

    extension = file_path.suffix

    # Check extension match
    extension = extension.lower()
    if extension and extension in extension_map:
        return (*extension_map[extension], encoding)

    return None


def _guess_text_file(file_path: Path) -> Optional[Tuple[str, str, str]]:
    """
    Attempt to guess a text file's MIME type and description based on the file
    name and extension.

    :param file_path: A ``Path`` instance containing the file path to check.
    :type file_path: ``Path``
    :returns: A 3-tuple containing (mime_type, description, encoding) if the
              type could be guessed or ``None`` otherwise.
    :rtype: ``Optional[Tuple[str, str, str]]``
    """
    return _generic_guess_file(
        file_path, TEXT_EXTENSION_MAP, TEXT_FILENAME_MAP, "utf-8"
    )


def _guess_binary_file(file_path: Path) -> Optional[Tuple[str, str, str]]:
    """
    Attempt to guess a binary file's MIME type and description based on the
    file name and extension.

    :param file_path: A ``Path`` instance containing the file path to check.
    :type file_path: ``Path``
    :returns: A 3-tuple containing (mime_type, description, encoding) if the
              type could be guessed or ``None`` otherwise.
    :rtype: ``Optional[Tuple[str, str, str]]``
    """
    guess = _generic_guess_file(
        file_path, BINARY_EXTENSION_MAP, BINARY_FILENAME_MAP, "binary"
    )

    if guess is not None:
        return guess

    abs_parent_path = file_path.absolute().parent
    abs_parent_str = str(abs_parent_path)
    if abs_parent_str in BINARY_FILE_PATHS:
        # Honour known text-like patterns even under binary-heavy directories.
        text_guess = _guess_text_file(file_path)
        if text_guess is not None:
            return text_guess
        return (*BINARY_FILE_PATHS[abs_parent_str], "binary")
    return None


def _guess_file(file_path: Path) -> Tuple[str, str, str]:
    """
    Attempt to guess a file's MIME type and description based on the file name
    and extension.

    :param file_path: A ``Path`` instance containing the file path to check.
    :type file_path: ``Path``
    :returns: A 3-tuple containing (mime_type, description, encoding).
    :rtype: ``Tuple[str, str, str]``
    """
    guess = _guess_binary_file(file_path)
    if guess is not None:
        return guess

    guess = _guess_text_file(file_path)
    if guess is not None:
        return guess

    return ("application/octet-stream", "unknown file type", "binary")


class FileTypeCategory(Enum):
    """
    Enum for file type categories.
    """

    TEXT = "text"
    BINARY = "binary"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    EXECUTABLE = "executable"
    CONFIG = "config"
    LOG = "log"
    DATABASE = "database"
    DOCUMENT = "document"
    DIRECTORY = "directory"
    SOURCE_CODE = "source_code"
    CERTIFICATE = "certificate"
    SYMLINK = "symlink"
    BLOCK = "block"
    CHAR = "char"
    SOCK = "socket"
    FIFO = "FIFO"
    UNKNOWN = "unknown"


class FileTypeInfo:
    """
    Class representing file type information and encoding.
    """

    TEXT_DOCUMENTS = (
        "application/rtf",
        "application/x-lyx",
    )

    def __init__(
        self,
        mime_type: str,
        description: str,
        category: FileTypeCategory,
        encoding: Optional[str] = None,
    ):
        """
        Initialise a new ``FileTypeInfo`` object.

        :param mime_type: The detected MIME type.
        :type mime_type: ``str``
        :param description: Type description returned by magic.
        :type description: ``str``
        :param category: File type category.
        :type category: ``FileTypeCategory``
        :param encoding: Optional file encoding.
        :type encoding: ``Optional[str]``
        """
        self.mime_type = mime_type
        self.description = description
        self.category = category
        self.encoding = encoding
        self.is_text_like = category in (
            FileTypeCategory.TEXT,
            FileTypeCategory.CONFIG,
            FileTypeCategory.LOG,
            FileTypeCategory.SOURCE_CODE,
        ) or (
            category == FileTypeCategory.DOCUMENT
            and (mime_type.startswith("text/") or (mime_type in self.TEXT_DOCUMENTS))
        )

    def __str__(self):
        """
        Return a string representation of this ``FileTypeInfo`` object.

        :returns: A human readable string describing this instance.
        :rtype: ``str``
        """
        return (
            f"MIME type: {self.mime_type}, "
            f"Category: {self.category.value}, "
            f"Encoding: {self.encoding if self.encoding else 'unknown'}, "
            f"Description: {self.description}"
        )


class FileTypeDetector:
    """
    Detect file types using ``magic`` from python3-file-magic.
    """

    # Custom rules for better categorization. Black likes to break this
    # so turn off formatting for the category_rules dict.
    # fmt: off
    category_rules: ClassVar[Dict[str, FileTypeCategory]] = {
        # --- Archives & Compression ---
        "application/zip": FileTypeCategory.ARCHIVE,
        "application/x-tar": FileTypeCategory.ARCHIVE,
        "application/gzip": FileTypeCategory.ARCHIVE,
        "application/x-gzip": FileTypeCategory.ARCHIVE,
        "application/x-bzip2": FileTypeCategory.ARCHIVE,
        "application/x-lzip": FileTypeCategory.ARCHIVE,
        "application/x-lzma": FileTypeCategory.ARCHIVE,
        "application/x-xz": FileTypeCategory.ARCHIVE,
        "application/zstd": FileTypeCategory.ARCHIVE,
        "application/x-7z-compressed": FileTypeCategory.ARCHIVE,
        "application/x-rar": FileTypeCategory.ARCHIVE,
        "application/x-rar-compressed": FileTypeCategory.ARCHIVE,
        "application/java-archive": FileTypeCategory.ARCHIVE,
        "application/x-iso9660-image": FileTypeCategory.ARCHIVE,
        "application/vnd.android.package-archive": FileTypeCategory.ARCHIVE,
        # --- Executables & Libraries ---
        "application/x-executable": FileTypeCategory.EXECUTABLE,
        "application/x-elf": FileTypeCategory.EXECUTABLE,
        "application/x-sharedlib": FileTypeCategory.EXECUTABLE,
        "application/x-pie-executable": FileTypeCategory.EXECUTABLE,
        "application/x-mach-binary": FileTypeCategory.EXECUTABLE,
        "application/x-dosexec": FileTypeCategory.EXECUTABLE,
        "application/vnd.microsoft.portable-executable": FileTypeCategory.EXECUTABLE,
        "application/x-msdownload": FileTypeCategory.EXECUTABLE,
        "application/x-object": FileTypeCategory.EXECUTABLE,
        # --- Documents (Office & PDF) ---
        "application/pdf": FileTypeCategory.DOCUMENT,
        "application/msword": FileTypeCategory.DOCUMENT,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            FileTypeCategory.DOCUMENT,
        "application/vnd.ms-excel": FileTypeCategory.DOCUMENT,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            FileTypeCategory.DOCUMENT,
        "application/vnd.ms-powerpoint": FileTypeCategory.DOCUMENT,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            FileTypeCategory.DOCUMENT,
        "application/vnd.oasis.opendocument.text": FileTypeCategory.DOCUMENT,
        "application/vnd.oasis.opendocument.spreadsheet": FileTypeCategory.DOCUMENT,
        "application/rtf": FileTypeCategory.DOCUMENT,
        "text/rtf": FileTypeCategory.DOCUMENT,
        "text/markdown": FileTypeCategory.DOCUMENT,
        "text/asciidoc": FileTypeCategory.DOCUMENT,
        "text/x-nfo": FileTypeCategory.DOCUMENT,
        "text/x-tex": FileTypeCategory.DOCUMENT,
        "text/x-bibtex": FileTypeCategory.DOCUMENT,
        "text/troff": FileTypeCategory.DOCUMENT,
        # --- Configuration & Data Serialization ---
        "application/json": FileTypeCategory.CONFIG,
        "application/ld+json": FileTypeCategory.CONFIG,
        "application/xml": FileTypeCategory.CONFIG,
        "text/xml": FileTypeCategory.CONFIG,
        "application/yaml": FileTypeCategory.CONFIG,
        "text/yaml": FileTypeCategory.CONFIG,
        "application/x-yaml": FileTypeCategory.CONFIG,
        "text/x-toml": FileTypeCategory.CONFIG,
        "application/toml": FileTypeCategory.CONFIG,
        "text/x-ini": FileTypeCategory.CONFIG,  # Unofficial but common
        # --- Databases ---
        "application/vnd.sqlite3": FileTypeCategory.DATABASE,
        "application/x-sqlite3": FileTypeCategory.DATABASE,
        "application/x-dbf": FileTypeCategory.DATABASE,
        "application/mbox": FileTypeCategory.DATABASE,  # Email storage
        # --- Source Code / Web Standards ---
        "application/javascript": FileTypeCategory.SOURCE_CODE,
        "application/x-javascript": FileTypeCategory.SOURCE_CODE,
        "text/javascript": FileTypeCategory.SOURCE_CODE,
        "text/x-python": FileTypeCategory.SOURCE_CODE,
        "text/x-script.python": FileTypeCategory.SOURCE_CODE,
        "text/x-shellscript": FileTypeCategory.SOURCE_CODE,
        "application/x-sh": FileTypeCategory.SOURCE_CODE,
        "text/x-c": FileTypeCategory.SOURCE_CODE,
        "text/x-c++": FileTypeCategory.SOURCE_CODE,
        "text/x-java-source": FileTypeCategory.SOURCE_CODE,
        "text/html": FileTypeCategory.SOURCE_CODE,
        "text/css": FileTypeCategory.SOURCE_CODE,
        "text/x-diff": FileTypeCategory.SOURCE_CODE,
        "text/x-makefile": FileTypeCategory.SOURCE_CODE,
        "application/x-zsh": FileTypeCategory.SOURCE_CODE,
        "application/x-fish": FileTypeCategory.SOURCE_CODE,
        "application/x-ksh": FileTypeCategory.SOURCE_CODE,
        "application/x-csh": FileTypeCategory.SOURCE_CODE,
        "application/x-bat": FileTypeCategory.SOURCE_CODE,
        "text/x-powershell": FileTypeCategory.SOURCE_CODE,
        "text/vbs": FileTypeCategory.SOURCE_CODE,
        "text/x-lua": FileTypeCategory.SOURCE_CODE,
        "text/x-perl": FileTypeCategory.SOURCE_CODE,
        "text/x-tcl": FileTypeCategory.SOURCE_CODE,
        "text/x-awk": FileTypeCategory.SOURCE_CODE,
        "text/x-sed": FileTypeCategory.SOURCE_CODE,
        # --- Certificates & Keys ---
        "application/x-x509-ca-cert": FileTypeCategory.CERTIFICATE,
        "application/x-pem-file": FileTypeCategory.CERTIFICATE,
        "application/pkix-cert": FileTypeCategory.CERTIFICATE,
        # --- System Inodes ---
        "inode/directory": FileTypeCategory.DIRECTORY,
        "inode/blockdevice": FileTypeCategory.BLOCK,
        "inode/chardevice": FileTypeCategory.CHAR,
        "inode/fifo": FileTypeCategory.FIFO,
        "inode/socket": FileTypeCategory.SOCK,
        "inode/symlink": FileTypeCategory.SYMLINK,
        # --- Generic Prefixes (Fallbacks) ---
        "text/": FileTypeCategory.TEXT,
        "image/": FileTypeCategory.IMAGE,
        "audio/": FileTypeCategory.AUDIO,
        "video/": FileTypeCategory.VIDEO,
        "font/": FileTypeCategory.BINARY,
        "model/": FileTypeCategory.BINARY,
    }
    # fmt: on

    def detect_file_type(self, file_path: Path, use_magic=False) -> FileTypeInfo:
        """
        Detect comprehensive file type information, optionally using
        python-magic for MIME type detection.

        :param file_path: The path to the file to inspect.
        :type file_path: ``Path``.
        :returns: File type information for ``file_path``.
        :rtype: ``FileTypeInfo``
        """
        if use_magic:
            # c9s magic does not have magic.error
            if hasattr(magic, "error"):
                magic_errors = (magic.error, OSError, ValueError)
            else:
                magic_errors = (OSError, ValueError)

            try:
                fm = magic.detect_from_filename(str(file_path))
                mime_type = fm.mime_type
                encoding = fm.encoding
                description = fm.name

                category = self._categorize_file(mime_type, file_path)

                return FileTypeInfo(mime_type, description, category, encoding)

            except magic_errors as err:
                _log_warn("Error detecting file type for %s: %s", str(file_path), err)
                return FileTypeInfo(
                    "application/octet-stream", "unknown", FileTypeCategory.UNKNOWN
                )
        else:
            return self._guess_file_type(file_path)

    def _categorize_file(self, mime_type: str, file_path: Path) -> FileTypeCategory:
        """
        Categorize file based on MIME type and path patterns.

        :param mime_type: Detected file MIME type.
        :type mime_type: ``str``
        :param file_path: Path to the file to categorize.
        :type file_path: ``Path``
        :returns: File type categorization.
        :rtype: ``FileTypeCategory``
        """
        mime_type = mime_type.lower()
        # Check path-based rules for common locations
        path_str = str(file_path).lower()
        if "/log/" in path_str or path_str.endswith(".log"):
            return FileTypeCategory.LOG
        if path_str.startswith("/etc/") or path_str.endswith(".conf"):
            return FileTypeCategory.CONFIG
        if "database" in path_str or path_str.endswith((".db", ".sqlite")):
            return FileTypeCategory.DATABASE

        # Special rules for systemd unit files outside /etc
        if file_path.suffix in SYSTEMD_UNIT_EXTENSIONS:
            return FileTypeCategory.CONFIG

        # Check MIME type rules
        for pattern, category in self.category_rules.items():
            if mime_type.startswith(pattern):
                return category

        return FileTypeCategory.BINARY

    def _guess_file_type(self, file_path: Path) -> FileTypeInfo:
        """
        Attempt to guess file type based on extension and file path without
        using python-magic.

        :param file_path: The path to guess file type for.
        :type file_path: ``Path``
        :returns: A ``FileTypeInfo`` object with a best-effort guess of the
                  file type.
        :rtype: ``FileTypeInfo``
        """
        guess = _guess_file(file_path)
        mime_type, description, encoding = guess
        category = self._categorize_file(mime_type, file_path)
        return FileTypeInfo(mime_type, description, category, encoding)
