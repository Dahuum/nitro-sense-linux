# Website reference analysis and Nitro design system

This is a static design and behavior audit of the user-supplied HTTrack mirror,
followed by a concrete system for the NitroSense Linux landing page. Observed
reference decisions and proposed Nitro decisions are identified separately. This
is a website design system, not a change to the application's hardware protocol.

## Source and inspection boundary

- Reference: `website-ref/ram-altman.lol/index.html`, mirrored on 2026-11-11.
- Source HTML size: 96,784 bytes; SHA-256:
  `8695748f25be12383becf70755a1dab667f56b79ec8cdbf98aacf466b0a33b45`.
- The root `website-ref/index.html` is HTTrack's directory page, not the design
  reference. `hts-cache` and log files are acquisition artifacts.
- The target includes its styles, four embedded WOFF2 faces and an inline script.
  The hardware illustration is DOM/CSS; the social preview and icons are separate
  assets. There is no application framework or backend in the captured page.
- These findings come from supplied HTML/CSS/JS. Static selectors establish
  declared layouts and interactions, not proof of the original live site's
  browser rendering, network behavior or current availability.
- HTTrack rewrote canonical/OG URL values and the script's shared URL to local
  `index.html`. Do not carry those rewritten values into production.
- A Cloudflare Insights module remains external to the mirror. Its availability,
  behavior and traffic were not observed. Nitro does not need that analytics
  dependency or the reference's analytics token.

## 1. The reference's organizing idea

**Observed:** the page explains one small piece of software through a physical
hardware metaphor and a concrete example. Its hierarchy is editorial:

1. Very large product name.
2. One compact description beside a single prominent source-code action.
3. A full-width illustrated RAM stick, followed by a contextual caption.
4. A two-column explanation beside an example of the software's output.
5. A second two-column explanation beside a runnable command block.
6. A short qualifying editorial note.
7. Sharing actions and a compact ruled footer.

The design's identity comes from typography, restrained color, spacing and the
RAM illustration. There is no sticky navigation, dashboard screenshot floating
in space, repeated feature-card grid, large pricing block or unrelated ornament.
The copy explains mechanisms and shows examples instead of repeating benefits.

**Nitro interpretation:** replace the reference's RAM metaphor with physical
cooling fans and four keyboard zones. Preserve the large masthead and rhythm of
explanation → tangible evidence → useful next action. Downloads are the primary
action; source and documentation remain nearby. The result should feel like the
same family of concise software pages with a Nitro-specific subject and palette.

## 2. Layout, sizing and spacing

### Observed reference values

| Primitive | Declared value / behavior |
|---|---|
| Page width | `max-width:1120px`; centered |
| Horizontal gutter | `max(clamp(20px,4vw,48px), env(safe-area-inset-*,0px))` |
| Page top padding | `clamp(32px,6vw,72px)` |
| Page bottom padding | 40px |
| Main section gap | `clamp(64px,10vw,120px)` |
| Hero internal gap | `clamp(28px,4vw,44px)` |
| Generic section internal gap | 22px |
| Caption gap | 16px |
| Explanatory split | `minmax(0,5fr) minmax(0,7fr)` |
| Split gap | 28px vertically; `clamp(32px,6vw,80px)` horizontally |
| Description measure | Pitch ≤34rem; explanatory note ≤26rem |
| Demo panel | 12px radius; `clamp(20px,3vw,30px)` padding; 16px internal gap |
| Code panel | 12px radius; 24px horizontal padding; space reserved above for Copy |
| Pill actions | 999px radius; primary padding 13px 22px |
| Mobile breakpoint | `max-width:760px` |

`min-width:0` on grid children and `overflow-wrap:anywhere` on variable text are
important parts of this system. Long commands and identifiers may wrap without
forcing the entire page wider than the viewport.

### Nitro adaptation

The 1120px cap includes side padding under border-box sizing; at desktop the
content width is 1024px after two 48px gutters. This distinction keeps the
implementation aligned with the mirror.

