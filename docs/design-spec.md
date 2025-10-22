# Project: News, Fixed - A Daily Positive News Digest for Kids

## Overview
Create a daily 2-page (front and back) newspaper for bright children that transforms weekly Fix The News content into daily reading material. The goal is to counter ambient negative news with evidence of human progress, formatted as a traditional black-and-white newspaper that can be easily printed at home.

## Source Material
- Fix The News weekly newsletter (https://fixthe.news)
- One weekly FTN issue should generate four daily "News, Fixed" editions (Monday-Thursday)
- Each article should include a QR code linking to the original source (not FTN, but the actual study/organization/news outlet FTN cites)
- In the future, family calendars (eg, the Wednesday edition would include "Scout meeting tonight at 5:30pm" and Friday edition might include weekend family activities)
- In the future, might include a rotating set of single-panel family-friendly nerdy cartoons (like old Far Sides or XKCDs)

## Format Specifications

### Physical Layout
- Standard 8.5" x 11" pages (2 pages total per day)
- Black and white only (optimized for home printing/photocopying)
- High contrast design with clear typography
- Newspaper-style columns for authentic feel

### Page 1 (Front)
- Header: "NEWS, FIXED" with tagline "The World Is Getting Better. Here's Proof."
- Date bar showing day number (e.g., "DAY 1 OF 4 FROM ISSUE #315")
- One major story (400-500 words) with QR code to source
- One feature box or "quick wins" section
- Tomorrow teaser box

### Page 2 (Back)
- 4-6 mini articles (100-150 words each) with QR codes
- "By The Numbers" section with 6 impactful statistics
- Footer reminding readers that good news exists but travels slowly

## Content Strategy

### Writing Style
- Accessible but not patronizing (target: bright 10-14 year olds)
- Explain complex concepts with analogies (e.g., "like leveling up in a video game")
- Include context for why the news matters to young readers
- Emphasize youth agency and possibility

### Story Selection from Each FTN Issue
Break into thematic days:
- Day 1: Health & Education
- Day 2: Environment & Conservation  
- Day 3: Technology & Energy
- Day 4: Society & Youth Movements

### QR Code Implementation
- Each article gets a QR code linking to original source
- Include small text under QR saying "Scan for [source name]"
- Consider adding backup tiny URL in case QR fails

## TODO List for Automation

### Immediate Setup Tasks
- [ ] Create HTML/CSS template for the 2-page format
- [ ] Set up QR code generation
- [ ] Build parser to extract source URLs from Fix The News links
- [ ] Create style guide for consistent rewriting

### Content Pipeline
- [ ] Script to parse Fix The News weekly email/webpage
- [ ] Categorizer to sort stories into 4 daily themes
- [ ] Rewriting tool/prompts to convert each story to appropriate reading level
- [ ] QR code generator that pulls source URLs
- [ ] Template filler that creates print-ready PDFs

### Enhancement Ideas
- [ ] Add "Dinner Table Question" for family discussion
- [ ] Include "Word of the Week" with science/civic terms
- [ ] Create weekend edition with puzzles/activities
- [ ] Build email subscription for automated daily delivery
- [ ] Consider version for different age ranges

### Testing Checklist
- [ ] Print test on home printer - check readability
- [ ] Test photocopying - ensure contrast holds
- [ ] Kid feedback - engaging but not condescending?
- [ ] Parent feedback - useful for family discussions?
- [ ] Teacher feedback - classroom appropriate?

## Sample Prompt for AI Assistant

"I need help creating 'News, Fixed' - a daily 2-page newspaper for bright kids (ages 10-14) that transforms positive news into engaging content. 

Using content from Fix The News issue #[NUMBER], please create Day [1-4] focusing on [THEME]. 

Requirements:
- One main story (400-500 words)
- 4-6 mini articles (100-150 words each)  
- 6 statistics for 'By The Numbers'
- QR code placeholder for each article marking where source link goes
- Written at an engaging but not patronizing level
- Explain why this news matters to young readers
- Include tomorrow teaser

Format as print-ready HTML with high contrast black and white design optimized for home printing."

## Success Metrics
- Kid voluntarily read it daily
- Generates dinner table discussions
- Counters doom-scrolling with evidence-based optimism
- Easy enough to produce daily with minimal effort
- Builds media literacy through source citations
