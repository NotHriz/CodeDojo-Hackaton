# Akses Campus — Team and Agent Onboarding

Last updated: 16 October 2026 (Asia/Kuala_Lumpur)

## Start here

Akses Campus is the current working direction for a three-person, 24-hour community hackathon project. It focuses on wheelchair accessibility information around a single campus, initially proposed as IIUM.

**Pitch:** Help students check campus accessibility conditions before visiting, using facility-level evidence, recent community reports, and a review-and-resolution workflow.

Read this file before planning or implementing features. It records the discussion so teammates and future agents can continue without reconstructing the chat. The user's latest instructions and any applicable `AGENTS.md` take precedence.

## Current status and decisions

- The team has three members and a 24-hour build window.
- The chosen working track is Persons with Disabilities (PWD), narrowed to wheelchair access.
- Akses Campus and IIUM are working project name and pilot location, respectively; branding and pilot boundaries can change.
- No application has been implemented yet. At the time of this onboarding, the workspace contained only `.git` and an empty `.gitignore`.
- No framework, database, map provider, hosting service, API credentials, or team member assignments have been confirmed.
- The MVP, role split, and schedule below are recommendations from the planning discussion, not completed work.
- Campus data coverage, access to intended users, and the current state of IIUM's existing accessibility map remain unverified.

## Problem and intended users

A wheelchair user planning a campus visit needs to know whether a destination meets their requirements and whether the information still reflects current conditions.

Example question: **“Where can I study nearby with a step-free entrance and an accessible toilet?”**

Primary users are students who use wheelchairs. Contributors may include other students and campus volunteers. A reviewer role can represent campus staff or a project moderator in the prototype; no actual university partnership or integration is established.

Focus on information and reporting. The application cannot remove physical barriers or guarantee that a visit will be possible.

## Judging rubric

| Category | Weight | What to demonstrate |
| --- | --- | --- |
| Problem Statement & Impact | 15% | A specific community need, supported by user feedback where possible |
| UI/UX & Accessibility | 20% | Intuitive navigation and an accessible end-to-end experience |
| Innovation & Technology Integration | 20% | Useful integration of modern technology such as APIs, cloud services, or AI |
| Technical Execution & Code Quality | 20% | A stable, functional prototype with understandable code |
| Ethical Standards & Value Alignment | 5% | Privacy, safety, respectful treatment, and alignment with IIUM values |
| Presentation & Live Pitching | 20% | A clear story, working live demo, and credible Q&A |

UI/UX, execution, and pitching together represent 60%. Prioritize a polished working flow. The rubric lists AI, APIs, and cloud services as examples; it does not require all three.

## MVP scope

Build one campus area with approximately 10–15 seeded locations, such as libraries, study spaces, cafés, and campus buildings.

1. **Browse:** Show locations on a map and in an accessible list.
2. **Filter:** Support step-free entrance, accessible toilet, and designated parking.
3. **Inspect:** Show specific facility observations, photos when available, information source, and last checked date.
4. **Report:** Let a contributor submit a temporary barrier or outdated-information report.
5. **Review and resolve:** Let a reviewer confirm, reject, or resolve a report, with visible status history.

The reporting workflow is the proposed differentiator and main demo moment. If time becomes tight, simplify map interactions and visual extras before removing the complete report lifecycle.

### Explicitly outside the initial MVP

- Accessible route planning, turn-by-turn navigation, or indoor positioning.
- Volunteer dispatch, emergency assistance, appointments, or job listings.
- City-wide coverage or a complete solution for every disability group.
- Automatic accessibility certification from photos or AI.
- University systems integration, unless access is actually obtained.
- Complex reputation systems, gamification, or social networking.

### Optional stretch feature

Natural-language search can translate “Find somewhere to study with a step-free entrance and an accessible toilet” into the existing filters.

Only add this after the core flow works. Display the interpreted filters so users can correct them. Search results must come from stored records; AI must not invent places, facilities, verification, or safety claims. Keep manual filters usable if the AI service fails.

## Core demo and acceptance criteria

**Demo story:** A student finds a study location, checks its evidence, and sees a newly submitted report about a blocked ramp. A reviewer confirms the report and later marks it resolved.

The MVP is demo-ready when:

- A user can find a location through the list and filters without relying on the map.
- Place details distinguish **yes**, **no**, and **unknown** for each facility.
- Known observations show their source and observation/check date; unknown dates remain unknown.
- A submitted report persists after refresh and appears on the relevant location.
- New reports are visibly unverified and do not silently overwrite established facility information.
- Reviewer actions update the report status and preserve the earlier history.
- Reviewer actions are restricted to the reviewer role, rather than merely hidden in the UI.
- The core flow works with a keyboard and has readable labels, contrast, and focus indicators.
- Loading, empty results, failed submissions, and unavailable external services have understandable states.
- Demo data is clearly identified, and the team has rehearsed the full flow on the deployed build.

## Suggested data model

Adapt this to the chosen stack; it is a design starting point, not an existing schema.

| Entity | Suggested fields |
| --- | --- |
| Place | ID, name, category, campus area, coordinates, description, demo-data flag |
| Facility observation | Place ID, facility type, yes/no/unknown value, observation date, source, evidence reference, verification status |
| Barrier report | ID, place ID, barrier type, description, optional photo, observed time, submitted time, status |
| Report action | Report ID, previous/new status, reviewer reference, timestamp, explanation |

Suggested report states: `unverified -> confirmed -> resolved`, with `unverified -> rejected` for invalid reports. If a contributor can say the barrier has cleared, treat that as information for review rather than granting reviewer authority.

Keep permanent facility observations separate from temporary reports. A blocked ramp is a current warning; it does not mean the building never had a ramp.

## Accessibility, privacy, and data integrity

- Use semantic controls, explicit form labels, keyboard support, meaningful alt text, and visible focus.
- Provide text labels alongside status colors and map markers.
- Do not describe a location as universally accessible based on one overall score. Present specific facilities so people can decide for themselves.
- Do not require users to disclose a disability, medical history, or exact live location.
- Request location permission only for an optional nearby feature; browsing must work without it.
- Avoid identifiable faces and personal information in evidence photos. Validate uploads if photo submission is implemented.
- Distinguish contributor reports from reviewer-confirmed information. Verification means someone reviewed evidence; it is not a guarantee or formal accessibility certification.
- Use fictional or clearly labelled sample data unless real campus observations have been checked. Do not invent photos, timestamps, testimonials, or university endorsements.
- A report is submitted to this prototype. Do not imply that campus authorities have received it without a real integration.
- Express IIUM value alignment through dignity, truthful information, responsible handling of data, and mutual assistance.

## Related work and evidence

The links below were researched during planning. Product capabilities can change. The comparison does not establish that other systems lack freshness indicators or reporting features.