Retain the 1120px page, fluid gutters, 5:7 split and generous section spacing.
Keep prose near a readable 45–65 characters rather than filling the entire page.
Use one principal illustration spanning the content width. On narrow screens,
stack explanation before its demonstration. Do not make the hero's title smaller
than ordinary marketing typography merely to preserve a two-column screenshot.
Use an inline Linux/version marker and compact utility links, not a full
navigation system that competes with the masthead.

At 760px and below: stack split columns, make primary CTA full width, allow
secondary pill links to wrap, reflow the hardware visual, and retain at least
20px side clearance. At 360px and below: keep labels and measurements readable,
allow titles to wrap deliberately, and never shrink code into illegibility.

## 3. Typography

### Observed reference values

The mirror embeds Funnel Display500 for headings, Funnel Sans400/500 for prose
and controls, and Geist Mono400 for code. Their fallback stacks include Avenir
Next, Segoe UI, system sans and platform monospace fonts. `font-display:swap`
prevents the custom fonts from making text invisible while loading.

| Role | Size / line-height | Weight / tracking |
|---|---|---|
| Masthead `h1` | `clamp(3.2rem,15.4vw,11.4rem)/.95` | 500; -.035em |
| Pitch | `clamp(1.3rem,2.5vw,1.7rem)/1.28` | 400; -.01em |
| Section `h2` | `clamp(1.8rem,3.6vw,2.6rem)/1.08` | 500; -.02em |
| Body | 1.0625rem / 1.6 | 400 |
| Editorial aside | `clamp(1.2rem,2.2vw,1.5rem)/1.36` | 400; -.008em |
| Code | .9375rem / 1.8 | 400 monospace |
| Secondary labels | .9375rem | Body family |

The tight masthead occupies an entire line and sets the tone. The section titles
are much smaller; body and metadata do not compete with it. `text-wrap:balance`
is applied to compact headings and the pitch.

**Nitro adaptation:** preserve this hierarchy and tight tracking. The implementation separately sources Funnel Display, Funnel Sans and Geist Mono
from Google Fonts, includes each SIL Open Font License, and self-hosts WOFF2
containers with `font-display:swap`. System stacks remain fallbacks. Do not extract and redistribute the mirror's
embedded font binaries based only on their presence in an HTML file. Color and
measured typographic hierarchy can convey the reference without copying assets.

## 4. Color and surface model

### Observed reference palettes

| Role | Light | Dark |
|---|---|---|
| Background | #f2f5f1 | #0a2d23 |
| Foreground | #10231b | #eaf2ed |
| Muted text | #52655b | #a2bcb0 |
| Hairline | #d3dcd4 | #1d4a3c |
| Panel | #ffffff | #0e382c |
| Physical hardware base | #0f5a43 | #12614a |
| Hardware edge | #0b4634 | #0d4c3a |
| Chip | #15191a | unchanged |
| Highlight | #e3bb4e | unchanged |
| Link / button | #0b6a4e / #0f5a43 | #e3bb4e |

The reference automatically responds to `prefers-color-scheme:dark`. CSS also
supports explicit `data-theme=light` and `data-theme=dark`; the inspected script
does **not** expose or persist a theme-toggle control. CSS support is not proof
that a visible theme selector exists.

### Implemented Nitro tokens

```css
:root {
  color-scheme: dark;
  --bg: #151313;
  --fg: #f3eee9;
  --muted: #aaa09b;
  --line: #3a3130;
  --panel: #1e1a19;
  --subtle: #292221;
  --board: #2c1515;
  --board-line: #64302c;
  --accent: #ff5b4e;
  --button: #ff5b4e;
  --button-ink: #1c1210;
  --code-bg: #100f0f;
  --code-ink: #f3eee9;
  --radius: 12px;
  --section-gap: clamp(64px, 10vw, 120px);
}
```

