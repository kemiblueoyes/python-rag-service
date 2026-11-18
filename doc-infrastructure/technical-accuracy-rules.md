---
version: 1
---

# Technical Accuracy Rules

Use these rules when drafting and reviewing technical documentation. Accuracy means that a reader can rely on the documented behavior, requirements, examples, and limitations. Do not treat plausible explanations or generated text as evidence.

## Verify against authoritative sources

Use `AGENTS.md` and its Documentation map to locate the source of truth for the behavior being documented. Depending on the subject, that may be implementation code, configuration, an OpenAPI definition, tests, command output, or a recorded evaluation report.

- Check factual claims against the relevant source rather than relying on memory, an earlier draft, or another generated summary.
- Prefer the source that defines or implements behavior over documentation that describes it. Use existing documentation for context and consistency, but investigate conflicts.
- Verify version-sensitive details against the version or revision being documented. Do not present behavior from an older release or a planned change as current.
- If sources disagree, identify the discrepancy and ask for clarification. Do not silently choose the most convenient account.
- Do not invent commands, paths, settings, defaults, endpoints, parameters, response fields, or example output.

Keep source references or verification notes during drafting so uncertain claims can be checked. The final page need not expose internal verification notes unless they are useful to readers.

## Distinguish current, planned, and conditional behavior

Describe implemented behavior as implemented, and planned behavior as planned. A design document, issue, or proposed change is not proof that a feature exists.

State relevant conditions: configuration, required providers, permissions, supported content sources, environment, or feature availability. If a behavior depends on one of these conditions, do not describe it as universal.

Document important limitations and unsupported cases when they affect whether a reader can complete the task or interpret the result.

## Technical Depth

Write at the level of technical detail the reader needs to complete their goal without guessing.

Use simple, clear language even when explaining technical concepts. Prefer precise terms over vague wording, but avoid jargon when a simpler term works just as well. When specialized terminology is necessary, use the correct term and explain it briefly when the audience may not already know it.

Do not remove important technical detail just to make the documentation easier to read. Simplify the language, not the information.

## Explaining technical concepts

Assume readers are technically capable, but do not assume they already know this project's architecture, retrieval approach, or terminology.

Explain specialized concepts when understanding them is necessary to complete the task or understand the system. Keep explanations brief and place them close to where the concept is first needed.

Do not explain common developer concepts unless the explanation is necessary for the task. Avoid interrupting procedures with background information that the reader does not need to continue.

For unfamiliar or project-specific terms, use the correct term rather than replacing it with vague language, and explain it in plain language when needed.

Follow `doc-infrastructure/terminology.md` for preferred terms and distinctions. Do not redefine terminology rules here.

## AI and system behavior language

### Describe actual system behavior

Describe what the system, component, or model actually does.

Name the responsible component when that distinction matters. Prefer specific descriptions such as **the retrieval pipeline retrieves**, **the model generates**, or **the application validates** over vague phrases such as **the AI knows**, **the AI decides**, or **the system understands**.

Do not imply that a language model performs checks or guarantees that are actually handled by application logic. For example, the model may propose citations, but the application validates them before returning the answer.

Use human-like language only when it is a harmless shorthand and does not misrepresent how the system works.

Prefer:

* The retrieval pipeline determines whether any results meet the support requirements.  
* The model generates an answer from the supplied context.  
* The application validates the model's proposed citations.

Avoid:

* The AI knows whether the documentation can answer the question.  
* The model verifies its sources.  
* The system understands that the query is unsupported.

### Claims about certainty and guarantees

Use absolute language only when the behavior is actually guaranteed by the implementation.

Avoid words such as **always**, **never**, **ensures**, **guarantees**, and **prevents** unless the system enforces that behavior in all supported cases.

When behavior depends on retrieval quality, model output, configuration, or external services, describe the condition or limitation instead of overstating certainty.

Prefer:

* The application validates citations before returning them.  
* The model is instructed to answer only from the supplied context.  
* The support gate can return no relevant results when the retrieved content does not adequately support the query.

Avoid:

* The model always answers from the documentation.  
* Citation validation prevents hallucinations.  
* Hybrid retrieval guarantees relevant results.

Distinguish between **design intent**, **implemented checks**, and **guaranteed behavior**. Do not present an instruction to the model as a guarantee that the model will follow it.

## Procedures and expected outcomes

- Include the prerequisites a reader actually needs, such as installed tools, running services, credentials, configuration, or existing indexed content. Do not assume that a prerequisite is met merely because it was established elsewhere in the documentation.
- Give commands, configuration values, paths, and actions precisely enough to follow. Identify placeholders and explain where readers obtain values they must supply.
- State what successful completion looks like when it may not be obvious. Include an observable result, response, file, log message, or verification command when useful.
- Explain consequential failure conditions and recovery steps when they are relevant to the procedure. Do not imply that an operation succeeded merely because a command exited without visible output.
- Keep optional steps and environment-specific variations distinct from required steps.

Do not add steps solely to make a procedure longer. Include what is necessary to perform and verify the task.

## Validate code examples and API details

- Match examples to the implemented interface and documented version. Check endpoint paths, HTTP methods, headers, authentication, parameters, response fields, and status codes against the API source of truth.
- Check commands for valid syntax, argument names, working directories, dependencies, and platform assumptions. Run safe examples when an appropriate environment is available; otherwise mark them as unverified during review.
- Never include real credentials, tokens, personal information, or secrets. Use clearly identified placeholders and avoid printing secrets in example output.
- Make sample requests and responses consistent with each other. Do not fabricate an exact response and present it as observed output.
- Explain important defaults and omitted values when they materially change behavior.
- For generated API reference content, update the authoritative API definition instead of treating the generated page as the source of truth.

Use `doc-infrastructure/fern-platform-rules.md` for presentation and Fern-specific syntax; those rules are separate from whether a sample is technically correct.

## Evaluation results and quantitative claims

- Identify the dataset or dataset version, evaluation method, metric, and run or report when presenting measured results.
- Distinguish recorded results from expectations, illustrative numbers, and earlier experiments.
- Compare runs only when their datasets, metrics, cutoffs, and other relevant conditions are comparable. State material differences when discussing them together.
- Do not generalize from one evaluation run into a guarantee about all queries or deployments.

## Handle uncertainty

If a claim cannot be confirmed, do not fill the gap with a plausible guess. Record the specific question and the source needed to resolve it, and ask the user or relevant subject-matter expert.

During drafting, clearly distinguish unresolved verification notes from publishable content. Do not leave unverified claims disguised as facts in the final draft.

## Code-sample rule

Format JSON for readability when displaying a response in the terminal. Match the formatting to the library used:

| Sample type | Format |
|---|---|
| cURL, when Python is a prerequisite | Append `\| python3 -m json.tool` |
| Python using `requests` or `httpx` | `print(json.dumps(response.json(), indent=2))` |
| Python using `urllib` | `payload = json.loads(response.read().decode())`, followed by `print(json.dumps(payload, indent=2))` |

- Include `import json` in Python samples that use it.
- Apply formatting when printing, while keeping parsed data available for further processing.
- Skip JSON formatting when the sample already prints selected fields in a readable layout.
- Don’t apply this pattern to streaming responses or responses without a JSON body.
