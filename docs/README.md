# PanPath Documentation

This directory contains the source files for PanPath's documentation, built with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).

## Building Locally

### Prerequisites

Install documentation dependencies:

```bash
pip install -e .[docs]
```

### Serve Documentation

Start a local development server:

```bash
mkdocs serve
```

Then open http://127.0.0.1:8000 in your browser.

The site will automatically reload when you make changes to the documentation files.

### Build Documentation

Build the static site:

```bash
mkdocs build
```

The built site will be in the `site/` directory.

## Structure

```
docs/
├── index.md                    # Home page
├── getting-started/            # Getting started guides
│   ├── installation.md
│   ├── quick-start.md
│   └── concepts.md
├── guide/                      # User guides
│   ├── local-paths.md
│   ├── cloud-storage.md
│   ├── async-operations.md
│   ├── bulk-operations.md
│   ├── cross-storage.md
│   ├── path-operations.md
│   └── error-handling.md
├── providers/                  # Cloud provider guides
│   ├── s3.md
│   ├── gcs.md
│   └── azure.md
├── advanced/                   # Advanced topics
│   ├── configuration.md
│   ├── custom-clients.md
│   ├── testing.md
│   └── performance.md
├── api/                        # API reference
│   ├── pan-path.md
│   ├── async-pan-path.md
│   ├── local.md
│   ├── s3.md
│   ├── gcs.md
│   ├── azure.md
│   └── exceptions.md
├── migration/                  # Migration guides
│   ├── from-pathlib.md
│   └── from-cloudpathlib.md
└── about/                      # About section
    ├── changelog.md
    ├── contributing.md
    └── license.md
```

## Writing Documentation

### Markdown Syntax

We use Python-Markdown with several extensions. See [mkdocs.yml](../mkdocs.yml) for the full list.

#### Code Blocks

Use fenced code blocks with syntax highlighting:

````markdown
```python
from panpath import PanPath

path = PanPath("s3://bucket/file.txt")
content = path.read_text()
```
````

#### Tabs

Use tabs for alternative content:

````markdown
=== "Sync"
    ```python
    path = PanPath("s3://bucket/file.txt")
    content = path.read_text()
    ```

=== "Async"
    ```python
    path = AsyncPanPath("s3://bucket/file.txt")
    content = await path.read_text()
    ```
````

#### Admonitions

Use admonitions for notes and warnings:

```markdown
!!! note
    This is an important note.

!!! warning
    Be careful with this operation.

!!! tip
    Here's a helpful tip.
```

#### API Documentation

Use mkdocstrings to auto-generate API docs:

```markdown
::: panpath.router.PanPath
    options:
      show_root_heading: true
      show_source: true
```

### Style Guide

- Use clear, concise language
- Include code examples for all features
- Use proper Markdown formatting
- Add cross-references to related sections
- Test all code examples

## Deployment

Documentation is automatically built and deployed to GitHub Pages when changes are pushed to the `main` branch.

The deployment is handled by the `.github/workflows/docs.yml` workflow.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for general contribution guidelines.

When contributing documentation:

1. Follow the existing structure and style
2. Test locally with `mkdocs serve`
3. Ensure all code examples work
4. Add to navigation in `mkdocs.yml` if needed
5. Submit a pull request

## Resources

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [mkdocstrings](https://mkdocstrings.github.io/)
- [Python-Markdown Extensions](https://python-markdown.github.io/extensions/)
