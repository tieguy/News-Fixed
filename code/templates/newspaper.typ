// News, Fixed - Typst Template
// Professional newspaper layout for print

#set page(
  paper: "us-letter",
  margin: 0.4in,
)

#set text(
  font: "New Computer Modern",
  size: 9pt,
  fallback: true,
)

#set par(
  justify: true,
  leading: 0.55em,
)

// Helper function for horizontal rules
#let hr(thickness: 1pt) = {
  line(length: 100%, stroke: thickness + black)
}

// Masthead
#align(center)[
  #text(size: 32pt, weight: "black")[NEWS, FIXED]
  #v(-6pt)
  #text(size: 9pt, style: "italic")[The World Is Getting Better. Here's Proof.]
]

#v(4pt)
#line(length: 100%, stroke: 3pt + black)
#v(2pt)

// Date bar
#grid(
  columns: (1fr, 1fr, 1fr),
  align: (left, center, right),
  text(weight: "bold", size: 9pt)[{{DAY_OF_WEEK}}],
  text(weight: "bold", size: 9pt)[{{DATE}}],
  text(weight: "bold", size: 9pt)[{{THEME}}],
)

#line(length: 100%, stroke: 2pt + black)
#v(6pt)

// === MAIN STORY ===
#text(size: 18pt, weight: "bold")[{{MAIN_TITLE}}]
#v(4pt)
#line(length: 100%, stroke: 2pt + black)
#v(4pt)

// Main content with QR code
#grid(
  columns: (6.38in, 1in),
  column-gutter: 0.12in,
  align: (left, center + top),
  // Main content in 2 columns
  [
    #columns(2, gutter: 0.12in)[
      {{MAIN_CONTENT}}
    ]
  ],
  // QR code
  [
    #box(
      image("{{MAIN_QR}}", width: 1in, height: 1in),
    )
    #v(4pt)
    #text(size: 7pt, style: "italic")[Scan for\ {{MAIN_SOURCE}}]
  ]
)

#v(8pt)
#line(length: 100%, stroke: 2pt + black)
#v(6pt)

// === SECONDARY STORIES AND FEATURE BOX ===
{{SECONDARY_STORIES}}

// Feature box
#box(
  width: 100%,
  height: 2.4in,
  stroke: 2pt + black,
  fill: luma(245),
  inset: 10pt,
  clip: true,
)[
  #text(size: 11pt, weight: "bold")[{{FEATURE_TITLE}}]
  #v(4pt)
  #text(size: 8pt)[{{FEATURE_CONTENT}}]
]

#v(10pt)

// === TOMORROW TEASER ===
{{TOMORROW_TEASER}}

// === FOOTER ===
#place(
  bottom,
  dy: -0.5in,
  text(size: 8pt, weight: "bold")[
    #align(center)[News, Fixed • Page 1 of 2]
  ]
)

#pagebreak()

// ============================================
// PAGE 2
// ============================================

#align(center)[
  #line(length: 100%, stroke: 3pt + black)
  #v(6pt)
  #text(size: 24pt, weight: "black")[NEWS, FIXED]
  #v(4pt)
  #text(size: 9pt)[{{DAY_OF_WEEK}}, {{DATE}}]
  #v(6pt)
  #line(length: 100%, stroke: 3pt + black)
]

#v(15pt)

#text(size: 14pt, weight: "bold")[QUICK READS]
#v(10pt)

// === MINI ARTICLES ===
{{MINI_ARTICLES}}

#v(15pt)
#line(length: 100%, stroke: 2pt + black)
#v(10pt)

// === BY THE NUMBERS ===
#text(size: 14pt, weight: "bold")[BY THE NUMBERS]
#v(8pt)

{{STATISTICS}}

// === XKCD COMIC ===
{{XKCD_SECTION}}

// === FOOTER PAGE 2 ===
#place(
  bottom,
  dy: -0.5in,
  [
    #align(center)[
      #text(size: 9pt, style: "italic")[{{FOOTER_MESSAGE}}]
      #v(4pt)
      #text(size: 8pt, weight: "bold")[News, Fixed • Page 2 of 2 • Good news exists, but it travels slowly. Keep reading.]
    ]
  ]
)
