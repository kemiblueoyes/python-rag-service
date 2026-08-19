document.addEventListener('DOMContentLoaded', () => {
	const clients = document.querySelectorAll('.dl-rag-client');

	clients.forEach((client) => {
		const form = client.querySelector('.dl-rag-search-form');
		const input = client.querySelector('.dl-rag-query');
		const status = client.querySelector('.dl-rag-status');
		const results = client.querySelector('.dl-rag-results');

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
        
            const query = input.value.trim();
        
            if (!query) {
                return;
            }
        
            const buttons = form.querySelectorAll('button[type="submit"]');
        
            buttons.forEach((button) => {
                button.disabled = true;
            });
        
            form.setAttribute('aria-busy', 'true');
        
            const mode = event.submitter?.dataset.mode || 'search';
            const isAnswer = mode === 'answer';
        
            const url = isAnswer
                ? dlRagConfig.answerUrl
                : dlRagConfig.searchUrl;
        
            status.textContent = isAnswer
                ? 'Generating answer…'
                : 'Searching…';
        
            results.replaceChildren();
        
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        query,
                    }),
                });
        
                const data = await response.json();
        
                if (!response.ok) {
                    throw new Error(
                        data.message ||
                        (isAnswer
                            ? 'Answer generation could not be completed.'
                            : 'Search could not be completed.')
                    );
                }
        
                if (isAnswer) {
                    renderAnswer(data, results, status);
                } else {
                    renderResults(data.results, results, status);
                }
            } catch (error) {
                status.textContent =
                    error.message ||
                    'The request could not be completed.';
            } finally {
                buttons.forEach((button) => {
                    button.disabled = false;
                });
        
                form.removeAttribute('aria-busy');
            }
        });
	});
});

/**
 * Shorten an excerpt without cutting a word in half.
 *
 * @param {string} text Excerpt text.
 * @param {number} maxLength Maximum displayed length.
 * @returns {string} Shortened excerpt.
 */
function truncateExcerpt(text, maxLength = 420) {
	const normalizedText = text
		.replace(/\s+/g, ' ')
		.trim();

	if (normalizedText.length <= maxLength) {
		return normalizedText;
	}

	const words = normalizedText.split(' ');
	let truncatedText = '';

	for (const word of words) {
		const candidate = truncatedText
			? `${truncatedText} ${word}`
			: word;

		if (candidate.length > maxLength) {
			break;
		}

		truncatedText = candidate;
	}

	return `${truncatedText}…`;
}

/**
 * Render search results.
 *
 * @param {Array} results Search results.
 * @param {HTMLElement} container Results container.
 * @param {HTMLElement} status Status container.
 */
function renderResults(results, container, status) {
	if (!results.length) {
		status.textContent = 'No relevant results found.';
		return;
	}

	status.textContent = `${results.length} result${
		results.length === 1 ? '' : 's'
	} found.`;

	results.forEach((result) => {
		const article = document.createElement('article');
		article.className = 'dl-rag-result';

		const title = document.createElement('h3');

        const link = document.createElement('a');
        link.href = result.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = result.title;

		title.appendChild(link);
		article.appendChild(title);

        if (result.heading_path && result.heading_path.length) {
            const heading = document.createElement('p');
            heading.className = 'dl-rag-result-heading';
        
            result.heading_path.forEach((headingText, index) => {
                if (index > 0) {
                    heading.appendChild(
                        document.createTextNode(' › ')
                    );
                }
        
                const isDeepestHeading =
                    index === result.heading_path.length - 1;
        
                if (isDeepestHeading && result.anchor) {
                    const headingLink = document.createElement('a');

                    headingLink.href =
                        `${result.url.replace(/#.*$/, '')}#${result.anchor}`;
                    
                    headingLink.target = '_blank';
                    headingLink.rel = 'noopener noreferrer';
                    headingLink.textContent = headingText;
        
                    heading.appendChild(headingLink);
                } else {
                    heading.appendChild(
                        document.createTextNode(headingText)
                    );
                }
            });
        
            article.appendChild(heading);
        }

		const excerpt = document.createElement('p');
		excerpt.textContent = truncateExcerpt(result.excerpt);
		article.appendChild(excerpt);

		container.appendChild(article);
	});
}

/**
 * Render supported inline Markdown safely.
 *
 * Currently supports **bold text**.
 *
 * @param {string} text Text to render.
 * @param {HTMLElement} container Destination element.
 */
/**
 * Render supported inline Markdown and citations safely.
 *
 * Supports **bold text** and citation IDs such as [S1].
 *
 * @param {string} text Text to render.
 * @param {HTMLElement} container Destination element.
 * @param {Array} sources Validated answer sources.
 */