These are Nitro design choices, not values recovered from the reference. Red is
an action/selection accent, not the color of all text. Main prose remains neutral.
Use labels and icons as well as color for verification states. Validate contrast
against the actual final backgrounds; do not assume an attractive red passes
for every small-text pairing. The implemented light theme uses #f6f0e9 background, #251614 foreground,
#71605b muted, #d9cbc2 borders, #fffaf5 panels and #b93228 accents. Dark is the
default; a new accessible toggle persists the choice under `nitro-site-theme`.
This toggle is a Nitro addition, not a recovered reference behavior.

## 5. Components and their contracts

| Component | Reference pattern | Nitro use and state contract |
|---|---|---|
| Masthead | Oversized product wordmark in text | NitroSense text with separate Linux/version marker; one semantic h1 |
| Pitch row | Short explanation + rounded CTA | One useful sentence + Download; GitHub/docs as secondary actions |
| Hardware figure | DOM RAM module, pins, chips, caption | Independently drawn dual-fan/four-zone strip; caption labels illustration and sample state |
| Explanatory split | Short heading/note left, output right | Hardware control description left, mode demonstration right |
| Output card | Structured email example with stable height | Sample device record with mode, requested values, measured RPM and provenance |
| Secondary action | Read another output | Explicit Auto/Max/Custom sample controls; selected state announced |
| Code panel | Wrapped commands and Copy | Actual app install/diagnostic commands; copy plaintext without prompt glyphs |
| Editorial aside | Brief qualification without boxed warning | Narrow support target and honest visual-verification boundary |
| Link pills | Share destinations with distinct focus/hover | Source, docs, releases and optional copy-page-link actions |
| Footer | One rule and two compact groups | Independence/license statement plus author/source/docs links |

Primary buttons: resting solid red; hover changes brightness/position subtly;
focus adds an offset high-contrast outline; active gives immediate feedback.
Secondary buttons: transparent with hairline border; hover strengthens border;
the mode-cycle action updates visible mode text and a concise status live region.
It is an action button, not a pressed toggle. The separate theme toggle reports
its state with `aria-pressed`.
Disabled controls should not be needed for working website navigation: link to
actual available artifacts and explain unsupported platforms in text.

## 6. Interaction analysis and adaptation

### What the reference script does

- Generates 20 RAM chips and marks one used. A short staggered startup animation
  flashes each chip before settling into its static state.
- Offers another example email. Subjects, bodies and sign-offs use shuffled bags
  that avoid immediate repetition rather than randomizing the entire page.
- Escapes text before constructing formatted output and retains stable panel
  heights so example changes do not move later sections unexpectedly.
- Copies a specific plaintext command sequence. Clipboard rejection selects the
  visible code and asks the user to copy manually. The reference reveals its
  Copy button only if the clipboard API exists; Nitro can provide the manual
  selection fallback even when the API is absent.
- Uses desktop popup windows for some share links and full-page/new-tab behavior
  for coarse pointers. Federated sharing opens a server field, validates a host,
  remembers the chosen server in localStorage and constructs an external URL.
- Exposes polite status messages and an optional touch-specific share action.

### Nitro interaction model

The website is a product explanation, not a remote laptop controller. A browser
mode selector must update local demonstration state only. It must not imply a
connection to hwmon, root permissions or the visitor's firmware.

Use a small deterministic data table from the documented tests:

| Sample | Displayed request | Recorded observations |
|---|---|---|
| Auto baseline | Firmware automatic | CPU3125 RPM, GPU3703 RPM |
| Max | Both100% / Max | CPU5769 RPM, GPU5660 RPM in the recorded cycle |
| Custom | CPU60%, GPU70% | CPU4615 RPM, GPU5769 RPM in the separate recorded test |

Every panel should say **recorded sample** or **interface illustration**. Do not
calculate arbitrary measured RPM from percentages, invent real-time telemetry,
or connect these example settings to hardware. Keep illustrative temperatures
separate unless the exact selected sample includes them. Update mode labels,
request metadata and explanatory note together. The independent hero fan
illustration uses decorative motion and is explicitly labeled as a design
preview; its rotation is not a measurement or a live device connection. Reserve
space to prevent mode changes from making the page jump.

