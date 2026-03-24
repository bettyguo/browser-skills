---
name: upload-download-file
description: Uploads a local file to an HTML5 file input, or triggers a download and captures the resulting path. Composes with multi-step-form for file-attaching workflows.
version: 0.1.0
allowed-tools: [wait_for_selector, fill, click, wait, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "input[type='file']"
    - "[role='button'][aria-label*='upload' i]"
  flake_rate_target: 0.08
  exercised_on:
    - httpbin-forms
    - the-internet-herokuapp
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
---

# Upload / Download File

## When to invoke

The user task requires uploading a local file or capturing a download.
The agent provides the file path in `vars.file_path` (uploads) or a
target directory in `vars.download_dir` (downloads).

The matcher hits this skill when an `<input type="file">` is present
on the page.

## Recipe

### Upload mode (`vars.mode = "upload"` or auto-detected via input[type=file] presence)

1. wait_for_selector selector="input[type='file']" state=attached timeout=5s
2. fill selector="input[type='file']" value="$vars.file_path"
3. wait extra=300ms

### Download mode (`vars.mode = "download"`)

Downloads in headless browsers route through the browser's download
API; this skill stubs the recipe for now and defers to the runner's
download event handler (M5 wiring).

## Success criteria (upload mode)

- assert input_type_file_has_files selector="input[type='file']"

## When NOT to use

- File-attach widgets that don't use a real `<input type="file">` (proprietary
  drag-and-drop). Vision fallback or a per-site bespoke approach.
- Multi-file uploads requiring drag-drop reorder. Not in v0.1.

## Known failures

- **Sites that gate file inputs behind a click-to-reveal:** the input
  isn't `attached` until a wrapper button is clicked. Run a `click`
  primitive first; spec your agent to chain.
- **Server-side validation of file size / type:** the skill submits;
  the agent reads validation errors via the form's error-message
  recipe.
- **macOS sandboxing of Playwright file uploads:** if Playwright runs
  in a security context that can't read `~/Documents`, uploads
  silently fail. Document in the agent's expected setup.

## Related skills

- `fill-multi-step-form` — common parent flow
- `verify-page-loaded` — run before to ensure the file input has rendered
