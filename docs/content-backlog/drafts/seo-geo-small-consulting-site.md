---
title: "SEO and GEO for a one-person consulting site: what I checked and fixed"
excerpt: "A practical pass for a small consulting site: titles, descriptions, schema, llms.txt, AI crawler access and the bugs a checklist misses. What I found on mine."
tags: [seo, geo, llmstxt, hugo, smallbusiness]
categories: [How-to]
keyword: seo for small consulting website
lane: client
status: draft
source: Nov 4 website SEO/GEO pass notes (rfd_it_services_site)
---

For a small consulting site, most of the search work is basic and checkable: one clear title and description per page, structured data that matches what's visible, a sitemap, crawler access for both search engines and AI assistants, and pages that don't break their own rules. I ran that pass on my own site this week. The basics were mostly there. The useful finds were the small breakages.

GEO here means generative engine optimization: making your pages easy for AI assistants to read, quote and cite.

## What was already in place

Worth listing, because if you have these you're ahead of most small sites:

- a unique title, meta description and canonical URL on every page;
- Open Graph tags so links preview properly;
- a generated sitemap;
- a `robots.txt` that explicitly allows the major AI crawlers;
- an `llms.txt` file listing case studies and projects for AI assistants;
- Person schema on the About page and Article and Breadcrumb schema on project pages;
- automated checks that fail the build if SEO or GEO basics regress.

## What I found

**Descriptions that ran too long.** Eleven pages had descriptions over 160 characters, which get cut off with an ellipsis in search results. Rewrite them to say the page's point in one plain sentence.

**Pages with two H1 headings.** Three pages had a second top-level heading inside the content, on top of the page title. One H1 per page, then H2s.

**A contact button you could barely read.** My nav's link style was more specific in CSS than the button style, so the Contact button rendered as dark text on dark blue with no padding. No checklist catches this. You catch it by looking at your own site on a normal screen.

**A homepage that looked abandoned.** The "recent writing" section stopped in mid-October because the site hadn't been rebuilt since then, even though the blog kept going. To a visitor that reads as "this person stopped".

**A Services link that went to Contact.** There was no real Services page, so the most important page for a consulting business didn't exist.

## What I added

- **ProfessionalService and Person schema on the home page,** so search engines and assistants can tell it's a business and who runs it.
- **Service and FAQ schema on the new Services page,** with the FAQ also shown as visible text. Never mark up content a reader can't see.
- **A richer `llms.txt`** that summarizes services, not just projects.
- **Internal links from project pages to Services,** so a reader who's impressed by a case study has somewhere to go.
- **More AI agents in `robots.txt`,** since new crawlers keep appearing.

## The parts that are judgment, not checklists

Some findings needed a decision from me rather than a fix:

- A Gmail contact address with "I'll reply in a few days" and no booking link is a weak call to action.
- My navigation shared a header with my blog and arcade, which created overlapping links. That was deliberate, so it stays for now.
- If your host or CDN blocks AI bots by default, your `robots.txt` doesn't matter. Check the dashboard setting, not just the file.

## A short checklist you can steal

1. Every page: one H1, a description under 160 characters, a canonical URL.
2. Structured data only for things a visitor can see on the page.
3. `robots.txt` that allows the crawlers you want, and a CDN setting that agrees.
4. An `llms.txt` that says plainly what you do and for whom.
5. A real Services page, linked from your best work.
6. A homepage that shows recent activity.
7. Look at the site yourself, on a laptop and a phone. Automated checks don't notice an unreadable button.

[ROBERT: confirm the Services page and these fixes are live before publishing; as of Nov 4 the deploy hadn't gone out.]
