#!/usr/bin/env python3
"""
Checks that every Java snippet in the blog post still matches this repo's source.

The post inlines code so it reads without a checkout, which creates a drift risk:
edit a connector, and the article silently starts lying. This compares every
```java block in the post against the real files, ignoring comments and whitespace.

Run from the repo root:
    python3 examples/check_blog_code.py [path/to/post.md]
"""
import glob
import os
import re
import sys

DEFAULT_POST = "companion_guide.md"
SRC_GLOB = "src/main/java/com/example/dsv2lab/**/*.java"


def normalize(text):
    """Strip line comments and collapse whitespace, so formatting is not compared."""
    text = re.sub(r"//.*$", "", text, flags=re.M)
    return re.sub(r"\s+", " ", text).strip()


def main():
    post_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_POST
    if not os.path.exists(post_path):
        print(f"Companion guide not found: {post_path}")
        print("Run from the demo root, or pass the path as an argument.")
        return 1

    post = open(post_path, encoding="utf-8").read()
    blocks = re.findall(r"```java\n(.*?)```", post, re.S)

    sources = glob.glob(SRC_GLOB, recursive=True)
    if not sources:
        print(f"No sources matched {SRC_GLOB}. Run from the repo root.")
        return 1
    haystack = normalize("\n".join(open(f).read() for f in sources))

    print(f"Checking {len(blocks)} Java blocks in {os.path.basename(post_path)} "
          f"against {len(sources)} source files")

    missing = []
    checked = 0
    for i, block in enumerate(blocks, 1):
        lines = [
            line for line in block.split("\n")
            if line.strip()
            and not line.strip().startswith(("//", "*", "/*", "}"))
            and "..." not in line
            and len(normalize(line)) > 25
        ]
        gone = [line for line in lines if normalize(line) not in haystack]
        checked += len(lines)
        status = "OK  " if not gone else "DIFF"
        print(f"  {status} block {i} ({len(lines)} lines)")
        for line in gone:
            print(f"        {line.strip()[:90]}")
            missing.append((i, line.strip()))

    print(f"\n{checked} code lines checked, {len(missing)} not found in source")
    if missing:
        print("\nThe post and the code have drifted. Update whichever is wrong.")
        return 1
    print("Post and code agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