Motion should reinforce the physical metaphor: short entry flashes or fan
rotation, gentle hover response, no scroll hijacking or mandatory long reveal
sequence. Respect `prefers-reduced-motion` by removing rotation, stagger and
transforms while keeping every measurement and control functional.

For sharing, the useful minimum is copying the actual production URL or linking
to GitHub. The reference's long list of social services and federated host form
are not requirements for a hardware utility's landing page. If included, they
must share Nitro copy and the production canonical URL, not HTTrack's local URL.

## 7. Content architecture for Nitro

1. **Masthead / pitch / download:** what this is and its narrow target.
2. **Hardware figure:** fans and four-zone keyboard; visually demonstrates the
   software's subject without impersonating a full application screenshot.
3. **Control example split:** select a recorded mode, see actual test numbers,
   understand requested percentages versus measured RPM.
4. **Native app split:** actual screenshot and a compact list of implemented
   fans, lighting, monitoring, device settings and local profiles. Do not repeat
   broad slogans across a grid of near-identical feature cards.
5. **Get started split:** executable user-level install commands; separate link
   to the privileged driver setup and compatibility details.
6. **Evidence / compatibility:** one exact model and tested environment; measured,
   firmware-readback and visually verified claims remain distinct.
7. **Downloads:** existing wheel, source archive and checksums; no simulated
   platform picker for Windows/macOS artifacts that do not exist.
8. **Compact qualification / footer:** initial release, remaining parity gaps,
   independent project and useful documentation/source links.

The README can follow the supplied AULA project's richer technical structure:
centered name/tagline/status/link row and screenshot; introduction; capability
matrix; exact hardware target; platform/artifact choices; source and driver
installation; safe explicit apply; diagnostics; development; documentation;
license/provenance. Transfer structure, not AULA's device capabilities, package
formats, test counts, hardware claims or stack.

## 8. Implementation and data boundaries

Keep the landing page buildless: semantic `index.html`, design tokens and
components in `style.css`, and deferred progressive enhancement in `script.js`.
No framework, database, authentication or native-app bridge is needed. The static
GitHub Pages workflow continues publishing `website/`.

The HTML must include readable baseline numbers, links, instructions, support
scope and downloads without JavaScript. JavaScript may enhance mode switching,
copy feedback and motion, but must not be required to reach a release or read
installation instructions. No hardware state or credential is stored. If a theme
preference is added, use a dedicated localStorage key and handle denied storage.

Production release destinations:

- Main release: `https://github.com/Dahuum/nitro-sense-linux/releases/latest`
- Wheel: `https://github.com/Dahuum/nitro-sense-linux/releases/download/v0.1.0/nitro_sense_linux-0.1.0-py3-none-any.whl`
- Source: `https://github.com/Dahuum/nitro-sense-linux/releases/download/v0.1.0/nitro-sense-linux-0.1.0.tar.gz`
- Checksums: `https://github.com/Dahuum/nitro-sense-linux/releases/download/v0.1.0/SHA256SUMS`
- Public page: `https://dahuum.github.io/nitro-sense-linux/`

Use correct canonical, OpenGraph and optional SoftwareApplication structured data
for Nitro. Do not retain the reference's parody author/content, analytics token,
brand icons, previews or embedded font assets. Locally authored SVG/CSS drawings
and the project's own native screenshot establish its own provenance.

## 9. Validation acceptance criteria

- One h1; ordered headings; semantic header/main/section/figure/footer landmarks.
- Keyboard-operable sample buttons and Copy; visible focus; selected state is
  programmatic; feedback is in a polite live region without constant chatter.
- At320/360/390/760/1024/1440px, no page-level horizontal overflow; commands wrap;
  sample labels and measurements fit; split sequence remains sensible.
- Test at both sides of the760px breakpoint, with reduced motion, no JavaScript,
  and unavailable/rejected clipboard APIs.
- Repeated sample changes update all related output and retain explicit sample
  labeling; no network or device operation is triggered by them.
- Every download is an existing release asset; docs links target real paths;
  production canonical/sharing URLs never point to local mirror addresses.
