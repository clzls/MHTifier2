#!/usr/bin/env python3
# Encoding: UTF-8
"""mhtifier.py
Un/packs an MHT "archive" into/from separate files, writing/reading them in directories to match their Content-Location.

Uses part's Content-Location to name paths, or index.html for the root HTML.
Content types will be assigned according to registry of MIME types mapping to file name extensions.
"""

# Standard library modules do the heavy lifting. Ours is all simple stuff.
import email
import email.message
import email.policy
import logging
import mimetypes
import os
import sys
import argparse

LogLvlNotice = 25


def main():
    """Convert MHT file given as command line argument (or stdin?) to files and directories in the current directory.

    Usage:
      cd foo-unpacked/
      mhtifier.py ../foo.mht
    """
    parser = argparse.ArgumentParser(
        description="Extract MHT archive into new directory.")
    parser.add_argument(
        "mht", metavar="MHT",
        help='path to MHT file, use "-" for stdin/stdout.')
    parser.add_argument(
        "d", metavar="DIR",
        help="directory to create to store parts in, or read them from.")  # ??? How to make optional, default to current dir?

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "-p", "--pack",
        action="store_true",
        help="pack file under DIR into an MHT.")
    mode.add_argument(
        "-u", "--unpack",
        action="store_true",
        help="unpack MHT into a new DIR.")

    parser.add_argument(
        "--fix-html-7bit",
        action="store_true",
        help="Try to fix abnormal html encodings.")
    parser.add_argument(
        "--first-only",
        action="store_true",
        help="Only extract 1 file, hopefully the main html.")
    parser.add_argument(
        "-o", "--overwrite",
        action="store_true",
        help="Overwrite exist files without prompt.")
    parser.add_argument(
        "--mht-enc",
        action="store",
        help="The encoding of the MHTML file.",
        default='utf-8-sig')
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()  # --help is built-in.

    logging.addLevelName(LogLvlNotice, 'NOTICE')
    if args.quiet:
        lvl = LogLvlNotice
    elif args.verbose:
        lvl = logging.DEBUG
    else:
        lvl = logging.INFO
    logging.basicConfig(level=lvl)

    _modLog = logging.getLogger(__name__)

    encoding = args.mht_enc
    fixHtml7bit = args.fix_html_7bit
    firstOnly = args.first_only
    overwrite = args.overwrite

    # File name or stdin/stdout?
    if args.mht == "-":
        mht = sys.stdout if args.pack else sys.stdin
    else:
        if args.pack and os.path.exists(args.mht) and not overwrite:
            # Refuse to overwrite MHT file.
            _modLog.error("MHT file exists, won't overwrite.")
            sys.exit(-2)
        mht = open(args.mht, "w" if args.pack else "r", encoding=encoding)

    # New directory?
    if args.unpack:
        try:
            os.makedirs(args.d)
        except FileExistsError:
            if overwrite:
                _modLog.warning('Dir exists.')
        pass

    # Change directory so paths (content-location) are relative to index.html.
    os.chdir(args.d)

    policy = email.policy.SMTPUTF8

    # Un/pack?
    if args.unpack:
        _modLog.info("Unpacking...")

        # Read entire MHT archive -- it's a multipart(/related) message.
        # After Python 3.2, it can decide how to load this file itself.
        a = email.message_from_file(mht, policy=policy)

        partsIt = a.iter_parts()  # Multiple parts, usually?
        if partsIt is None:
            partsIt = [a]  # Single part, convert to list.

        partsLen = 0
        # Save all parts to files.
        for p in partsIt:  # walk() for a tree, but I'm guessing MHT is never nested?
            # ??? cs = p.get_charset() # Expecting "utf-8" for root HTML, None for all other parts.
            # String coerced to lower case of the form maintype/subtype, else get_default_type().
            ct = p.get_content_type()
            # File path. Expecting root HTML is only part with no location.
            fp = p.get("content-location") or "index.html"

            content = p.get_content()
            if isinstance(content, str):
                if fixHtml7bit:
                    content = p.get_payload()
                # Re-encode strings (html, hopefully) into UTF-8 bytes.
                content = content.encode('utf-8')

            _modLog.debug(
                "Writing %s to %s, %d bytes...",
                ct, fp, len(content))

            # Create directories as necessary.
            if os.path.dirname(fp):
                os.makedirs(os.path.dirname(fp), exist_ok=True)

            # Save part's body to a file.
            open(fp, "wb").write(content)
            partsLen += 1

            if firstOnly:
                break

        _modLog.info("Done.")
        _modLog.info("Unpacked {} files.".format(partsLen))

    else:
        _modLog.info("Packing...")

        # Create archive as multipart message.
        a = email.message.EmailMessage(policy)
        a["MIME-Version"] = "1.0"
        a.make_related()
        a.set_param("type", "text/html")

        # Walk current directory.
        partsLen = 0
        for (root, _, files) in os.walk("."):
            # Create message part from each file and attach them to archive.
            for f in files:
                p = os.path.join(root, f).lstrip("./")
                m = email.message.EmailMessage(policy)
                # Encode and set type of part.
                t = mimetypes.guess_type(f)[0]
                if t:
                    m.set_param("type", t)
                    maintype, subtype = t.split('/')

                _modLog.debug("Reading %s as %s...", p, t)

                if t and t.startswith("text/"):
                    m.set_content(open(p, "rt").read(), subtype=subtype)
                else:
                    if not t:
                        maintype = 'application'
                        subtype = 'octet-stream'
                    m.set_content(open(p, "rb").read(),
                                  maintype=maintype, subtype=subtype)

                # Only set charset for index.html to UTF-8, and no location.
                if f == "index.html":
                    m.set_charset("utf-8")
                else:
                    m["Content-Location"] = p
                a.attach(m)
                partsLen += 1

        # Write MHT file.
        # ??? verify index.html is present!?
        # Not an mbox file, so we don't need to mangle "From " lines, I guess?
        mht.write(a.as_string(unixfrom=False))

        _modLog.info("Done.")
        _modLog.info("Packed {} files.".format(partsLen))


if __name__ == "__main__":
    main()