function appendInlineFormatting(
	text,
	container,
	sources = []
) {
	const parts = text.split(
		/(\*\*[^*]+\*\*|\[S\d+\])/g
	);

	parts.forEach((part) => {
		if (
			part.startsWith('**') &&
			part.endsWith('**') &&
			part.length > 4
		) {
			const strong = document.createElement('strong');
			strong.textContent = part.slice(2, -2);
			container.appendChild(strong);
			return;
		}

		const citationMatch = part.match(/^\[(S\d+)\]$/);

		if (citationMatch) {
			const citationId = citationMatch[1];

			const source = sources.find(
				(item) => item.citation_id === citationId
			);

			if (source) {
				const citationLink =
					document.createElement('a');

				citationLink.className =
					'dl-rag-citation';

				citationLink.href = source.anchor
					? `${source.url.replace(/#.*$/, '')}#${source.anchor}`
					: source.url;

				citationLink.target = '_blank';
				citationLink.rel =
					'noopener noreferrer';

				citationLink.textContent = part;

				container.appendChild(citationLink);
				return;
			}
		}

		container.appendChild(
			document.createTextNode(part)
		);
	});
}

/**
 * Render a generated answer with limited Markdown formatting.
 *
 * Supports paragraphs, unordered lists, and bold text.
 *
 * @param {string} text Generated answer.
 * @param {HTMLElement} container Destination element.
 */
function renderAnswerContent(
	text,
	container,
	sources = []
) {
	const lines = text
		.replace(/\r\n/g, '\n')
		.split('\n');

	let paragraphLines = [];
	let list = null;

	function flushParagraph() {
		if (!paragraphLines.length) {
			return;
		}

		const paragraph = document.createElement('p');

		appendInlineFormatting(
            paragraphLines.join(' '),
            paragraph,
            sources
        );

		container.appendChild(paragraph);
		paragraphLines = [];
	}

	lines.forEach((line) => {
		const trimmedLine = line.trim();

		if (!trimmedLine) {
			flushParagraph();
			list = null;
			return;
		}

		const listMatch = trimmedLine.match(/^[-*]\s+(.+)$/);

		if (listMatch) {
			flushParagraph();

			if (!list) {
				list = document.createElement('ul');
				container.appendChild(list);
			}

			const item = document.createElement('li');

			appendInlineFormatting(
				listMatch[1],
				item,
                sources
			);

			list.appendChild(item);
			return;
		}

		list = null;
		paragraphLines.push(trimmedLine);
	});

	flushParagraph();
}

/**
 * Render a grounded answer and its validated sources.
 *
 * @param {Object} data Answer response.
 * @param {HTMLElement} container Results container.
 * @param {HTMLElement} status Status container.
 */
function renderAnswer(data, container, status) {
	status.textContent = data.sufficient_evidence
		? ''
		: 'The available pages and articles may not contain enough information.';

	const article = document.createElement('article');
	article.className = 'dl-rag-answer';

    const answerContent = document.createElement('div');
    answerContent.className = 'dl-rag-answer-content';

    renderAnswerContent(
        data.answer,
        answerContent,
        data.sources || []
    );

    article.appendChild(answerContent);

	if (data.sources && data.sources.length) {
		const sourcesHeading = document.createElement('h3');
		sourcesHeading.textContent = 'Sources';

		article.appendChild(sourcesHeading);

		const sourceList = document.createElement('ul');
		sourceList.className = 'dl-rag-sources';

		data.sources.forEach((source) => {
			const item = document.createElement('li');

			const citation = document.createElement('strong');
			citation.textContent = `[${source.citation_id}] `;

			const link = document.createElement('a');
			link.href = source.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = source.title;

			item.appendChild(citation);
			item.appendChild(link);

            if (
                source.heading_path &&
                source.heading_path.length
            ) {
                item.appendChild(
                    document.createTextNode(' — ')
                );
            
                source.heading_path.forEach((headingText, index) => {
                    if (index > 0) {
                        item.appendChild(
                            document.createTextNode(' › ')
                        );
                    }
            
                    const isDeepestHeading =
                        index === source.heading_path.length - 1;
            
                    if (isDeepestHeading && source.anchor) {
                        const headingLink = document.createElement('a');
            
                        headingLink.href =
                            `${source.url.replace(/#.*$/, '')}#${source.anchor}`;
            
                        headingLink.target = '_blank';
                        headingLink.rel = 'noopener noreferrer';
                        headingLink.textContent = headingText;
            
                        item.appendChild(headingLink);
                    } else {
                        item.appendChild(
                            document.createTextNode(headingText)
                        );
                    }
                });
            }

			sourceList.appendChild(item);
		});

		article.appendChild(sourceList);
	}

	container.appendChild(article);
}