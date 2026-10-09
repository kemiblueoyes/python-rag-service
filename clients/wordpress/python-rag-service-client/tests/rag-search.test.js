'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const { JSDOM } = require('jsdom');

const SCRIPT_PATH = path.join(__dirname, '../assets/rag-search.js');

function loadClient() {
	const dom = new JSDOM(
		'<!doctype html><html><body><div id="status"></div><div id="results"></div></body></html>',
		{ url: 'https://wordpress.example/search/', runScripts: 'dangerously' }
	);
	const script = dom.window.document.createElement('script');
	script.textContent = fs.readFileSync(SCRIPT_PATH, 'utf8');
	dom.window.document.body.appendChild(script);
	return dom.window;
}

function renderSearch(window, results) {
	const status = window.document.getElementById('status');
	const container = window.document.getElementById('results');
	container.replaceChildren();
	window.renderResults(results, container, status);
	return container;
}

function renderAnswer(window, data) {
	const status = window.document.getElementById('status');
	const container = window.document.getElementById('results');
	container.replaceChildren();
	window.renderAnswer(data, container, status);
	return container;
}

function linkData(root) {
	return [...root.querySelectorAll('a')].map((link) => ({
		text: link.textContent,
		href: link.href,
		target: link.getAttribute('target'),
		rel: link.getAttribute('rel'),
	}));
}

test('search renders http and https links, including heading fragments', () => {
	const window = loadClient();
	const container = renderSearch(window, [
		{
			title: 'HTTP result',
			url: 'http://example.com/http-doc',
			excerpt: 'HTTP excerpt',
			heading_path: ['Overview', 'HTTP section'],
			anchor: 'http-section',
		},
		{
			title: 'HTTPS result',
			url: 'HTTPS://example.com/docs/page#old',
			excerpt: 'HTTPS excerpt <em>kept as text</em>',
			heading_path: ['HTTPS section'],
			anchor: 'new-section',
		},
	]);

	assert.deepEqual(linkData(container), [
		{
			text: 'HTTP result',
			href: 'http://example.com/http-doc',
			target: '_blank',
			rel: 'noopener noreferrer',
		},
		{
			text: 'HTTP section',
			href: 'http://example.com/http-doc#http-section',
			target: '_blank',
			rel: 'noopener noreferrer',
		},
		{
			text: 'HTTPS result',
			href: 'https://example.com/docs/page#old',
			target: '_blank',
			rel: 'noopener noreferrer',
		},
		{
			text: 'HTTPS section',
			href: 'https://example.com/docs/page#new-section',
			target: '_blank',
			rel: 'noopener noreferrer',
		},
	]);
	assert.equal(container.querySelector('em'), null);
	assert.equal(
		container.textContent.includes('HTTPS excerpt <em>kept as text</em>'),
		true
	);
	assert.equal(container.textContent.includes('Overview'), true);
});

test('one rejected search URL stays text and the other result still links', () => {
	const window = loadClient();
	const rejected = [
		['Script title', 'javascript:alert(1)'],
		['Data title', 'data:text/html,hello'],
		['Ftp title', 'ftp://example.com/file'],
		['Case title', 'JavaScript:alert(1)'],
		['Space title', ' https://example.com/spaced'],
		['Inner space title', 'https://exa mple.com/spaced'],
		['Broken title', 'https://'],
		['Relative title', '/docs/relative'],
		['Hostless title', 'example.com/docs'],
		['User title', 'http://user@example.com/only-user'],
		['Creds title', 'https://user:s3cret-token@example.com/private'],
		['Empty user title', 'https://@example.com/empty-user'],
	];
	const container = renderSearch(window, [
		...rejected.map(([title, url]) => ({
			title,
			url,
			excerpt: `${title} excerpt`,
			heading_path: [`${title} heading`],
			anchor: 'rejected-anchor',
		})),
		{
			title: 'Kept result',
			url: 'https://example.com/kept',
			excerpt: 'Kept excerpt',
			heading_path: ['Kept heading'],
			anchor: 'kept',
		},
	]);

	assert.deepEqual(
		linkData(container).map((link) => link.text),
		['Kept result', 'Kept heading']
	);
	assert.equal(linkData(container)[1].href, 'https://example.com/kept#kept');
	const markup = container.innerHTML;
	for (const token of [
		'javascript:',
		'JavaScript:',
		'data:text',
		'ftp://',
		's3cret-token',
		'only-user',
		'empty-user',
	]) {
		assert.equal(markup.includes(token), false, token);
	}
	for (const [title] of rejected) {
		assert.equal(container.textContent.includes(title), true, title);
		assert.equal(
			container.textContent.includes(`${title} heading`),
			true,
			title
		);
		assert.equal(
			container.textContent.includes(`${title} excerpt`),
			true,
			title
		);
	}
	const articles = container.querySelectorAll('article');
	assert.equal(articles.length, rejected.length + 1);
	assert.equal(articles[0].querySelector('a'), null);
	assert.equal(articles[0].querySelector('h3').textContent, 'Script title');
});

test('answer, citation, and heading links reject one bad source', () => {
	const window = loadClient();
	const container = renderAnswer(window, {
		sufficient_evidence: true,
		answer: 'See **retrieval** in [S1] and [S2].\n\n- Extra [S2]',
		sources: [
			{
				citation_id: 'S1',
				title: 'Unsafe source',
				url: 'javascript:alert(document.domain)',
				heading_path: ['Parent', 'Unsafe heading'],
				anchor: 'unsafe',
			},
			{
				citation_id: 'S2',
				title: 'Safe source',
				url: 'https://example.com/answer-doc#old',
				heading_path: ['Parent', 'Safe heading'],
				anchor: 'safe',
			},
		],
	});

	assert.equal(container.textContent.includes('retrieval'), true);
	assert.equal(container.querySelector('strong').textContent, 'retrieval');
	assert.equal(container.textContent.includes('[S1]'), true);
	assert.equal(container.textContent.includes('[S2]'), true);
	assert.equal(container.textContent.includes('Unsafe source'), true);
	assert.equal(container.textContent.includes('Unsafe heading'), true);
	assert.equal(container.textContent.includes('Extra'), true);

	const links = linkData(container);
	assert.deepEqual(
		links.map((link) => link.text),
		['[S2]', '[S2]', 'Safe source', 'Safe heading']
	);
	for (const link of links) {
		assert.equal(link.target, '_blank');
		assert.equal(link.rel, 'noopener noreferrer');
		assert.equal(link.href.startsWith('https://example.com/answer-doc'), true);
	}
	assert.equal(
		links.filter((link) => link.text === '[S2]' || link.text === 'Safe heading')
			.every((link) => link.href === 'https://example.com/answer-doc#safe'),
		true
	);
	assert.equal(
		links.find((link) => link.text === 'Safe source').href,
		'https://example.com/answer-doc#old'
	);
	assert.equal(container.innerHTML.includes('javascript:'), false);
	assert.equal(container.querySelector('.rag-service-citation').textContent, '[S2]');
	const sourceItems = container.querySelectorAll('.rag-service-sources li');
	assert.equal(sourceItems.length, 2);
	assert.equal(sourceItems[0].querySelector('a'), null);
	assert.equal(sourceItems[1].querySelector('a').textContent, 'Safe source');
});