| Work | Relevant capabilities or findings | Lesson for this project |
| --- | --- | --- |
| [Wheelmap](https://news.wheelmap.org/en/) | OpenStreetMap-based crowdsourced wheelchair accessibility map, traffic-light ratings, toilet information, and photos | Mapping and community ratings are established ideas |
| [AccessNow](https://accessnow.com/blog/whats-new-in-the-accessnow-app/) | Accessibility discovery, ratings, facility features, photos, and lightweight contributions; linked update dated December 2025 | Feature-level information and photo contributions alone are insufficient differentiation |
| [Google Maps Accessible Places](https://blog.google/products-and-platforms/products/maps/wheelchair-accessible-places-google-maps/) | Official 2020 announcement describes entrance, seating, restroom, and parking accessibility information | Prepare a concrete answer to “Why not Google Maps?”; this historical announcement does not prove current local coverage |
| [AccessAble university guides](https://www.accessable.co.uk/inspire-me/heading-to-uni) | Detailed university access guides covering learning spaces, accommodation, parking, and toilets | Campus guides already exist; useful facility detail matters |
| [Project Sidewalk](https://makeabilitylab.cs.washington.edu/project/sidewalk/) | Research on collecting sidewalk accessibility information using crowdsourcing, imagery, and computer vision | Contributor guidance and data quality are substantive technical problems |
| [IIUM accessibility initiative, 2023](https://news.iium.edu.my/enhancing-iium-accessibility-empowering-students-of-all-abilities/) | Landscape Architecture and the Disability Service Unit collaborated on accessibility improvements; students prepared a campus accessibility map described as in progress at the time | Do not claim to create IIUM's first accessibility map; investigate the current initiative and potential complementarity |
| [UiTM wheelchair accessibility mapping project, 2024](https://ir.uitm.edu.my/id/eprint/101768/) | Unpublished student project focused on a mobile accessibility map for UiTM Seri Iskandar | A Malaysian campus map is also an existing project direction; the abstract does not establish outcomes |
| [Saha et al., Project Sidewalk, CHI 2019](https://makeabilitylab.cs.washington.edu/media/publications/Saha_ProjectSidewalkAWebBasedCrowdsourcingToolForCollectingSidewalkAccessibilityDataAtScale_CHI2019.pdf) | Deployment research identifies concerns around reliability, maintenance, and whether labels reflect users' needs | Show evidence, dates, review state, and clear definitions |
| [Chan et al., Physical accessibility in Malaysian higher educational institutions](https://journals.sagepub.com/doi/10.1177/00208728221094417) | Abstract reports a survey of 52 students and interviews with 14, partial dissatisfaction with facilities, and differing perspectives across disability groups; online 2022, issue 2023 | Supports investigating the local problem, not claiming that an app fixes physical infrastructure; only the abstract was reviewed |

### Defensible innovation claim

“We are prototyping a campus-focused workflow for checking accessibility evidence and keeping temporary barrier reports visible, reviewed, and resolved.”

This is a proposed project angle to validate, not a proven market gap. Avoid claims such as “the first accessibility map,” “competitors have no reporting,” or “AI guarantees accessibility.”

## Suggested responsibilities and schedule

Assign actual names once the team agrees. Balance tasks against the team's strengths.

| Owner | Main responsibility |
| --- | --- |
| Teammate 1 | Accessible UI, place details, list, and filters |
| Teammate 2 | Data model, persistence, report lifecycle, reviewer authorization, and deployment |
| Teammate 3 | Map integration, seed data/evidence, user validation, and pitch preparation |

Suggested 24-hour allocation:

- **Hours 0–2:** Validate the problem, check the existing IIUM map, agree scope and stack, sketch the demo, and define shared data/API contracts.
- **Hours 2–6:** Establish the application, seed data, initial deployment, and a working place list/details flow.
- **Hours 6–14:** Build filters, map, report submission, reviewer actions, and persistence. Integrate continuously.
- **Hours 14–18:** Complete evidence/status presentation, accessibility improvements, and error handling. Add stretch work only if the MVP is stable.
- **Hours 18–24:** Freeze features, verify the deployed demo, fix material issues, prepare slides, and rehearse Q&A.

## Engineering and future-agent guidance

1. Inspect the current repository and applicable `AGENTS.md` before editing. This file describes the initial state and may become outdated.
2. Check the latest user direction. Do not infer that optional features, a particular stack, or external integrations have been approved or implemented.
3. If the stack is still undecided, propose a small architecture the team can maintain and resolve the choice before creating incompatible foundations.
4. Preserve teammates' changes. Agree file ownership when work overlaps and keep shared data contracts consistent.
5. Build the smallest working vertical flow first: stored place -> list -> details -> persistent report -> reviewer action.
6. Keep secrets out of source control and browser bundles. Document environment variable names without secret values.
7. Validate report input and authorization on the trusted backend, not only in client UI controls.
8. Verify meaningful behavior: filtering unknown facilities, persistent reports, allowed status transitions, reviewer access restrictions, and the main keyboard flow.
9. Use the chosen framework's standard build/lint checks. Document actual commands once tooling exists; do not claim checks passed unless run.
10. Record setup, seed/reset procedure, deployment details, and known limitations in the repository as implementation progresses.
11. Keep this onboarding accurate as decisions change. Clearly separate completed work, remaining work, and future ideas.
12. Do not contact users or university representatives, publish externally, or claim institutional approval without the team's authorization. Preparing interview questions and pitch materials is appropriate.

## Next actions

- Confirm team skills, pilot area, and technology stack.
- Check the current IIUM accessibility map and reporting process.
- Seek feedback from a wheelchair user or relevant campus representative through a team-authorized approach.
- Agree the three facility definitions and collect a small, honestly labelled dataset.
- Assign owners and define the place/report data contract.
- Implement and deploy the first end-to-end flow before adding optional technology.

## Pitch and Q&A preparation

Lead with one student's decision, demonstrate the complete workflow, and explain what was actually built.

Prepare answers to:

- **Why not Google Maps or AccessNow?** Show the campus-specific evidence and reporting workflow. Acknowledge existing tools and avoid unverified claims about their limitations.
- **How do you know information is correct?** Explain sources, observation dates, unknown values, and reviewer status, including the prototype's limits.
- **Who maintains it after the hackathon?** Propose campus stewardship and recurring checks; do not present a proposed partner as committed.
- **What is the AI doing?** If implemented, it only translates search intent into visible filters over stored data.
- **What did you validate?** Report actual interviews, observations, and tests. If none occurred, say so and explain the next validation step.
