---
version: 1
---

# Fern/Platform Rules

The content model defines what a documentation page *is*. Fern defines how that page is published, navigated, displayed, and exposed to search/AI.

## URL and slug rules

**Do not use frontmatter `slug` by default.**

Let `docs.yml` determine URL structure. Use explicit navigation-level slugs only when we have a reason to preserve or improve a URL.

## Markdown heading rules

Fern automatically creates the page's H1. **Do not add another `#` heading** inside an MDX file. The body starts at H2.

## Internal links have a Fern-specific rule

Inside MDX pages, don't use:

\[Authentication\](../get-started/authentication.mdx)

Fern specifically does **not** support file-relative paths for inter-page links.

Use the published site path:

\[Authentication\](/get-started/authentication)

For generated API endpoints, Fern has an even better mechanism:

\[Search endpoint\](api:POST/search)

That lets Fern resolve the API reference link at build time instead of us hardcoding its generated URL. ([Build With Fern](https://buildwithfern.com/learn/docs/writing-content/markdown-basics))

## Reusable Fern components

The important rule is **components should clarify the semantic structure, not decorate the page**.

### Cards: overview navigation

Use cardgroups for overview navigation to related areas.

```html
<CardGroup cols={2}>
    <Card>
    ...
    </Card>
</CardGroup>
```

### Steps: sequential instructions

Use `<Steps>` for sequential instructions in tutorials and how-to pages.


### CodeBlocks vs Tabs

Choose between `<CodeBlocks>` and `<Tabs>` based on what varies between the grouped snippets.

**Use `<CodeBlocks>` when the snippets differ by programming language.** Tab names are generated automatically from the language label after the fence, so you don't write titles. This is the default for showing the same operation across SDKs.

````html
<CodeBlocks>
```python Python
    ...
```
```typescript cURL
    ...
```
</CodeBlocks>
````

**Use `<Tabs>` when the snippets differ by anything other than (just) language** (ecosystem, concept, etc.), or when the tabs share one language and so can't be distinguished by a language label.

```html
<Tabs>
    <Tab title="Something">
    ...
    </Tab>
    <Tab title="Something else">
    ...
    </Tab>
</Tabs>
```

```html
<Tabs>
    <Tab title="Python">
        ```python
            ...
        ```
        Some other content such as a table
        
    </Tab>
    <Tab title="cURL">
        ```cURL
            ...
        ```
        Some other content such as a table
    </Tab>
</Tabs>
```

Additional conventions:
- Don't wrap a single snippet in `<CodeBlocks>` just for styling; use a plain fenced code block.

### Callouts: important caveat

```html
<Info>For genuine context the reader would otherwise miss.</Info>

<Warning>Only for production-blocking issues where user action may cause failure and might be irreversible.</Warning>

<Note>For highlighting helpful context or supplementary information.</Note>

<Error>This callout should only be used in API reference docs for indicating a potential error or missing information that must be added.</Error>
```

### Accordion: secondary material

Use `<Accordion>` sparingly for optional secondary material. Accordions should not hide information someone needs to complete a procedure.

### Schema: data models

Use `<Schema>` for API data models in a guide.

### Files: repo directory
 
Use `<Files>` for repository/directory examples.

## Reusable snippets

Fern has native single-sourcing. ([Build With Fern](https://buildwithfern.com/learn/docs/writing-content/reusable-snippets?utm_source=chatgpt.com))

Create snippets in fern/docs/snippets and reuse them with:

\<Markdown src="/snippets/api-key-prerequisite.mdx" /\>

Snippets can also accept parameters. Fern resolves the snippet path from the `fern/` directory root. 

Rule:

* Use snippets for content that is genuinely identical across pages—standard warnings, repeated prerequisites, constants, or repeated instructions.

Don't make entire content-type sections reusable just to reduce duplication. Two pages that both have a "Prerequisites" section do not necessarily have the same prerequisites.

## Changelog should use Fern's changelog feature

Rather than building an ordinary Markdown page containing every release, use Fern's dedicated changelog support. Fern supports a changelog folder, post metadata, tags, descriptions, authors, draft entries, and changelog-specific layouts. ([Build With Fern](https://buildwithfern.com/learn/docs/configuration/changelogs?utm_source=chatgpt.com))

Individual entries still follow our content model for a release note.

The **Changelog landing page** itself is better thought of as an overview rather than another release note.