- Inspect desktop and mobile screenshots; do not rely on HTML syntax alone.
- Keep copied HTTrack files outside the published site and source-release inputs.
- Publish through GitHub Pages and verify the successful deployed version.

## 10. What must remain distinguishable

**Observed:** exact source tokens, DOM hierarchy, declared CSS rules and inspected
script algorithms. **Design choices:** the Nitro red palette, fan/zone metaphor,
mode demo, release-focused content and simpler sharing controls. **Unverified:**
original live-server behavior, original cross-browser rendering, unmirrored
resources and native hardware visible effects. A reference-inspired landing page
must not turn those unknowns into unsupported product claims.


## 11. Final implementation inventory

| File | Responsibility |
|---|---|
| `website/index.html` | Static content, semantic landmarks, baseline samples, accessible controls, real release links and structured metadata |
| `website/style.css` | Source-inspired typography, Nitro color tokens, physical fan/zone illustration, all component states, 760/360px reflow and reduced motion |
| `website/script.js` | Deterministic recorded-sample cycle, safe copy/manual-selection feedback, canonical page sharing and persisted theme toggle |
| `website/assets/native-app.png` | The project's actual native app screenshot, shown through a disclosure |
| `website/assets/fonts/` | Independently obtained OFL fonts and each font's license; self-hosted WOFF2 delivery |
| `.github/workflows/pages.yml` | Existing GitHub Pages publication of the static directory |

The reference hardware illustration settles after a startup flash. Nitro uses
slow continuous fan rotation instead, disabled by reduced motion. The fans and
four-zone strip remain a labeled illustration independent of the recorded RPM
card. The mode action cycles Auto → Max → Custom → Auto and announces its new
recorded values. The screenshot disclosure provides native-app proof without
turning the hero into a floating window mockup.

The website stores only an optional theme preference. Mode changes and copy
controls make no device or telemetry calls. The page requires no backend,
application installation, account, analytics service or external runtime asset
request to read its core content. The supplied HTTrack directory is ignored by
Git and excluded from distribution.

## 12. Browser verification record

The local HTTrack reference was rendered in an isolated Chromium browser with
the external analytics URL blocked. The Nitro implementation was then served
locally and checked in that browser. The original live reference server was not
needed or treated as an additional source.

Verified on 2026-11-11:

- No horizontal overflow at 320, 360, 390, 760, 761, 1024 and 1440px.
- Auto → Max → Custom → Auto cycles reproduce the published RPM values.
- Fixed sample panel heights across all three modes: 587.25px at 320px,
  550.06px at 390px, 537.66px at 760px and 472.09px at 1440px. Reserved mobile
  title/body space prevents the example from shifting the rest of the page.
- Dark/light switching works; the selected light theme survives reload.
- A rejected clipboard request selects the exact visible installation commands;
  page-link fallback prints the real production URL instead of failing silently.
- The native screenshot disclosure opens and loads the actual app image.
- Reduced-motion preference removes decorative fan rotation.
- With JavaScript disabled, instructions, baseline samples, disclosures and all
  three release downloads remain readable/usable; enhancement buttons stay hidden.
- Keyboard Tab exposes the skip link with a visible focus indicator.
- Desktop, mobile and light-theme screenshots were visually inspected. Browser
  exception collection reported no runtime exceptions.
- Static checks validated unique IDs, one h1, local anchors, image/font/script
  paths, README local links and JavaScript syntax. The production page is checked
  again after GitHub Pages deployment.

This is bounded Chromium/browser-layout validation, not a claim of a complete
cross-browser accessibility audit or a new native-app hardware test.


Nitro's final desktop masthead uses `clamp(3.3rem,17vw,12.8rem)/.95`, with
-.045em tracking, tuned to make the shorter NitroSense word occupy the same
editorial emphasis as the reference. Below760px it uses
`clamp(3.3rem,14.7vw,7rem)`. Gutters independently honor left/right safe-area
insets. The source's exact values above remain observations, separate from
these implementation adjustments.
