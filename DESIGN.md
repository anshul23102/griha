---
name: Griha
description: Home-loan underwriting in the grammar of Indian Railways station boards and reservation charts.
colors:
  board-yellow: "#FFC21A"
  signage-black: "#121212"
  chart-blue: "#12439A"
  platform-paper: "#F3F4F6"
  sheet-white: "#FFFFFF"
  rule-ink: "#1B1B1B"
  rule-faint: "#D5D9DF"
  confirmed-green: "#0E7A3E"
  waiting-orange: "#A64600"
  declined-red: "#B3141B"
  night-ground: "#0C0D0F"
  night-sheet: "#15171A"
  night-action-blue: "#8FB4FF"
  night-focus-yellow: "#FFC21A"
  night-rule: "#8D94A0"
typography:
  display:
    fontFamily: "Hind, system-ui, sans-serif"
    fontSize: "clamp(2.25rem, 5vw, 4rem)"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Hind, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 600
    lineHeight: 1.15
  body:
    fontFamily: "Hind, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Hind, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    letterSpacing: "0.04em"
  data:
    fontFamily: "Azeret Mono, ui-monospace, monospace"
    fontSize: "0.875rem"
    fontWeight: 500
rounded:
  board: "0px"
  chip: "0px"
spacing:
  unit: "4px"
  row: "12px"
  section: "48px"
---

# Design System: Griha

## Overview

**Creative North Star: "The Reservation Chart"**

Every Indian knows how to read a station board and a reservation chart without being taught. Griha borrows that grammar for lending: orientation lives on a signage-yellow board with black type, bilingual by nature (Devanagari over Latin); work lives on ruled, dense, white chart sheets; verdicts print like a thermal ticket. The pipeline is a route of stations a case travels through, and the decision is where it arrives.

The system is for operators. Density is high, rules are hairline, and nothing moves unless it tells you something changed. Yellow orients and never decorates; it appears on the board header, the route strip and the active tab, and nowhere on the chart sheets. Statuses always carry words and a glyph, never colour alone.

**Key Characteristics:**
- Signage board header on every page, Hindi and English stacked
- Ruled chart tables as the default data container, not cards
- Route strip (stations with arrival times) as the single progress device
- Thermal-ticket decision slip with perforated edge
- One authored motion: the indicator-board flap when a verdict lands
- Night platform (dark) by default for contrast and presence; a day-platform light theme designed in parallel

## Colors

Signage yellow and black do the orienting; blue acts; three signal colours carry verdicts.

### Primary
- **Platform Yellow** (#FFC21A): orientation only: board headers, route strip, the logo chip, and the current location in navigation (active nav tab, active filter). Never an action button or a fill on chart sheets.
- **Signage Black** (#121212): type on yellow, text, rules.
- **Chart Blue** (#12439A): the only action colour: primary buttons, links, focus ring. 9:1 on white.

### Neutral
- **Platform Paper** (#F3F4F6): page ground. **Sheet White** (#FFFFFF): chart sheets. **Rule Ink** (#1B1B1B): structural rules. **Faint Rule** (#D5D9DF): row dividers.
- **Night Ground** (#0C0D0F) and **Night Sheet** (#15171A) in the dark theme, where yellow becomes the text accent on black.

### Status
- **Confirmed Green** (#0E7A3E), **Waiting Orange** (#B84E00), **Declined Red** (#B3141B). Always paired with a word and a glyph.

### Named Rules
**The Orientation Rule.** Yellow tells you where you are. It may mark the current place (active tab, active filter) but never offers an action: actions are blue.
**The Words Rule.** A status is its word first, glyph second, colour third.

## Typography

**Everything:** Hind (Latin and Devanagari in one family, weights 400 to 700). **Data:** Azeret Mono. All self-hosted via Fontsource. The condensed signage face was dropped: it read as elongated.

**Character:** one bilingual humanist sans at confident weights, plus a thermal-print mono only for numbers, IDs and hashes.

### Hierarchy
- **Display** (700, clamp 2.25-4rem, 1.02): the board line only.
- **Title** (600, 1.375rem, 1.15): sheet and section titles.
- **Body** (400, 1rem, 1.55, 65ch max): explanations, reasons.
- **Label** (600, 0.8125rem, +0.04em): column heads, chips, field labels. Not uppercase everywhere.
- **Data** (500, 0.875rem, tabular): amounts, IDs, hashes, timings.

### Named Rules
**The Mono Is For Measurement Rule.** Azeret Mono appears only on numbers, identifiers and hashes.

## Layout

A 12-column grid in a 1240px container, 4px base unit, 12px row rhythm in charts, 48px between sections. Every page opens with the board header, then the work. Desk and case pages are two-column at lg with a sticky route strip; below md everything stacks and the board shrinks to one line. Touch targets are at least 44px on the apply flow.

## Elevation & Depth

Flat. Depth is made with rules and one sheet-on-ground step, not shadow. The only shadow is the ticket's, a short hard offset (0 2px 0 rule) that reads as paper thickness.

## Shapes

Square corners everywhere. Sheets carry an 8px top rule like a ledger head. A hazard stripe (black and yellow, 14px) marks the platform edge under every board. The ticket has semicircle perforation notches. No pills.

## Components

### Station Board
Yellow plate, 2px black inner frame, Devanagari line above Latin line in Barlow/Hind 700, optional right-aligned mono "arrival" strip.

### Route Strip
Horizontal track on yellow: station circles for each pipeline stage with arrival time beneath in mono; passed stations filled black, warned stations hatched, failed stations red-ringed.

### Chart
Ruled table: 2px rule under header, faint rules between rows, no zebra, no cards, mono right-aligned numerals.

### Decision Ticket
Sheet with perforated side notches, big status word, case ID in mono, terms as a fare table.

### Buttons
Square-ish (4px), chart blue fill with white text for the one primary action, outlined for secondary, red outline for destructive and isolated by space.

### Fields
Label above, 44px control, 2px rule border, chart-blue focus ring 3px, error text below in declined red with a glyph.

## Do's and Don'ts

### Do:
- **Do** open every page with the bilingual board header.
- **Do** show every verdict as word plus glyph plus colour.
- **Do** keep chart rows dense and ruled; open detail inline.
- **Do** label synthetic data and internal policy values wherever they appear.

### Don't:
- **Don't** use cards inside cards or icon-plus-heading card grids. Entry points are platform numerals, not icon cards.
- **Don't** use yellow on anything pressable.
- **Don't** use gradient text, glass, glows, or decorative motion.
- **Don't** draw trains, tracks or tickets as illustration. Use the grammar, not the clip-art.
