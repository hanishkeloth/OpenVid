# Contributing to OpenVid

Open an issue for reproducible bugs or discuss a substantial feature before implementing it. Include OS, Python/Node versions, provider/model if relevant, and steps to reproduce. Remove keys, workspace cookies, signed URLs, private scripts and customer content from logs.

Set up from the README, install `requirements-dev.txt`, and run the Python and JavaScript tests. Provider tests should use fakes by default. Live paid calls must be intentional, use your authorised account, and record request IDs. Do not add automatic retries that can duplicate paid generations.

Keep credentials server-side. New providers need explicit capabilities, validated inputs, sanitised failures, and unsupported-field documentation. Preserve workspace isolation and optimistic document revisions. Never render user-uploaded HTML as executable compositions.

In pull requests, describe the user-visible change and checks run. Application contributions are AGPL-3.0-only. Assets need their own provenance and redistribution terms; the code licence does not cover third-party media.
